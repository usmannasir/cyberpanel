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
#include "cgidconn.h"

#include "cgidworker.h"
#include "cgidconfig.h"
#include "suexec.h"

#include <http/httpcgitool.h>
#include <http/httpextconnector.h>
#include <http/httpresourcemanager.h>
#include <http/httpsession.h>
#include <http/serverprocessconfig.h>
#include <log4cxx/logger.h>

#include <sys/socket.h>
#include <openssl/md5.h>

CgidConn::CgidConn()
{
}


CgidConn::~CgidConn()
{
}


ExtRequest *CgidConn::getReq() const
{
    return getConnector();
}


void CgidConn::init(int fd, Multiplexer *pMplx)
{
    EdStream::init(fd, pMplx, POLLIN | POLLOUT | POLLHUP | POLLERR);
}


//interface defined by EdStream
int CgidConn::doRead()
{
    if (!getConnector())
        return LS_FAIL;

    LS_DBG_M(this, "CgidConn::onRead()");
    int resultNeedParseMode =
        getConnector()->getHttpSession()->getReq()->getContextState(
            EXEC_CMD_PARSE_RES);
    int len = 0;
    int ret = 0;

    do
    {
        len = ret = read(HttpResourceManager::getGlobalBuf(), GLOBAL_BUF_SIZE);
        if (ret > 0)
        {
            LS_DBG_M(this, "Process STDOUT %d bytes", len);
//            printf( ">>read %d bytes from CGI\n", len );
//            printf( "%.*s", len, HttpResourceManager::getGlobalBuf() );
            if (resultNeedParseMode)
                getConnector()->getHttpSession()->getExtCmdBuf().append(
                    HttpResourceManager::getGlobalBuf(), len);
            else
            {
                ret = getConnector()->processRespData(
                          HttpResourceManager::getGlobalBuf(), len);
                if (ret == -1)
                    break;
            }
        }
        else
        {
            if (ret)
            {
                endResp();
                return 0;
            }
            break;
        }
    }
    while (len == GLOBAL_BUF_SIZE);
    if ((ret != -1) && (getConnector()) && !resultNeedParseMode)
        getConnector()->flushResp();
    return ret;
}


int CgidConn::readResp(char *pBuf, int size)
{
    int len = read(pBuf, size);
    if (len == -1)
        endResp();
    return len;

}

int CgidConn::endResp()
{
    if (getConnector()->getHttpSession()->getReq()->getContextState(
            EXEC_CMD_PARSE_RES))
        getConnector()->getHttpSession()->extCmdDone();
    else
        getConnector()->endResponse(0, 0);
    return 0;
}

int CgidConn::doWrite()
{
    if (!getConnector())
        return LS_FAIL;
    LS_DBG_M(this, "CgidConn::onWrite()");
    int ret = getConnector()->extOutputReady();
    if (!(getConnector()->getState() & HEC_FWD_REQ_BODY))
    {
        if (m_iTotalPending > 0)
            return flush();
        else
        {
            suspendWrite();
            ::shutdown(getfd(), SHUT_WR);
        }
    }
    return ret;
}


int CgidConn::doError(int error)
{
    if (!getConnector())
        return LS_FAIL;
    LS_DBG_M(this, "CgidConn::onError()");
    //getState() = HEC_COMPLETE;
    endResp();
    return LS_FAIL;
}


bool CgidConn::wantRead()
{
    return false;
}


bool CgidConn::wantWrite()
{
    return false;
}


//interface defined by HttpExtProcessor
void CgidConn::abort()
{
    setState(CLOSING);
    ::shutdown(getfd(), SHUT_RDWR);
}


void CgidConn::cleanUp()
{
    setConnector(NULL);
    setState(CLOSING);
    ::shutdown(getfd(), SHUT_RDWR);
//    close();
    recycle();
}


int CgidConn::begin()
{
    return 1;
}


int CgidConn::beginReqBody()
{
    return 1;
}


int CgidConn::endOfReqBody()
{
    if (m_iTotalPending)
    {
        int ret = flush();
        if (ret)
            return ret;
    }
    suspendWrite();
    ::shutdown(getfd(), SHUT_WR);
    return 0;
}


int  CgidConn::sendReqHeader()
{
    m_pPendingBuf = m_req.get();
    m_iTotalPending = m_req.size();
    return 1;
}


int CgidConn::sendReqBody(const char *pBuf, int size)
{
    int ret = 0;
    /**
     * If it is running a ext cmd by a module, should be SUSPENDED now,
     * but we still need to send out the pending data.
     */
    if (getConnector()->getHttpSession()->getFlag(HSF_SUSPENDED))
        size = 0;

    if (m_iTotalPending == 0)
    {
        if (size > 0)
            ret = write(pBuf, size);
    }
    else
    {
        IOVec iov;
        iov.append(m_pPendingBuf, m_iTotalPending);
        if (size > 0)
            iov.append(pBuf, size);
        ret = writev(iov);
        if (ret >= m_iTotalPending)
        {
            ret = ret - m_iTotalPending;
            m_iTotalPending = 0;
        }
        else if (ret > 0)
        {
            m_iTotalPending -= ret;
            m_pPendingBuf += ret;
            ret = 0;
        }
    }

    return ret;
}


