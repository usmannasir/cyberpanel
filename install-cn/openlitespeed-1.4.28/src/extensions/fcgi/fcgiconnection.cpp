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
#include "fcgiconnection.h"
#include "fcgiapp.h"
#include "fcginamevaluepair.h"
#include "fcgirecord.h"

#include <http/httpcgitool.h>
#include <http/httpextconnector.h>
#include <http/httpresourcemanager.h>
#include <http/httpstatuscode.h>
#include <log4cxx/logger.h>
#include <util/iovec.h>
#include <util/stringtool.h>

#include <assert.h>
#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <poll.h>
#include <unistd.h>

const char FcgiConnection::s_padding[8] = { 0, 0, 0, 0, 0, 0, 0, 0 };

FcgiConnection::FcgiConnection()
    : m_bufOS(this)
    , m_recSize(0)
    , m_iId(1)
    , m_iWantWrite(1)
    , m_iTotalPending(0)
    , m_iCurStreamHeader(0)
{
    memset(m_streamHeaders, 0, sizeof(m_streamHeaders));
}


FcgiConnection::~FcgiConnection()
{
}


void FcgiConnection::init(int fd, Multiplexer *pMplx)
{
    EdStream::init(fd, pMplx, POLLIN | POLLOUT | POLLHUP | POLLERR);
    m_bufOS.getBuf()->clear();
    m_recSize = 0;
    m_iRecStatus = 0;
}


bool FcgiConnection::isOutputBufEmpty()
{
    return m_bufOS.isEmpty();
}


// Return Value:
//      -1 error occured while sending the data,
//      > 0     bytes sent + cached

int FcgiConnection::sendRecord(const char *rec, int size)
{

    int ret = m_bufOS.cacheWrite(rec, size);
    return ret;
}


/**
  * @return -1 error, > 0 success.
  *
  */

int FcgiConnection::endOfStream(int streamType, int id)
{
    FCGI_Header rec;
    FcgiRecord::setRecordHeader(rec, streamType, id, 0);
    int ret = sendRecord((char *)&rec, sizeof(rec));
    return ret;
}


// Return Value:
//      -1 if error,
//      0  if still have data in the cache
//      other  packet is sent or cached
//
int FcgiConnection::sendStreamPacket(int streamType, int id,
                                     const char *pBuf, int size)
{
    assert(size <= FCGI_MAX_PACKET_SIZE);
    if (!m_bufOS.isEmpty())   //still have data in OutputBuf
        return 0;
    FCGI_Header rec;
    FcgiRecord::setRecordHeader(rec, streamType, id, size);
    IOVec iov;
    iov.append((char *)&rec, sizeof(rec));
    if (size > 0)
    {
        iov.append((char *)pBuf, size);
        if (rec.paddingLength > 0)
            iov.append(s_padding, rec.paddingLength);
    }
    int ret = m_bufOS.writev(iov);
    return ret;

}


/**
  * @param streamType the type of stream, FCGI_STDIN, FCGI_PARAM
  * @param id           the id of the request, start from 1
  * @param pBuf         the buffer contain the to be sent data
  * @param size         the size of data to be sent
  *
  * @return -1, if error;
  *         other, bytes sent or cached in the memory
  */

int FcgiConnection::writeStream(int streamType, int id,
                                const char *pBuf, int size)
{
    if (size < 0)
        return 0;
    if (!m_bufOS.isEmpty())   //still have data in OutputBuf
        return 0;
    int packetSize;
    int left = size;
    do
    {
        packetSize = left;
        if (packetSize > FCGI_MAX_PACKET_SIZE)
            packetSize = FCGI_MAX_PACKET_SIZE;
        int ret = sendStreamPacket(streamType, id, pBuf, packetSize);
        switch (ret)
        {
        case -1:
            return LS_FAIL;
        case 0:
            return size - left;
        default:
            left -= packetSize;
            pBuf += packetSize;
        }
    }
    while (left > 0);
    return size - left;
}


int FcgiConnection::doRead()
{
    LS_DBG_L(this, "FcgiConnection::doRead()");
    return processFcgiData();
}


/**
  * @return -1 if error occur
  *         0   if buffer is not empty
  *         1   if buffer is empty
  */

