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
#include "fcgirequest.h"
#include "fcgirecord.h"
#include "fcgiconnection.h"
#include <http/httpcgitool.h>
#include <http/httpextconnector.h>
#include <http/httplog.h>
#include <http/httpstatuscode.h>

#include <assert.h>
#include <stdio.h>
#include <string.h>

FcgiRequest::FcgiRequest(HttpExtConnector *pConnector)
    : m_iId(1)
    , m_iProtocolStatus(-1)
    , m_iWantWrite(1)
    , m_iCurStreamHeader(0)
    , m_iTotalPending(0)
    , m_pFcgiConn(NULL)
{
    //memset( &m_beginReqRec, 0, sizeof( m_beginReqRec ) );
    setConnector(pConnector);
}


FcgiRequest::~FcgiRequest()
{
}


void FcgiRequest::reset()
{
    //m_iId = 0;
    m_iWantWrite = 1;
    m_iovec.clear();
    m_iCurStreamHeader = 0;
    m_env.clear();
}


int  FcgiRequest::beginRequest(int Role, int iKeepConn)
{
    assert(m_pFcgiConn != NULL);
    FCGI_BeginRequestRecord *pRec
        = (FCGI_BeginRequestRecord *)m_streamHeaders;
    FcgiRecord::setRecordHeader(
        pRec->header, FCGI_BEGIN_REQUEST, m_iId, 8);
    pRec->body.roleB0 = Role & 0xff;
    pRec->body.roleB1 = (Role >> 8) && 0xff;
    pRec->body.flags = iKeepConn & 0xff;
    m_iovec.clear();
    m_iCurStreamHeader = sizeof(FCGI_BeginRequestRecord);
    m_iovec.append(m_streamHeaders, sizeof(FCGI_BeginRequestRecord));
    return 1;
}


void  FcgiRequest::abort()
{
    m_iProtocolStatus = FCGI_ABORT_REQUEST;
    //sendAbortRec();
}


int  FcgiRequest::sendReqHeader()
{
    int size = m_env.size();
    if (size == 0)
    {
        HttpCgiTool::buildFcgiEnv(&m_env, getConnector()->getHttpSession());
        size = m_env.size();
    }
    int ret = 1;
    ret = sendSpecial(m_env.get(), size);
    return ret;

}


/**
  * @return 0, connection busy
  *         -1, error
  *         other, bytes sent, conutue
  *
  */

int  FcgiRequest::sendReqBody(const char *pBuf, int size)
{
    int ret = 1;
    if (size > 0)
    {
        if (!m_iovec.empty())
        {
            ret = pendingWrite(pBuf, size, FCGI_STDIN);
            if (flush() == -1)
                ret = -1;
        }
        else
            ret = m_pFcgiConn->writeStream(FCGI_STDIN, m_iId, pBuf, size);
    }
    return ret;
}


int FcgiRequest::beginReqBody()
{
    if (!m_iovec.empty())
    {
        pendingEndStream(FCGI_PARAMS);
        return 1;
    }
    else
        return m_pFcgiConn->endOfStream(FCGI_PARAMS, m_iId);
}


int FcgiRequest::endOfReqBody()
{
    if (!m_iovec.empty())
    {
        pendingEndStream(FCGI_STDIN);
        return flush();
    }
    else
        return m_pFcgiConn->endOfStream(FCGI_STDIN, m_iId);
}


int  FcgiRequest::endOfRequest(int endCode, int status)
{
    m_iProtocolStatus = status;
    HttpExtConnector *pConnector = getConnector();
    assert(pConnector);
    if (endCode)
    {
        LS_ERROR(pConnector, "FcgiRequest::endOfRequest( %d, %d)!",
                 endCode, status);
        pConnector->endResponse(SC_500, status);
    }
    else
        pConnector->endResponse(endCode, status);
    return 0;
}


int FcgiRequest::begin()
{
    return beginRequest(FCGI_RESPONDER,
                        FCGI_KEEP_CONN);
}


//int  FcgiRequest::onExtWrite( )
//{
//    int ret = 0;
//    HttpExtConnector * pConnector = getConnector();
//    assert( pConnector );
//    LS_DBG_M(pConnector, "FcgiRequest::onWrite()");
//    ret = pConnector->extOutputReady( );
//    return ret;
//}


