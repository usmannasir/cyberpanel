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
#include "httpfetch.h"

#include <adns/adns.h>
#include <lsr/ls_fileio.h>
#include <lsr/ls_strtool.h>
#include <log4cxx/logger.h>
#include <socket/coresocket.h>
#include <socket/gsockaddr.h>
#include <sslpp/sslcontext.h>
#include <sslpp/sslerror.h>
#include <util/httpfetchdriver.h>
#include <util/vmembuf.h>

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static int HttpFetchCounter = 0;

HttpFetch::HttpFetch()
    : m_iFdHttp(-1)
    , m_pBuf(NULL)
    , m_iStatusCode(0)
    , m_pReqBuf(NULL)
    , m_iReqBufLen(0)
    , m_iReqSent(0)
    , m_iReqHeaderLen(0)
    , m_iHostLen(0)
    , m_iNonBlocking(0)
    , m_iEnableDriver(0)
    , m_pReqBody(NULL)
    , m_iReqBodyLen(0)
    , m_iConnTimeout(20)
    , m_pRespContentType(NULL)
    , m_pProxyAddrStr(NULL)
    , m_pProxyAddr(NULL)
    , m_pAdnsReq(NULL)
    , m_pfProcessor(NULL)
    , m_iSsl(0)
    , m_pDriver(NULL)
    , m_iTimeoutSec(-1)
    , m_iReqInited(0)
    , m_iEnableDebug(0)
{
    m_pLogger = Logger::getRootLogger();
    m_iLoggerId = HttpFetchCounter ++;
    //m_pLogger->debug( "HttpFetch[%d]::HttpFetch()", getLoggerId() );
}

HttpFetch::~HttpFetch()
{
    closeConnection();
    if (m_pBuf)
        delete m_pBuf;
    if (m_pReqBuf)
        free(m_pReqBuf);
    if (m_pRespContentType)
        free(m_pRespContentType);
    if (m_pAdnsReq)
        m_pAdnsReq->setCallback(NULL);
    if (m_pProxyAddrStr)
        free(m_pProxyAddrStr);
    if (m_pProxyAddr)
        delete m_pProxyAddr;
    if (m_pDriver)
        delete m_pDriver;
}

void HttpFetch::releaseResult()
{
    if (m_pBuf)
    {
        m_pBuf->close();
        delete m_pBuf;
        m_pBuf = NULL;
    }
    if (m_pRespContentType)
    {
        free(m_pRespContentType);
        m_pRespContentType = NULL;
    }
}

void HttpFetch::reset()
{
    closeConnection();
    if (m_pReqBuf)
    {
        free(m_pReqBuf);
        m_pReqBuf = NULL;
    }
    releaseResult();
    m_iStatusCode    = 0;
    m_iReqBufLen     = 0;
    m_iReqSent       = 0;
    m_iReqHeaderLen  = 0;
    m_iHostLen       = 0;
    m_iReqBodyLen    = 0;
    m_iReqInited     = 0;
    if (m_pProxyAddr)
    {
        delete m_pProxyAddr;
        m_pProxyAddr = NULL;
    }
}

int HttpFetch::allocateBuf(const char *pSaveFile)
{
    int ret;
    if (m_pBuf != NULL)
        delete m_pBuf;
    m_pBuf = new VMemBuf();
    if (!m_pBuf)
        return LS_FAIL;
    if (pSaveFile)
    {
        ret = m_pBuf->set(pSaveFile, 8192);
        if (ret != 0)
        {
            LS_ERROR(m_pLogger, "HttpFetch[%d]::failed to create file %s: %s.",
                             getLoggerId(), pSaveFile, strerror(errno));
        }
        else if (m_iEnableDebug)
        {
            LS_DBG_M(m_pLogger, "HttpFetch[%d]::allocateBuf File %s created.",
                    getLoggerId(), pSaveFile);
        }
    }
    else
        ret = m_pBuf->set(VMBUF_ANON_MAP, 8192);
    return ret;

}

