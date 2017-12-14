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
#include "lsapiconn.h"
#include "lsapiworker.h"
#include "lsapiconfig.h"

#include <extensions/localworker.h>
#include <extensions/registry/extappregistry.h>

#include <edio/multiplexer.h>
#include <edio/multiplexerfactory.h>
#include <http/httpcgitool.h>
#include <http/httpdefs.h>
#include <http/httpextconnector.h>
#include <http/httpreq.h>
#include <http/httpsession.h>
#include <http/httpstatuscode.h>
#include <log4cxx/logger.h>
#include <util/datetime.h>

#include <fcntl.h>
#include <sys/socket.h>

//#define DBG_LSAPI
#ifdef DBG_LSAPI
static int dbg_fd = -1;
#endif

inline void swapIntEndian(int *pInteger)
{
    char *p = (char *)pInteger;
    char b;
    b = p[0];
    p[0] = p[3];
    p[3] = b;
    b = p[1];
    p[1] = p[2];
    p[2] = b;

}


LsapiConn::LsapiConn()
    : m_pid(-1)
    , m_iTotalPending(0)
    , m_iPacketLeft(0)
    , m_iPacketHeaderLeft(0)
    , m_lReqBeginTime(0)
    , m_lReqSentTime(0)
    , m_lsreq(&m_iovec)
    , m_respState(LSAPI_CONN_IDLE)

{
}


LsapiConn::~LsapiConn()
{
}


void LsapiConn::init(int fd, Multiplexer *pMplx)
{
    EdStream::init(fd, pMplx, POLLIN | POLLOUT | POLLHUP | POLLERR);
    reset();

}


int LsapiConn::connect(Multiplexer *pMplx)
{
    LsapiWorker *pWorker = (LsapiWorker *)getWorker();
    if (pWorker->selfManaged())
        return ExtConn::connect(pMplx);
    int fds[2];
    errno = ECONNRESET;
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, fds) == -1)
    {
        LS_ERROR("[LsapiConn::connect()] socketpair() failed!");
        return LS_FAIL;
    }
    fcntl(fds[0], F_SETFD, FD_CLOEXEC);
    setReqProcessed(0);
    setToStop(0);
    //if ( pApp->getCurInstances() >= pApp->getConfig().getInstances() )
    //    return LS_FAIL;
    m_pid = LocalWorker::workerExec(pWorker->getConfig(), fds[1]);
    ::close(fds[1]);

    if (m_pid == -1)
    {
        ::close(fds[0]);
        return LS_FAIL;
    }
    else
    {
        LS_DBG_L("[%s] add child process pid: %d", pWorker->getName(), m_pid);
        PidRegistry::add(m_pid, pWorker, 0);
    }

    ::fcntl(fds[0], F_SETFL, MultiplexerFactory::getMultiplexer()->getFLTag());
    init(fds[0], pMplx);

    //Increase the number of successful request to avoid max connections reduction.
    incReqProcessed();

    setState(PROCESSING);
    onWrite();

    return 1;
}


int LsapiConn::close()
{
    ExtConn::close();
    if (m_pid > 0)
    {
        ((LsapiWorker *)getWorker())->moveToStopList(m_pid);
        m_pid = -1;
    }
    return 0;
}


int LsapiConn::doWrite()
{
    if (getConnector())
    {
        int state = getConnector()->getState();
        if ((!state) || (state & (HEC_FWD_REQ_HEADER | HEC_FWD_REQ_BODY)))
        {
            int ret = getConnector()->extOutputReady();
            if (getState() == ABORT)
            {
                if (getConnector())
                {
                    incReqProcessed();
                    getConnector()->endResponse(0, 0);
                }
            }
            return ret;
        }
    }
    if (m_iTotalPending > 0)
        return flush();
    else
        suspendWrite();
    return 0;
}