int FcgiRequest::onStdOut()
{
    HttpExtConnector *pConnector = getConnector();
    assert(pConnector);
    LS_DBG_M(pConnector, "onStdOut()");
    return pConnector->extInputReady();

}


int  FcgiRequest::processStdOut(char *pBuf, int size)
{
    HttpExtConnector *pConnector = getConnector();
    assert(pConnector);
    LS_DBG_M(pConnector, "Process STDOUT %d bytes", size);
    return pConnector->processRespData(pBuf, size);
}


int  FcgiRequest::processStdErr(char *pBuf, int size)
{
    HttpExtConnector *pConnector = getConnector();
    assert(pConnector);
    LS_DBG_M(pConnector, "Process STDERR %d bytes", size);
    return pConnector->processErrData(pBuf, size);
}


int  FcgiRequest::onError()
{
    endOfRequest(SC_500, -1);
    return 0;
}


void FcgiRequest::cleanUp()
{
    //ExtRequest::cleanUp();
    if (m_pFcgiConn)
    {
        FcgiConnection *pConn = m_pFcgiConn;
        m_pFcgiConn->removeRequest(this);
        pConn->recycle();
    }
    reset();
}


void FcgiRequest::finishRecvBuf()
{
    if (m_pFcgiConn)
        m_pFcgiConn->finishRecvBuf();
    m_iProtocolStatus = 0;
}


//void FcgiRequest::continueRead()
//{
//    m_iWantRead = 1;
//    m_pFcgiConn->continueRead();
//}


void FcgiRequest::continueWrite()
{
    m_iWantWrite = 1;
    m_pFcgiConn->continueWrite();
}


int FcgiRequest::connUnavail()
{
    getConnector()->endResponse(SC_500, -1);
    return 0;
}


int FcgiRequest::pendingEndStream(int type)
{
    assert(m_iCurStreamHeader < 64);
    FCGI_Header *pRec = (FCGI_Header *)
                        & (m_streamHeaders[ m_iCurStreamHeader]);
    m_iCurStreamHeader += sizeof(FCGI_Header);
    FcgiRecord::setRecordHeader(*pRec, type, m_iId, 0);
    m_iovec.appendCombine((char *)pRec, sizeof(FCGI_Header));
    return 1;
}


int FcgiRequest::pendingWrite(const char *pBuf, int size, int type)
{
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
    m_iTotalPending += packetSize;
    if (pRec->paddingLength > 0)
    {
        m_iovec.append(FcgiConnection::s_padding, pRec->paddingLength);
        m_iTotalPending += pRec->paddingLength;
    }
    size -= packetSize;
    pBuf += packetSize;
    if ((size > 0)
        || (m_iTotalPending > FCGI_MAX_PACKET_SIZE * 2)
        || (m_iCurStreamHeader >= 56))
        ret = flush();
    if ((size > 0) && (ret > 0))
    {
        size = m_pFcgiConn->writeStream(type, m_iId, pBuf, size);
        if (size == -1)
            return LS_FAIL;
        ret = size + packetSize;
    }
    return ret;
}


int  FcgiRequest::sendSpecial(const char *pBuf, int size)
{
    int ret = 1;
    if (size > 0)
        ret = pendingWrite(pBuf, size, FCGI_PARAMS);
    return ret;
}


int  FcgiRequest::flush()
{
    int ret = 1;
    if (!m_iovec.empty())
    {
        ret = m_pFcgiConn->cacheWritev(m_iovec);
        if (ret == -1)
            return LS_FAIL;
        assert(ret >= m_iTotalPending + m_iCurStreamHeader);
        m_iovec.clear();
        m_iTotalPending = 0;
        m_iCurStreamHeader = 0;
    }
    return ret;
}


int FcgiRequest::sendAbortRec()
{
    LS_DBG_L(getLogger(), "[%s] [FCGI] send abort packet!",
             getConnector()->getLogId());
    FCGI_Header rec;
    FcgiRecord::setRecordHeader(rec, FCGI_ABORT_REQUEST, m_iId, 0);
    return m_pFcgiConn->sendRecord((const char *)&rec, sizeof(rec));
}


int FcgiRequest::readResp(char *pBuf, int size)
{
    return m_pFcgiConn->readStdOut(m_iId, pBuf, size);
}


void FcgiRequest::onProcessorTimer()
{
    if (m_pFcgiConn)
        m_pFcgiConn->onProcessorTimer();
}