int HttpFetch::initReq(const char *pURL, HttpFetchSecure isSecure,
                       const char *pBody, int bodyLen,
                       const char *pSaveFile, const char *pContentType)
{
    if (m_iReqInited)
        return 0;
    m_iReqInited = 1;

    if (m_iFdHttp != -1)
        return LS_FAIL;

    switch (isSecure)
    {
    case HF_UNKNOWN:
        if (strncasecmp(pURL, "https", 5) != 0)
            break;
        // fall through
    case HF_SECURE:
        setUseSsl(1);
        if ((m_iSsl) && (m_ssl.getSSL()))
            m_ssl.release();
        break;
    default:
        break;
    };

    m_pReqBody = pBody;
    if (m_pReqBody)
    {
        m_iReqBodyLen = bodyLen;
        if (buildReq("POST", pURL, pContentType) == -1)
            return LS_FAIL;
    }
    else
    {
        m_iReqBodyLen = 0;
        if (buildReq("GET", pURL) == -1)
            return LS_FAIL;
    }

    if (allocateBuf(pSaveFile) == -1)
        return LS_FAIL;

    if (m_iEnableDebug)
        LS_DBG_M(m_pLogger, "HttpFetch[%d]::intiReq url=%s", getLoggerId(),
                 pURL);
    return 0;
}

int HttpFetch::asyncDnsLookupCb(void *arg, const long lParam, void *pParam)
{
    HttpFetch *pFetch = (HttpFetch *)arg;
    if (lParam > 0)
    {
        pFetch->startProcess();
    }
    else
        pFetch->endReq(-1);

    return 0;
}

int HttpFetch::startDnsLookup(const char *addrServer)
{
    m_pProxyAddr = new GSockAddr();
    int flag = NO_ANY;
    int ret;
    AdnsReq *pReq = NULL;
    if (!m_iEnableDriver)
    {
        flag |= DO_NSLOOKUP_DIRECT;
        ret = m_pProxyAddr->set(PF_INET, addrServer, flag);
    }
    else
    {
        ret = m_pProxyAddr->asyncSet(PF_INET, addrServer, flag,
                                      asyncDnsLookupCb, this, &pReq );
        m_pAdnsReq = pReq;
    }
    if (ret == 0)
        return startProcess();
     return ret;
}

static SSL *getSslContext()
{
    static SslContext *s_pFetchCtx = NULL;
    if (!s_pFetchCtx)
    {
        s_pFetchCtx = new SslContext();
        if (s_pFetchCtx)
        {
            s_pFetchCtx->setRenegProtect(0);
            //s_pFetchCtx->setCipherList();
        }
        else
            return NULL;
    }
    return s_pFetchCtx->newSSL();
}


void HttpFetch::setSSLAgain()
{
    if (m_ssl.wantRead())
        m_pDriver->switchWriteToRead();
    if (m_ssl.wantWrite())
        m_pDriver->switchReadToWrite();
}

int HttpFetch::connectSSL()
{
    if (!m_ssl.getSSL())
    {
        m_ssl.setSSL(getSslContext());
        if (!m_ssl.getSSL())
            return LS_FAIL;
        m_ssl.setfd(m_iFdHttp);
        char ch = m_aHost[m_iHostLen];
        m_aHost[m_iHostLen] = 0;
        m_ssl.setTlsExtHostName(m_aHost);
        m_aHost[m_iHostLen] = ch;
    }
    int ret = m_ssl.connect();
    switch (ret)
    {
    case 0:
        setSSLAgain();
        break;
    case 1:
        LS_DBG_M(m_pLogger, "HttpFetch[%d]:: [SSL] connected",
                 getLoggerId());
        break;
    default:
        if (errno == EIO)
            LS_DBG_M(m_pLogger, "HttpFetch[%d]:: SSL_connect() failed!: %s",
                    getLoggerId(), SslError().what());
        break;
    }

    return ret;
}

int HttpFetch::startReq(const char *pURL, int nonblock, int enableDriver,
                        const char *pBody, int bodyLen, const char *pSaveFile,
                        const char *pContentType, const char *addrServer,
                        HttpFetchSecure isSecure)
{
    if (initReq(pURL, isSecure, pBody, bodyLen, pSaveFile, pContentType) != 0)
        return LS_FAIL;
    m_iNonBlocking = nonblock;
    m_iEnableDriver = (enableDriver || isUseSsl());

    if (m_pProxyAddr)
        return startReq(pURL, nonblock, enableDriver, pBody, bodyLen,
                        pSaveFile, pContentType, *m_pProxyAddr, isSecure);
    if (m_iEnableDebug)
        LS_DBG_M(m_pLogger, "HttpFetch[%d]:: Host is [%s]",
                 getLoggerId(), m_aHost);

    if (addrServer == NULL)
        addrServer = m_aHost;
    return startDnsLookup(addrServer);
}

