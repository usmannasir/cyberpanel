/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2015  LiteSpeed Technologies, Inc.                 *
*                                                                            *
*    This program is free software: you can redistribute it and/or modify    *
*    it under the terms of the GNU General Public License as published by    *
*    the Free Software Foundation, either version 3 of the License, or       *
*    (at your option) any later version.                                     *
*                                                                            *
*    This program is distributed in the hope that it will be useful,         *
*    but WITHOUT ANY WARRANTY; without even the implied warranty of          *
*    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the            *
*    GNU General Public License for more details.                            *
*                                                                            *
*    You should have received a copy of the GNU General Public License       *
*    along with this program. If not, see http://www.gnu.org/licenses/.      *
*****************************************************************************/
#include "httpextconnector.h"
#include <http/handlerfactory.h>
#include <http/handlertype.h>
#include <http/httpcgitool.h>
#include <http/httpdefs.h>
#include <http/httphandler.h>
#include <http/httpreq.h>
#include <http/httpresourcemanager.h>
#include <http/httpserverconfig.h>
#include <http/httpsession.h>
#include <http/httpstatuscode.h>
#include <http/stderrlogger.h>
#include <log4cxx/logger.h>
#include <util/gzipbuf.h>
#include <util/vmembuf.h>

#include <extensions/httpextprocessor.h>
#include <extensions/loadbalancer.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/socket.h>


HttpExtConnector::HttpExtConnector()
    : m_pSession(NULL)
    , m_pProcessor(NULL)
    , m_pWorker(NULL)
    , m_iState(HEC_BEGIN_REQUEST)
    , m_iRespState(0)
    , m_iReqBodySent(0)
    , m_iRespBodyLen(0)
    , m_iRespBodySent(0)
{
}


HttpExtConnector::~HttpExtConnector()
{
}


int HttpExtConnector::cleanUp(HttpSession *pSession)
{
    LS_DBG_M(this, "HttpExtConnector::cleanUp() ...");
    //if ( !(getState() & (HEC_ABORT_REQUEST|HEC_ERROR|HEC_COMPLETE)) )
    if (!(getState() & (HEC_COMPLETE)))
    {
        m_iState &= ~HEC_FWD_RESP_BODY;
        abortReq();
        if (getProcessor())
            getProcessor()->finishRecvBuf();
        releaseProcessor();
    }
    resetConnector();
    HandlerFactory::recycle(this);
    return 0;
}


int HttpExtConnector::releaseProcessor()
{
    LS_DBG_M(this, "Release ExtProcessor!");
    if (m_pProcessor)
    {
        HttpExtProcessor *pProcessor = m_pProcessor;
        m_pProcessor = NULL;
        pProcessor->cleanUp();
    }
    else
    {
        if (next() && getWorker())
        {
            getWorker()->removeReq(this);
            getHttpSession()->resumeEventNotify();
        }

    }
    return 0;
}


void HttpExtConnector::resetConnector()
{
    memset(&m_iState, 0, (char *)(&m_iRespBodySent + 1) - (char *)&m_iState);
    m_respHeaderBuf.clear();
}


