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
#include "httpreq.h"

#include <http/accesscache.h>
#include <http/denieddir.h>
#include <http/handlertype.h>
#include <http/hotlinkctrl.h>
#include <http/htauth.h>
#include <http/httpcontext.h>
#include <http/httpdefs.h>
#include <http/httpmethod.h>
#include <http/httpmime.h>
#include <http/httpresourcemanager.h>
#include <http/httpserverconfig.h>
#include <http/httpstatuscode.h>
#include <http/httpver.h>
#include <http/httpvhost.h>
#include <http/serverprocessconfig.h>
#include <http/vhostmap.h>
#include "staticfilecachedata.h"
#include <log4cxx/logger.h>
#include <lsr/ls_fileio.h>
#include <lsr/ls_hash.h>
#include <lsr/ls_strtool.h>
#include <lsr/ls_xpool.h>
#include <ssi/ssiruntime.h>
#include <util/blockbuf.h>
#include <util/gpath.h>
#include <util/httputil.h>
#include <util/iovec.h>
#include <util/radixtree.h>
#include <util/vmembuf.h>
#include <util/datetime.h>

#include <ctype.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include <new>



#define URL_INDEX_PAD 32

struct envAlias_t
{
    const char *orgName;
    unsigned short orgNameLen;
    const char *inuseName;
    unsigned short inuseNameLen;
};


const envAlias_t envAlias[] =
{
    {"cache-control", 13, "LS_CACHE_CTRL", 13},
};


#define HEADER_BUF_INIT_SIZE 2048
#define REQ_BUF_INIT_SIZE    1024
static const char s_hex[17] = "0123456789ABCDEF";
static char *escape_uri(char *p, char *pEnd, const char *pURI, int uriLen)
{
    const char *pURIEnd = pURI + uriLen;
    char ch;
    while ((pURI < pURIEnd) && (p < pEnd))
    {
        ch = *pURI++;
        if (isalnum(ch))
            *p++ = ch;
        else
        {
            switch (ch)
            {
            case '_':
            case '-':
            case '!':
            case '~':
            case '*':
            case '\\':
            case '(':
            case ')':
            case '/':
            case '\'':
            case ';':
            case '$':
            case '.':
                *p++ = ch;
                break;
            default:
                if (p >= pEnd - 3)
                    break;
                *p++ = '%';
                *p++ = s_hex[((unsigned char)ch) >> 4 ];
                *p++ = s_hex[ ch & 0xf ];
                break;
            }
        }
    }
    return p;
}


HttpReq::HttpReq()
    : m_pSslConn(NULL)
    , m_headerBuf(HEADER_BUF_INIT_SIZE)
    , m_fdReqFile(-1)
{
    m_headerBuf.resize(HEADER_BUF_PAD);
    *((int *)m_headerBuf.begin()) = 0;
    m_iReqHeaderBufRead = m_iReqHeaderBufFinished = HEADER_BUF_PAD;
    //m_pHTAContext = NULL;
    m_pContext = NULL;
    m_pSSIRuntime = NULL;
    ::memset(m_commonHeaderLen, 0,
             (char *)(&m_code + 1) - (char *)m_commonHeaderLen);
    m_upgradeProto = UPD_PROTO_NONE;
    m_pRealPath = NULL;
    m_pPool = ls_xpool_new();
    ls_xpool_skipfree(m_pPool);
    uSetURI(NULL, 0);
    ls_str_set(&m_curUrl.val, NULL, 0);
    m_pUrls = (ls_strpair_t *)malloc(sizeof(ls_strpair_t) *
                                     (MAX_REDIRECTS + 1));
    memset(m_pUrls, 0, sizeof(ls_strpair_t) * (MAX_REDIRECTS + 1));
    m_pEnv = NULL;
    m_pAuthUser = NULL;
    m_pRange = NULL;
    m_iBodyType = REQ_BODY_UNKNOWN;
    m_cookies.init();
    m_pUrlStaticFileData = NULL;
}


HttpReq::~HttpReq()
{
    if (m_fdReqFile != -1)
        ::close(m_fdReqFile);
    m_unknHeaders.release(m_pPool);
    ls_xpool_delete(m_pPool);
    m_pPool = NULL;
    uSetURI(NULL, 0);
    ls_str_set(&m_curUrl.val, NULL, 0);
    if (m_pUrls)
        free(m_pUrls);
    m_pUrls = NULL;
    m_pEnv = NULL;
    m_pAuthUser = NULL;
    m_pRange = NULL;
    m_cookies.clear();
    m_pUrlStaticFileData = NULL;
}


void HttpReq::reset()
{
    if (m_fdReqFile != -1)
    {
        ::close(m_fdReqFile);
        m_fdReqFile = -1;
    }
    if (m_pReqBodyBuf)
    {
        if (!m_pReqBodyBuf->isMmaped())
            delete m_pReqBodyBuf;
        else
            HttpResourceManager::getInstance().recycle(m_pReqBodyBuf);
    }
    ::memset(m_commonHeaderOffset, 0,
             (char *)(&m_code + 1) - (char *)m_commonHeaderOffset);
    m_pHttpHandler = NULL;
    m_pSslConn = NULL;
    resetHeaderBuf();
    m_pRealPath = NULL;
    ls_xpool_reset(m_pPool);
    ls_xpool_skipfree(m_pPool);
    m_unknHeaders.init();
    m_cookies.init();
    uSetURI(NULL, 0);
    ls_str_set(&m_curUrl.val, NULL, 0);
    memset(m_pUrls, 0, sizeof(ls_strpair_t) * (MAX_REDIRECTS + 1));
    m_pEnv = NULL;
    m_pAuthUser = NULL;
    m_pRange = NULL;
}


void HttpReq::resetHeaderBuf()
{
    m_iReqHeaderBufRead = m_iReqHeaderBufFinished = HEADER_BUF_PAD;
    m_headerBuf.resize(HEADER_BUF_PAD);
}


void HttpReq::reset2()
{
    if (m_iReqHeaderBufFinished == HEADER_BUF_PAD)
        return;

    reset();
    if (m_iReqHeaderBufRead - m_iReqHeaderBufFinished > 0)
    {
        memmove(m_headerBuf.begin() + HEADER_BUF_PAD,
                m_headerBuf.begin() + m_iReqHeaderBufFinished,
                m_iReqHeaderBufRead - m_iReqHeaderBufFinished);
        m_headerBuf.resize(HEADER_BUF_PAD + m_iReqHeaderBufRead -
                           m_iReqHeaderBufFinished);
        m_iReqHeaderBufRead = m_headerBuf.size();
        m_iReqHeaderBufFinished = HEADER_BUF_PAD;
    }
    else
        resetHeaderBuf();
}


int HttpReq::setQS(const char *qs, int qsLen)
{
    return ls_str_xsetstr(&m_curUrl.val, qs, qsLen, m_pPool);
}


void HttpReq::uSetURI(char *pURI, int uriLen)
{
    ls_str_set(&m_curUrl.key, pURI, uriLen);
}


int HttpReq::appendPendingHeaderData(const char *pBuf, int len)
{
    if (m_headerBuf.available() < len)
        if (m_headerBuf.grow(len))
            return LS_FAIL;
    memmove(m_headerBuf.end(), pBuf, len);
    m_headerBuf.used(len);
    return 0;
}


static inline int growBuf(AutoBuf &buf, int len)
{
    int g = 1024;
    if (g < len)
        g = len;
    if (buf.grow(g) == -1)
        return SC_500;
    return 0;
}


int HttpReq::processHeader()
{
    if (m_iHeaderStatus == HEADER_REQUEST_LINE)
    {
        int ret = processRequestLine();
        if (ret)
        {
            if ((m_iHeaderStatus == HEADER_REQUEST_LINE) &&
                (m_iReqHeaderBufFinished >=
                 HttpServerConfig::getInstance().getMaxURLLen()))
            {
                m_reqLineLen = m_iReqHeaderBufFinished - m_reqLineOff;
                return SC_414;
            }
        }

        return ret;
    }
    else
        return processHeaderLines();
}

#define MAX_HEADER_TAG_LEN  20

const HttpVHost *HttpReq::matchVHost(const VHostMap *pVHostMap)
{
    const HttpVHost *pVHost = NULL;
    register char *pHost = m_headerBuf.begin() + m_iHostOff;
    register char *pHostEnd = pHost + m_iHostLen;
    register char ch = *pHostEnd;
    register int  www = 4;
    if (m_iLeadingWWW && pVHostMap->isStripWWW())
    {
        pHost += www;
        www = 0;
    }
    *pHostEnd = 0;
    pVHost = pVHostMap->matchVHost(pHost, pHostEnd);
    if (www && !pVHost && m_iLeadingWWW)
    {
        pHost += 4;
        pVHost = pVHostMap->matchVHost(pHost, pHostEnd);
    }
    *pHostEnd = ch;
    return pVHost;
}

const HttpVHost *HttpReq::matchVHost()
{
    if (!m_pVHostMap)
        return NULL;
    m_pVHost = m_pVHostMap->getDedicated();
    if (!m_pVHost)
    {
        char *pHost = m_headerBuf.begin() + m_iHostOff;
        char *pHostEnd = pHost + m_iHostLen;
        char ch = *pHostEnd;
        if (m_iLeadingWWW)
            pHost += 4;
        *pHostEnd = 0;
        m_pVHost = m_pVHostMap->matchVHost(pHost, pHostEnd);
        *pHostEnd = ch;
    }
    if (m_pVHost)
        ((HttpVHost *)m_pVHost)->incRef();
    return m_pVHost;
}


int HttpReq::removeSpace(const char **pCur, const char *pBEnd)
{
    while (1)
    {
        if (*pCur >= pBEnd)
        {
            m_iReqHeaderBufFinished = *pCur - m_headerBuf.begin();
            return 1;
        }
        if (isspace(**pCur))
            ++*pCur;
        else
            return 0;
    }
}


int HttpReq::processRequestLine()
{
    int result = 0;
    const char *pCur = m_headerBuf.begin() + m_iReqHeaderBufFinished;
    const char *pBEnd = m_headerBuf.end();
    int iBufLen = pBEnd - pCur;
    assert(iBufLen >= 0);
    
    if (pBEnd > HttpServerConfig::getInstance().getMaxURLLen() +
        m_headerBuf.begin())
        pBEnd = HttpServerConfig::getInstance().getMaxURLLen() +
                m_headerBuf.begin();

    const char *pLineEnd;
    while ((pLineEnd = (const char *)memchr(pCur, '\n', pBEnd - pCur)) != NULL)
    {
        while (pCur < pLineEnd)
        {
            if (!isspace(*pCur))
                break;
            ++pCur;
        }
        if (pCur != pLineEnd)
            break;
        ++pCur;
        m_iReqHeaderBufFinished = pCur - m_headerBuf.begin();
    }
    if (pLineEnd == NULL)
    {
        if (iBufLen < MAX_BUF_SIZE + 20)
            return 1;
        else
            return SC_400;
    }
    m_reqLineOff = pCur - m_headerBuf.begin();

    const char *p = pCur;
    while ((p < pLineEnd) && ((*p != ' ') && (*p != '\t')))
        ++p;
    result = parseMethod(pCur, p);
    if (result)
        return result;

    pCur = p + 1;
    while ((p < pLineEnd) && ((*p == ' ') || (*p == '\t')))
        ++p;
    pCur = p;
    result = parseHost(pCur, pLineEnd);
    if (result)
        return result;
    p += m_iHostLen;
    pCur = (char *)memchr(p, '/', (pLineEnd - p));
    //FIXME:should we handle other cases?
    if (!pCur || pCur > pLineEnd)
        return SC_400;
    while ((p < pLineEnd) && ((*p != ' ') && (*p != '\t')))
        ++p;
    if (p >= pLineEnd || pCur > p)
        return SC_400;
    m_reqURLOff = pCur - m_headerBuf.begin();
    result = parseURL(pCur, p);
    if (result)
        return result;

    pCur = p + 1;
    while ((p < pLineEnd) && ((*p == ' ') || (*p == '\t')))
        ++p;
    pCur = p;

    result = parseProtocol(pCur, pLineEnd);
    if (result)
        return result;
    m_reqLineLen = pLineEnd - m_headerBuf.begin() - m_reqLineOff;
    if (*(pLineEnd - 1) == '\r')
        m_reqLineLen --;

    m_iHeaderStatus = HEADER_HEADER;
    m_iHS1 = 0;
    m_iHS2 = HttpHeader::H_HEADER_END;
    m_iHS3 = 0;
    m_iReqHeaderBufFinished = pLineEnd + 1 - m_headerBuf.begin();
    result = processHeaderLines();

    return result;
}