int FcgiConnection::flushOutBuf()
{
    if (m_bufOS.flush() == -1)
        return LS_FAIL;
    return m_bufOS.isEmpty();
}


int FcgiConnection::doWrite()
{
    LS_DBG_L(this, "FcgiConnection::doWrite()");
    int ret = flushOutBuf();
    if (ret <= 0)
        return ret;
    if (getConnector())
    {
        int state = getConnector()->getState();
        if ((!state) || (state & (HEC_FWD_REQ_HEADER | HEC_FWD_REQ_BODY)))
            return getConnector()->extOutputReady();
    }
    suspendWrite();
    return 0;
}


int FcgiConnection::doError(int err)
{
    LS_DBG_L(this, "FcgiConnection::doError()");
    if (getConnector())
    {
        int state = getConnector()->getState();
        if (!(state & (HEC_FWD_RESP_BODY | HEC_ABORT_REQUEST
                       | HEC_ERROR | HEC_COMPLETE)))
        {
            LS_DBG_L(this, "FCGI Peer closed connection, "
                     "try another connection!");
            connError(err);
            return 0;
        }
        if (!(state & HEC_COMPLETE))
            endOfRequest(SC_500, -1);
    }
    return 0;
}


int FcgiConnection::processEndOfRequestRecord(char *pBuf, int size)
{
    FCGI_EndRequestBody *endReqBody;
    if ((m_recSize == 0) && (size >= (int)sizeof(FCGI_EndRequestBody)))
        endReqBody = (FCGI_EndRequestBody *)pBuf;
    else
    {
        m_bufRec.append(pBuf, size);
        if (m_bufRec.size() >= (int)sizeof(FCGI_EndRequestBody))
        {
            endReqBody = (FCGI_EndRequestBody *)m_bufRec.begin();
            m_bufRec.clear();
        }
        else
            return 0;

    }
    int code = endReqBody->appStatusB3;
    code <<= 8;
    code |= endReqBody->appStatusB2;
    code <<= 8;
    code |= endReqBody->appStatusB1;
    code <<= 8;
    code |= endReqBody->appStatusB0;
    int status = endReqBody->protocolStatus;
    incReqProcessed();
    setInProcess(0);
    if (getState() == ABORT)
        setState(PROCESSING);
    return endOfRequest(code, status);
}


int FcgiConnection::buildFcgiRecHeader(char *pBuf, int size, int &len)
{
    len = sizeof(FCGI_Header) - m_recSize;
    if (len > size)
    {
        len = size;
        memmove((char *)&m_recCur + m_recSize, pBuf, len);
        m_recSize += len;
        return 1;
    }
    else
    {
        memmove((char *)&m_recCur + m_recSize, pBuf, len);
        if (LS_LOG_ENABLED(LOG4CXX_NS::Level::DBG_HIGH))
        {
            char achBuf[256];
            StringTool::hexEncode(
                (char *)&m_recCur, sizeof(FCGI_Header), achBuf);
            LS_DBG_H(this, "FCGI Header: %s", achBuf);
        }
        if (!FcgiRecord::testRecord(m_recCur))
        {
            //FIXME: error message: invalid FCGI Record
            return LS_FAIL;
        }
        m_recSize = 0;
        m_iContentLen = FcgiRecord::getContentLength(m_recCur);
        if (m_iContentLen)
            m_iRecStatus = REC_CONTENT;
        else
        {
            if (m_recCur.paddingLength)
                m_iRecStatus = REC_PADDING;
        }
        m_iRecId = FcgiRecord::getId(m_recCur);
        return 0;
    }
}


int FcgiConnection::processFcgiRecData(char *pBuf, int size, int &end)
{
    if (m_iRecId == 0)
    {
        //printf( "process management record!\n" );
        assert(m_recCur.type == FCGI_GET_VALUES_RESULT);
        return processManagementRec(pBuf, size);
    }
    if (m_iId == m_iRecId)
    {
        switch (m_recCur.type)
        {
        case FCGI_END_REQUEST:
            //printf( "process EndOfRequest\n" );
            end = 1;
            processEndOfRequestRecord(pBuf, size);
            break;
        case FCGI_STDOUT:
            //TEST: debug code
            //::write( 1, pBuf, size );
            processStdOut(pBuf, size);
            break;
        case FCGI_STDERR:
            processStdErr(pBuf, size);
            break;
        case FCGI_UNKNOWN_TYPE:
            break;
        }
    }
    return 0;
}