int LsapiConn::sendReqHeader()
{
    int ret = m_lsreq.buildReq(getConnector()->getHttpSession(),
                               &m_iTotalPending);
    if (ret)
    {
        LS_INFO(this, "Failed to build LSAPI request header, "
                "can't forward request to external LSAPI application.");
//        ((HttpExtConnector *)pReq)->setProcessor( NULL );
//        setConnector( NULL );
        return LS_FAIL;
    }
    setInProcess(1);
    m_lReqSentTime = DateTime::s_curTime;
    return 1;
}


int  LsapiConn::sendReqBody(const char *pBuf, int size)
{
    m_iovec.append(pBuf, size);
    int ret = writev(m_iovec);
    if (m_iTotalPending > 0)
    {
        if (ret > m_iTotalPending)
        {
            ret -= m_iTotalPending;
            m_iTotalPending = 0;
            m_iovec.clear();
        }
        else
        {
            m_iovec.pop_back(1);
            if (ret > 0)
            {
                m_iTotalPending -= ret;
                m_iovec.finish(ret);
                ret = 0;
            }
        }
    }
    else
        m_iovec.clear();
#ifdef DBG_LSAPI
    if (ret > 0)
        ::write(dbg_fd, pBuf, ret);
#endif
    return ret;
}


void LsapiConn::abort()
{
    setState(ABORT);
    sendAbortReq();
    //::shutdown( getfd(), SHUT_RDWR );
}


int LsapiConn::sendAbortReq()
{
    LS_DBG_L(this, "[LSAPI] send abort packet!");
    lsapi_packet_header rec;
    LsapiReq::buildPacketHeader(&rec, LSAPI_ABORT_REQUEST,
                                LSAPI_PACKET_HEADER_LEN);
    return write((char *)&rec, sizeof(rec));
}


void LsapiConn::reset()
{
    m_iovec.clear();
    m_iTotalPending = 0;
    m_respState     = LSAPI_CONN_IDLE;
    //m_reqReceived   = 0;
    //memset( &m_iTotalPending, 0,
    //        ((char *)(&m_pChunkIS + 1)) - (char *)&m_iTotalPending );
}


int  LsapiConn::begin()
{

#ifdef DBG_LSAPI
    dbg_fd = open("/home/gwang/lsapi_req_dump.bin",
                  O_RDWR | O_CREAT | O_TRUNC, 0600);
#endif

    return 1;
}


int  LsapiConn::beginReqBody()
{
    // get ready to read response packet
    m_iPacketLeft = 0;
    m_iPacketHeaderLeft = 8;

    return 1;
}


int  LsapiConn::endOfReqBody()
{
    if (m_iTotalPending)
    {
        int ret = flush();
        if (ret)
            return ret;
    }
    suspendWrite();
    m_lReqSentTime = DateTime::s_curTime;
    return 0;
}


int  LsapiConn::flush()
{
    if (m_iTotalPending)
    {
        int ret = writev(m_iovec, m_iTotalPending);
        if (ret >= m_iTotalPending)
        {
            ret -= m_iTotalPending;
            m_iTotalPending = 0;
            m_iovec.clear();
        }
        else
        {
            if (ret > 0)
            {
                m_iTotalPending -= ret;
                m_iovec.finish(ret);
                return 1;
            }
            return LS_FAIL;
        }
    }
    return 0;
}


int LsapiConn::doRead()
{
    LS_DBG_L(this, "LsapiConn::doRead()");
    int ret;
    ret = processResp();
//    if ( m_respState )
//        ret = processResp();
//    else
//        ret = processRespBuffed();
    if (getState() == ABORT)
    {
        if (getConnector())
        {
            incReqProcessed();
            getConnector()->endResponse(0, 0);
        }
    }
    return ret;
}