int HttpReq::parseProtocol(const char *pCur, const char *pBEnd)
{
    if (strncasecmp(pCur, "http/1.", 7) != 0)
        return SC_400;
    pCur += 7;
    {
        if (*pCur == '1')
        {
            m_ver = HTTP_1_1;
            keepAlive(1);
            ++pCur;
        }
        else if (*pCur == '0')
        {
            keepAlive(0);
            m_ver = HTTP_1_0;
            *(char *)pCur++ = '1';  //for mod_proxy, always use HTTP/1.1
        }
        else
        {
            m_ver = HTTP_1_1;
            return SC_505;
        }
    }
    return 0;
}


int HttpReq::parseURL(const char *pCur, const char *pBEnd)
{
    const char *pFound = pCur, *pMark = (const char *)memchr(pCur, '?',
                                        pBEnd - pCur);
    int result = 0;
    if (pMark)
    {
        pCur = pMark + 1;
        setQS(pCur, pBEnd - pCur);
    }
    else
    {
        ls_str_set(&m_curUrl.val, NULL, 0);
        pMark = pBEnd;
    }
    result = parseURI(pFound, pMark);
    if (result != 0)
        return result;
    m_reqURLLen = pBEnd - m_headerBuf.begin() - m_reqURLOff;
    //m_reqURLLen = pCur - m_headerBuf.begin() - m_reqURLOff;
    return 0;
}


int HttpReq::parseURI(const char *pCur, const char *pBEnd)
{
    int len = pBEnd - pCur;
    char *p = (char *)ls_xpool_alloc(m_pPool, len + URL_INDEX_PAD);
    int n = HttpUtil::unescape(p, len, pCur);
    --n;
    n = GPath::clean(p, n);
    if (n <= 0)
        return SC_400;
    *(p + n) = '\0';
    uSetURI(p, n);
    return 0;
}


int HttpReq::parseHost(const char *pCur, const char *pBEnd)
{
    //nohost case, return directly
    if ((*pCur == '/') || (*pCur == '%'))
        return 0;

    const char *pHost;
    pHost = (const char *)memchr(pCur, ':', pBEnd - pCur);
    if ((pHost) && (pHost + 2 < pBEnd))
    {
        if ((*(pHost + 1) != '/') || (*(pHost + 2) != '/'))
            return SC_400;
    }
    else
    {
        m_iReqHeaderBufFinished = pCur - m_headerBuf.begin();
        return 1;
    }

    pHost += 3;
    const char *pHostEnd = (const char *)memchr(pHost, '/', (pBEnd - pHost));
    if (pHostEnd != NULL)
    {
        m_iHostLen = pHost - pCur;
        postProcessHost(pHost , pHostEnd);
    }
    else
    {
        pCur = pBEnd;
        m_iReqHeaderBufFinished = m_headerBuf.size();
        return 1;
    }
    if (!m_iHostLen)
        m_iHostOff = 0;

    return 0;
}


int HttpReq::parseMethod(const char *pCur, const char *pBEnd)
{

    if ((m_method = HttpMethod::parse2(pCur)) == 0)
        return SC_400;

    if (m_method == HttpMethod::HTTP_HEAD)
        m_iNoRespBody = 1;

    if ((m_method < HttpMethod::HTTP_OPTIONS) ||
        (m_method >= HttpMethod::HTTP_METHOD_END))
        return SC_505;

//     if (m_method == HttpMethod::HTTP_OPTIONS)
//         return SC_405;

    pCur += HttpMethod::getLen(m_method);
    if ((*pCur != ' ') && (*pCur != '\t'))
        return SC_400;
    return 0;
}


void HttpReq::setScriptNameLen(int n)
{
    m_iScriptNameLen = n;
    ls_str_set(&m_pathInfo, (char *)getURI() + m_iScriptNameLen,
               getURILen() - n);
}


int HttpReq::processHeaderLines()
{
    const char *pBEnd = m_headerBuf.end();
    const char *pMark = NULL;
    const char *pLineEnd = NULL;
    const char *pLineBegin  = m_headerBuf.begin() + m_iReqHeaderBufFinished;
    const char *pTemp = NULL;
    const char *pTemp1 = NULL;
    key_value_pair *pCurHeader = NULL;
    bool headerfinished = false;
    int index;

    m_upgradeProto = UPD_PROTO_NONE; //0;
    while ((pLineEnd  = (const char *)memchr(pLineBegin, '\n',
                        pBEnd - pLineBegin)) != NULL)
    {
        pMark = (const char *)memchr(pLineBegin, ':', pLineEnd - pLineBegin);
        if (pMark != NULL)
        {
            while (1)
            {
                if (pLineEnd + 1 >= pBEnd)
                {
                    m_iReqHeaderBufFinished = pLineBegin - m_headerBuf.begin();
                    return 1;
                }
                if ((*(pLineEnd + 1) == ' ') || (*(pLineEnd + 1) == '\t'))
                {
                    *((char *)pLineEnd) = ' ';
                    if (*(pLineEnd - 1) == '\r')
                        *((char *)pLineEnd - 1) = ' ';
                }
                else
                    break;
                pLineEnd  = (const char *)memchr(pLineEnd, '\n', pBEnd - pLineEnd);
                if (pLineEnd == NULL)
                    return 1;
                else
                    continue;
            }
            pTemp = pMark + 1;
            pTemp1 = pLineEnd;
            skipSpaceBothSide(pTemp, pTemp1);
            if (strncmp(pTemp, "() {", 4) == 0)
            {
                LS_INFO(getLogSession(), "Status 400: CVE-2014-6271, "
                        "CVE-2014-7169 signature detected in request header!");
                return SC_400;
            }
            index = HttpHeader::getIndex(pLineBegin);
            if (index != HttpHeader::H_HEADER_END)
            {
                m_commonHeaderLen[ index ] = pTemp1 - pTemp;
                m_commonHeaderOffset[index] = pTemp - m_headerBuf.begin();
                int Result = processHeader(index);
                if (Result != 0)
                    return Result;
            }
            else
            {
                pCurHeader = newUnknownHeader();
                pCurHeader->keyOff = pLineBegin - m_headerBuf.begin();
                pCurHeader->keyLen = skipSpace(pMark, pLineBegin) - pLineBegin;
                pCurHeader->valOff = pTemp - m_headerBuf.begin();
                pCurHeader->valLen = pTemp1 - pTemp;

                if (pCurHeader->keyLen == 7 && strncasecmp(pLineBegin, "Upgrade", 7) == 0)
                {
                    if (pCurHeader->valLen == 9 && strncasecmp(pTemp, "websocket", 9) == 0)
                        m_upgradeProto = UPD_PROTO_WEBSOCKET;
                    else if (pCurHeader->valLen >= 3 && strncasecmp(pTemp, "h2c", 3) == 0)
                    {
                        m_upgradeProto = UPD_PROTO_HTTP2;
                        //Destroy it, to avoid loop calling
                        memset((char *)(pLineBegin - 2), 0x20, 7 + pCurHeader->valLen + 4);//
                    }
                }
                else if (pCurHeader->keyLen == 16
                         && (strncasecmp(pLineBegin, "CF-Connecting-IP", 16) == 0))
                    m_iCfIpHeader = m_unknHeaders.getSize();
                else if (pCurHeader->keyLen == 17
                         && strncasecmp(pLineBegin, "X-Forwarded-Proto", 17) == 0)
                {
                    if (pCurHeader->valLen == 5 && strncasecmp(pTemp, "https", 5) == 0)
                        m_iContextState |= X_FORWARD_HTTPS;
                }
                else if (pCurHeader->keyLen == 5
                         && (strncasecmp(pLineBegin, "proxy", 5) == 0))
                {
                    LS_INFO(getLogSession(), "Status 400: HTTPOXY attack detected!");
                    return SC_400;
                }
            }
        }
        pLineBegin = pLineEnd + 1;
        if ((*(pLineEnd - 1) == '\r') && (*(pLineEnd - 2) == '\n'))
        {
            headerfinished = true;
            break;
        }
    }
    m_iReqHeaderBufFinished = pLineBegin - m_headerBuf.begin();
    if (headerfinished)
    {
        m_iHttpHeaderEnd = m_iReqHeaderBufFinished;
        m_iReqHeaderBufRead = m_headerBuf.size();
        m_iHeaderStatus = HEADER_OK;
        return 0;
    }
    return 1;
}


int HttpReq::processHeader(int index)
{
    const char *pCur = m_headerBuf.begin() + m_commonHeaderOffset[index];
    const char *pBEnd = pCur + m_commonHeaderLen[ index ];
    switch (index)
    {
    case HttpHeader::H_HOST:
        m_iHostOff = m_commonHeaderOffset[index];
        postProcessHost(pCur, pBEnd);
        break;
    case HttpHeader::H_CONTENT_LENGTH:
        m_lEntityLength = strtoll(pCur, NULL, 0);
        break;
    case HttpHeader::H_CONTENT_TYPE:
        updateBodyType(pCur);
        break;
    case HttpHeader::H_TRANSFER_ENCODING:
        if (strncasecmp(pCur, "chunked", 7) == 0)
        {
            if (getMethod() <= HttpMethod::HTTP_HEAD)
                return SC_400;
            m_lEntityLength = CHUNKED;
        }
        break;
    case HttpHeader::H_ACC_ENCODING:
        if (m_commonHeaderLen[ index ] >= 2)
        {
            char ch = *pBEnd;
            *((char *)pBEnd) = 0;
            if ((m_commonHeaderLen[ index ] >= 4)
                && (strstr(pCur, "gzip") != NULL))
                m_iAcceptGzip = REQ_GZIP_ACCEPT |
                                HttpServerConfig::getInstance().getGzipCompress();
            if (strstr(pCur, "br") != NULL)
                m_iAcceptBr = REQ_BR_ACCEPT |
                                HttpServerConfig::getInstance().getBrCompress();
            *((char *)pBEnd) = ch;
        }
        break;
    case HttpHeader::H_CONNECTION:
        if (m_ver == HTTP_1_1)
            keepAlive(strncasecmp(pCur, "clos", 4) != 0);
        else
            keepAlive(strncasecmp(pCur, "keep", 4) == 0);
        break;
    default:
        break;
    }
    return 0;
}


int HttpReq::postProcessHost(const char *pCur, const char *pBEnd)
{
    const char *pstrfound;
    if ((pCur + 4) < pBEnd)
    {
        char ch1;
        int iNum = pBEnd - pCur;
        for (int i = 0; i < iNum; i++)
        {
            ch1 = pCur[i];
            if ((ch1 >= 'A') && (ch1 <= 'Z'))
            {
                ch1 |= 0x20;
                ((char *)pCur)[i] = ch1;
            }
        }
        if (strncmp((char *)pCur, "www.", 4) == 0)
            m_iLeadingWWW = 1;
    }
    pstrfound = (char *)memchr(pCur, ':', (pBEnd - pCur));
    if (pstrfound)
        m_iHostLen = pstrfound - pCur;
    else
        m_iHostLen += pBEnd - pCur;
    if (!m_iHostLen)
        m_iHostOff = 0;

    return 0;
}