//int FcgiConnection::processFcgiDataNew()
//{
//    int len, ret = 0;
//    do
//    {
//        switch( m_iRecStatus )
//        {
//        case REC_HEADER:
//            break;
//        case REC_CONTENT:
//            break;
//        case REC_PADDING:
//            break;
//        }
//        if ( ret == -1 )
//        {
//            LS_DBG_L(this, "[FCGI] protocol error");
//            errno = EPROTO;
//            m_iState = CLOSING;
//            return LS_FAIL;
//        }
//    }while( ret > 0 ) ;
//    if (( m_pReq )&&( m_pReq->wantAbort() ))
//    {
//        reconnect();
//        // Most fast CGI will not recognize the FCGI_ABORT_REQUEST
//        // so we just reconnect instead of send abort request
//        //m_pReq->sendAbortReq();
//    }
//    return 0;
//}


#define FCGI_INPUT_BUFSIZE GLOBAL_BUF_SIZE
int FcgiConnection::processFcgiData()
{
    int len, ret = 0;
    int end = 0;
    do
    {
        len = read(HttpResourceManager::getGlobalBuf(),
                   FCGI_INPUT_BUFSIZE);
        LS_DBG_H(this, "Read %d bytes from Fast CGI.", len);
        if (!len)
            break;
        if (len == -1)
            return len;
        int used;
        char *pCur = HttpResourceManager::getGlobalBuf();
        int left = len;
        while (left > 0)
        {
            switch (m_iRecStatus)
            {
            case REC_HEADER:
                ret = buildFcgiRecHeader(pCur, left, used);
                break;
            case REC_CONTENT:
                used = m_iContentLen - m_recSize;
                if (used > left)
                {
                    used = left;
                    m_recSize += used;
                    ret = processFcgiRecData(pCur, used, end);
                }
                else
                {
                    ret = processFcgiRecData(pCur, used, end);
                    m_recSize = 0;
                    if (m_recCur.paddingLength)
                        m_iRecStatus = REC_PADDING;
                    else
                        m_iRecStatus = REC_HEADER;
                }
                break;
            case REC_PADDING:
                used = m_recCur.paddingLength - m_recSize;
                if (used > left)
                {
                    used = left;
                    m_recSize += used;
                }
                else
                {
                    m_iRecStatus = REC_HEADER;
                    m_recSize = 0;
                }
                break;
            }
            pCur += used;
            left -= used;
            if (ret == -1)
            {
                LS_DBG_L(this, "[FCGI] protocol error, Record Status=%d, "
                         "Record Size=%d, Content Length=%d",
                         m_iRecStatus, m_recSize, m_iContentLen);
                errno = EIO;
                return LS_FAIL;
            }
        }
    }
    while (len == FCGI_INPUT_BUFSIZE) ;
    if (getState() == ABORT)
    {
        //setState( ABORT );
        close();
        incReqProcessed();
        endOfRequest(0, FCGI_REQUEST_COMPLETE);
        // Most fast CGI will not recognize the FCGI_ABORT_REQUEST
        // so we just reconnect instead of send abort request
        //m_pReq->sendAbortReq();
    }
    else if (!end)
    {
        if (getConnector())
            getConnector()->flushResp();
    }
    return 0;
}


#define FCGI_MAX_CONNS  "FCGI_MAX_CONNS"
#define FCGI_MAX_REQS   "FCGI_MAX_REQS"
#define FCGI_MPXS_CONNS "FCGI_MPXS_CONNS"

int FcgiConnection::queryAppAttr()
{
    char achBuf[256];
    FCGI_Header *pHeader = (FCGI_Header *)achBuf;
    char *p = achBuf + sizeof(FCGI_Header);
    int size = sizeof(achBuf) - sizeof(FCGI_Header);
    int len = 0;
    int ret;
    len += (ret = FcgiNameValuePair::append(p, size, FCGI_MAX_CONNS, ""));
    p += ret;
    size -= ret;
    len += (ret = FcgiNameValuePair::append(p, size, FCGI_MAX_REQS, ""));
    p += ret;
    size -= ret;
    len += (ret = FcgiNameValuePair::append(p, size, FCGI_MPXS_CONNS, ""));
    p += ret;
    size -= ret;
    FcgiRecord::setRecordHeader(*pHeader, FCGI_GET_VALUES, 0, len);
    return sendRecord(achBuf, sizeof(FCGI_Header) + len);
}


