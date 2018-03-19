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
#include "proxyconn.h"
#include "proxyworker.h"
#include "proxyconfig.h"

#include <edio/multiplexer.h>
#include <edio/multiplexerfactory.h>
#include <extensions/extworker.h>
#include <http/chunkinputstream.h>
#include <http/httpdefs.h>
#include <http/httpextconnector.h>
#include <http/httpreq.h>
#include <http/httpresourcemanager.h>
#include <http/httpsession.h>
#include <http/httpstatuscode.h>
#include <log4cxx/logger.h>
#include <sslpp/sslcontext.h>
#include <sslpp/sslerror.h>

#include <sys/socket.h>


static char s_achForwardHttps[] = "X-Forwarded-Proto: https\r\n";
static char s_achForwardHost[] = "X-Forwarded-Host: ";

ProxyConn::ProxyConn()
{
    strcpy(m_extraHeader, "Accept-Encoding: gzip\r\nX-Forwarded-For: ");
    memset(&m_iTotalPending, 0,
           ((char *)(&m_pChunkIS + 1)) - (char *)&m_iTotalPending);
}


ProxyConn::~ProxyConn()
{
}


void ProxyConn::init(int fd, Multiplexer *pMplx)
{
    EdStream::init(fd, pMplx, POLLIN | POLLOUT | POLLHUP | POLLERR);
    reset();
    m_iSsl = ((ProxyWorker *)getWorker())->getConfig().getSsl();
    if ((m_iSsl) && (m_ssl.getSSL()))
        m_ssl.release();
    m_lReqBeginTime = time(NULL);

    //Increase the number of successful request to avoid max connections reduction.
    incReqProcessed();
}


static SSL *getSslConn()
{
    static SslContext *s_pProxyCtx = NULL;
    if (!s_pProxyCtx)
    {
        s_pProxyCtx = new SslContext();
        if (s_pProxyCtx)
        {
            s_pProxyCtx->setRenegProtect(0);
            //s_pProxyCtx->setCipherList();
        }
        else
            return NULL;
    }
    return s_pProxyCtx->newSSL();
}


void ProxyConn::setSSLAgain()
{
    if (m_ssl.wantRead())
        MultiplexerFactory::getMultiplexer()->switchWriteToRead(this);
    if (m_ssl.wantWrite())
        MultiplexerFactory::getMultiplexer()->switchReadToWrite(this);
}


int ProxyConn::connectSSL()
{
    if (!m_ssl.getSSL())
    {
        m_ssl.setSSL(getSslConn());
        if (!m_ssl.getSSL())
            return LS_FAIL;
        m_ssl.setfd(getfd());
        HttpReq *pReq = getConnector()->getHttpSession()->getReq();
        char *pHostName;
        int hostLen = pReq->getNewHostLen();
        if (hostLen > 0)
            pHostName = (char *)pReq->getNewHost();
        else
        {
            pHostName = (char *)pReq->getHeader(HttpHeader::H_HOST);
            hostLen = pReq->getHeaderLen(HttpHeader::H_HOST);
        }
        if (pHostName)
        {
            char ch = *(pHostName + hostLen);
            *(pHostName + hostLen) = 0;
            m_ssl.setTlsExtHostName(pHostName);
            *(pHostName + hostLen) = ch;
        }
    }
    int ret = m_ssl.connect();
    switch (ret)
    {
    case 0:
        setSSLAgain();
        break;
    case 1:
        LS_DBG_L(this, "[SSL] connected!");
        break;
    default:
        if (errno == EIO)
            LS_DBG_L(this, "SSL_connect() failed!: %s ", SslError().what());
        break;
    }

    return ret;
}