int HttpFetch::startReq(const char *pURL, int nonblock, int enableDriver,
                        const char *pBody, int bodyLen, const char *pSaveFile,
                        const char *pContentType, const GSockAddr &sockAddr,
                        HttpFetchSecure isSecure)
{
    if (initReq(pURL, isSecure, pBody, bodyLen, pSaveFile, pContentType) != 0)
        return LS_FAIL;
    m_iNonBlocking = nonblock;
    m_iEnableDriver = (enableDriver || isUseSsl());

    m_pProxyAddr = new GSockAddr(sockAddr);

    return startProcess();
}


int HttpFetch::startProcess()
{
    if (m_iEnableDriver)
        m_pDriver = new HttpFetchDriver(this);
    if (m_iTimeoutSec <= 0)
        m_iTimeoutSec = 60;
    m_tmStart = time(NULL);

    return startProcessReq(*m_pProxyAddr);

}

int HttpFetch::buildReq(const char *pMethod, const char *pURL,
                        const char  *pContentType)
{
    int len = strlen(pURL) + 200;
    char *pReqBuf;
    const char *pURI;
    if ((strncasecmp(pURL, "http://", 7) != 0) &&
        (strncasecmp(pURL, "https://", 8) != 0))
        return LS_FAIL;
    if (pContentType == NULL)
        pContentType = "application/x-www-form-urlencoded";
    const char *p = pURL + 7;
    if (*(pURL + 4) != ':')
        ++p;
    pURI = strchr(p, '/');
    if (!pURI)
        return LS_FAIL;
    if (pURI - p > 250)
        return LS_FAIL;
    m_iHostLen = pURI - p;
    memcpy(m_aHost, p, m_iHostLen);
    m_aHost[ m_iHostLen ] = 0;
    if (m_iHostLen == 0)
        return LS_FAIL;
    if (m_iReqBufLen < len)
    {
        pReqBuf = (char *)realloc(m_pReqBuf, len);
        if (pReqBuf == NULL)
            return LS_FAIL;
        m_iReqBufLen = len;
        m_pReqBuf = pReqBuf;
    }
    m_iReqHeaderLen = ls_snprintf(m_pReqBuf, len,
                                  "%s %s HTTP/1.0\r\n"
                                  "Host: %s\r\n"
                                  "Connection: Close\r\n",
                                  pMethod, pURI, m_aHost);
    if (m_iReqBodyLen > 0)
    {
        m_iReqHeaderLen += ls_snprintf(m_pReqBuf + m_iReqHeaderLen,
                                       len - m_iReqHeaderLen,
                                       "Content-Type: %s\r\n"
                                       "Content-Length: %d\r\n",
                                       pContentType,
                                       m_iReqBodyLen);
    }
    strcpy(m_pReqBuf + m_iReqHeaderLen, "\r\n");
    if (strchr(m_aHost, ':') == NULL)
        strcat(m_aHost, (m_iSsl ? ":443" : ":80"));
    m_iReqHeaderLen += 2;
    m_iReqSent = 0;
    if (m_iEnableDebug)
        LS_DBG_M(m_pLogger, "HttpFetch[%d]::buildReq Host=%s [0]", getLoggerId(),
                 m_aHost);
    return 0;

}


int HttpFetch::pollEvent(int evt, int timeoutSecs)
{
    struct pollfd  pfd;
    pfd.events = evt;
    pfd.fd = m_iFdHttp;
    pfd.revents = 0;

    return poll(&pfd, 1, timeoutSecs * 1000);

}