int HttpExtConnector::parseHeader(const char *&pBuf, int &len, int proxy)
{
    int ret;
    int empty;
    size_t bufLen;
    const char *pWBuf ;
    empty = m_respHeaderBuf.empty();
    //empty = 0;
    if (empty)
    {
        pWBuf = pBuf;
        bufLen = len;
    }
    else
    {
        if (m_respHeaderBuf.append(pBuf, len) < 0)
            return LS_FAIL;
        bufLen = m_respHeaderBuf.size();
        pWBuf = m_respHeaderBuf.begin();
    }
    if ((proxy) && (m_iRespHeaderSize == 0))
    {
        m_iRespState |= HEC_RESP_PROXY;
        if (bufLen >= 7)
        {
            if (memcmp(pWBuf, "HTTP/1.", 7) != 0)
                return -2;
        }
    }
    ret = HttpCgiTool::parseRespHeader(this, pWBuf, bufLen, m_iRespState);
    if (ret > 0)
    {
        m_iRespHeaderSize += ret;
        if (!empty)
        {
            m_respHeaderBuf.pop_front(ret);
            pBuf = m_respHeaderBuf.begin();
            len = m_respHeaderBuf.size();
        }
        else
        {
            pBuf += ret ;
            len -= ret;
        }
    }
    else if (ret < 0)
    {
        errResponse(SC_500, NULL);
        return LS_FAIL;
    }
    if (m_iRespState & 0xff)
        return respHeaderDone();
    else
    {
        if (m_iRespHeaderSize >
            HttpServerConfig::getInstance().getMaxDynRespHeaderLen())
        {
            LS_WARN(getLogger(), "The size of dynamic response header: %d is"
                    " over the limit.",  m_iRespHeaderSize);
            //abortReq(5);
            abortReq();
            errResponse(SC_500, NULL);
            return LS_FAIL;
        }
        if (empty && len > 0)
            ret = m_respHeaderBuf.append(pBuf, len);
    }

    return ret;
}


int  HttpExtConnector::respHeaderDone()
{
    int ret = m_pSession->respHeaderDone();
    if (m_iRespState & HEC_RESP_AUTHORIZED)
        ret = 1;
    if (ret == 1)
        m_iState |= HEC_REDIRECT;
    else if (ret == 0)
    {
        if ((m_iRespState & (HEC_RESP_NPH | HEC_RESP_NPH2)) ==
            (HEC_RESP_NPH | HEC_RESP_NPH2))
            m_iRespState |= HEC_RESP_NOBUFFER;
    }
    return ret;
}


int HttpExtConnector::processRespData(const char *pBuf, int len)
{

    if ((getState() & (HEC_ABORT_REQUEST | HEC_ERROR | HEC_COMPLETE |
                       HEC_REDIRECT)))
        return len;
    if (!(m_iRespState & 0xff))
    {
        int ret = parseHeader(pBuf, len);
        if ((ret) || !(m_iRespState & 0xff))
            return ret;
    }
    if (len > 0)
        return processRespBodyData(pBuf, len);
    else
        return 0;
}


char *HttpExtConnector::getRespBuf(size_t &len)
{
    if ((m_iRespState & 0xff) && m_pSession->getRespCache()
        && m_pSession->isHookDisabled(LSI_HKPT_RECV_RESP_BODY))
    {
        if (!m_pSession->getGzipBuf())
            return m_pSession->getRespCache()->getWriteBuffer(len);
    }

    len = GLOBAL_BUF_SIZE;
    return HttpResourceManager::getGlobalBuf();
}


int HttpExtConnector::flushResp()
{
    if (!(m_iRespState & 0xff))
        return 0;
    //return m_pSession->flushDynBody(m_iRespState & HEC_RESP_NOBUFFER);
    int finished = m_iState & (HEC_ABORT_REQUEST | HEC_ERROR | HEC_COMPLETE);
    int ret = m_pSession->flush();
    if ((ret == 0) && (!finished) && m_pProcessor)
        m_pProcessor->continueRead();
    return ret;
}


int HttpExtConnector::processRespBodyData(const char *pBuf, int len)
{
    LS_DBG_M(this, "HttpExtConnector::processRespBodyData(%d)", len);
    int ret = m_pSession->appendDynBody(pBuf, len);
    if (ret == -1)
        errResponse(SC_500, NULL);
    else if (m_pSession->shouldSuspendReadingResp())
        m_pProcessor->suspendRead();

    //        return checkRespSize();
    return ret;
}


int HttpExtConnector::extInputReady()
{
    return 0;

}


void HttpExtConnector::abortReq()
{
    if (!(getState() & HEC_COMPLETE))
    {
        LS_DBG_M(this, "Abort request... ");
        m_iState |= HEC_ABORT_REQUEST;
        if (m_pProcessor)
            m_pProcessor->abort();
    }
}