const char *HttpReq::skipSpace(const char *pOrg, const char *pDest)
{
    char ch;
    if (pOrg > pDest)
    {
        //pTemp = pOrg - 1;
        for (; pOrg > pDest; pOrg--)
        {
            ch = *(pOrg - 1);
            if ((ch == ' ') || (ch == '\t') || (ch == '\r'))
                continue;
            else
                break;
        }
    }
    else
    {
        for (; pOrg < pDest; pOrg++)
        {
            if ((*pOrg == ' ') || (*pOrg == '\t') || (*pOrg == '\r'))
                continue;
            else
                break;
        }
    }
    return pOrg;
}


int HttpReq::skipSpaceBothSide(const char *&pHBegin, const char *&pHEnd)
{
    char ch;
    for (; pHBegin <= pHEnd; pHEnd--)
    {
        if (pHBegin == pHEnd)
            break;
        ch = *(pHEnd - 1);
        if ((ch == ' ') || (ch == '\t') || (ch == '\r'))
            continue;
        else
            break;
    }
    if (pHBegin + 1 >= pHEnd)
        return (pHEnd - pHBegin);
    for (; pHBegin <= pHEnd; pHBegin++)
    {
        if (pHBegin == pHEnd)
            break;
        if ((*pHBegin == ' ') || (*pHBegin == '\t') || (*pHBegin == '\r'))
            continue;
        else
            break;
    }
    return (pHEnd - pHBegin);
}


key_value_pair *HttpReq::newKeyValueBuf()
{
    return (key_value_pair *)ls_xpool_alloc(m_pPool, sizeof(key_value_pair));
}


key_value_pair *HttpReq::newUnknownHeader()
{
    if (m_unknHeaders.getCapacity() == 0)
        m_unknHeaders.guarantee(m_pPool, 10);
    else if (m_unknHeaders.getCapacity() <= m_unknHeaders.getSize() + 1)
        m_unknHeaders.guarantee(m_pPool, m_unknHeaders.getCapacity() * 2);
    return m_unknHeaders.getNew();
}


key_value_pair *HttpReq::getUnknHeaderByKey(const AutoBuf &buf,
        const char  *pName, int namelen) const
{
    const char *p;
    int index = 0;
    key_value_pair *ptr;
    while ((ptr = m_unknHeaders.getObj(index)) != NULL)
    {
        if (namelen == ptr->keyLen)
        {
            p = buf.getp(ptr->keyOff);
            if (strncasecmp(p, pName, namelen) == 0)
                return ptr;
        }
        ++index;
    }
    return NULL;
}


int HttpReq::processNewReqData(const struct sockaddr *pAddr)
{
    if (!m_pVHost->isEnabled())
    {
        LS_INFO(getLogSession(), "VHost disabled [%s], access denied.",
                getVHost()->getName());
        return SC_403;
    }
    if (!m_pVHost->enableGzip())
        andGzip(~GZIP_ENABLED);

    if (!m_pVHost->enableBr())
        andBr(~BR_ENABLED);
    AccessCache *pAccessCache = m_pVHost->getAccessCache();
    if (pAccessCache)
    {
        if (//!m_accessGranted &&
            !pAccessCache->isAllowed(pAddr))
        {
            LS_INFO(getLogSession(),
                    "[ACL] Access to virtual host [%s] is denied.",
                    getVHost()->getName());
            return SC_403;
        }
    }

    m_iScriptNameLen = getURILen();
    if (getLogger() && LS_LOG_ENABLED(LOG4CXX_NS::Level::DBG_LESS))
    {
        const char *pQS = getQueryString();
        int len = getQueryStringLen();
        LS_DBG_L(getLogSession(), "New request: \n\tMethod=[%s], URI=[%s],\n"
                 "\tQueryString=[%.*s]\n\tContent Length=%lld\n",
                 HttpMethod::get(getMethod()), getURI(), len, pQS,
                 (long long)getContentLength());
    }
    //access control of virtual host
    return 0;
}


int HttpReq::getPort() const
{
    return m_pVHostMap->getPort();
}


const AutoStr2 &HttpReq::getPortStr() const
{
    return m_pVHostMap->getPortStr();
}


const AutoStr2 *HttpReq::getLocalAddrStr() const
{
    return m_pVHostMap->getAddrStr();
}


void HttpReq::getAAAData(struct AAAData &aaa, int &satisfyAny)
{
    m_pContext->getAAAData(aaa);
    if (aaa.m_pHTAuth)
    {
        m_pHTAuth = aaa.m_pHTAuth;
        m_pAuthRequired = m_pContext->getAuthRequired();
    }
    satisfyAny = m_pContext->isSatisfyAny();
    if (m_pFMContext)
    {
        if (m_pFMContext->getConfigBits() & BIT_ACCESS)
            aaa.m_pAccessCtrl = m_pFMContext->getAccessControl();
        if (m_pFMContext->getConfigBits() & BIT_AUTH)
            m_pHTAuth = aaa.m_pHTAuth = m_pFMContext->getHTAuth();
        if (m_pFMContext->getConfigBits() & BIT_AUTH_REQ)
            m_pAuthRequired = aaa.m_pRequired = m_pFMContext->getAuthRequired();
        if (m_pFMContext->getConfigBits() & BIT_SATISFY)
            satisfyAny      = m_pFMContext->isSatisfyAny();
    }
}


int HttpReq::translatePath(const char *pURI, int uriLen, char *pReal,
                           int len) const
{

    const HttpContext *pContext = m_pContext;
    *pReal = 0;
    if ((!pContext) ||
        (strncmp(pContext->getURI(), pURI, pContext->getURILen()) != 0))
        pContext = m_pVHost->bestMatch(pURI, uriLen);

    if (pContext && pContext->getHandlerType() > HandlerType::HT_STATIC)
        pContext = NULL;
    return translate(pURI, uriLen, pContext, pReal, len);
}


int HttpReq::translate(const char *pURI, int uriLen,
                       const HttpContext *pContext, char *pReal, int len) const
{
    char *pHead = pReal;
    int l;
    *pReal = 0;
    //offset context URI from request URI
    if (pContext != NULL)
    {
        //assert( pContext->match( pURI ) );
        l = pContext->getLocationLen();
        if (l >= len)
            return LS_FAIL;
        ::memmove(pReal, pContext->getLocation(), l);
        len -= l;
        pReal += l;
        if ('/' == *pURI)
        {
            uriLen -= pContext->getURILen();
            pURI += pContext->getURILen();
        }
    }
    else
    {
        const AutoStr2 *pDocRoot = m_pVHost->getDocRoot();
        l = pDocRoot->len();
        if (l >= len)
            return LS_FAIL;
        ::memmove(pReal , pDocRoot->c_str(), l);
        len -= l;
        pReal += l;
        ++pURI;
        --uriLen;
    }
    if (uriLen > 0)
    {
        if (uriLen > len)
            return LS_FAIL;
        ::memmove(pReal, pURI, uriLen);
        pReal += uriLen;
    }
    *pReal = 0;
    return pReal - pHead;
}


int HttpReq::setCurrentURL(const char *pURL, int len, int alloc)
{
    assert(pURL);
    if (*pURL != '/')
    {
        LS_DBG_L(getLogSession(), "URL is invalid - does not start with '/'.");
        return SC_400;
    }
    char *pURI;
    int iURILen = len;
    const char *pArgs = pURL;
    if (getLocation() == pURL)
    {
        //share the buffer of location
        pURI = (char *)getLocation();
        ls_str_set(&m_location, NULL, 0);
    }
    else
        pURI = (char *)ls_xpool_alloc(m_pPool, len + URL_INDEX_PAD);
    //decode URI
    int n = HttpUtil::unescapeInPlace(pURI, iURILen, pArgs);
    if (n == -1)
    {
        LS_DBG_L(getLogSession(), "Unable to decode request URI: %s.",
                 pURI);
        return SC_400;    //invalid url format
    }
    uSetURI(pURI, iURILen);
    if ((alloc) || (n - 1 - (pArgs - pURI) > 0) || (!m_pSSIRuntime))
        setQS(getURI() + (pArgs - pURI), n - 1 - (pArgs - pURI));

    else
        m_curUrl.val = m_pUrls[m_iRedirects - 1].val;
    m_iScriptNameLen = getURILen();
    ls_str_setlen(&m_pathInfo, 0);
    return 0;
}


int HttpReq::setRewriteURI(const char *pURL, int len, int no_escape)
{
    int totalLen = len + ((!no_escape) ? len * 2 : 0);
    if (totalLen > MAX_URL_LEN)
        totalLen = MAX_URL_LEN;
    char *p = (char *)ls_xpool_alloc(m_pPool, totalLen + URL_INDEX_PAD);
    char *pEnd = p + totalLen - 1;
    uSetURI(p, totalLen);
    if (!no_escape)
        p = escape_uri(p, pEnd, pURL, len);
    else
    {
        memcpy(p, pURL, len);
        p += len;
    }
    *p = 0;
    ls_str_setlen(&m_curUrl.key, p - getURI());
    m_iScriptNameLen = getURILen();
    return 0;
}


int HttpReq::appendIndexToUri(const char *pIndex, int indexLen)
{
    ls_str_xappend(&m_curUrl.key, pIndex, indexLen, m_pPool);
    m_iScriptNameLen = getURILen();
    ls_str_setlen(&m_pathInfo, 0);
    return 0;
}


int HttpReq::setRewriteQueryString(const char *pQS, int len)
{
    setQS(pQS, len);
    return 0;
}


static void sanitizeHeaderValue(char *pHeaderVal, int len)
{
    char *pHeaderEnd = pHeaderVal + len;
    while(pHeaderVal < pHeaderEnd)
    {
        if (*pHeaderVal == '\r' || *pHeaderVal == '\n')
            *pHeaderVal = ' ';
        ++pHeaderVal;
    }
}    


int HttpReq::setRewriteLocation(char *pURI, int uriLen,
                                const char *pQS, int qsLen, int escape)
{
    int totalLen = uriLen + qsLen + 2 + ((escape) ? uriLen : 0);
    if (totalLen > MAX_URL_LEN)
        totalLen = MAX_URL_LEN;

    char *p = (char *)ls_xpool_alloc(m_pPool, totalLen + URL_INDEX_PAD);
    char *pEnd = p + totalLen - 1;
    ls_str_set(&m_location, p, totalLen);
    if (escape)
        p += HttpUtil::escape(pURI, p, pEnd - p - 4);
    else
    {
        memcpy(p, pURI, uriLen);
        sanitizeHeaderValue(p, uriLen);
        p += uriLen;
    }
    if (qsLen != 0)
    {
        *p++ = '?';
        if (qsLen > pEnd - p)
            qsLen = pEnd - p;
        memmove(p, pQS, qsLen);
        sanitizeHeaderValue(p, qsLen);
        p += qsLen;
    }
    *p = 0;
    ls_str_setlen(&m_location, p - getLocation());
    return 0;
}


int HttpReq::saveCurURL()
{
    if (m_iRedirects >= MAX_REDIRECTS)
    {
        LS_ERROR(getLogSession(), "Maximum number of redirect reached.");
        return SC_500;
    }
    m_pUrls[m_iRedirects].key = m_curUrl.key;
    m_pUrls[m_iRedirects++].val = m_curUrl.val;

    return 0;
}


int HttpReq::internalRedirect(const char *pURL, int len, int alloc)
{
    assert(pURL);
    int ret = saveCurURL();
    if (ret)
        return ret;
    setCurrentURL(pURL, len, alloc);
    return detectLoopRedirect();
}


int HttpReq::internalRedirectURI(const char *pURI, int len,
                                 int resetPathInfo, int no_escape)
{
    assert(pURI);
    int ret = saveCurURL();
    if (ret)
        return ret;
    setRewriteURI(pURI, len, no_escape);
    if (resetPathInfo)
    {
        ls_str_setlen(&m_pathInfo, 0);
        return detectLoopRedirect();
    }
    return 0;
}