int HttpFetch::startProcessReq(const GSockAddr &sockAddr)
{
    m_iReqState = 0;

    if (m_iEnableDebug)
        LS_DBG_M(m_pLogger, "HttpFetch[%d]::startProcessReq sockAddr=%s",
                 getLoggerId(), sockAddr.toString());
    int ret = CoreSocket::connect(sockAddr, O_NONBLOCK, &m_iFdHttp);
    if (m_iFdHttp == -1)
        return LS_FAIL;
    ::fcntl(m_iFdHttp, F_SETFD, FD_CLOEXEC);
    startDriver();

    if (!m_iNonBlocking)
    {
        if ((ret = pollEvent(POLLIN|POLLOUT, m_iConnTimeout)) != 1)
        {
            closeConnection();
            return -1;
        }
        else
        {
            int error;
            socklen_t len = sizeof(int);
            ret = getsockopt(m_iFdHttp, SOL_SOCKET, SO_ERROR, &error, &len);
            if ((ret == -1) || (error != 0))
            {
                if (ret != -1)
                    errno = error;
                endReq(-1);
                return LS_FAIL;
            }
        }
        int val = fcntl(m_iFdHttp, F_GETFL, 0);
        fcntl(m_iFdHttp, F_SETFL, val & (~O_NONBLOCK));
    }
    if (ret == 0)
    {
        m_iReqState = 2; //connected, sending request header
        ret = sendReq();
    }
    else
        m_iReqState = 1; //connecting

    if (m_iEnableDebug)
        LS_DBG_M(m_pLogger, "HttpFetch[%d]::startProcessReq ret=%d state=%d",
                 getLoggerId(), ret, m_iReqState);
    return ret;
}


short HttpFetch::getPollEvent() const
{
    if (m_iReqState <= 3)
        return POLLOUT;
    else
        return POLLIN;
}

int HttpFetch::sendReq()
{
    int error;
    int ret = 0;
    switch (m_iReqState)
    {
    case 1: //connecting
        {
            socklen_t len = sizeof(int);
            ret = getsockopt(m_iFdHttp, SOL_SOCKET, SO_ERROR, &error, &len);
        }
        if ((ret == -1) || (error != 0))
        {
            if (ret != -1)
                errno = error;
            endReq(-1);
            return LS_FAIL;
        }
        m_iReqState = 2;
    //fall through
    case 2:
        if ((m_iSsl) && (!m_ssl.isConnected()))
        {
            ret = connectSSL();
            if (ret != 1)
                return ret;
        }
        if (m_iSsl)
            ret = m_ssl.write(m_pReqBuf + m_iReqSent, m_iReqHeaderLen - m_iReqSent);
        else
            ret = ::ls_fio_write(m_iFdHttp, m_pReqBuf + m_iReqSent,
                                m_iReqHeaderLen - m_iReqSent);
        //write( 1, m_pReqBuf + m_reqSent, m_reqHeaderLen - m_reqSent );
        if (m_iEnableDebug)
            LS_DBG_M(m_pLogger,
                     "HttpFetch[%d]::sendReq::nio_write fd=%d len=%d [%d - %d] ret=%d",
                     getLoggerId(), m_iFdHttp,
                     m_iReqHeaderLen - m_iReqSent, m_iReqHeaderLen, m_iReqSent, ret);
        if (ret > 0)
            m_iReqSent += ret;
        else if (ret == -1)
        {
            if (errno != EAGAIN)
            {
                endReq(-1);
                return LS_FAIL;
            }
        }
        if (m_iReqSent >= m_iReqHeaderLen)
        {
            m_iReqState = 3;
            m_iReqSent = 0;
        }
        else
            break;
    //fall through
    case 3: //send request body
        if (m_iReqBodyLen)
        {
            if (m_iReqSent < m_iReqBodyLen)
            {
                if (m_iSsl)
                    ret = m_ssl.write(m_pReqBody + m_iReqSent,
                                     m_iReqBodyLen - m_iReqSent);
                else
                    ret = ::ls_fio_write(m_iFdHttp, m_pReqBody + m_iReqSent,
                                     m_iReqBodyLen - m_iReqSent);
                //write( 1, m_pReqBody + m_reqSent, m_reqBodyLen - m_reqSent );
                if (ret == -1)
                {
                    if (errno != EAGAIN)
                    {
                        endReq(-1);
                        return LS_FAIL;
                    }
                    return LS_FAIL;
                }
                if (ret > 0)
                    m_iReqSent += ret;
                if (m_iReqSent < m_iReqBodyLen)
                    break;
            }
        }
        m_resHeaderBuf.clear();
        m_iReqState = 4;
    }
    if ((ret == -1) && (errno != EAGAIN))
        return LS_FAIL;
    return 0;
}