int HttpExtConnector::extOutputReady()
{
    int ret = 0;
    if (getState() == HEC_BEGIN_REQUEST)
    {
        ret = m_pProcessor->begin();
        if (ret > 0)
            extProcessorReady();
        else
            return LS_FAIL;
    }
    if (!(getState() & (HEC_FWD_REQ_HEADER | HEC_FWD_REQ_BODY)))
    {
        if (m_pProcessor)
            m_pProcessor->suspendWrite();
    }
    else
    {
        if ((getState() & HEC_FWD_REQ_HEADER))
            return sendReqHeader();
        else if ((getState() & HEC_FWD_REQ_BODY))
            ret = sendReqBody();
    }
    return ret;
}


void HttpExtConnector::extProcessorReady()
{
    setState(HEC_FWD_REQ_HEADER);
}


int HttpExtConnector::processErrData(const char *pBuf, int len)
{
    assert(pBuf);
    assert(len >= 0);
    if (!StdErrLogger::getInstance().isEnabled())
        return 0;
    char *pTemp = (char *)malloc(len + 1);
    if (pTemp)
    {
        memmove(pTemp, pBuf, len);
        *(pTemp + len) = 0;
        LS_NOTICE(this, "[STDERR] %s", pTemp);
        free(pTemp);
    }
    return 0;

}


int HttpExtConnector::endResponse(int endCode, int protocolStatus)
{
    LS_DBG_L(this, "[EXT] EndResponse( endCode=%d, protocolStatus=%d )",
             endCode, protocolStatus);
    int ret = 0;
    if (m_iState & HEC_COMPLETE)
        return 0;
    if (!(m_iRespState & HttpReq::HEADER_OK)
        && !(m_iState & HEC_ABORT_REQUEST))
    {
        m_iRespState |= HttpReq::HEADER_OK;
        LS_NOTICE(this, "Premature end of response header.");
        return errResponse(SC_500, NULL);
    }
    m_iState |= HEC_COMPLETE;
    if (!(m_iState & (HEC_ABORT_REQUEST | HEC_ERROR)) && !endCode
        && getWorker())
        getWorker()->getReqStats()->incReqProcessed();
    releaseProcessor();
    if (m_iRespState & HEC_RESP_AUTHORIZED)
    {
        m_pSession->authorized();
        return 0;
    }
    if ((m_iRespState & 0xff) &&
        !(m_iState & (HEC_ERROR | HEC_REDIRECT)))
        return m_pSession->endResponse(!(m_iState & HEC_ABORT_REQUEST));
    else
        m_pSession->continueWrite();
    return ret;
}


int HttpExtConnector::onWrite(HttpSession *pSession)
{
    if ((m_iState & (HEC_COMPLETE | HEC_ERROR)) == 0)
    {
        LS_DBG_M(this, "Response buffer is empty, suspend HttpSession write!");
        //m_pHttpSession->resetRespBodyBuf();
        getHttpSession()->suspendWrite();
        m_pProcessor->continueRead();
        return 1;
    }
    else
    {
        LS_DBG_M(this, "ReqBody: %lld, RespBody: %lld, HEC_COMPLETE!",
                 (long long)m_iReqBodySent,
                 (long long)m_pSession->getDynBodySent());
        return 0;
    }
}