int HttpReq::detectLoopRedirect()
{
    const char *pURI = getURI();
    const char *pArg = getQueryString();
    //detect loop
    int i;
    for (i = 0; i < m_iRedirects; ++i)
    {
        ls_strpair_t tmp = m_pUrls[i];
        if
        (
            ((int)ls_str_len(&tmp.key) == getURILen())
            && (strncmp(ls_str_cstr(&tmp.key), pURI, ls_str_len(&tmp.key)) == 0)
            && ((int)ls_str_len(&tmp.val) == getQueryStringLen())
            && (strncmp(ls_str_cstr(&tmp.val), pArg, ls_str_len(&tmp.val)) == 0)
        )
            break;

    }
    if (i < m_iRedirects)   //loop detected
    {
        m_curUrl.key = m_pUrls[--m_iRedirects].key;
        m_curUrl.val = m_pUrls[m_iRedirects].val;
        LS_ERROR(getLogSession(), "Detected loop redirection.");
        //TODO:
        // print the redirect url stack.
        return SC_500;
    }
    LS_DBG_L(getLogSession(), "Redirect to: \n\tURI=[%s],\n"
             "\tQueryString=[%s]", getURI(), getQueryString());
    if (m_pReqBodyBuf)
        m_pReqBodyBuf->rewindReadBuf();

    return 0;
}


int HttpReq::redirect(const char *pURL, int len, int alloc)
{
    //int method = getMethod();
    if (//( HttpMethod::HTTP_PUT < method )||
        (*pURL != '/'))
    {
        if (pURL != getLocation())
            setLocation(pURL, len);
        //Do not remove this line, otherwise, external custom error page breaks
        setStatusCode(SC_302);
        return SC_302;
    }
    return internalRedirect(pURL, len, alloc);
}


int HttpReq::contextRedirect(const HttpContext *pContext, int destLen)
{
    int code = pContext->redirectCode();
    if ((code >= SC_400) || ((code != -1) && (code < SC_300)))
        return code;
    char *pDestURI;
    if (destLen)
        pDestURI = HttpResourceManager::getGlobalBuf();
    else
    {
        int contextURILen = pContext->getURILen();
        int uriLen = getURILen();
        pDestURI = (char *)pContext->getLocation();
        destLen = pContext->getLocationLen();
        if (contextURILen < uriLen)
        {
            char *p = HttpResourceManager::getGlobalBuf();
            memmove(p, pDestURI, destLen);
            memmove(p + destLen, getURI() + contextURILen,
                    uriLen - contextURILen + 1);
            pDestURI = p;
            destLen += uriLen - contextURILen;
        }
    }

    if ((code != -1) || (*pDestURI != '/'))
    {
        if (code == -1)
            code = SC_302;
        int qslen = getQueryStringLen();
        if (qslen > 0)
        {
            memmove(pDestURI + destLen + 1, getQueryString(), qslen);
            *(pDestURI + destLen++) = '?';
            destLen += qslen;
        }
        setLocation(pDestURI, destLen);
        return code;
    }
    else
        return internalRedirect(pDestURI, destLen);
}


static const char *findSuffix(const char *pBegin, const char *pEnd)
{
    const char *pCur = pEnd;
    if (pBegin < pEnd - 16)
        pBegin = pEnd - 16;
    while (pCur > pBegin)
    {
        char ch = *(pCur - 1);
        if (ch == '/')
            break;
        if (ch == '.')
            return pCur;
        --pCur;
    }
    return NULL;
}


int HttpReq::processMatchList(const HttpContext *pContext,
                              const char *pURI, int iURILen)
{
    m_iMatchedLen = 2048;
    const HttpContext *pMatchContext = pContext->match(pURI, iURILen,
                                       HttpResourceManager::getGlobalBuf(),
                                       m_iMatchedLen);
    if (pMatchContext)
    {
        m_pContext = pMatchContext;
        m_pHttpHandler = m_pContext->getHandler();
        if (pMatchContext->getHandlerType() != HandlerType::HT_REDIRECT)
        {
            char *p = strchr(HttpResourceManager::getGlobalBuf(), '?');
            if (p)
            {
                *p = 0;
                int newLen = p - HttpResourceManager::getGlobalBuf();
                ++p;
                setQS(p, m_iMatchedLen - newLen);
                m_iMatchedLen = newLen;
            }
        }
        if (m_iMatchedLen == 0)
        {
            m_iMatchedLen = iURILen;
            memmove(HttpResourceManager::getGlobalBuf(), pURI, iURILen + 1);
        }
    }
    else
        m_iMatchedLen = 0;
    return m_iMatchedLen;
}


int HttpReq::checkSuffixHandler(const char *pURI, int len, int &cacheable)
{
    if (!m_iMatchedLen)
    {
        const char *pURIEnd = pURI + len - 1;
        int ret = processSuffix(pURI, pURIEnd, cacheable);
        if (ret)
            return ret;
    }
    if (m_pHttpHandler->getType() == HandlerType::HT_PROXY)
        return -2;
    LS_DBG_L(getLogSession(), "Cannot find appropriate handler for [%s].",
             pURI);
    return SC_404;
}


int HttpReq::processSuffix(const char *pURI, const char *pURIEnd,
                           int &cacheable)
{
    const char *pSuffix = findSuffix(pURI, pURIEnd);
    if (pSuffix)
    {
        const HotlinkCtrl *pHLC = m_pVHost->getHotlinkCtrl();
        if (pHLC)
        {
            int ret = checkHotlink(pHLC, pSuffix);
            if (ret)
            {
                if (cacheable)
                    cacheable = ret;
                else
                    return ret;
            }
        }
    }
    if (m_pHttpHandler->getType() == HandlerType::HT_NULL)
        return setMimeBySuffix(pSuffix);
    return 0;
}


const char *HttpReq::getMimeBySuffix(const char *pSuffix)
{
    const MimeSetting *pMime = m_pContext->determineMime(pSuffix,
                               (char *)m_pForcedType);
    if (pMime)
        return pMime->getMIME()->c_str();
    else
        return NULL;
}


int HttpReq::setMimeBySuffix(const char *pSuffix)
{
    if (!m_pMimeType)
        m_pMimeType = m_pContext->determineMime(pSuffix, (char *)m_pForcedType);
    m_pHttpHandler = m_pMimeType->getHandler();
    if (!m_pHttpHandler)
    {
        LS_INFO(getLogSession(),
                "Missing handler for suffix [.%s], access denied.",
                pSuffix ? pSuffix : "");
        return SC_403;
    }
    if (m_pHttpHandler->getType() != HandlerType::HT_NULL)
    {
        LS_DBG_L(getLogSession(), "Find handler [%s] for [.%s].",
                 m_pHttpHandler->getName(), pSuffix ? pSuffix : "");
        if (!m_pContext->isScriptEnabled())
        {
            LS_INFO(getLogSession(), "Scripting is disabled for "
                    "VHost [%s], context [%s] access denied.",
                    m_pVHost->getName(), m_pContext->getURI());
            return SC_403;
        }
    }
    else
    {
        if (getPathInfoLen() > 0)   //Path info is not allowed for static file
        {
            LS_INFO(getLogSession(),
                    "URI '%s' refers to a static file with PATH_INFO [%s].",
                    getURI(), getPathInfo());
            return SC_404;
        }
        if ((m_pMimeType->getMIME()->len() > 20) &&
            (strncmp("x-httpd-", m_pMimeType->getMIME()->c_str() + 12, 8) == 0))
        {
            LS_ERROR(getLogSession(), "MIME type [%s] for suffix '.%s' does not "
                     "allow serving as static file, access denied!",
                     m_pMimeType->getMIME()->c_str(), pSuffix ? pSuffix : "");
            dumpHeader();
            return SC_403;
        }
    }
    return 0;
}


int HttpReq::locationToUrl(const char *pLocation, int len)
{
    char achURI[8192];
    const HttpContext *pNewCtx;
    pNewCtx = m_pVHost->matchLocation(pLocation, len);
    if (pNewCtx)
    {
        int n = snprintf(achURI, 8192, "%s%s", pNewCtx->getURI(),
                         pLocation + pNewCtx->getLocationLen());
        pLocation = achURI;
        len = n;
        LS_DBG_H(getLogSession(), "File [%s] has been mapped to URI: [%s],"
                 " via context: [%s]", pLocation, achURI, pNewCtx->getURI());
    }
    setLocation(pLocation, len);
    return 0;
}


int HttpReq::postRewriteProcess(const char *pURI, int len)
{
    //if is rewriten to file path, reverse lookup context from file path
    const HttpContext *pNewCtx;
    pNewCtx = m_pVHost->matchLocation(pURI, len);
    if (pNewCtx)
    {
        // should skip context processing;
        m_iContextState &= ~PROCESS_CONTEXT;
        m_pContext = pNewCtx;
        m_pHttpHandler = pNewCtx->getHandler();
        m_pMimeType = NULL;
        // if new context is same as previous one skip authentication
        if (pNewCtx != m_pContext)
        {
            m_iContextState &= ~CONTEXT_AUTH_CHECKED;
            m_pContext = pNewCtx;
        }
        m_iMatchedLen = len;
        memmove(HttpResourceManager::getGlobalBuf(), pURI, len + 1);
    }
    else
    {
        setRewriteURI(pURI, len);
        if (m_pContext && len > m_pContext->getURILen())
        {
            const HttpContext *pContext = m_pVHost->bestMatch(pURI, len);
            if (pContext != m_pContext)
            {
                m_pContext = pContext;
                return 1;
            }
        }
        if (m_pContext && (strncmp(m_pContext->getURI(), pURI,
                                   m_pContext->getURILen()) != 0))
        {
            if (m_pContext->shouldMatchFiles())
                filesMatch(getURI() + getURILen());
            return 1;
        }
    }
    return 0;
}


int HttpReq::processContext(const HttpContext *&pOldCtx)
{
    const char *pURI;
    int   iURILen;
    pOldCtx = m_pContext;
    pURI = getURI();
    iURILen = getURILen();
    m_pMimeType = NULL;
    m_iMatchedLen = 0;

    if (m_pVHost->getRootContext().getMatchList())
        processMatchList(&m_pVHost->getRootContext(), pURI, iURILen);

    if (!m_iMatchedLen)
    {
        m_pContext = m_pVHost->bestMatch(pURI, iURILen);
        if (!m_pContext)
        {
            LS_DBG_L(getLogSession(), "No context found for URI: [%s].", pURI);
            return SC_404;
        }
        LS_DBG_H(getLogSession(), "Find context with URI: [%s], "
                 "location: [%s].", m_pContext->getURI(),
                 m_pContext->getLocation() ? m_pContext->getLocation() : "");

        if ((*(m_pContext->getURI() + m_pContext->getURILen() - 1) == '/') &&
            (*(pURI + m_pContext->getURILen() - 1) != '/'))
            return redirectDir(pURI);
        m_pHttpHandler = m_pContext->getHandler();

        if (m_pContext->getMatchList())   //regular expression match
            processMatchList(m_pContext, pURI, iURILen);
    }
    if (m_pHttpHandler->getType() == HandlerType::HT_PROXY)
        return -2;
    if (m_pHttpHandler->getType() == HandlerType::HT_MODULE
        && m_iMatchedLen == 0)
    {
      setScriptNameLen(m_pContext->getURILen());
    }
    if (m_pContext != pOldCtx)
        m_iContextState &= ~CONTEXT_AUTH_CHECKED;
    return 0;
}


int HttpReq::processContextPath()
{
    int ret;
    const char *pURI;
    int   iURILen;
    pURI = getURI();
    iURILen = getURILen();
    if (m_pContext->getHandlerType() == HandlerType::HT_REDIRECT)
    {
        ret = contextRedirect(m_pContext, m_iMatchedLen);
        if (ret)
            return ret;
        return LS_FAIL;
    }

    if (m_iMatchedLen)
        return processMatchedURI(pURI, iURILen,
                                 HttpResourceManager::getGlobalBuf(),
                                 m_iMatchedLen);

    int cacheable = 0;
    ret = processURIEx(pURI, iURILen, cacheable);


    if (cacheable > 1)         //hotlinking status
        return cacheable;
    return ret;
}