inline int verifyPacketHeader(struct lsapi_packet_header *pHeader)
{
    if ((LSAPI_VERSION_B0 != pHeader->m_versionB0) ||
        (LSAPI_VERSION_B1 != pHeader->m_versionB1) ||
        (LSAPI_RESP_HEADER > pHeader->m_type) ||
        (LSAPI_REQ_RECEIVED < pHeader->m_type))
        return LS_FAIL;
    if (LSAPI_ENDIAN != (pHeader->m_flag & LSAPI_ENDIAN_BIT))
    {
        char b;
        b = pHeader->m_packetLen.m_bytes[0];
        pHeader->m_packetLen.m_bytes[0] = pHeader->m_packetLen.m_bytes[3];
        pHeader->m_packetLen.m_bytes[3] = b;
        b = pHeader->m_packetLen.m_bytes[1];
        pHeader->m_packetLen.m_bytes[1] = pHeader->m_packetLen.m_bytes[2];
        pHeader->m_packetLen.m_bytes[2] = b;
    }
    return pHeader->m_packetLen.m_iLen;
}


void LsapiConn::setRespBuf(char *pStart)
{
    m_pRespHeader       = pStart;
    m_pRespHeaderBufEnd = pStart + m_iPacketLeft;

    if (m_pRespHeaderBufEnd > &m_respBuf[sizeof(m_respBuf)])
        m_pRespHeaderBufEnd = &m_respBuf[sizeof(m_respBuf)];
}


int LsapiConn::processPacketHeader(char *pBuf, int len)
{
    if (m_iPacketHeaderLeft < len)
        len = m_iPacketHeaderLeft;
    memmove(((char *)&m_respHeader) + sizeof(m_respHeader) -
            m_iPacketHeaderLeft,
            pBuf, len);

    m_iPacketHeaderLeft -= len;

    if (m_iPacketHeaderLeft == 0)
    {
        m_iPacketLeft = verifyPacketHeader(&m_respHeader) -
                        LSAPI_PACKET_HEADER_LEN;
        if (m_iPacketLeft < 0)
        {
            LS_WARN(this, "LSAPI Packet header is invalid!");
            errno = EIO;
            return LS_FAIL;
        }
//         if ( m_iPacketLeft > LSAPI_MAX_HEADER_LEN )
//         {
//             LS_WARN( "[%s] LSAPI Packet is too large: %d",
//                     getLogId(), m_iPacketLeft ));
//          errno = EIO;
//             return LS_FAIL;
//         }
        switch (m_respHeader.m_type)
        {
        case LSAPI_RESP_END:
            incReqProcessed();
            setInProcess(0);
            if (getConnector())
                getConnector()->endResponse(0, 0);
            return 0;
        case LSAPI_RESP_HEADER:
            if (m_respState == LSAPI_CONN_READ_RESP_BODY)
            {
                LS_WARN(this, "Invalid LSAPI Response Header Packet following "
                        "STREAM packet");
                errno = EIO;
                return LS_FAIL;
            }
            else
            {
                m_iCurRespHeader = 0;
                m_respState = LSAPI_CONN_READ_RESP_INFO;
                m_pRespHeaderProcess = (char *)&m_respInfo;
                setRespBuf(m_pRespHeaderProcess);
            }
            break;
        case LSAPI_REQ_RECEIVED:
            //m_reqReceived       = 1;
            setCPState(1);
            break;
        }
    }
    return len;
}