int HttpExtConnector::process(HttpSession *pSession,
                              const HttpHandler *pHandler)
{
    assert(pSession);
    //resetConnector();
    assert(pHandler);
    setHttpSession(pSession);
    setAttempts(0);
    m_iRespHeaderSize = 0;
    if (pHandler->getType() == HandlerType::HT_LOADBALANCER)
    {
        LoadBalancer *pLB = (LoadBalancer *)pHandler;
        setLB(pLB);
        ExtWorker *pWorker = pLB->selectWorker(pSession, this);
        setWorker(pWorker);
        LS_DBG_L(this, "Assign new request to ExtProcessor [%s]!",
                 pWorker ? pWorker->getName() : "unavailable");
    }
    else
    {
        setLB(NULL);
        setWorker((ExtWorker *)pHandler);
    }
    m_iState = HEC_BEGIN_REQUEST;

    if (getWorker() == NULL)
    {
        LS_ERROR(this, "External processor is not available!");
        return SC_500; //Fast cgi App Not found
    }
    int ret = m_pWorker->processRequest(this);
    if (ret > 1)
    {
        LS_DBG_L(this, "Can't add new request to ExtProcessor [%s]!",
                 m_pWorker->getName());
    }
    else
    {
        if (ret == 1)
            ret = 0;
        m_iRespState |= (m_pWorker->getConfigPointer()->getBuffering() &
                         (HEC_RESP_NPH | HEC_RESP_NOBUFFER));
        if (m_pWorker->getRole() == EXTAPP_AUTHORIZER)
            m_iRespState |= HEC_RESP_AUTHORIZER;
    }
    return ret;
}


int  HttpExtConnector::tryRecover()
{
    LS_DBG_L(this, "HttpExtConnector::tryRecover()...");
    if (isRecoverable())
    {
        int attempts = incAttempts();
        int maxAttempts;
        LoadBalancer *pLB = getLB();
        if (pLB)
            maxAttempts = pLB->getWorkerCount() * 3;
        else
            maxAttempts = 3;
        resetConnector();
        if (attempts < maxAttempts)
        {
            LS_DBG_L(this, "Trying to recover from connection problem, attempt: #%d!",
                     attempts);
            if (pLB && (attempts % 3) == 0)
            {
                ExtWorker *pWorker = pLB->selectWorker(m_pSession, this);
                if (pWorker)
                {
                    LS_DBG_L(this, "[LB] retry worker: [%s]",
                             pWorker->getName());
                }
                else
                    LS_DBG_L(this, "[LB] Backup worker is unavailable.");
                setWorker(pWorker);
                LS_DBG_L(this, "Trying to recover from connection problem, attempt: #%d!",
                         attempts);
            }
            else if (((attempts % 3) >= 2) && !m_pWorker->isReady())
            {
                LS_DBG_L(this, "Try to restart external application [%s] at [%s]...",
                         m_pWorker->getName(), m_pWorker->getURL());
                m_pWorker->start();
            }
            if (m_pWorker)
            {
                int ret = m_pWorker->processRequest(this, 1);
                if ((ret == 0) || (ret == 1))
                    return 0;
            }
        }
        //if ( m_pWorker )
        //    m_pWorker->tryRestart();
        errResponse(SC_503, NULL);
    }
    else
        endResponse(0, 0);
    return LS_FAIL;
}


int HttpExtConnector::sendReqHeader()
{
    int ret = getProcessor()->sendReqHeader();
    if (ret == -1)
        return LS_FAIL;
    ret = reqHeaderDone();
    return ret;
}


int HttpExtConnector::reqHeaderDone()
{
    LS_DBG_M(this, "Request header is done");
    HttpReq *pReq = getHttpSession()->getReq();
    getProcessor()->beginReqBody();
    getProcessor()->continueRead();
    if (!(m_iRespState & HEC_RESP_AUTHORIZER) && (pReq->getBodyBuf()))
    {
        pReq->getBodyBuf()->rewindReadBuf();
        setState(HEC_REQ_HEADER_DONE);
        return sendReqBody();
    }
    else
    {
        setState(HEC_FWD_RESP_HEADER);
        return reqBodyDone();
    }
}


int HttpExtConnector::reqBodyDone()
{
    LS_DBG_M(this, "Request body done!");
    //getProcessor()->suspendWrite();
    return getProcessor()->endOfReqBody();
}