int CgidConn::addRequest(ExtRequest *pReq)
{
    assert(pReq);
    setConnector((HttpExtConnector *)pReq);
    int ret;
    HttpReq *req = getConnector()->getHttpSession()->getReq();
    if (req->getContextState(EXEC_EXT_CMD))
        ret = buildSSIExecHeader(1);
    else if (req->getContextState(EXEC_CMD_PARSE_RES))
        ret = buildSSIExecHeader(0);
    else
        ret = buildReqHeader();
    if (ret)
    {
//        LS_DBG_L(this, "Request header can't fit into 8K buffer, "
//                 "can't forward request to servlet engine");
        ((HttpExtConnector *)pReq)->setProcessor(NULL);
        setConnector(NULL);
    }
    return ret;
}


int CgidConn::buildSSIExecHeader(int checkContext)
{
    static unsigned int s_id = 0;
    HttpSession *pSession = getConnector()->getHttpSession();
    HttpReq *pReq = pSession->getReq();
    const char *pReal;
    const AutoStr2 *psChroot = NULL;
    const char *pChroot = NULL;
    int ret = 0;
    uid_t uid = 0;
    gid_t gid = 0;
    pReal = pReq->getRealPath()->c_str();

    if (checkContext)
    {
        ret = pReq->getUGidChroot(&uid, &gid, &psChroot);//FIXME:
        if (ret)
            return ret;
//    LS_DBG_L(this, "UID: %d, GID: %d", pHeader->m_uid, pHeader->m_gid);
        if (psChroot)
        {
//        LS_DBG_L(this, "chroot: %s, real path: %s", pChroot->c_str(), pReal);
            pChroot = psChroot->c_str();
            ret = psChroot->len();
        }
        else
        {
            pChroot = NULL;
            ret = 0;
        }
    }
    char achBuf[4096];
    memccpy(achBuf, pReal, 0, 4096);
    char *argv[256];
    char **p;
    char *pDir ;
    SUExec::buildArgv(achBuf, &pDir, argv, 256);
    if (pDir)
        *(argv[0] - 1) = '/';
    else
        pDir = argv[0];

    int priority = ((CgidWorker *)getWorker())->getConfig().getPriority();

    m_req.buildReqHeader(uid, gid, priority,
                         ServerProcessConfig::getInstance().getUMask(),
                         pChroot, ret, pDir, strlen(pDir),
                         ((CgidWorker *)getWorker())->getConfig().getRLimits());
    p = &argv[1];
    while (*p)
    {
        m_req.appendArgv(*p, strlen(*p));
        ++p;
    }
    m_req.appendArgv(NULL, 0);

    HttpCgiTool::buildEnv(&m_req, pSession);

    m_req.finalize(s_id++, ((CgidWorker *)
                            getWorker())->getConfig().getSecret(),
                   LSCGID_TYPE_CGI);
    return 0;
}


int CgidConn::buildReqHeader()
{
    static unsigned int s_id = 0;
    HttpSession *pSession = getConnector()->getHttpSession();
    HttpReq *pReq = pSession->getReq();
    const char *pQueryString = pReq->getQueryString();
    const char *pQsEnd = pReq->getQueryString() + pReq->getQueryStringLen();
    const char *pReal;
    const AutoStr2 *psChroot;
    const AutoStr2 *realPath = pReq->getRealPath();
    const char *pChroot;
    int ret;
    uid_t uid;
    gid_t gid;
    pReal = realPath->c_str();
    ret = pReq->getUGidChroot(&uid, &gid, &psChroot);
    if (ret)
        return ret;
//    LS_DBG_L(this, "UID: %d, GID: %d", pHeader->m_uid, pHeader->m_gid);
    if (psChroot)
    {
//        LS_DBG_L(this, "chroot: %s, real path: %s", pChroot->c_str(), pReal);
        pChroot = psChroot->c_str();
        ret = psChroot->len();
    }
    else
    {
        pChroot = NULL;
        ret = 0;
    }
    int priority = ((CgidWorker *)getWorker())->getConfig().getPriority();

    m_req.buildReqHeader(uid, gid, priority,
                         ServerProcessConfig::getInstance().getUMask(),
                         pChroot, ret, pReal, pReq->getRealPath()->len(),
                         ((CgidWorker *)getWorker())->getConfig().getRLimits());
    if (pQueryString && (memchr(pQueryString, '=',
                                pQsEnd - pQueryString) == NULL))
    {
        char *pPlus;
        do
        {
            pPlus = (char *)memchr(pQueryString, '+', pQsEnd - pQueryString);
            if (pPlus != pQueryString)
            {
                int len;
                if (pPlus)
                    len = pPlus - pQueryString;
                else
                    len = pQsEnd - pQueryString;
                m_req.appendArgv(pQueryString, len);
            }
            if (pPlus)
                pQueryString = pPlus + 1;
        }
        while (pPlus);
    }
    m_req.appendArgv(NULL, 0);

    HttpCgiTool::buildEnv(&m_req, pSession);

    m_req.finalize(s_id++, ((CgidWorker *)
                            getWorker())->getConfig().getSecret(),
                   LSCGID_TYPE_CGI);
    return 0;
}


int CgidConn::removeRequest(ExtRequest *pReq)
{
    if (getConnector())
    {
        getConnector()->setProcessor(NULL);
        setConnector(NULL);
    }
    return 0;
}


void CgidConn::onTimer()
{
}


void CgidConn::dump()
{
}


int  CgidConn::flush()
{
    if (m_iTotalPending)
    {
        int ret = write(m_pPendingBuf, m_iTotalPending);

        if (ret > 0)
        {
            if (ret < m_iTotalPending)
            {
                m_pPendingBuf += ret;
                m_iTotalPending -= ret;
                return 1;
            }
            else
                m_iTotalPending = 0;
        }
        else
            return ret;
    }
    return 0;
}