int LsapiConn::processRespBuffed()
{
    int ret;
    int left;
    int len;
    m_pRespHeader = (char *)&m_respHeader;
    m_pRespHeaderBufEnd = &m_respBuf[1024];
    ret = read(m_pRespHeader, m_pRespHeaderBufEnd - m_pRespHeader);
    if (ret <= 0)
        return ret;
    if (ret < (int)sizeof(lsapi_packet_header))
    {
        m_iPacketHeaderLeft = sizeof(lsapi_packet_header) - ret;
        return ret;
    }
    m_pRespHeaderBufEnd     = m_pRespHeader + ret;
    m_iPacketLeft = verifyPacketHeader(&m_respHeader) -
                    LSAPI_PACKET_HEADER_LEN;
    if (m_iPacketLeft < 0)
    {
        errno = EIO;
        return LS_FAIL;
    }
    if (!m_iPacketLeft)
        m_iPacketHeaderLeft = LSAPI_PACKET_HEADER_LEN;
    else
        m_iPacketHeaderLeft = 0;
    if (ret < (int)(sizeof(lsapi_packet_header) + sizeof(lsapi_resp_info)))
    {
        m_pRespHeader += ret;
        switch (m_respHeader.m_type)
        {
        case LSAPI_RESP_END:
            m_respState = LSAPI_CONN_IDLE;
            incReqProcessed();
            setInProcess(0);
            getConnector()->endResponse(0, 0);
            return 0;
        case LSAPI_RESP_HEADER:
            m_iCurRespHeader    = 0;
            m_respState         = LSAPI_CONN_READ_RESP_INFO;
            m_pRespHeaderProcess = (char *)&m_respInfo;
            setRespBuf(m_pRespHeaderProcess);
            return ret;
        case LSAPI_REQ_RECEIVED:
            //m_reqReceived       = 1;
            setCPState(1);
            break;
        }
        m_pRespHeaderProcess    = (char *)&m_respInfo;
    }
    else
    {
        m_iCurRespHeader        = 0;
        m_respState             = LSAPI_CONN_READ_HEADER_LEN;
        m_pRespHeaderProcess    = m_respBuf;
    }
    while ((left = m_pRespHeaderBufEnd - m_pRespHeaderProcess) > 0)
    {
        if (m_iPacketHeaderLeft > 0)
        {
            ret = processPacketHeader(m_pRespHeaderProcess, left);
            if (ret <= 0)
                return ret;
            m_pRespHeaderProcess += ret;
            left -= ret;
        }

        if (m_iPacketLeft > 0)
        {
            HttpExtConnector *pHEC = getConnector();
            if (!pHEC)
                return LS_FAIL;
            int &respState = pHEC->getRespState();
            if (m_iPacketLeft < left)
            {
                len = m_iPacketLeft;
                m_iPacketLeft = 0;
                m_iPacketHeaderLeft = LSAPI_PACKET_HEADER_LEN;
            }
            else
            {
                len = left;
                m_iPacketLeft -= left;
                left = 0;
            }
            switch (m_respHeader.m_type)
            {
            case LSAPI_RESP_HEADER:
                ret = processRespHeader(m_pRespHeaderBufEnd, respState);
                if (ret < 0)
                    return ret;
                break;
            case LSAPI_RESP_STREAM:
                LS_DBG_M(this, "Process response stream %d bytes", len);
                ret = pHEC->processRespData(m_pRespHeaderProcess, len);
                if (respState & 0xff)
                    m_respState = LSAPI_CONN_READ_RESP_BODY;
                if (ret == -1)
                    return ret;
                m_pRespHeaderProcess += len;
                break;
            case LSAPI_STDERR_STREAM:
                LS_DBG_M(this, "Process STDERR stream %d bytes", len);
                ret = pHEC->processErrData(m_pRespHeaderProcess, len);
                m_pRespHeaderProcess += len;
                break;
            default:
                LS_NOTICE(this, "Unknown Packet Type %c, LSAPI protocol is "
                          "broken.", m_respHeader.m_type);
                errno = EIO;
                return LS_FAIL;
            }
        }
        else
            m_iPacketHeaderLeft = LSAPI_PACKET_HEADER_LEN;


    }
    return 1;
}