int HttpExtConnector::sendReqBody()
{
    HttpReq *pReq = getHttpSession()->getReq();
    VMemBuf *pVMemBuf = pReq->getBodyBuf();
    size_t size;
    char *pBuf;
    int count = 0;
    while (((pBuf = pVMemBuf->getReadBuffer(size)) != NULL) && (size > 0))
    {
        int written = getProcessor()->sendReqBody(pBuf, size);
        if (written > 0)
        {
            pVMemBuf->readUsed(written);
            m_iReqBodySent += written;
        }
        LS_DBG_M(this,
                 "Processor sent request body %d bytes, total sent: %lld\n",
                 written, (long long)m_iReqBodySent);
        if ((written != (int)size) || (++count == 2))
        {
            if (written != -1)
                getProcessor()->continueWrite();
            //THINKING: set request aborted flag if return -1?
            return written;
        }
    }
    if (pReq->getBodyRemain() <= 0)
    {
        setState(getState() & ~HEC_FWD_REQ_BODY);
        reqBodyDone();
    }
    else
    {
        getProcessor()->suspendWrite();
        getHttpSession()->continueRead();
        LS_DBG_M(this, "All received request body sent, suspend write\n");

    }
    return 0;
}


int HttpExtConnector::onRead(HttpSession *pSession)
{
    if ((getState() & HEC_ERROR) || !getProcessor())
        return LS_FAIL;
    if ((getState() & (HEC_FWD_REQ_BODY | HEC_COMPLETE)) == HEC_FWD_REQ_BODY)
        return sendReqBody();
    else
        getHttpSession()->suspendRead();
    return 0;
}


bool HttpExtConnector::isRecoverable()
{
    if (m_iState & HEC_FWD_RESP_BODY)
        return false;
    //if ( m_iReqBodySent == 0 )
    //    return true;
    //HttpReq * pReq = getHttpSession()->getReq();
    return true;
}


int HttpExtConnector::errResponse(int code, const char *pErr)
{
    m_iState |= HEC_ERROR;
    if (getHttpSession())
    {
        if (!(m_iState & HEC_FWD_RESP_BODY))
        {
            getHttpSession()->getReq()->setStatusCode(code);
            getHttpSession()->changeHandler();
        }
        getHttpSession()->continueWrite();
    }
    return LS_FAIL;
}


void HttpExtConnector::onTimer()
{
//    if ( m_pProcessor )
//        m_pProcessor->onProcessorTimer();
}


void HttpExtConnector::suspend()
{
    getHttpSession()->suspendEventNotify();
}


void HttpExtConnector::extProcessorError(int errCode)
{
    if (!(getState() & (HEC_ABORT_REQUEST | HEC_ERROR | HEC_COMPLETE)))
    {
        const char *pName;
        if (m_pWorker)
            pName = m_pWorker->getURL();
        else
            pName = "";
        LS_ERROR(this, "[%s]: %s", pName, strerror(errCode));
        errResponse(SC_503,
                    "<html><title>Not Avaiable</title>"
                    "<body><h1>Failed to communicate with external application!</h1>"
                    "</body></html>");
    }
}


const char   *HttpExtConnector::getLogId()
{
    if (m_pSession)
        return m_pSession->getLogId();
    else
        return "idle";
}


LOG4CXX_NS::Logger *HttpExtConnector::getLogger() const
{
    if (m_pSession)
        return m_pSession->getLogger();
    else
        return NULL;

}


void HttpExtConnector::dump()
{
    LS_INFO(this, "HttpExtConnector state: %d, request body sent: %lld, "
            "response body size: %lld, response body sent:%lld, "
            "left in buffer: %lld, attempts: %d.",
            m_iState, (long long)m_iReqBodySent, 
            (long long)m_pSession->getResp()->getContentLen(),
            (long long)m_pSession->getDynBodySent(),
            (long long)((m_pSession->getRespCache()) 
                         ? m_pSession->getRespCache()->writeBufSize() 
                         : 0), 
            getAttempts());
    if (m_pProcessor)
        m_pProcessor->dump();
    else
        LS_INFO(this, "External processor is not available.");
}


int HttpExtConnector::dumpAborted()
{
    return (m_pProcessor != NULL);
}


int HttpExtConnector::isAlive()
{
    return getHttpSession()->isAlive();
}


void HttpExtConnector::setHttpError(int error)
{
    errResponse(error, NULL);
}




