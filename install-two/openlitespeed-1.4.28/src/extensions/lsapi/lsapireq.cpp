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
#include "lsapireq.h"
#include <http/httpcontext.h>
#include <http/httpcgitool.h>
#include <http/httpmethod.h>
#include <http/httpserverversion.h>
#include <http/httpsession.h>
#include <http/httpver.h>
#include <http/phpconfig.h>
#include <util/ienv.h>
#include <util/iovec.h>

#include <fcntl.h>
#include <unistd.h>

class LsapiEnv : public IEnv
{
    AutoBuf *m_pBuf;
public:
    LsapiEnv(AutoBuf *pBuf) : m_pBuf(pBuf) {};
    ~LsapiEnv() {}

    int add(const char *name, size_t nameLen,
            const char *value, size_t valLen)
    {
        return LsapiReq::addEnv(m_pBuf, name, nameLen, value, valLen);
    }
    static int add(AutoBuf *pBuf, const char *name, size_t nameLen,
                   const char *value, size_t valLen);
    int add(const char *buf, size_t len)
    {   return -1;      }
    void clear() {}
    const char *get() const {  return NULL;   }
    int bufSize() const      {  return m_pBuf->size();      }
    LS_NO_COPY_ASSIGN(LsapiEnv);
};


int LsapiReq::addEnv(AutoBuf *pAutoBuf, const char *name, size_t nameLen,
                     const char *value, size_t valLen)
{
    if (!name)
        return 0;
    //assert( value );
    //assert( nameLen == strlen( name ) );
    //assert( valLen == strlen( value ) );
    if ((nameLen > 1024) || (valLen > 65535))
        return 0;
    int bufLen = pAutoBuf->available();
    if (bufLen < (int)(nameLen + valLen + 6))
    {
        int grow = ((nameLen + valLen + 6 - bufLen + 1023) >> 10) << 10;
        int ret = pAutoBuf->grow(grow);
        if (ret == -1)
            return ret;
    }
    char *pBuf = pAutoBuf->end();
    *pBuf++ = ((nameLen + 1) >> 8) & 0xff;
    *pBuf++ = (nameLen + 1) & 0xff;
    *pBuf++ = ((valLen + 1) >> 8) & 0xff;
    *pBuf++ = (valLen + 1) & 0xff;
    memmove(pBuf, name, nameLen);
    pBuf += nameLen;
    *pBuf++ = 0;
    memmove(pBuf, value, valLen);
    pBuf += valLen;
    *pBuf++ = 0;
    pAutoBuf->used(pBuf - pAutoBuf->end());
    return 0;
}


LsapiReq::LsapiReq(IOVec *pVec)
    : m_bufReq(4096)
    , m_pIovec(pVec)

{
}


LsapiReq::~LsapiReq()
{
}


int LsapiReq::appendEnv(LsapiEnv *pEnv, HttpSession *pSession)
{
    HttpReq *pReq = pSession->getReq();
    int n;
    int count = HttpCgiTool::buildCommonEnv(pEnv, pSession);
    const AutoStr2 *psTemp = pReq->getRealPath();
    if (psTemp)
    {
        pEnv->add("SCRIPT_FILENAME", 15, psTemp->c_str(), psTemp->len());
        ((lsapi_req_header *)m_bufReq.begin())->m_scriptFileOff = pEnv->bufSize() -
                psTemp->len() - 1;
        ++count;
    }
    pEnv->add("QUERY_STRING", 12, pReq->getQueryString(),
              pReq->getQueryStringLen());
    ((lsapi_req_header *)m_bufReq.begin())->m_queryStringOff =
        pEnv->bufSize() - pReq->getQueryStringLen() - 1;
    const char *pTemp = pReq->getURI();
    pEnv->add("SCRIPT_NAME", 11, pTemp, pReq->getScriptNameLen());
    ((lsapi_req_header *)m_bufReq.begin())->m_scriptNameOff =
        pEnv->bufSize() - pReq->getScriptNameLen() - 1;

    n = pReq->getVersion();
    pEnv->add("SERVER_PROTOCOL", 15, HttpVer::getVersionString(n),
              HttpVer::getVersionStringLen(n));
    pEnv->add("SERVER_SOFTWARE", 15, HttpServerVersion::getVersion(),
              HttpServerVersion::getVersionLen());
    n = pReq->getMethod();
    pEnv->add("REQUEST_METHOD", 14, HttpMethod::get(n),
              HttpMethod::getLen(n));
    ((lsapi_req_header *)m_bufReq.begin())->m_requestMethodOff =
        pEnv->bufSize() - HttpMethod::getLen(n) - 1;
    count += 5;
    ((lsapi_req_header *)m_bufReq.begin())->m_cntEnv = count;
    m_bufReq.append("\0\0\0\0", 4);
    return 0;
}