int ProxyConn::doWrite()
{
    int ret;
    if ((m_iSsl) && (!m_ssl.isConnected()))
    {
        ret = connectSSL();
        if (ret != 1)
            return ret;
    }
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


int ProxyConn::sendReqHeader()
{
    m_iovec.clear();
    HttpSession *pSession = getConnector()->getHttpSession();
    HttpReq *pReq = pSession->getReq();
    //remove the trailing "\r\n" before adding our headers
    const char *pBegin = pReq->getOrgReqLine();
    m_iTotalPending = pReq->getHttpHeaderLen();
    int newReqLineLen = 0;
    int headerLen = 17;
    char *pExtraHeader = &m_extraHeader[23];
    const char *pForward = pReq->getHeader(HttpHeader::H_X_FORWARDED_FOR);
    int len;
    if (*pForward != '\0')
    {
        len = pReq->getHeaderLen(HttpHeader::H_X_FORWARDED_FOR);
        if (len > 160)
            len = 160;
        memmove(&pExtraHeader[headerLen], pForward, len);
        headerLen += len;
        pExtraHeader[headerLen++] = ',';

    }
    //add "X-Forwarded-For" header
    memmove(&pExtraHeader[headerLen], pSession->getPeerAddrString(),
            pSession->getPeerAddrStrLen());
    headerLen += pSession->getPeerAddrStrLen();
    pExtraHeader[headerLen++] = '\r';
    pExtraHeader[headerLen++] = '\n';

#if 1       //always set "Accept-Encoding" header to "gzip"
    char *pAE = (char *)pReq->getHeader(HttpHeader::H_ACC_ENCODING);
    if (*pAE)
    {
        int len = pReq->getHeaderLen(HttpHeader::H_ACC_ENCODING);
        if (len >= 4)
        {
            memmove(pAE, "gzip", 4);
            memset(pAE + 4, ' ', len - 4);
        }
    }
    else
    {
        pExtraHeader = m_extraHeader;
        headerLen += 23;
    }
#endif

    if (*(pBegin + --m_iTotalPending - 1) == '\r')
        --m_iTotalPending;
    if (*pForward)
    {
        if ((pBegin + m_iTotalPending) -
            (pForward + pReq->getHeaderLen(HttpHeader::H_X_FORWARDED_FOR)) == 2)
        {
            const char *p = pForward -= 16;
            while (*(p - 1) != '\n')
                --p;
            m_iTotalPending = p - pBegin;
        }
    }

    //reconstruct request line if URL has been rewritten
    if (pReq->getRedirects() > 0)
    {
        const char *pReqLine = pReq->encodeReqLine(newReqLineLen);
        if (newReqLineLen > 0)
        {
            m_iovec.append(pReqLine, newReqLineLen);
            pBegin += pReq->getOrgReqLineLen() - 9;
            m_iTotalPending -= pReq->getOrgReqLineLen() - 9;
        }

    }

    int newHostLen = pReq->getNewHostLen();
    char *pHost = (char *)pReq->getHeader(HttpHeader::H_HOST);
    int hostLen = pReq->getHeaderLen(HttpHeader::H_HOST);
    if (newHostLen > 0)
    {
        if (*pHost)
        {
            m_iovec.append(pBegin, pHost - pBegin);
            m_iovec.append(pReq->getNewHost(), newHostLen);
            m_iovec.append(pHost + hostLen,
                           pBegin + m_iTotalPending - pHost - hostLen);
            m_iTotalPending += (newHostLen - hostLen);
        }
        else
        {
            m_iovec.append(pBegin, m_iTotalPending);
            m_iovec.append("Host: ", 6);
            m_iovec.append(pReq->getNewHost(), newHostLen);
            m_iovec.append("\r\n", 2);
            m_iTotalPending += newHostLen + 8;
        }
    }
    else
        m_iovec.append(pBegin, m_iTotalPending);
    m_iTotalPending += newReqLineLen;

    if (hostLen)
    {
        m_iovec.append(s_achForwardHost, sizeof(s_achForwardHost) - 1);
        m_iovec.append(pHost, hostLen);
        m_iovec.append("\r\n", 2);
        m_iTotalPending += hostLen + sizeof(s_achForwardHost) + 1 ;
    }

    if (pSession->isSSL())
    {
        m_iovec.append(s_achForwardHttps, sizeof(s_achForwardHttps) - 1);
        m_iTotalPending += sizeof(s_achForwardHttps) - 1;
    }

    //if ( headerLen > 0 )
    {
        pExtraHeader[headerLen++] = '\r';
        pExtraHeader[headerLen++] = '\n';
        m_iovec.append(pExtraHeader, headerLen);
        m_iTotalPending += headerLen;
    }
    m_iReqHeaderSize = m_iTotalPending;
    m_iReqBodySize = pReq->getContentFinished();
    setInProcess(1);
    return 1;
}


int  ProxyConn::sendReqBody(const char *pBuf, int size)
{
    int ret;
    if (m_iTotalPending > 0)
    {
        m_iovec.append(pBuf, size);
        int total = m_iTotalPending + size;
        int finished = 0;
        if (m_iSsl)
            ret = m_ssl.writev(m_iovec.get(), m_iovec.len(), &finished);
        else
            ret = writev(m_iovec, total);
        m_iovec.pop_back(1);
        if (ret > 0)
        {
            m_iReqTotalSent += ret;
            if (ret >= total)
            {
                m_iTotalPending = 0;
                m_iovec.clear();
                return size;
            }
            if (ret >= m_iTotalPending)
            {
                ret -= m_iTotalPending;
                m_iovec.clear();
                m_iTotalPending = 0;
                return ret;
            }
            else
            {
                m_iovec.finish(ret);
                m_iTotalPending -= ret;
                return 0;
            }
        }
    }
    else
    {
        if (m_iSsl)
            ret = m_ssl.write(pBuf, size);
        else
            ret = write(pBuf, size);
        if (ret > 0)
            m_iReqTotalSent += ret;
    }
    return ret;
}


void ProxyConn::abort()
{
    setState(ABORT);
    //::shutdown( getfd(), SHUT_RDWR );
}


int ProxyConn::close()
{
    if (m_iSsl && m_ssl.getSSL())
    {
        LS_DBG_L(this, "Shutdown Proxy SSL ...");
        m_ssl.release();
    }
    return ExtConn::close();
}


void ProxyConn::reset()
{
    m_iovec.clear();
    if (m_pChunkIS)
        HttpResourceManager::getInstance().recycle(m_pChunkIS);
    memset(&m_iTotalPending, 0,
           ((char *)(&m_pChunkIS + 1)) - (char *)&m_iTotalPending);
}


int  ProxyConn::begin()
{
    return 1;
}


int  ProxyConn::beginReqBody()
{
    return 1;
}


int ProxyConn::read(char *pBuf , int size)
{
    int len = m_pBufEnd - m_pBufBegin;
    if (len > 0)
    {
        if (len > size)
            len = size;
        memmove(pBuf, m_pBufBegin, len);
        m_pBufBegin += len;
        if (len >= size)
            return len;
        pBuf += len;
        size -= len;
    }
    int ret;
    if (m_iSsl)
        ret = m_ssl.read(pBuf, size);
    else
        ret = ExtConn::read(pBuf, size);
    LS_DBG_L(this, "Read Response %d bytes", ret);
    if (m_iSsl && (ret < 0))
        errno = ECONNRESET;
    if (ret > 0)
    {
        m_iRespRecv += ret;
        //::write( 1, pBuf, ret );
        len += ret;
        return len;
    }
    else if (len)
        return len;
    return ret;
}


int ProxyConn::readvSsl(const struct iovec *vector,
                        const struct iovec *pEnd)
{
    int total = 0;
    int ret;
    while (vector < pEnd)
    {
        ret = m_ssl.read((char *)vector->iov_base, vector->iov_len);
        if (ret > 0)
            total += ret;
        if (ret < 0)
            return LS_FAIL;
        if (ret < (int)vector->iov_len)
            break;
        ++vector;
    }
    return total;
}


int ProxyConn::readv(struct iovec *vector, size_t count)
{
    int len;
    int total = 0;
    const struct iovec *pEnd = vector + count;
    while ((len = m_pBufEnd - m_pBufBegin) > 0)
    {
        if (vector == pEnd)
            return total;
        if (len > (int)vector->iov_len)
            len = vector->iov_len;
        memmove(vector->iov_base, m_pBufBegin, len);
        m_pBufBegin += len;
        total += len;
        if (len == (int)vector->iov_len)
            ++vector;
        else
        {
            vector->iov_base = (char *)vector->iov_base + len;
            vector->iov_len -= len;
            break;
        }
    }
    int ret;
    if (m_iSsl)
        ret = readvSsl(vector, pEnd);
    else
        ret = ExtConn::readv(vector, pEnd - vector);
    LS_DBG_L(this, "Read Response %d bytes", ret);
    if (ret > 0)
    {
//        int left = ret;
//        const struct iovec* pVec = vector;
//        while( left > 0 )
//        {
//            int writeLen = pVec->iov_len;
//            if ( writeLen > left )
//                writeLen = left;
//            ::write( 1, pVec->iov_base, writeLen );
//            ++pVec;
//            left -= writeLen;
//        }
        m_iRespRecv += ret;
        total += ret;
        return total;
    }
    else if (total)
        return total;
    return ret;
}


int ProxyConn::doRead()
{
    int ret;
    LS_DBG_L(this, "ProxyConn::doRead()");
    if ((m_iSsl) && (!m_ssl.isConnected()))
    {
        ret = connectSSL();
        if (ret != 1)
            return ret;
        return doWrite();
    }

    ret = processResp();
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


int ProxyConn::processResp()
{
    HttpExtConnector *pHEC = getConnector();
    if (!pHEC)
    {
        errno = ECONNRESET;
        return LS_FAIL;
    }
    int len = 0;
    int ret = 0;
    int &respState = pHEC->getRespState();
    if (!(respState & 0xff))
    {
        char *p = HttpResourceManager::getGlobalBuf();
        const char *pBuf = p;
        if (m_iSsl)
            len = m_ssl.read(p, 1460);
        else
            len = ExtConn::read(p, 1460);

        if (len > 0)
        {
            int copy = len;
            if (m_iRespHeaderRecv + copy > 4095)
                copy = 4095 - m_iRespHeaderRecv;
            //memmove( &m_achRespBuf[ m_iRespHeaderRecv ], pBuf, copy );
            m_iRespHeaderRecv += copy;
            m_iRespRecv += len;
            LS_DBG_L(this, "Read Response %d bytes", len);
            //debug code
            //::write( 1, pBuf, len );

            ret = pHEC->parseHeader(pBuf, len, 1);
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
        }
        else
            return len;
        if (respState & 0xff)
        {
            //debug code
            //::write(1, HttpResourceManager::getGlobalBuf(),
            //        pBuf - HttpResourceManager::getGlobalBuf() );
            HttpReq *pReq = pHEC->getHttpSession()->getReq();
            if (pReq->noRespBody())
            {
                incReqProcessed();
                if (len > 0)
                    abort();
                else if (respState & HEC_RESP_CONN_CLOSE)
                    setState(CLOSING);
                else if (getState() == ABORT)
                    setState(PROCESSING);

                setInProcess(0);
                pHEC->endResponse(0, 0);
                return 0;
            }

            m_iRespBodySize = pHEC->getHttpSession()->getResp()->getContentLen();
            LS_DBG_L(this, "Response body size of proxy reply is %lld",
                     (long long)m_iRespBodySize);
            if (m_iRespBodySize == LSI_RSP_BODY_SIZE_CHUNKED)
                setupChunkIS();
            else if (!(respState & HEC_RESP_CONT_LEN))
                m_iRespBodySize = INT_MAX;

            m_pBufBegin = pBuf;
            m_pBufEnd = pBuf + len;
            LS_DBG_M(this, "Process Response body %d bytes", len);
            return readRespBody();
        }
    }
    else
        return readRespBody();
    return 0;
}


int ProxyConn::readRespBody()
{
    HttpExtConnector *pHEC = getConnector();
    int ret = 0;
    size_t bufLen;
    if (!pHEC)
        return LS_FAIL;
    if (m_pChunkIS)
    {
        while (getState() != ABORT && !m_pChunkIS->eos())
        {
            char *pBuf = pHEC->getRespBuf(bufLen);
            if (!pBuf)
                return LS_FAIL;
            ret = m_pChunkIS->read(pBuf, bufLen);
            if (ret >= 0)
            {
                if (ret > 0)
                {
                    m_lLastRespRecvTime = time(NULL);
                    m_iRespBodyRecv += ret;
                    int ret1 = pHEC->processRespBodyData(pBuf, ret);
                    if (ret1 == -1)
                        ret = LS_FAIL;
                    if (ret > 1024 || (ret < (int)bufLen))
                        pHEC->flushResp();
                }
                if (m_pChunkIS->eos())
                {
                    ret = 0;
                    break;
                }
                pHEC->flushResp();
                return ret;
            }
            else
            {
                if ((errno == ECONNRESET) && (getConnector()))
                    break;
                return LS_FAIL;
            }
        }
    }
    else
    {
        while ((getState() != ABORT) && (m_iRespBodySize - m_iRespBodyRecv > 0))
        {
            char *pBuf = pHEC->getRespBuf(bufLen);
            if (!pBuf)
                return LS_FAIL;
            int64_t toRead = m_iRespBodySize - m_iRespBodyRecv;
            if (toRead > (int64_t)bufLen)
                toRead = bufLen ;
            ret = read(pBuf, toRead);
            if (ret > 0)
            {
                m_iRespBodyRecv += ret;
                pHEC->processRespBodyData(pBuf, ret);
                if (ret > 1024)
                    pHEC->flushResp();
                //if ( ret1 )
                //    return ret1;
                if (m_iRespBodySize - m_iRespBodyRecv <= 0)
                    break;
                if (ret < (int)toRead)
                {
                    pHEC->flushResp();
                    return 0;
                }
            }
            else
            {
                if (ret)
                {
                    if ((errno == ECONNRESET) && (getConnector()))
                        break;
                }
                return ret;
            }
        }
    }
    incReqProcessed();
    if (pHEC->getRespState() & HEC_RESP_CONN_CLOSE)
        setState(CLOSING);

    setInProcess(0);
    pHEC->endResponse(0, 0);
    return ret;

}


void ProxyConn::setupChunkIS()
{
    assert(m_pChunkIS == NULL);
    m_pChunkIS = HttpResourceManager::getInstance().getChunkInputStream();
    m_pChunkIS->setStream(this);
    m_pChunkIS->open();
}


int ProxyConn::doError(int err)
{
    LS_DBG_L(this, "ProxyConn::doError()");
    if (getConnector())
    {
        int state = getConnector()->getState();
        if (!(state & (HEC_FWD_RESP_BODY | HEC_ABORT_REQUEST
                       | HEC_ERROR | HEC_COMPLETE)))
        {
            LS_DBG_L(this, "Proxy Peer closed connection, "
                     "try another connection!");
            connError(err);
            return 0;
        }
        if (!(state & HEC_COMPLETE))
            getConnector()->endResponse(SC_500, -1);
    }
    return 0;
}


int ProxyConn::addRequest(ExtRequest *pReq)
{
    assert(pReq);
    setConnector((HttpExtConnector *)pReq);
    reset();
    m_lReqBeginTime = time(NULL);
    return 0;
}


ExtRequest *ProxyConn::getReq() const
{
    return getConnector();
}


int ProxyConn::removeRequest(ExtRequest *pReq)
{
    if (getConnector())
    {
        getConnector()->setProcessor(NULL);
        setConnector(NULL);
    }
    return 0;
}


int  ProxyConn::endOfReqBody()
{
    if (m_iTotalPending)
    {
        int ret = flush();
        if (ret)
            return ret;
    }
    suspendWrite();
    m_lReqSentTime = time(NULL);
    return 0;
}


int  ProxyConn::flush()
{
    if (m_iTotalPending)
    {
        int ret;
        int finished = 0;
        if (m_iSsl)
            ret = m_ssl.writev(m_iovec.get(), m_iovec.len(), &finished);
        else
            ret = writev(m_iovec, m_iTotalPending);
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


void ProxyConn::finishRecvBuf()
{
    //doRead();
}


void ProxyConn::cleanUp()
{
    setConnector(NULL);
    reset();
    recycle();
}


void ProxyConn::onTimer()
{
//    if (!( getEvents() & POLLIN ))
//    {
//        LS_WARN( this, "Oops! POLLIN is turned off for this proxy connection,"
//                 " turn it on, this should never happen!!!!");
//        continueRead();
//    }
//    if (( m_iTotalPending > 0 )&& !( getEvents() & POLLOUT ))
//    {
//        LS_WARN( this, "Oops! POLLOUT is turned off while there is pending data,"
//                    " turn it on, this should never happen!!!!");
//        continueWrite();
//    }
    if (m_lLastRespRecvTime)
    {
        long tm = time(NULL);
        long delta = tm - m_lLastRespRecvTime;
        if ((delta > getWorker()->getTimeout()) && (m_iRespBodyRecv))
        {
            if (m_pChunkIS)
            {
                LS_INFO(this, "Timeout, partial chunk encoded body received,"
                        " received: %lld, chunk len: %d, remain: %d!",
                        (long long)m_iRespBodyRecv, m_pChunkIS->getChunkLen(),
                        m_pChunkIS->getChunkRemain());
            }
            else
                LS_INFO(this, "Timeout, partial response body received,"
                        " body len: %lld, received: %lld!",
                        (long long)m_iRespBodySize, (long long)m_iRespBodyRecv);
            setState(ABORT);
            getConnector()->endResponse(0, 0);
            return;
        }
        else if ((m_pChunkIS) && (!m_pChunkIS->getChunkLen()) && (delta > 1))
        {
            if ((getConnector()))
            {
                LS_DBG_L(this, "Missing trailing CRLF in Chunked Encoding,"
                         " remain: %d!", m_pChunkIS->getChunkRemain());
//                const char * p = m_pChunkIS->getLastBytes();
//                LS_INFO(this,
//                        "Last 8 bytes are: %#x %#x %#x %#x %#x %#x %#x %#x",
//                        p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7]);
//                HttpReq * pReq = getConnector()->getHttpSession()->getReq();
//                pReq->dumpHeader();

                setState(CLOSING);
                getConnector()->endResponse(0, 0);
                return;
            }
        }
    }

    ExtConn::onTimer();
}


bool ProxyConn::wantRead()
{
    return false;
}


bool ProxyConn::wantWrite()
{
    return false;
}


int  ProxyConn::readResp(char *pBuf, int size)
{
    return 0;
}


void ProxyConn::dump()
{
    LS_INFO(this,
            "Proxy connection state: %d, watching event: %d, "
            "Request header:%d, body:%lld, sent:%lld, "
            "Response header: %d, total: %d bytes received in %ld seconds,"
            "Total processing time: %ld.",
            getState(), getEvents(), m_iReqHeaderSize,
            (long long)m_iReqBodySize, (long long)m_iReqTotalSent, 
            m_iRespHeaderRecv, m_iRespRecv,
            (m_lReqSentTime) ? time(NULL) - m_lReqSentTime : 0,
            time(NULL) - m_lReqBeginTime);
//    if ( m_iRespHeaderRecv > 0 )
//    {
//        m_achRespBuf[ m_iRespHeaderRecv ] = 0;
//        LS_INFO(this, "Response Header Received:%s", m_achRespBuf);
//    }
}