void FcgiConnection::processManagementVal(
    char *pName, int nameLen, char *pValue, int valLen)
{
    char ch = *(pValue + valLen);
    *(pValue + valLen) = 0;
    int val = strtol(pValue, NULL, 10);
    *(pValue + valLen) = ch;

    if (strncmp(pName, FCGI_MAX_CONNS, nameLen) == 0)
    {
        //printf( "FCGI_MAX_CONNS=%d\n", val );
        ((FcgiApp *)getWorker())->setFcgiMaxConns(val);
    }
    else if (strncmp(pName, FCGI_MAX_REQS, nameLen) == 0)
    {
        //printf( "FCGI_MAX_REQS=%d\n", val );
        ((FcgiApp *)getWorker())->setFcgiMaxReqs(val);
    }
    else if (strncmp(pName, FCGI_MPXS_CONNS, nameLen) == 0)
    {
        //printf( "FCGI_MPXS_CONNS=%d\n", val );
        ((FcgiApp *)getWorker())->setMultiplexConns(val);
    }
}


int FcgiConnection::processManagementRec(char *pBuf, int size)
{
    m_bufRec.append(pBuf, size);
    if (m_bufRec.size() == m_iContentLen)
    {
        if (m_recCur.type == FCGI_GET_VALUES_RESULT)
        {
            assert(m_bufRec.size() >= m_iContentLen);
            m_bufRec.append("", 1);   //pad a '\0'
            char *p = m_bufRec.begin();
            int used = 0;
            char *pName;
            char *pValue;
            int nameLen;
            int valLen;
            ((FcgiApp *)getWorker())->gotManagementInfo();
            while (used < m_iContentLen)
            {
                int ret = FcgiNameValuePair::decode(p, size, pName, nameLen,
                                                    pValue, valLen);
                if (ret != -1)
                {
                    used += ret;
                    p += ret;
                    size -= ret;
                    if (valLen > 0)
                        processManagementVal(pName, nameLen,
                                             pValue, valLen);
                }
                else
                    break;
            }
        }
        m_bufRec.clear();
    }
    return 0;
}


bool FcgiConnection::wantRead()
{
    return true;
}


bool FcgiConnection::wantWrite()
{
    return ((!m_bufOS.isEmpty()) || m_iWantWrite);
}


int FcgiConnection::addRequest(ExtRequest *pReq)
{
    setConnector((HttpExtConnector *)pReq);
//    if ( pReq )
//    {
//        m_pReq = (FcgiRequest *)pReq;
//        ((FcgiRequest *)pReq)->setFcgiConn( this );
//    }
    m_iWantWrite = 1;
    m_iovec.clear();
    m_bufOS.getBuf()->clear();
    m_env.clear();
    m_lReqBeginTime = time(NULL);
    m_lReqSentTime = 0;
    return 0;
}


ExtRequest *FcgiConnection::getReq() const
{
    return getConnector();
}


int FcgiConnection::removeRequest(ExtRequest *pReq)
{
    //assert( (HttpExtConnector *) pReq == getConnector() );
    if (getConnector())
    {
        getConnector()->setProcessor(NULL);
        setConnector(NULL);
    }
    return 0;
}


void FcgiConnection::finishRecvBuf()
{
    processFcgiData();
}


int FcgiConnection::readStdOut(int iReqId, char *pBuf, int size)
{
    //FIXME:
    return 0;
}


void FcgiConnection::suspendWrite()
{
    LS_DBG_L(this, "FcgiConnection::suspendWrite()");
    m_iWantWrite = 0;
    if (m_bufOS.isEmpty())
        EdStream::suspendWrite();
}