int LsapiConn::processResp()
{
    int ret;
    while (getState() == PROCESSING)
    {
        if (m_iPacketHeaderLeft > 0)
        {
            ret = read(((char *)&m_respHeader) + sizeof(m_respHeader) -
                       m_iPacketHeaderLeft,
                       m_iPacketHeaderLeft);
            LS_DBG_M(this, "Process packet header %d bytes", ret);
            if (ret > 0)
            {
                m_iPacketHeaderLeft -= ret;
                if (m_iPacketHeaderLeft == 0)
                {
                    m_iPacketLeft = verifyPacketHeader(&m_respHeader) -
                                    LSAPI_PACKET_HEADER_LEN;
                    if (m_iPacketLeft < 0)
                    {
                        const char *p = (const char *)&m_respHeader;
                        LS_WARN("[%s] LSAPI Packet header is invalid,"
                                "('%c','%c','%c','%c','%c','%c','%c','%c')",
                                getLogId(), *p, *(p + 1), *(p + 2), *(p + 3),
                                *(p + 4), *(p + 5), *(p + 6), *(p + 7));
                        break;

                    }
//                     if ( m_iPacketLeft > LSAPI_MAX_HEADER_LEN )
//                     {
//                         LS_WARN( "[%s] LSAPI Packet is too large: %d",
//                                 getLogId(), m_iPacketLeft ));
//                      break;
//                     }
                    switch (m_respHeader.m_type)
                    {
                    case LSAPI_RESP_END:
                        m_respState = 0;
                        incReqProcessed();
                        setInProcess(0);
                        getConnector()->endResponse(0, 0);
                        return 0;
                    case LSAPI_RESP_HEADER:
                        m_iCurRespHeader = 0;
                        m_respState = LSAPI_CONN_READ_RESP_INFO;
                        m_pRespHeaderProcess = (char *)&m_respInfo;
                        setRespBuf(m_pRespHeaderProcess);
                        break;
                    case LSAPI_REQ_RECEIVED:
                        //m_reqReceived       = 1;
                        setCPState(1);
                        break;
                    }
                }
            }
            if (m_iPacketHeaderLeft > 0)
            {
                if ((m_respState == LSAPI_CONN_READ_RESP_BODY) &&
                    (getConnector()))
                    getConnector()->flushResp();
                return ret;
            }
        }
        if (m_iPacketLeft > 0)
        {
            switch (m_respHeader.m_type)
            {
            case LSAPI_RESP_HEADER:
                ret = processRespHeader();
                if (ret <= 0)
                    return ret;
                break;
            case LSAPI_RESP_STREAM:
                ret = readRespBody();
                if (ret <= 0)
                {
                    if ((m_respState == LSAPI_CONN_READ_RESP_BODY) &&
                        (getConnector()))
                        getConnector()->flushResp();
                    return ret;
                }
                break;
            case LSAPI_STDERR_STREAM:
                ret = readStderrStream();
                if (ret <= 0)
                    return ret;
                break;
            default:
                //error: protocol error
                LS_NOTICE(this, "Unknown Packet Type %c, LSAPI protocol is "
                          "broken.", m_respHeader.m_type);
                errno = EIO;
                return LS_FAIL;
            }
        }
        else
            m_iPacketHeaderLeft = LSAPI_PACKET_HEADER_LEN;
    }
    errno = EIO;
    return LS_FAIL;
}