char *HttpReq::allocateAuthUser()
{
    m_pAuthUser = (char *)ls_xpool_alloc(m_pPool, AUTH_USER_SIZE);
    return m_pAuthUser;
}


int HttpReq::redirectDir(const char *pURI)
{
    char newLoc[MAX_URL_LEN];
    char *p = newLoc;
    char *pEnd = newLoc + sizeof(newLoc);
    p += HttpUtil::escape(pURI, p, MAX_URL_LEN - 4);
    *p++ = '/';
    const char *pQueryString = getQueryString();
    if (pQueryString)
    {
        int len = getQueryStringLen();
        *p++ = '?';
        if (len > pEnd - p)
            len = pEnd - p;
        memmove(p, pQueryString, len);
        p += len;
    }
    setLocation(newLoc, p - newLoc);
    return SC_301;
}


int HttpReq::processMatchedURI(const char *pURI, int uriLen,
                               char *pMatched, int len)
{
    if (!m_pContext->allowBrowse())
    {
        LS_INFO(getLogSession(), "Context [%s] is not accessible: access denied.",
                m_pContext->getURI());
        return SC_403; //access denied
    }
    if (m_pHttpHandler->getType() >= HandlerType::HT_FASTCGI)
    {
        m_pRealPath = NULL;
        return 0;
    }
    char *pBegin = pMatched + 1;
    char *pEnd = pMatched + len;
    int cacheable = 0;
    return processPath(pURI, uriLen, pMatched, pBegin, pEnd, cacheable);

}


int HttpReq::processURIEx(const char *pURI, int uriLen, int &cacheable)
{
    if (m_pContext)
    {
        if (!m_pContext->allowBrowse())
        {
            LS_INFO(getLogSession(), "Context [%s] is not accessible: "
                    "access denied.", m_pContext->getURI());
            return SC_403; //access denied
        }
        if (m_pContext->getHandlerType() >= HandlerType::HT_FASTCGI)
        {
            int contextLen = m_pContext->getURILen();
            cacheable = (contextLen >= uriLen);
            m_iScriptNameLen = contextLen;
            if ((contextLen != uriLen)
                && (*(m_pContext->getURI() + contextLen - 1) == '/'))
                --contextLen;
            if (contextLen < uriLen)
                ls_str_xsetstr(&m_pathInfo, pURI + contextLen, uriLen - contextLen,
                               m_pPool);
            m_pRealPath = NULL;
            return 0;
        }
    }
    char *pBuf = HttpResourceManager::getGlobalBuf();
    int pathLen = translate(pURI, uriLen, m_pContext,
                            pBuf, GLOBAL_BUF_SIZE - 1);
    if (pathLen == -1)
    {
        LS_ERROR(getLogSession(),
                 "translate() failed, translation buffer is too small.");
        return SC_500;
    }
    char *pEnd = pBuf + pathLen;
    char *pBegin = pEnd - uriLen;
    if (m_pContext)
    {
        pBegin += m_pContext->getURILen();
        if (*(pBegin - 1) == '/')
            --pBegin;
    }
    if (m_pUrlStaticFileData
        && m_pUrlStaticFileData->tmaccess == DateTime::s_curTime)
        return 0;
    else
        return processPath(pURI, uriLen, pBuf, pBegin, pEnd, cacheable);
}


int HttpReq::processPath(const char *pURI, int uriLen, char *pBuf,
                         char *pBegin, char *pEnd,  int &cacheable)
{
    int ret;
    char *p;
    ret = SC_404;
    //find the first valid file or directory
    p = pEnd;
    do
    {
        while ((p > pBegin) && (*(p - 1) == '/'))
            --p;
        *p = 0;
        ret = ls_fio_stat(pBuf, &m_fileStat);

        if (p != pEnd)
            *p = '/';
        if (ret != -1)
        {
            if ((S_ISDIR(m_fileStat.st_mode)))
            {
                if (p == pEnd)
                    return redirectDir(pURI);
                else
                {
                    if (++p != pEnd)
                    {
                        LS_DBG_L(getLogSession(), "File not found [%s].", pBuf);
                        return SC_404;
                    }
                }
            }
            break;
        }
        while ((--p > pBegin) && (*p != '/'))
            ;
    }
    while (p >= pBegin);
    if (ret == -1)
    {
        //if ( strcmp( p, "/favicon.ico" ) != 0 )
        LS_DBG_L(getLogSession(), "(stat)File not found [%s].", pBuf);
        return checkSuffixHandler(pURI, uriLen, cacheable);
    }
    if (p != pEnd)
    {
        // set PATH_INFO and SCRIPT_NAME
        ls_str_xsetstr(&m_pathInfo, p, pEnd - p, m_pPool);
        int orgURILen = getOrgURILen();
        if (pEnd - p < orgURILen)
        {
            if (strncmp(getOrgURI() + orgURILen - (pEnd - p), p, pEnd - p) == 0)
                m_iScriptNameLen = uriLen - (pEnd - p);
        }
        *p = 0;
    }
    else
        cacheable = 1;
    // if it is a directory then try to append index file
    if (S_ISDIR(m_fileStat.st_mode))
    {
        if (p != pEnd)
            return checkSuffixHandler(pURI, uriLen, cacheable);
        //NOTE: why need to check this?
        //if (m_pHttpHandler->getType() != HandlerType::HT_NULL )
        //    return SC_404;
        int l = pBuf + GLOBAL_BUF_SIZE - p;
        const StringList *pIndexList = m_pContext->getIndexFileList();
        if (pIndexList)
        {
            StringList::const_iterator iter;
            StringList::const_iterator iterEnd = pIndexList->end();
            for (iter = pIndexList->begin();
                 iter < iterEnd; ++iter)
            {
                int n = (*iter)->len() + 1;
                if (n > l)
                    continue;
                memcpy(p, (*iter)->c_str(), n);
                if (ls_fio_stat(pBuf, &m_fileStat) != -1)
                {
                    p += n - 1;
                    l = 0;
                    appendIndexToUri((*iter)->c_str(), n - 1);
                    break;
                }
            }
        }
        cacheable = 0;
        if (l)
        {
            *p = 0;
            if (m_pContext->isAutoIndexOn())
            {
                addEnv("LS_AI_PATH", 10, pBuf, p - pBuf);
                const AutoStr2 *pURI = m_pVHost->getAutoIndexURI();
                ret = internalRedirectURI(pURI->c_str(), pURI->len());
                if (ret)
                    return ret;
                return LS_FAIL;  //internal redirect
            }
            LS_DBG_L(getLogSession(), "Index file is not available in [%s].",
                     pBuf);
            return SC_404; //can't find a index file
        }
    }
    *p = 0;
    {
        ret = checkSymLink(pBuf, p - pBuf, pBegin);
        if (ret)
            return ret;

        int forcedType = 0;
        if (m_pContext->shouldMatchFiles())
            forcedType = filesMatch(p);
        if ((!forcedType) &&
            (m_pHttpHandler->getType() == HandlerType::HT_NULL))
        {
            //m_pMimeType = NULL;
            ret = processSuffix(pBuf, p, cacheable);
            if (ret)
                return ret;
        }

    }
    m_sRealPathStore.setStr(pBuf, p - pBuf);

    if (m_pUrlStaticFileData)
    {
        if (m_pVHost->checkFileChanged(m_pUrlStaticFileData, m_fileStat) == 0)
        {
            m_pUrlStaticFileData->tmaccess = DateTime::s_curTime;
            return 0;
        }
        else
            m_pUrlStaticFileData = NULL;
    }

    m_pRealPath = &m_sRealPathStore;
    return ret;
}


int HttpReq::filesMatch(const char *pEnd)
{
    int len;
    const char *p = pEnd;

    while (*(p - 1) != '/')
        --p;
    len = pEnd - p;
    if (len)
    {
        assert(!m_pFMContext);
        m_pFMContext = m_pContext->matchFilesContext(p, len);
        if ((m_pFMContext) && (m_pFMContext->getConfigBits()& BIT_FORCE_TYPE))
        {
            if (m_pFMContext->getForceType())
            {
                m_pMimeType = m_pFMContext->getForceType();
                m_pHttpHandler = m_pMimeType->getHandler();
                return 1;
            }
        }
    }
    return 0;
}


int HttpReq::checkSymLink(const char *pPath, int pathLen,
                          const char *pBegin)
{
    int follow = m_pVHost->followSymLink();
    int restrained = m_pVHost->restrained();
    int hasLink = 0;
    HttpServerConfig &httpServConf = HttpServerConfig::getInstance();
    if ((follow == LS_ALWAYS_FOLLOW) && !restrained &&
        (httpServConf.checkDeniedSymLink() == 0))
        return 0;
    //--pBegin;
    while (*pBegin != '/' && pBegin > pPath)
        --pBegin;
    char achTmp[MAX_BUF_SIZE];
    char *pEnd;
    memmove(achTmp, pPath, pathLen);
    pEnd = &achTmp[ pathLen ];
    *pEnd = 0;
    //int rpathLen = GPath::checkSymLinks( pBuf, p, pBuf + MAX_BUF_SIZE,
    //                pBegin, follow, &hasLink );
    int rpathLen = GPath::checkSymLinks(achTmp, pEnd,
                                        &achTmp[MAX_BUF_SIZE - 1],
                                        &achTmp[pBegin - pPath], follow, &hasLink);
    if (rpathLen > 0)
    {
        if (httpServConf.checkDeniedSymLink())
        {
            if (httpServConf.getDeniedDir()->isDenied(achTmp))
            {
                LS_INFO(getLogSession(), "checkSymLinks() pBuf:%p, pBegin: %p, "
                        "target: %s, return: %d, hasLink: %d, errno: %d",
                        pPath, pBegin, achTmp, rpathLen, hasLink, errno);
                LS_INFO(getLogSession(),
                        "Path [%s] is in access denied list, access denied.",
                        achTmp);
                return SC_403;
            }
        }
        //p = pBuf + rpathLen;
    }
    else
    {
        LS_INFO(getLogSession(),
                "Found symbolic link, or owner of symbolic link and link "
                "target does not match for path [%s], access denied. ret=%d, errno=%d",
                pPath, rpathLen, errno);
        return SC_403;
    }
    if (hasLink && restrained)
    {
        if (strncmp(achTmp, m_pVHost->getVhRoot()->c_str(),
                    m_pVHost->getVhRoot()->len()) != 0)
        {
            if (strncmp(achTmp, m_pContext->getLocation(),
                        m_pContext->getLocationLen()) != 0)
            {
                LS_INFO(getLogSession(),
                        "Path [%s] is beyond restrained VHOST root [%s]",
                        achTmp, m_pVHost->getVhRoot()->c_str());

                return SC_403;
            }
        }
    }
    LS_DBG_H(getLogSession(),
             "Check Symbolic link for [%s] is successful, access to target "
             "[%s] is granted", pPath, achTmp);
    return 0;
}