int  FcgiConnection::sendReqHeader()
{
    int size = m_env.size();
    if (size == 0)
    {
        HttpCgiTool::buildFcgiEnv(&m_env, getConnector()->getHttpSession());
        size = m_env.size();
    }
    int ret = sendSpecial(m_env.get(), size);
    setInProcess(1);
    return ret;
}


/**
  * @return 0, connection busy
  *         -1, error
  *         other, bytes sent, conutue
  *
  */

int  FcgiConnection::sendReqBody(const char *pBuf, int size)
{
    int ret = 1;
    if (size > 0)
    {
        if (!m_iovec.empty())
        {
            ret = pendingWrite(pBuf, size, FCGI_STDIN);
            //flush();
        }
        else
            ret = writeStream(FCGI_STDIN, m_iId, pBuf, size);
    }
    return ret;
}


int FcgiConnection::beginReqBody()
{
    LS_DBG_M(this, "FcgiConnection::beginReqBody()");
    if (!m_iovec.empty())
    {
        pendingEndStream(FCGI_PARAMS);
        return 1;
    }
    else
        return endOfStream(FCGI_PARAMS, m_iId);
}


int FcgiConnection::endOfReqBody()
{
    LS_DBG_M(this, "FcgiConnection::endOfReqBody()");
    int ret;
    if (!m_iovec.empty())
    {
        pendingEndStream(FCGI_STDIN);
        ret = flush();
        if (!ret)
            suspendWrite();
    }
    else
    {
        endOfStream(FCGI_STDIN, m_iId);
        if (!m_bufOS.isEmpty())
            EdStream::continueWrite();
        else
            suspendWrite();
    }
    m_lReqSentTime = time(NULL);
    return 0;
}


int  FcgiConnection::endOfRequest(int endCode, int status)
{
    HttpExtConnector *pConnector = getConnector();
    if (!pConnector)
        return 0;
    if (endCode)
    {
        LS_ERROR(this, "FcgiConnection::endOfRequest( %d, %d)!",
                 endCode, status);
        pConnector->endResponse(SC_500, status);
    }
    else
        pConnector->endResponse(endCode, status);
    return 0;
}


int FcgiConnection::onStdOut()
{
    HttpExtConnector *pConnector = getConnector();
    if (!pConnector)
        return 0;
    LS_DBG_M(this, "onStdOut()");
    return pConnector->extInputReady();

}


int  FcgiConnection::processStdOut(char *pBuf, int size)
{
    HttpExtConnector *pConnector = getConnector();
    if (!pConnector)
        return size;
    LS_DBG_M(this, "Process STDOUT %d bytes", size);
    return pConnector->processRespData(pBuf, size);
}


int  FcgiConnection::processStdErr(char *pBuf, int size)
{
    HttpExtConnector *pConnector = getConnector();
    if (!pConnector)
        return size;
    LS_DBG_M(this, "Process STDERR %d bytes", size);
    return pConnector->processErrData(pBuf, size);
}


void FcgiConnection::cleanUp()
{
    //ExtRequest::cleanUp();
    if (!getWorker()->getConfigPointer()->isPersistConn())
    {
        LS_DBG_M(this, "Non-Persistent connection, close.");
        close();
    }
    setConnector(NULL);
    recycle();
}


void FcgiConnection::continueWrite()
{
    m_iWantWrite = 1;
    EdStream::continueWrite();
}


void  FcgiConnection::abort()
{
    LS_DBG_M(this, "FcgiConnection::abort()");
    setState(ABORT);
    //sendAbortRec();
}


int FcgiConnection::begin()
{
    LS_DBG_M(this, "FcgiConnection::beginRequest()");
    FCGI_BeginRequestRecord *pRec
        = (FCGI_BeginRequestRecord *)m_streamHeaders;
    FcgiRecord::setRecordHeader(
        pRec->header, FCGI_BEGIN_REQUEST, m_iId, 8);
    unsigned short role = getWorker()->getRole();
    pRec->body.roleB0 = role & 0xff;
    pRec->body.roleB1 = (role >> 8) & 0xff;
    pRec->body.flags = getWorker()->getConfigPointer()->isPersistConn() & 0xff;
    m_iovec.clear();
    m_iCurStreamHeader = sizeof(FCGI_BeginRequestRecord);
    m_iTotalPending = 0;
    m_iovec.append(m_streamHeaders, sizeof(FCGI_BeginRequestRecord));
    return 1;
}