int LsapiConn::processRespHeader(char *pEnd, int &status)
{
    switch (m_respState)
    {
    case LSAPI_CONN_READ_RESP_INFO:
        if (pEnd - m_pRespHeaderProcess >= (int)sizeof(m_respInfo))
        {
            m_pRespHeaderProcess += sizeof(m_respInfo);
            ++m_respState;
            if (LSAPI_ENDIAN != (m_respHeader.m_flag & LSAPI_ENDIAN_BIT))
            {
                swapIntEndian(&m_respInfo.m_cntHeaders);
                swapIntEndian(&m_respInfo.m_status);
            }
            if (m_respInfo.m_status)
            {
                int code;
                code = HttpStatusCode::getInstance().codeToIndex(m_respInfo.m_status);
                if (code != -1)
                    getConnector()->getHttpSession()->getReq()->updateNoRespBodyByStatus(code);
            }
        }
        else
            return 0;
    case LSAPI_CONN_READ_HEADER_LEN:
        if (pEnd - m_pRespHeaderProcess >= (int)sizeof(short) *
            m_respInfo.m_cntHeaders)
        {
            m_pRespHeaderProcess += sizeof(short) * m_respInfo.m_cntHeaders;
            if (LSAPI_ENDIAN != (m_respHeader.m_flag & LSAPI_ENDIAN_BIT))
            {
                char *p = m_respBuf;
                char ch;
                for (int i = 0; i < m_respInfo.m_cntHeaders; ++i)
                {
                    ch = *p;
                    *p = *(p + 1);
                    *(p + 1) = ch;
                    p += 2;
                }
            }
            ++m_respState;
        }
        else
            return 0;
    case LSAPI_CONN_READ_HEADER:
        if (m_respInfo.m_cntHeaders > 0)
        {
            while (m_iCurRespHeader < m_respInfo.m_cntHeaders)
            {
                short *p = ((short *)m_respBuf) + m_iCurRespHeader;
                int len = *p;
                if (len > 0)
                {
                    if (m_pRespHeaderProcess + len <= pEnd)
                    {
                        char *pHeaderEnd = m_pRespHeaderProcess + len - 1;
                        *pHeaderEnd = 0;
                        if (HttpCgiTool::processHeaderLine(
                                getConnector(),
                                m_pRespHeaderProcess, pHeaderEnd, status) == -1)
                            return LS_FAIL;
                        m_pRespHeaderProcess += len;
                    }
                    else
                        return 0;
                }
                ++m_iCurRespHeader;
            }
            status |= HttpReq::HEADER_OK;
            getConnector()->respHeaderDone();
        }
        ++m_respState;
    }
    return 0;
}


int LsapiConn::processRespHeader()
{
    HttpExtConnector *pHEC = getConnector();
    int ret;
    int len = 0;
    if (!pHEC)
        return LS_FAIL;
    int &respState = pHEC->getRespState();
    if (!(respState & 0xff))
    {
        while (m_iPacketLeft > 0)
        {
            len = ExtConn::read(m_pRespHeader, m_pRespHeaderBufEnd - m_pRespHeader);
            LS_DBG_M(this, "Process response header %d bytes", len);
            if (len > 0)
            {
                m_iPacketLeft -= len;
                ret = processRespHeader(m_pRespHeader + len, respState);
                switch (ret)
                {
                case -2:
                    LS_WARN(this, "Invalid Http response header, retry!");
                    //debug code
                    //::write( 1, pBuf, len );
                    errno = ECONNRESET;
                case -1:
                    return LS_FAIL;
                }

                if (m_iPacketLeft > 0)
                {
                    m_pRespHeader += len;
                    if ((m_pRespHeader > m_pRespHeaderProcess) &&
                        (m_pRespHeader != &m_respBuf[ m_respInfo.m_cntHeaders * sizeof(short) ]))
                    {
                        len = m_pRespHeader - m_pRespHeaderProcess;
                        memmove(&m_respBuf[ m_respInfo.m_cntHeaders * sizeof(short) ],
                                m_pRespHeaderProcess, m_pRespHeader - m_pRespHeaderProcess);
                        m_pRespHeaderProcess = &m_respBuf[ m_respInfo.m_cntHeaders * sizeof(
                                                               short) ];
                        m_pRespHeader = m_pRespHeaderProcess + len;
                    }
                    else
                        m_pRespHeader = m_pRespHeaderProcess =
                                            &m_respBuf[ m_respInfo.m_cntHeaders * sizeof(short) ];
                    setRespBuf(m_pRespHeader);
                }

            }
            else
                return len;
        }
        if (m_iPacketLeft == 0)
        {
            m_iPacketHeaderLeft = LSAPI_PACKET_HEADER_LEN;
            len = 1;
        }
        return len;
    }
    else
    {
        //error: protocol error, header received already.
        errno = EIO;
        return LS_FAIL;
    }
}