int HttpFetch::getLine(char *&p, char *pEnd,
                       char *&pLineBegin, char *&pLineEnd)
{
    int ret = 0;
    pLineBegin = NULL;
    pLineEnd = (char *)memchr(p, '\n', pEnd - p);
    if (!pLineEnd)
    {
        if (pEnd - p + m_resHeaderBuf.size() < 8192)
        {
            m_resHeaderBuf.append(p, pEnd - p);
        }
        else
            ret = -1;
        p = pEnd;
    }
    else
    {
        if (m_resHeaderBuf.size() == 0)
        {
            pLineBegin = p;
            p = pLineEnd + 1;
            if (m_iEnableDebug)
                LS_DBG_M(m_pLogger,
                         "HttpFetch[%d] pLineBegin: %p, pLineEnd: %p",
                        getLoggerId(), pLineBegin, pLineEnd);
        }
        else
        {
            if (pLineEnd - p + m_resHeaderBuf.size() < 8192)
            {
                m_resHeaderBuf.append(p, pLineEnd - p);
                p = pLineEnd + 1;
                pLineBegin = m_resHeaderBuf.begin();
                pLineEnd = m_resHeaderBuf.end();
                m_resHeaderBuf.clear();
                if (m_iEnableDebug)
                    LS_DBG_M(m_pLogger,
                             "HttpFetch[%d] Combined pLineBegin: %p, pLineEnd: %p",
                             getLoggerId(), pLineBegin, pLineEnd);
            }
            else
            {
                if (m_iEnableDebug)
                    LS_DBG_M(m_pLogger,
                             "HttpFetch[%d] line too long, fail request.",
                             getLoggerId());
                ret = -1;
                p = pEnd;
            }
        }
        if (pLineBegin)
        {
            if (*(pLineEnd - 1) == '\r')
                --pLineEnd;
            *pLineEnd = 0;
        }
    }
    return ret;
}


int HttpFetch::recvResp()
{
    int ret = 0;
    int len;
    char *p;
    char *pEnd;
    char *pLineBegin;
    char *pLineEnd;
    AutoBuf buf(8192);
    while (m_iStatusCode != -1)
    {
        ret = pollEvent(POLLIN, 1);
        if (ret != 1)
            break;
        if (m_iSsl)
            ret = m_ssl.read(buf.begin(), 8192);
        else
            ret = ::ls_fio_read(m_iFdHttp, buf.begin(), 8192);
        if (m_iEnableDebug)
            LS_DBG_M(m_pLogger, "HttpFetch[%d]::recvResp fd=%d ret=%d",
                     getLoggerId(), m_iFdHttp, ret);
        if (ret == 0)
        {
            if (m_iRespBodyLen == -1)
                return endReq(0);
            else
            {
                endReq(-1);
                return -1;
            }
        }

        if (ret <= 0)
            break;
        p = buf.begin();
        pEnd = p + ret;
        while (p < pEnd)
        {
            switch (m_iReqState)
            {
            case 4: //waiting response status line
                if (getLine(p, pEnd, pLineBegin, pLineEnd))
                {
                    endReq(-1);
                    return -1;
                }
                if (pLineBegin)
                {
                    if (memcmp(pLineBegin, "HTTP/1.", 7) != 0)
                    {
                        endReq(-1);
                        return -1;
                    }
                    pLineBegin += 9;
                    if (!isdigit(*pLineBegin) || !isdigit(*(pLineBegin + 1)) ||
                        !isdigit(*(pLineBegin + 2)))
                    {
                        endReq(-1);
                        return -1;
                    }
                    m_iStatusCode = (*pLineBegin     - '0') * 100 +
                                    (*(pLineBegin + 1) - '0') * 10 +
                                    *(pLineBegin + 2) - '0';
                    m_iReqState = 5;
                    m_iRespBodyLen = -1;
                }
                else
                    break;
            //fall through
            case 5: //waiting response header
                if (getLine(p, pEnd, pLineBegin, pLineEnd))
                {
                    endReq(-1);
                    return -1;
                }
                if (pLineBegin)
                {
                    if (strncasecmp(pLineBegin, "Content-Length:", 15) == 0)
                        m_iRespBodyLen = strtol(pLineBegin + 15, (char **)NULL, 10);
                    else if (strncasecmp(pLineBegin, "Content-Type:", 13) == 0)
                    {
                        pLineBegin += 13;
                        while ((pLineBegin < pLineEnd) && isspace(*pLineBegin))
                            ++pLineBegin;
                        if (pLineBegin < pLineEnd)
                        {
                            if (m_pRespContentType)
                                free(m_pRespContentType);
                            m_pRespContentType = strdup(pLineBegin);
                        }
                    }
                    else if (pLineBegin == pLineEnd)
                    {
                        m_iReqState = 6;
                        m_iRespBodyRead = 0;
                        if ((m_iRespBodyLen == 0) || (m_iRespBodyLen < -1))
                            return endReq(0);

                    }

                }
                break;
            case 6: //waiting response body
                if ((len = m_pBuf->write(p, pEnd - p)) == -1)
                {
                    endReq(-1);
                    return -1;
                }
                if ((m_iRespBodyLen > 0) && (m_pBuf->writeBufSize() >= m_iRespBodyLen))
                    return endReq(0);
                p += len;
                break;
            }
        }
    }
    if ((ret == -1) && (errno != EAGAIN) && (errno != ETIMEDOUT))
        return LS_FAIL;
    return 0;
}