int FcgiConnection::connUnavail()
{
    getConnector()->endResponse(SC_500, -1);
    return 0;
}


int FcgiConnection::pendingEndStream(int type)
{
    LS_DBG_M(this, "FcgiConnection::pendingEndStream()");
    assert(m_iCurStreamHeader < 64);
    FCGI_Header *pRec = (FCGI_Header *)
                        & (m_streamHeaders[ m_iCurStreamHeader]);
    m_iCurStreamHeader += sizeof(FCGI_Header);
    FcgiRecord::setRecordHeader(*pRec, type, m_iId, 0);
    m_iovec.appendCombine((char *)pRec, sizeof(FCGI_Header));
    return 1;
}


int FcgiConnection::pendingWrite(const char *pBuf, int size, int type)
{
    LS_DBG_M(this, "FcgiConnection::pendingWrite(), m_iCurStreamHeader=%d",
             m_iCurStreamHeader);
    int ret = size;
    int packetSize = size;
    if (packetSize > FCGI_MAX_PACKET_SIZE)
        packetSize = FCGI_MAX_PACKET_SIZE;

    FCGI_Header *pRec = (FCGI_Header *)
                        & (m_streamHeaders[ m_iCurStreamHeader]);
    m_iCurStreamHeader += sizeof(FCGI_Header);
    FcgiRecord::setRecordHeader(*pRec, type, m_iId, packetSize);
    m_iovec.appendCombine((char *)pRec, sizeof(FCGI_Header));
    m_iovec.append((char *)pBuf, packetSize);
    m_iTotalPending += packetSize ;
    if (pRec->paddingLength > 0)
    {
        m_iovec.append(FcgiConnection::s_padding, pRec->paddingLength);
        m_iTotalPending += pRec->paddingLength;
    }
    size -= packetSize;
    pBuf += packetSize;
    if ((size > 0)
        || (m_iTotalPending > FCGI_MAX_PACKET_SIZE)
        || (m_iCurStreamHeader >= 56))
    {
        int ret1 = flush();
        if (ret1 == -1)
            return LS_FAIL;
        if ((size > 0) && (ret1 == 0))
        {
            size = writeStream(type, m_iId, pBuf, size);
            if (size == -1)
                return LS_FAIL;
            ret = size + packetSize;
        }
    }
    return ret;
}


int  FcgiConnection::sendSpecial(const char *pBuf, int size)
{
    int ret = 1;
    if (size > 0)
        ret = pendingWrite(pBuf, size, FCGI_PARAMS);
    return ret;
}


int  FcgiConnection::flush()
{
    LS_DBG_M(this, "FcgiConnection::flush()");
    if (!m_iovec.empty())
    {
        int ret = m_bufOS.cacheWritev(m_iovec);
        if (ret == -1)
            return LS_FAIL;
        assert(ret >= m_iTotalPending + m_iCurStreamHeader);
        m_iovec.clear();
        m_iTotalPending = 0;
        if (!m_bufOS.isEmpty())
            EdStream::continueWrite();
    }
    return 0;
}


int FcgiConnection::sendAbortRec()
{
    LS_DBG_L(this, "[FCGI] send abort packet!");
    FCGI_Header rec;
    FcgiRecord::setRecordHeader(rec, FCGI_ABORT_REQUEST, m_iId, 0);
    return sendRecord((const char *)&rec, sizeof(rec));
}


int FcgiConnection::readResp(char *pBuf, int size)
{
    return readStdOut(m_iId, pBuf, size);
}


void FcgiConnection::dump()
{
    LS_INFO(this, "FcgiConnection watching event: %d, wantWrite: %d, "
            "total Pending: %d, buffered: %d, record status: %d, size:%d, "
            "content len: %d, request processed: %d, total processing time: "
            "%ld, waiting for response for %ld seconds.",
            getEvents(), m_iWantWrite, m_iTotalPending,
            m_bufOS.getBuf()->size(), m_iRecStatus, m_recSize, m_iContentLen,
            getReqProcessed(), time(NULL) - m_lReqBeginTime,
            (m_lReqSentTime) ? time(NULL) - m_lReqSentTime : 0);

}