int LsapiConn::readRespBody()
{
    HttpExtConnector *pHEC = getConnector();
    int ret;
    size_t bufLen;
    if (!pHEC)
        return LS_FAIL;
    int &respState = pHEC->getRespState();
    while (m_iPacketLeft > 0)
    {
        char *pBuf = pHEC->getRespBuf(bufLen);
        if (!pBuf)
            return LS_FAIL;
        int toRead = m_iPacketLeft + sizeof(m_respHeader);
        if (toRead > (int)bufLen)
            toRead = bufLen ;
        ret = read(pBuf, toRead);
        if (ret > 0)
        {
            int len, packetLen;
            LS_DBG_M(this, "Process response stream %d bytes, packet left: %d",
                     ret, m_iPacketLeft);
            if (ret >= m_iPacketLeft)
            {
                packetLen       = m_iPacketLeft;
                m_iPacketLeft   = 0;
            }
            else
            {
                packetLen       = ret;
                m_iPacketLeft  -= ret;
            }
            if (!(respState & 0xff))
            {
                len = pHEC->processRespData(pBuf, packetLen);
                if (respState & 0xff)
                    m_respState = LSAPI_CONN_READ_RESP_BODY;
                if (len == -1)
                    return len;
            }
            else
                len = pHEC->processRespBodyData(pBuf, packetLen);
            if (m_iPacketLeft <= 0)
            {
                m_iPacketHeaderLeft = LSAPI_PACKET_HEADER_LEN;
                if (ret > packetLen)
                {
                    LS_DBG_M(this, "Process packet header %d bytes",
                             ret - packetLen);
                    int len1 = processPacketHeader(pBuf + packetLen,
                                                   ret - packetLen);
                    if (len1 <= 0)
                        return len1;
                    if ((m_respHeader.m_type != LSAPI_RESP_STREAM) ||
                        (m_iPacketLeft <= 0))
                        return 1;
                }
                else
                    break;
            }
            if (len == 1)
                return 0;
            if (len)
                return len;
            if (ret < (int)toRead)
            {
                pHEC->flushResp();
                return 0;
            }
        }
        else
            return ret;
    }
    return 1;
}


int LsapiConn::readStderrStream()
{
    HttpExtConnector *pHEC = getConnector();
    int     ret;
    size_t  bufLen;
    char    achBuf[2049];

    while (m_iPacketLeft > 0)
    {
        char *pBuf = achBuf;
        bufLen = sizeof(achBuf);
        int toRead = m_iPacketLeft + sizeof(m_respHeader);
        if (toRead > (int)bufLen)
            toRead = bufLen ;
        ret = read(pBuf, toRead);
        if (ret > 0)
        {
            int len, packetLen;
            LS_DBG_M(this, "Process STDERR stream %d bytes, packet left: %d",
                     ret, m_iPacketLeft);
            if (ret >= m_iPacketLeft)
            {
                packetLen       = m_iPacketLeft;
                m_iPacketLeft   = 0;
            }
            else
            {
                packetLen       = ret;
                m_iPacketLeft  -= ret;
            }

            if ((packetLen == 8) && !m_iPacketLeft
                && (m_respHeader.m_packetLen.m_iLen == 16)
                && (memcmp(achBuf, "\0PID", 4) == 0))
            {
                //ignore this packet for now.
            }
            else if (pHEC)
                pHEC->processErrData(pBuf, packetLen);
            else
            {
                char ch = pBuf[packetLen];
                pBuf[ packetLen ] = 0;
                LS_NOTICE(this, "[LSAPI:STDERR]: %s", pBuf);
                pBuf[ packetLen ] = ch;
            }

            if (m_iPacketLeft <= 0)
            {
                m_iPacketHeaderLeft = LSAPI_PACKET_HEADER_LEN;
                if (ret > packetLen)
                {
                    LS_DBG_M(this, "Process packet header %d bytes",
                             ret - packetLen);
                    len = processPacketHeader(pBuf + packetLen, ret - packetLen);
                    if (len <= 0)
                        return len;
                    if ((m_respHeader.m_type != LSAPI_STDERR_STREAM) ||
                        (m_iPacketLeft <= 0))
                        return 1;
                }
                else
                    break;
            }
        }
        else
            return ret;
    }
    return 1;
}