int LsapiReq::appendSpecialEnv(LsapiEnv *pEnv, HttpSession *pSession,
                               struct lsapi_req_header *pHeader)
{
    //pHeader->m_cntSpecialEnv = 1;
    //pEnv->add( "\001\004safe_mode", 11, "1", 1 );
    PHPConfig *pConfig = pSession->getReq()->getContext()->getPHPConfig();
    if (pConfig)
    {
        pHeader->m_cntSpecialEnv = pConfig->getCount();
        m_bufReq.append(pConfig->getLsapiEnv().begin(),
                        pConfig->getLsapiEnv().size());

    }
    else
        pHeader->m_cntSpecialEnv = 0;
    m_bufReq.append("\0\0\0\0", 4);
    return 0;
}


int LsapiReq::appendHttpHeaderIndex(HttpReq *pReq, int cntUnknown)
{
    pReq->appendHeaderIndexes(m_pIovec, cntUnknown);
    return 0;
}


int LsapiReq::buildReq(HttpSession *pSession, int *totalLen)
{
    int ret;
    LsapiEnv env(&m_bufReq);


    HttpReq *pReq = pSession->getReq();
    lsapi_req_header *pHeader = (lsapi_req_header *)m_bufReq.begin();
    m_bufReq.resize(sizeof(lsapi_req_header));

    pHeader->m_httpHeaderLen    = pReq->getHttpHeaderEnd();
    if (pReq->getContentLength() >= 2 * 1024 * 1024 * 1024LL)
        pHeader->m_reqBodyLen = -2;
    else
        pHeader->m_reqBodyLen       = pReq->getContentLength();
    pHeader->m_cntUnknownHeaders = pReq->getUnknownHeaderCount();

    ret = appendSpecialEnv(&env, pSession, pHeader);
    if (ret)
        return ret;
    ret = appendEnv(&env, pSession);
    if (ret)
        return ret;
    int pad = (8 - (m_bufReq.size() % 8)) % 8;
    m_bufReq.append("\0\0\0\0\0\0\0", pad);
    *totalLen = m_bufReq.size() + sizeof(lsapi_http_header_index)
                + ((lsapi_req_header *)m_bufReq.begin())->m_cntUnknownHeaders *
                sizeof(lsapi_header_offset)
                + ((lsapi_req_header *)m_bufReq.begin())->m_httpHeaderLen;
    buildPacketHeader(&((lsapi_req_header *)m_bufReq.begin())->m_pktHeader,
                      LSAPI_BEGIN_REQUEST,
                      *totalLen);
    m_pIovec->append(m_bufReq.begin(), m_bufReq.size());

    ret = appendHttpHeaderIndex(pReq,
                                ((lsapi_req_header *)m_bufReq.begin())->m_cntUnknownHeaders);
    if (ret)
        return ret;

    m_pIovec->append(pReq->getHeaderBuf().begin(), pReq->getHttpHeaderEnd());
    //test code
    //dumpReq( "/home/gwang/lsapi_req_dump.bin" );
    return 0;
}


int LsapiReq::dumpReq(char *pFile)
{
    //test code
    int fd = open(pFile, O_RDWR | O_CREAT | O_TRUNC, 0600);
    writev(fd, m_pIovec->get(), m_pIovec->len());
    close(fd);
    return 0;
}