int HttpReq::checkPathInfo(const char *pURI, int iURILen, int &pathLen,
                           short &scriptLen, short &pathInfoLen,
                           const HttpContext *pContext)
{
    if (!pContext)
    {
        pContext = m_pVHost->bestMatch(pURI, iURILen);
        if (!pContext)
            pContext = &m_pVHost->getRootContext();
    }
    int contextLen = pContext->getURILen();
    char *pBuf = HttpResourceManager::getGlobalBuf();
    if (pContext->getHandlerType() >= HandlerType::HT_FASTCGI)
    {
        scriptLen = contextLen;
        if (*(pContext->getURI() + contextLen - 1) == '/')
            --contextLen;
        if (contextLen < iURILen)
            pathInfoLen = iURILen - contextLen;
        memccpy(pBuf, getDocRoot()->c_str(), 0, GLOBAL_BUF_SIZE - 1);
        pathLen = getDocRoot()->len();
        memccpy(pBuf + pathLen, pURI, 0, GLOBAL_BUF_SIZE - pathLen);
        pathLen += contextLen;
        return 0;
    }
    if (m_iMatchedLen > 0)
        pathLen = m_iMatchedLen;
    else
        pathLen = translate(pURI, iURILen, pContext,
                            pBuf, GLOBAL_BUF_SIZE - 1);
    if (pathLen == -1)
        return LS_FAIL;
    char *pEnd = pBuf + pathLen;
    char *pBegin = pEnd - iURILen;
    if (*pURI == '/')
        pBegin += pContext->getURILen() - 1;
    //find the first valid file or directory
    char *p = NULL;
    char *p1 = pEnd;
    char *pTest;
    int ret;

    do
    {
        pTest = p1;
        while ((pTest > pBegin) && (*(pTest - 1) == '/'))
            --pTest;
        *pTest = 0;
        ret = ls_fio_stat(pBuf, &m_fileStat);

        if (pTest != pEnd)
            *pTest = '/';
        if (ret != -1)
        {
            if (S_ISREG(m_fileStat.st_mode))
                p = pTest;
            break;
        }
        p1 = p = pTest;
        while ((--p1 > pBegin) && (*p1 != '/'))
            ;
    }
    while (p1 > pBegin);
    if (!p)
        p = pTest;
    // set PATH_INFO and SCRIPT_NAME
    pathInfoLen = (pEnd - p);
    int orgURILen = getOrgURILen();
    if (pathInfoLen < orgURILen)
    {
        if (strncmp(getOrgURI() + orgURILen - pathInfoLen, p, pathInfoLen) == 0)
            scriptLen = getURILen() - pathInfoLen;
    }
    pathLen = p - pBuf;
    return 0;
}


int HttpReq::addWWWAuthHeader(HttpRespHeaders &buf) const
{
    if (m_pHTAuth)
        return m_pHTAuth->addWWWAuthHeader(buf);
    else
        return 0;
}


//NOTICE: Returns length set, currently return value isn't used, so may switch to new string if needed.
int HttpReq::setLocation(const char *pLoc, int len)
{
    assert(pLoc);
    int ret = ls_str_xsetstr(&m_location, pLoc, len, m_pPool);
    if (m_location.ptr != NULL)
        sanitizeHeaderValue(m_location.ptr, m_location.len);
    return ret;
}


int  HttpReq::appendRedirHdr(const char *pDisp, int len)
{
    ls_str_xappend(&m_redirHdrs, pDisp, len, m_pPool);
    char *p = ls_str_buf(&m_redirHdrs) + ls_str_len(&m_redirHdrs) - 2;
    *p++ = '\r';
    *p = '\n';
    return len;
}


void HttpReq::updateBodyType(const char *pHeader)
{
    if (strncasecmp(pHeader,
                    "application/x-www-form-urlencoded", 33) == 0)
        m_iBodyType = REQ_BODY_FORM;
    else if (strncasecmp(pHeader, "multipart/form-data", 19) == 0)
        m_iBodyType = REQ_BODY_MULTIPART;
}


#define HTTP_PAGE_SIZE 4096
int HttpReq::prepareReqBodyBuf()
{
//     if ((m_lEntityLength != CHUNKED) &&
//         (m_lEntityLength <= m_headerBuf.capacity() - m_iReqHeaderBufFinished))
//     {
//         m_pReqBodyBuf = new VMemBuf();
//         if (!m_pReqBodyBuf)
//             return SC_500;
//         BlockBuf *pBlock = new BlockBuf(m_headerBuf.begin() +
//                                         m_iReqHeaderBufFinished, m_lEntityLength);
//         if (!pBlock)
//             return SC_500;
//         m_pReqBodyBuf->set(pBlock);
//     }
//     else
    {
        m_pReqBodyBuf = HttpResourceManager::getInstance().getVMemBuf();
        if (!m_pReqBodyBuf || m_pReqBodyBuf->reinit(m_lEntityLength))
        {
            LS_ERROR(getLogSession(),
                     "Failed to obtain or reinitialize VMemBuf.");
            return SC_500;
        }
    }
    return 0;
}


void HttpReq::replaceBodyBuf(VMemBuf *pBuf)
{
    VMemBuf *pOld = getBodyBuf();
    setContentLength(pBuf->getCurWOffset());
    m_pReqBodyBuf = pBuf;
    if (pOld)
    {
        if (pOld->isMmaped())
            HttpResourceManager::getInstance().recycle(pOld);
        else
            delete pOld;
    }
}


void HttpReq::updateNoRespBodyByStatus(int code)
{
    if (!(m_iContextState & KEEP_AUTH_INFO))
    {
        switch (m_code = code)
        {
        case SC_100:
        case SC_101:
        case SC_204:
        case SC_205:
        case SC_304:
            m_iNoRespBody = 1;
        }
    }
}


void HttpReq::processReqBodyInReqHeaderBuf()
{
    int already = m_iReqHeaderBufRead - m_iReqHeaderBufFinished;
    if (!already)
        return;
    if (already > m_lEntityLength)
        already = m_lEntityLength;
    size_t size;
    if (m_lEntityLength > m_headerBuf.capacity() - m_iReqHeaderBufFinished)
    {
        char *pBuf = getBodyBuf()->getWriteBuffer(size);
        assert(pBuf);
        assert((int)size >= already);
        memmove(pBuf, m_headerBuf.begin() + m_iReqHeaderBufFinished, already);
    }
    getBodyBuf()->writeUsed(already);
    m_lEntityFinished = already;
    m_iReqHeaderBufFinished += already;
}


void HttpReq::tranEncodeToContentLen()
{
    int off = m_commonHeaderOffset[HttpHeader::H_TRANSFER_ENCODING];
    if (!off)
        return;
    int len = 8;
    char *pBegin = m_headerBuf.begin() + off - 1;
    while (*pBegin != ':')
    {
        ++len;
        --pBegin;
    }
    if ((pBegin[-1] | 0x20) != 'g')
        return;
    pBegin -= 17;
    len += 17;
    int n = ls_snprintf(pBegin, len, "Content-length: %lld", 
                        (long long)m_lEntityFinished);
    memset(pBegin + n, ' ', len - n);
    m_commonHeaderOffset[HttpHeader::H_CONTENT_LENGTH] =
        pBegin + 16 - m_headerBuf.begin();
    m_commonHeaderLen[ HttpHeader::H_CONTENT_LENGTH] = n - 16;
    m_lEntityLength = m_lEntityFinished;
}


const AutoStr2 *HttpReq::getDocRoot() const
{
    return m_pVHost->getDocRoot();
}


const ExpiresCtrl *HttpReq::shouldAddExpires()
{
    const ExpiresCtrl *p;
    if (m_pContext)
        p = &m_pContext->getExpires();
    else if (m_pVHost)
        p = &m_pVHost->getExpires();
    else
        p = HttpMime::getMime()->getDefault()->getExpires();
    if (p->isEnabled())
    {
        if (m_pMimeType->getExpires()->getBase())
            p = m_pMimeType->getExpires();
        else if (!p->getBase())
            p = NULL;
    }
    else
        p = NULL;
    return p;
}


int HttpReq::checkHotlink(const HotlinkCtrl *pHLC, const char *pSuffix)
{
    if ((!pHLC) ||
        (pHLC->getSuffixList()->find(pSuffix) == NULL))
        return 0;
    int ret = 0;
    char chNULL = 0;
    char *pRef = (char *)getHeader(HttpHeader::H_REFERER);
    if (*pRef)
    {
        char *p = (char *)memchr(pRef + 4, ':', 2);
        if (!p)
            pRef = &chNULL;
        else
        {
            if ((*(++p) != '/') || (*(++p) != '/'))
                pRef = &chNULL;
            else
                pRef = p + 1;
        }
    }
    if (!*pRef)
    {
        if (!pHLC->allowDirectAccess())
        {
            LS_INFO(getLogSession(),
                    "[HOTLINK] Direct access detected, access denied.");
            ret = SC_403;
        }
    }
    else
    {
        int len = strcspn(pRef, "/:");
        char ch = *(pRef + len);
        *(pRef + len) = 0;
        if (pHLC->onlySelf())
        {
            const char *pHost = getHeader(HttpHeader::H_HOST);
            if (memcmp(pHost, pRef, getHeaderLen(HttpHeader::H_HOST)) != 0)
            {
                LS_INFO(getLogSession(), "[HOTLINK] Reference from other "
                        "website, access denied, referrer: [%s]", pRef);
                ret = SC_403;
            }
        }
        else
        {
            if (!pHLC->allowed(pRef, len))
            {
                LS_INFO(getLogSession(), "[HOTLINK] Disallowed referrer,"
                        " access denied, referrer: [%s]", pRef);
                ret = SC_403;
            }
        }
        *(pRef + len) = ch;
    }
    if (ret)
    {
        const char *pRedirect = pHLC->getRedirect();
        if (pRedirect)
        {
            if (strcmp(pRedirect, getURI()) == 0)     //redirect to the same url
                return 0;
            setLocation(pRedirect, pHLC->getRedirectLen());
            return SC_302;
        }
    }
    return ret;
}


void HttpReq::dumpHeader()
{
    const char *pBegin = getOrgReqLine();
    char *pEnd = (char *)pBegin + getOrgReqLineLen();
    if (m_iHeaderStatus == HEADER_REQUEST_LINE)
        return;
    if (pEnd >= m_headerBuf.begin() + m_iReqHeaderBufFinished)
    {
        pEnd = m_headerBuf.begin() + m_iReqHeaderBufFinished;
        if (pEnd >= m_headerBuf.begin() + m_headerBuf.capacity())
            pEnd = m_headerBuf.begin() + m_headerBuf.capacity() - 1;
    }
    if (pEnd < pBegin)
        pEnd = (char *)pBegin;
    *pEnd = 0;
    LS_INFO(getLogSession(), "Content len: %lld, Request line: \n%s",
            (long long)m_lEntityLength, pBegin);
    if (m_iRedirects > 0)
    {
        LS_INFO(getLogSession(), "Redirect: #%d, URL: %s",
                m_iRedirects, getURI());
    }
}


int HttpReq::getUGidChroot(uid_t *pUid, gid_t *pGid,
                           const AutoStr2 **pChroot)
{
    ServerProcessConfig &procConfig = ServerProcessConfig::getInstance();
    if (m_fileStat.st_mode & (S_ISUID | S_ISGID))
    {
        if (!m_pContext || !m_pContext->allowSetUID())
        {
            LS_INFO(getLogSession(), "Context [%s] set UID/GID mode is "
                    "not allowed, access denied.", m_pContext->getURI());
            return SC_403;
        }
    }
    if (m_pVHost && !m_pContext)
        m_pContext = &m_pVHost->getRootContext();
    char chMode = UID_FILE;
    if (m_pContext)
        chMode = m_pContext->getSetUidMode();
    switch (chMode)
    {
    case UID_FILE:
        *pUid = m_fileStat.st_uid;
        *pGid = m_fileStat.st_gid;
        break;
    case UID_DOCROOT:
        if (m_pVHost)
        {
            *pUid = m_pVHost->getUid();
            *pGid = m_pVHost->getGid();
            break;
        }
    case UID_SERVER:
    default:
        *pUid = procConfig.getUid();
        *pGid = procConfig.getGid();
    }
    if (procConfig.getForceGid())
        *pGid = procConfig.getForceGid();
    if ((*pUid < procConfig.getUidMin()) ||
        (*pGid < procConfig.getGidMin()))
    {
        LS_INFO(getLogSession(), "CGI's UID or GID is smaller "
                "than the minimum UID, GID configured, access denied.");
        return SC_403;
    }
    *pChroot = NULL;
    if (m_pVHost)
    {
        chMode = m_pContext->getChrootMode();
        switch (chMode)
        {
        case CHROOT_VHROOT:
            *pChroot = m_pVHost->getVhRoot();
            break;
        case CHROOT_PATH:
            *pChroot = m_pVHost->getChroot();
            if (!(*pChroot)->c_str())
                *pChroot = NULL;
        }
    }
    if (!*pChroot)
        *pChroot = procConfig.getChroot();
    return 0;

}