int LsapiConn::doError(int err)
{
    LS_DBG_L(this, "LsapiConn::doError()");
    if (getConnector())
    {
        int state = getConnector()->getState();
        if (!(state & (HEC_FWD_RESP_BODY | HEC_ABORT_REQUEST
                       | HEC_ERROR | HEC_COMPLETE)))
        {
            LS_DBG_L(this, "Lsapi Peer closed connection, "
                     "try another connection!");
            connError(err);
            return 0;
        }
        if (!(state & HEC_COMPLETE))
            getConnector()->endResponse(SC_500, -1);
    }
    return 0;
}


int LsapiConn::addRequest(ExtRequest *pReq)
{
    assert(pReq);
    setConnector((HttpExtConnector *)pReq);
    reset();
    m_lReqBeginTime = DateTime::s_curTime;

    return 0;
}


ExtRequest *LsapiConn::getReq() const
{
    return getConnector();
}


int LsapiConn::removeRequest(ExtRequest *pReq)
{
    if (getConnector())
    {
        getConnector()->setProcessor(NULL);
        setConnector(NULL);
        //reset();
    }
    return 0;
}


void LsapiConn::finishRecvBuf()
{
    //doRead();
}


void LsapiConn::cleanUp()
{
    setConnector(NULL);
    reset();
    if (getState() == ABORT)
        close();
    recycle();
}


void LsapiConn::onTimer()
{
    if (m_respState && !getCPState()
        && (DateTime::s_curTime - m_lReqSentTime >= 3))
    {
        LS_NOTICE(this, "No request delivery notification has been received "
                  "from LSAPI application, possible dead lock.");
        if (((LsapiWorker *)getWorker())->getConfig().getSelfManaged())
            getWorker()->addNewProcess();
        else
            connError(ETIMEDOUT);
        return;
    }
    /*    if ( m_lLastRespRecvTime )
        {
            long tm = time( NULL );
            long delta = tm - m_lLastRespRecvTime;
            if (( delta > getWorker()->getTimeout() )&&( m_iRespBodyRecv ))
            {
                if ( m_pChunkIS )
                    LS_INFO(this, "Timeout, partial chunk encoded body received,"
                        " received: %d, chunk len: %d, remain: %d!",
                        m_iRespBodyRecv, m_pChunkIS->getChunkLen(),
                        m_pChunkIS->getChunkRemain());
                else
                    LS_INFO(this, "Timeout, partial response body received,"
                        " body len: %d, received: %d!",
                        m_iRespBodySize, m_iRespBodyRecv);
                setState( CLOSING );
                if ( getConnector() )
                    getConnector()->endResponse( 0, 0 );
                return;
            }
            else if (( m_pChunkIS )&&( delta > 2 ))
            {
                if ((!m_pChunkIS->getChunkLen())&&( getConnector() ))
                {
                    LS_INFO(this, "Missing trailing CRLF in Chunked Encoding!");
                    setState( CLOSING );
                    getConnector()->endResponse( 0, 0 );
                    return;
                }
            }
        }*/

    ExtConn::onTimer();
}


bool LsapiConn::wantRead()
{
    return false;
}


bool LsapiConn::wantWrite()
{
    return false;
}


int  LsapiConn::readResp(char *pBuf, int size)
{
    return 0;
}


void LsapiConn::dump()
{
    /*    LS_INFO(this, "Lsapi connection state: %d, watching event: %d, "
                    "Request header:%d, body:%d, sent:%d, "
                    "Response header: %d, total: %d bytes received in %ld seconds,"
                    "Total processing time: %ld.",
                    getState(), getEvents(), m_iReqHeaderSize, m_iReqBodySize,
                    m_iReqTotalSent, m_iRespHeaderRecv, m_iRespRecv,
                    (m_lReqSentTime)?time(NULL) - m_lReqSentTime : 0,
                    time(NULL) - m_lReqBeginTime ));*/
}