int HttpFetch::endReq(int res)
{
    if (m_pBuf)
    {
        if (res == 0)
        {
            m_iReqState = 7;
            if (m_pBuf->getFd() != -1)
                m_pBuf->exactSize();
        }
//        m_pBuf->close();
    }
    if (res != 0)
    {
        m_iReqState = 8;
        m_iStatusCode = res;
    }
    if (m_iFdHttp != -1)
        closeConnection();
    if (m_pfProcessor != NULL)
        (*m_pfProcessor)(m_pProcessorArg, this);
    return 0;
}


int HttpFetch::cancel()
{
    return endReq(-1);
}


int HttpFetch::processEvents(short revent)
{
    if (revent & POLLOUT)
        if (sendReq() == -1)
            return -1;
    if (revent & POLLIN)
        if (recvResp() == -1)
            return -1;
    if (revent & POLLERR)
        endReq(-1);
    return 0;
}


int HttpFetch::process()
{
    while ((m_iFdHttp != -1) && (m_iReqState < 4))
        sendReq();
    while ((m_iFdHttp != -1) && (m_iReqState < 7)
        && m_tmStart + m_iTimeoutSec > time(NULL))
        recvResp();
    return (m_iReqState == 7) ? 0 : -1;
}


void HttpFetch::setProxyServerAddr(const char *pAddr)
{
    if (m_pProxyAddr)
        delete  m_pProxyAddr;

    if (pAddr)
    {
        m_pProxyAddr = new GSockAddr();
        if (m_pProxyAddr->set(pAddr, NO_ANY | DO_NSLOOKUP) == -1)
        {
            delete m_pProxyAddr;
            m_pProxyAddr = NULL;
            LS_ERROR(m_pLogger,
                     "HttpFetch[%d] invalid proxy server address '%s', ignore.",
                     getLoggerId(), pAddr);
            return;
        }

        if (m_iEnableDebug)
            LS_DBG_M(m_pLogger, "HttpFetch[%d]::setProxyServerAddr %s",
                     getLoggerId(), pAddr);
        if (m_pProxyAddrStr)
            free(m_pProxyAddrStr);
        m_pProxyAddrStr = strdup(pAddr);
    }
}

void HttpFetch::closeConnection()
{
    if (m_iFdHttp != -1)
    {
        if (m_iSsl && m_ssl.getSSL())
        {
            LS_DBG_L("Shutdown HttpFetch SSL ...");
            m_ssl.release();
        }

        if (m_iEnableDebug)
            LS_DBG_M(m_pLogger, "HttpFetch[%d]::closeConnection fd=%d ",
                     getLoggerId(), m_iFdHttp);
        close(m_iFdHttp);
        m_iFdHttp = -1;
        stopDriver();
    }
}

void HttpFetch::startDriver()
{
    if (m_pDriver)
    {
        m_pDriver->setfd(m_iFdHttp);
        m_pDriver->start();
    }
}

void HttpFetch::stopDriver()
{
    if (m_pDriver)
    {
        m_pDriver->stop();
        m_pDriver->setfd(-1);
    }
}