const AutoStr2 *HttpReq::getDefaultCharset() const
{
    if (m_pContext)
        return m_pContext->getDefaultCharset();
    return NULL;
}


void  HttpReq::smartKeepAlive(const char *pValue)
{
    if (m_pVHost->getSmartKA())
        if (!HttpMime::shouldKeepAlive(pValue))
            m_iKeepAlive = 0;
}


const char *HttpReq::findEnvAlias(const char *pKey, int keyLen,
                                  int &aliasKeyLen)
{
    int count = sizeof(envAlias) / sizeof(envAlias_t);
    for (int i = 0; i < count; ++i)
    {
        if (envAlias[i].orgNameLen == keyLen &&
            strncasecmp(envAlias[i].orgName, pKey, keyLen) == 0)
        {
            aliasKeyLen = envAlias[i].inuseNameLen;
            return envAlias[i].inuseName;
        }
    }

    //can't find alias, use the org one
    aliasKeyLen = keyLen;
    return pKey;
}


ls_strpair_t *HttpReq::addEnv(const char *pOrgKey, int orgKeyLen,
                              const char *pValue, int valLen)
{
    int keyLen = 0;
    const char *pKey = findEnvAlias(pOrgKey, orgKeyLen, keyLen);
    ls_strpair_t *sp;

    if (m_pEnv == NULL)
        m_pEnv = RadixNode::newNode(m_pPool, NULL, NULL);

    if ((sp = (ls_strpair_t *)m_pEnv->find(pKey, keyLen)) == NULL)
    {
        sp = (ls_strpair_t *)ls_xpool_alloc(m_pPool, sizeof(ls_strpair_t));
        ls_str_x(&sp->key, pKey, keyLen, m_pPool);
        ls_str_x(&sp->val, pValue, valLen, m_pPool);
        if (m_pEnv->insert(m_pPool, ls_str_cstr(&sp->key),
                           ls_str_len(&sp->key), sp) == NULL)
            return NULL;
    }
    else if (strncasecmp(ls_str_cstr(&sp->val), pValue, valLen) != 0)
        ls_str_xsetstr(&sp->val, pValue, valLen, m_pPool);
    ++m_iEnvCount;
    return sp;
}


const char *HttpReq::getEnv(const char *pOrgKey, int orgKeyLen,
                            int &valLen)
{
    int keyLen = 0;
    const char *pKey = findEnvAlias(pOrgKey, orgKeyLen, keyLen);
    ls_strpair_t *sp;

    if ((m_pEnv != NULL)
        && ((sp = (ls_strpair_t *)m_pEnv->find(pKey, keyLen)) != NULL))
    {
        valLen = ls_str_len(&sp->val);
        return ls_str_cstr(&sp->val);
    }
    return NULL;
}


const RadixNode *HttpReq::getEnvNode() const
{
    return m_pEnv;
}


int HttpReq::getEnvCount()
{
    return m_iEnvCount;
}


void HttpReq::unsetEnv(const char *pKey, int keyLen)
{
    ls_strpair_t *sp;

    if (m_pEnv != NULL)
    {
        sp = (ls_strpair_t *)m_pEnv->erase(pKey, keyLen);
        if (sp == NULL)
            return;
        ls_str_xd(&sp->key, m_pPool);
        ls_str_xd(&sp->val, m_pPool);
        ls_xpool_free(m_pPool, sp);
        --m_iEnvCount;
    }
}


const char *HttpReq::getUnknownHeaderByIndex(int idx, int &keyLen,
        const char *&pValue, int &valLen)
{
    key_value_pair *pIdx = getUnknHeaderPair(idx);
    if (pIdx)
    {
        pValue = m_headerBuf.getp(pIdx->valOff);
        valLen = pIdx->valLen;
        keyLen = pIdx->keyLen;
        return m_headerBuf.getp(pIdx->keyOff);
    }
    return NULL;
}


const char *HttpReq::getCfIpHeader(int &len)
{
    key_value_pair *pIdx = getUnknHeaderPair(m_iCfIpHeader - 1);
    if (pIdx)
    {
        len = pIdx->valLen;
        return m_headerBuf.getp(pIdx->valOff);
    }
    return NULL;
}


char HttpReq::getRewriteLogLevel() const
{
    return m_pVHost->getRewriteLogLevel();
}


void HttpReq::appendHeaderIndexes(IOVec *pIOV, int cntUnknown)
{
    pIOV->append(&m_commonHeaderLen,
                 (char *)&m_headerIdxOff - (char *)&m_commonHeaderLen);
    if (cntUnknown > 0)
    {
        key_value_pair *pIdx = getUnknHeaderPair(0);
        pIOV->append(pIdx, sizeof(key_value_pair) * cntUnknown);
    }
}


const AutoBuf *HttpReq::getExtraHeaders() const
{
    return (m_pContext) ? m_pContext->getExtraHeaders() : NULL;
}


char HttpReq::isGeoIpOn() const
{
    return (m_pContext) ? m_pContext->isGeoIpOn() : 0;
}


uint32_t HttpReq::isIpToLocOn() const
{
    return (m_pContext) ? m_pContext->isIpToLocOn() : 0;
}


const char *HttpReq::encodeReqLine(int &len)
{
    const char *pURI = getURI();
    int uriLen = getURILen();
    int qsLen = getQueryStringLen();
    int maxLen = uriLen * 3 + 16 + qsLen;
    char *p = (char *)ls_xpool_alloc(m_pPool, maxLen + 10);
    char *pStart = p;
    memmove(p, HttpMethod::get(m_method), HttpMethod::getLen(m_method));
    p += HttpMethod::getLen(m_method);
    *p++ = ' ';
    //p = escape_uri( p, pURI, uriLen );
    memmove(p, pURI, uriLen);
    p += uriLen;
    if (qsLen > 0)
    {
        *p++ = '?';
        memmove(p, getQueryString(), qsLen);
        p += qsLen;
    }
    len = p - pStart;
    return pStart;
}


int HttpReq::getDecodedOrgReqURI(char *&pValue)
{
    if (m_iRedirects > 0)
    {
        pValue = ls_str_buf(&(m_pUrls[0].key));
        return ls_str_len(&(m_pUrls[0].key));
    }
    else
    {
        pValue = ls_str_buf(&m_curUrl.key);
        return getURILen();
    }
}


SSIConfig *HttpReq::getSSIConfig()
{
    if (m_pContext)
        return m_pContext->getSSIConfig();
    return NULL;
}


uint32_t HttpReq::isXbitHackFull() const
{
    return (m_pContext) ? (m_pContext->isXbitHackFull() &&
                           (S_IXGRP & m_fileStat.st_mode)) : 0 ;
}


uint32_t HttpReq::isIncludesNoExec() const
{
    return (m_pContext) ? m_pContext->isIncludesNoExec() : 1 ;
}


void HttpReq::backupPathInfo()
{
    m_pSSIRuntime->savePathInfo(m_pathInfo, m_iRedirects);
}


void HttpReq::restorePathInfo()
{
    int oldRedirects = m_iRedirects;
    m_pSSIRuntime->restorePathInfo(m_pathInfo, m_iRedirects);
    if (m_iRedirects < oldRedirects)
    {
        m_curUrl.key = m_pUrls[m_iRedirects].key;
        m_curUrl.val = m_pUrls[m_iRedirects].val;
    }
}


void HttpReq::stripRewriteBase(const HttpContext *pCtx,
                               const char *&pURL, int &iURLLen)
{
    if ((pCtx->getLocationLen() <= m_iMatchedLen) &&
        (strncmp(HttpResourceManager::getGlobalBuf(), pCtx->getLocation(),
                 pCtx->getLocationLen()) == 0))
    {
        pURL = HttpResourceManager::getGlobalBuf() + pCtx->getLocationLen();
        iURLLen = m_iMatchedLen - pCtx->getLocationLen();
    }
}


int HttpReq::detectLoopRedirect(const char *pURI, int uriLen,
                                const char *pArg, int qsLen, int isSSL)
{
    //detect loop
    int i;
    const char *p = pURI;
    int relativeLen = uriLen;
    if (strncasecmp(p, "http", 4) == 0)
    {
        int isHttps;
        p += 4;
        isHttps = (*p == 's');
        if (isHttps != isSSL)
            return 0;
        if (isHttps)
            ++p;
        if (strncmp(p, "://", 3) == 0)
            p += 3;
        const char *pOldHost = getHeader(HttpHeader::H_HOST);
        int oldHostLen = getHeaderLen(HttpHeader::H_HOST);
        if ((*pOldHost) &&
            (strncasecmp(p, pOldHost, oldHostLen) != 0))
            return 0;
        p += oldHostLen;
        if (*p != '/')
            return 0;
        relativeLen -= p - pURI;
    }

    const char *pCurURI = getURI();
    const char *pCurArg = getQueryString();
    int         iCurURILen = getURILen();
    int         iCurQSLen = getQueryStringLen();
    if ((iCurURILen == relativeLen) && (iCurQSLen == qsLen)
        && (pCurURI != p) &&
        (strncmp(p, pCurURI, iCurURILen) == 0) &&
        (strncmp(pArg, pCurArg, iCurQSLen) == 0))
        return 1;
    for (i = 0; i < m_iRedirects; ++i)
    {
        ls_strpair_t tmp = m_pUrls[i];
        if (((((int)ls_str_len(&tmp.key) == uriLen)
              && (strncmp(ls_str_cstr(&tmp.key), pURI,
                          ls_str_len(&tmp.key)) == 0))
             || (((int)ls_str_len(&tmp.key) == relativeLen)
                 && (strncmp(ls_str_cstr(&tmp.key), p,
                             ls_str_len(&tmp.key)) == 0)))
            && ((int)ls_str_len(&tmp.val) == qsLen)
            && (strncmp(ls_str_cstr(&tmp.val), pArg,
                        ls_str_len(&tmp.val)) == 0))
            break;
    }
    if (i < m_iRedirects)   //loop detected
        return 1;

    return 0;
}


int HttpReq::getETagFlags() const
{
    int tagMod = 0;
    int etag;
    if (m_pContext)
        etag = m_pContext->getFileEtag();
    else if (m_pVHost)
        etag = m_pVHost->getRootContext().getFileEtag();
    else
    {
        etag = HttpServerConfig::getInstance()
               .getGlobalVHost()->getRootContext().getFileEtag();
    }
    if (tagMod)
    {
        int mask = (tagMod & ETAG_MOD_ALL) >> 3;
        etag = (etag & ~mask) | (tagMod & mask);
    }
    return etag;
}


int HttpReq::checkScriptPermission()
{
    if (!m_pRealPath)
        return 1;
    if (m_fileStat.st_mode &
        HttpServerConfig::getInstance().getScriptForbiddenBits())
    {
        LS_INFO(getLogSession(),
                "[%s] file permission is restricted for script %s.",
                getVHost()->getName(), m_pRealPath->c_str());
        return 0;
    }
    return 1;
}

int HttpReq::removeCookie(const char *pName, int nameLen)
{
    cookieval_t *pEntry = getCookie(pName, nameLen);
    if (pEntry)
    {
        if (m_cookies.getSize() == 1)
            m_commonHeaderOffset[ HttpHeader::H_COOKIE ] = 0;
        else
        {
            const char *p = m_headerBuf.getp(pEntry->keyOff);
            memset((char *)p, ' ', m_headerBuf.getp(pEntry->valOff)
                   + pEntry->valLen - p);
            pEntry->keyLen = pEntry->keyOff = 0;
        }
        return 1;
    }
    return 0;
}


