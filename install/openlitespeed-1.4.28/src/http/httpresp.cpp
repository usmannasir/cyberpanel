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
#include "httpresp.h"

// #include <http/httpheader.h> //setheader commented out.
#include <lsr/ls_strtool.h>
#include <util/datetime.h>
#include <util/stringtool.h>

#include <string.h>


HttpResp::HttpResp(ls_xpool_t *pool)
    : m_respHeaders(pool)
{
    m_lEntityLength = 0;
    m_lEntityFinished = 0;
}


HttpResp::~HttpResp()
{
}


void HttpResp::reset()
{
    m_respHeaders.reset();
    m_lEntityLength = LSI_RSP_BODY_SIZE_UNKNOWN;
    m_lEntityFinished = 0;
}


void HttpResp::appendContentLenHeader()
{
    if (m_lEntityLength >= 0)
    {
        static char sLength[44] = {0};
        int n = StringTool::offsetToStr(sLength, 43, m_lEntityLength);
        m_respHeaders.add(HttpRespHeaders::H_CONTENT_LENGTH, sLength, n);
    }
}


// void HttpResp::outputHeader()
// {
//     m_respHeaders.getHeaders(&m_iovec);
//     int bufSize = m_iovec.bytes();
//     m_iHeaderLeft += bufSize;
//     m_iHeaderTotalLen = m_iHeaderLeft;
// }


int HttpResp::appendHeader(const char *pName, int nameLen,
                           const char *pValue, int valLen)
{
    m_respHeaders.add(pName, nameLen, pValue, valLen, LSI_HEADEROP_ADD);
    return 0;
}


//void HttpResp::setHeader( int headerCode, long lVal )
//{
//    char buf[80];
//    int len = sprintf( buf, "%s%ld\r\n", HttpHeader::getHeader( headerCode ), lVal );
//    m_outputBuf.append( buf, len );
//}


int HttpResp::appendLastMod(long tmMod)
{
    static char sTimeBuf[RFC_1123_TIME_LEN + 1] = {0};
    DateTime::getRFCTime(tmMod, sTimeBuf);
    m_respHeaders.add(HttpRespHeaders::H_LAST_MODIFIED, sTimeBuf,
                      RFC_1123_TIME_LEN);
    return 0;
}


int HttpResp::addCookie(const char *pName, const char *pVal,
                        const char *path, const char *domain, int expires,
                        int secure, int httponly)
{
    char achBuf[8192] = "";
    char *p = achBuf;

    if (!pName || !pVal || !domain)
        return LS_FAIL;

    if (path == NULL)
        path = "/";
    p += ls_snprintf(achBuf, 8091, "%s=%s; path=%s; domain=%s",
                     pName, pVal, path, domain);
    if (expires)
    {
        memcpy(p, "; expires=", 10);
        p += 10;
        long t = DateTime::s_curTime + expires * 60;
        DateTime::getRFCTime(t, p);
        p += RFC_1123_TIME_LEN;
    }
    if (secure)
    {
        memcpy(p, "; secure", 8);
        p += 8;
    }
    if (httponly)
    {
        memcpy(p, "; HttpOnly", 10);
        p += 10;
    }
    m_respHeaders.add(HttpRespHeaders::H_SET_COOKIE, achBuf, p - achBuf,
                      LSI_HEADEROP_ADD);
    return 0;
}