cookieval_t *HttpReq::setCookie(const char *pName, int nameLen,
                                const char *pValue,
                                int valLen)
{
    char *p;
    cookieval_t *pIdx = NULL;
    int keyOff, valOff;
    if (m_commonHeaderLen[ HttpHeader::H_COOKIE ] >= 16384 ||
        (int)m_commonHeaderLen[ HttpHeader::H_COOKIE ] + valLen + nameLen + 1 >
        32768)
    {
        LS_DBG_L(getLogSession(),
                 "Cookie size [%hd] is too large, stop updating cookie from Set-Cookie.",
                 m_commonHeaderLen[ HttpHeader::H_COOKIE ]);
        return NULL;
    }
    pIdx = getCookie(pName, nameLen);
    if (pIdx)
    {
        if (valLen <= pIdx->valLen)
        {
            p = (char *)m_headerBuf.getp(pIdx->valOff);
            if ((valLen == pIdx->valLen) &&
                (memcmp(pValue, p, valLen) == 0))
            {
                LS_DBG_L(getLogSession(), "same value [%.*s=%.*s].",
                         nameLen, pName, valLen, pValue);
                return NULL;
            }
            clearContextState(CACHE_PRIVATE_KEY | CACHE_KEY);

            memmove(p, pValue, valLen);
            LS_DBG_L(getLogSession(), "replace cookie [%.*s] with new value [%.*s].",
                     nameLen, pName, valLen, pValue);
            pIdx->flag |= COOKIE_FLAG_RESP_UPDATE;
            int diff = pIdx->valLen - valLen;
            if (diff > 0)
            {
                if (pIdx->valLen + pIdx->valOff ==
                    m_commonHeaderOffset[ HttpHeader::H_COOKIE ] +
                    m_commonHeaderLen[ HttpHeader::H_COOKIE ])
                    m_commonHeaderLen[ HttpHeader::H_COOKIE ] -= diff;
                memset(p + valLen, ' ', diff);
                pIdx->valLen = valLen;
            }
            return pIdx;
        }
        p = m_headerBuf.getp(pIdx->keyOff);
        memset((char *)p, ' ', m_headerBuf.getp(pIdx->valOff) + pIdx->valLen
               - p);
    }
    if (m_cookies.getSize() == 0)
    {
        //create cookie: header
        m_headerBuf.append("Cookie: ", 8);
        m_commonHeaderOffset[ HttpHeader::H_COOKIE ] = m_headerBuf.size();
        m_commonHeaderLen[ HttpHeader::H_COOKIE ] = 0;
    }
    else if (m_headerBuf.size() > m_commonHeaderOffset[ HttpHeader::H_COOKIE ]
             + m_commonHeaderLen[ HttpHeader::H_COOKIE ] + 4)
    {
        copyCookieHeaderToBufEnd(m_commonHeaderOffset[ HttpHeader::H_COOKIE ],
                                 NULL, m_commonHeaderLen[ HttpHeader::H_COOKIE ]);
    }
    else
        m_headerBuf.resize(m_commonHeaderOffset[ HttpHeader::H_COOKIE ]
                           + m_commonHeaderLen[ HttpHeader::H_COOKIE ]);

    if (!pIdx)
    {
        pIdx = m_cookies.insertCookieIndex(m_pPool, &m_headerBuf, pName, nameLen);
        pIdx->flag = 0;
        m_cookies.cookieClassify(pIdx, pName, nameLen, pValue, valLen);
        LS_DBG_L(getLogSession(), "insert new cookie[%.*s].",
                 nameLen, pName);
    }

    if (m_commonHeaderLen[ HttpHeader::H_COOKIE ] > 0)
    {
        if (*(m_headerBuf.end() - 1) != ';')
        {
            m_headerBuf.append(";", 1);
            ++m_commonHeaderLen[ HttpHeader::H_COOKIE ];
        }
    }

    keyOff = m_headerBuf.size();
    valOff = keyOff + nameLen + 1;
    if (pValue == pName + nameLen + 1)
    {
        m_headerBuf.append(pName, nameLen + valLen + 1);
        *m_headerBuf.getp(valOff - 1) = '=';
    }
    else
    {
        m_headerBuf.append(pName, nameLen);
        m_headerBuf.append("=", 1);
        m_headerBuf.append(pValue, valLen);
    }
    LS_DBG_L(getLogSession(), "append cookie [%.*s] with new value [%.*s].",
             nameLen, pName, valLen, pValue);

    pIdx->keyOff = keyOff;
    pIdx->flag |= COOKIE_FLAG_RESP_UPDATE;
    pIdx->keyLen = nameLen;
    pIdx->valOff = valOff;
    pIdx->valLen = valLen;
    m_commonHeaderLen[ HttpHeader::H_COOKIE ] += nameLen + valLen + 1;

    m_headerBuf.append("\r\n", 2);

    clearContextState(CACHE_PRIVATE_KEY | CACHE_KEY);

    return pIdx;

}


int HttpReq::processSetCookieHeader(const char *pValue, int valLen)
{
    const char *pEnd = pValue + valLen;
    const char *pCookieName, *pCookieValue;
    int cookieNameLen, cookieValueLen;
    if (getContextState(DUM_BENCHMARK_TOOL))
        return 0;
    while ((pValue < pEnd) && isspace(*pValue))
        ++pValue;
    pCookieName = pValue;
    pValue = pCookieValue = (const char *)memchr(pValue, '=', pEnd - pValue);
    if (!pCookieValue)
        return -1;
    while (isspace(pValue[-1]))
        --pValue;
    cookieNameLen = pValue - pCookieName;
    if (cookieNameLen <= 0)
        return -1;

    ++pCookieValue;
    pValue = (const char *)memchr(pCookieValue, ';', pEnd - pCookieValue);
    if (!pValue)
        pValue = pEnd;
    while (pValue > pCookieValue && isspace(pValue[-1]))
        --pValue;
    while (pValue > pCookieValue && isspace(*pCookieValue))
        ++pCookieValue;
    cookieValueLen = pValue - pCookieValue;
    return (setCookie(pCookieName, cookieNameLen, pCookieValue,
                      cookieValueLen) != NULL);
}


cookieval_t *HttpReq::getCookie(const char *pName, int nameLen)
{
    int i;
    parseCookies();

    for (i = 0; i < m_cookies.getSize(); ++i)
    {
        cookieval_t *pEntry = m_cookies.getObj(i);
        if (pEntry->keyLen == nameLen)
        {
            char *p = (char *)m_headerBuf.getp(pEntry->keyOff);
            if (strncasecmp(pName, p, nameLen) == 0)
                return pEntry;
        }
    }
    return NULL;
}


int HttpReq::parseCookies()
{
    const char *pCookies;
    const char *pEnd;
    const char *p, *pVal, *pNameEnd, *pValEnd;
    int nameOff, valOff, len;

    if (m_iContextState & COOKIE_PARSED)
        return 0;
    m_iContextState |= COOKIE_PARSED;

    pCookies = getHeader(HttpHeader::H_COOKIE);
    len = getHeaderLen(HttpHeader::H_COOKIE);
    if (!pCookies || !*pCookies || len == 0)
        return 0;
    pEnd = pCookies + len ;
    for (; pCookies < pEnd; pCookies = p + 1)
    {
        p = (const char *)memchr(pCookies, ';', pEnd - pCookies);
        if (!p)
            p = pEnd;
        pValEnd = p;
        while (isspace(*pCookies))
            ++pCookies;
        if (p == pCookies)
            continue;
        pVal = (const char *)memchr(pCookies, '=', p - pCookies);
        if (!pVal)
            continue;
        pNameEnd = pVal++;
        while (isspace(*pVal))
            ++pVal;
        nameOff = pCookies - m_headerBuf.begin();
        valOff = pVal - m_headerBuf.begin();
        while (isspace(pValEnd[-1]))
            --pValEnd;

        cookieval_t *pCookieEntry = m_cookies.insertCookieIndex(m_pPool,
                                    &m_headerBuf, pCookies, pNameEnd - pCookies);
        if (!pCookieEntry)
            return -1;

        pCookieEntry->keyOff    = nameOff;
        pCookieEntry->flag      = 0;
        pCookieEntry->keyLen    = pNameEnd - pCookies;
        pCookieEntry->valOff    = valOff;
        pCookieEntry->valLen    = pValEnd - pVal;
        m_cookies.cookieClassify(pCookieEntry, pCookies, pCookieEntry->keyLen,
                                 pVal, pCookieEntry->valLen);
    }
    return 0;
}

cookieval_t *CookieList::insertCookieIndex(ls_xpool_t *pool,
        AutoBuf *pData,
        const char *pName, int nameLen)
{
    if (getCapacity() == 0)
        guarantee(pool, 10);
    else if (getCapacity() <= getSize() + 1)
        guarantee(pool, getCapacity() * 2);

    cookieval_t *pCookieEntry = getNew();
    if (!pCookieEntry)
        return NULL;

    while (pCookieEntry > begin())
    {
        cookieval_t *pCmp = pCookieEntry - 1;
        const char *pCmpName = pData->getp(pCmp->keyOff);
        int len = pCmp->keyLen;
        if (len > nameLen)
            len = nameLen;
        int res = strncasecmp(pCmpName, pName, len);
        if (res > 0 || (res == 0 && pCmp->keyLen > nameLen))
            --pCookieEntry;
        else
            break;
    }
    if (pCookieEntry != end() - 1)
    {
        memmove(pCookieEntry + 1, pCookieEntry,
                (char *)(end() - 1) - (char *)pCookieEntry);
        if (m_iSessIdx && m_iSessIdx - 1 >= pCookieEntry - begin())
            ++m_iSessIdx;
    }
    return pCookieEntry;
}

void CookieList::cookieClassify(cookieval_t *pCookieEntry,
                                const char *pCookies, int nameLen,
                                const char *pVal, int valLen)
{
    if (valLen >= 32)
    {
        if (nameLen == 8 && strncasecmp(pCookies, "frontend", 8) == 0)
        {
            pCookieEntry->flag |= COOKIE_FLAG_FRONTEND;
            if (!isSessIdxSet() ||
                ((begin() + getSessIdx())->flag & COOKIE_FLAG_PHPSESSID))
                setSessIdx(pCookieEntry - begin());
        }
        else if (nameLen == 9 && strncasecmp(pCookies, "PHPSESSID", 9) == 0)
        {
            pCookieEntry->flag |= COOKIE_FLAG_PHPSESSID;
            if (!isSessIdxSet())
                setSessIdx(pCookieEntry - begin());
        }
        else if (nameLen == 10 && strncasecmp(pCookies, "xf_session", 10) == 0)
        {
            pCookieEntry->flag |= COOKIE_FLAG_XF_SESSID;
            if (!isSessIdxSet() ||
                ((begin() + getSessIdx())->flag & COOKIE_FLAG_PHPSESSID))
                setSessIdx(pCookieEntry - begin());
        }
    }
}

int HttpReq::copyCookieHeaderToBufEnd(int oldOff, const char *pCookie,
                                      int cookieLen)
{
    int offset, diff;
    char *pBuf;
    m_headerBuf.append("Cookie: ", 8);
    offset = m_headerBuf.size();
    m_headerBuf.appendAllocOnly(cookieLen + 2);

    if (!pCookie)
        pCookie = m_headerBuf.getp(
                      m_commonHeaderOffset[ HttpHeader::H_COOKIE ]);

    m_commonHeaderOffset[ HttpHeader::H_COOKIE ] = offset;

    pBuf = m_headerBuf.getp(offset);
    memmove(pBuf, pCookie, cookieLen);
    pBuf += cookieLen;
    *pBuf++ = '\r';
    *pBuf++ = '\n';

    diff = offset - oldOff;
    if (diff == 0)
        return 0;

    cookieval_t *p = m_cookies.begin();
    while (p < m_cookies.end())
    {
        p->keyOff += diff;
        p->valOff += diff;
        ++p;
    }
    return 0;
}

int HttpReq::checkUrlStaicFileCache()
{
    HttpVHost *host = (HttpVHost *)getVHost();
    m_pUrlStaticFileData = host->getUrlStaticFileData(getURI());
    return 0;
}


