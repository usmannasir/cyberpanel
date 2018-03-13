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
#ifndef HTTPHEADER_H
#define HTTPHEADER_H

#include <stddef.h>

#define HASH_TABLE_SIZE 66

class HttpHeader
{
public:
    enum
    {
        // most common request-header
        H_ACCEPT = 0,
        H_ACC_CHARSET,
        H_ACC_ENCODING,
        H_ACC_LANG,
        H_AUTHORIZATION,
        H_CONNECTION,
        H_CONTENT_TYPE,
        H_CONTENT_LENGTH,
        H_COOKIE,
        H_COOKIE2,
        H_HOST,
        H_PRAGMA,
        H_REFERER,
        H_USERAGENT,
        H_CACHE_CTRL,
        H_IF_MODIFIED_SINCE,
        H_IF_MATCH,
        H_IF_NO_MATCH,
        H_IF_RANGE,
        H_IF_UNMOD_SINCE,
        H_KEEP_ALIVE,
        H_RANGE,
        H_X_FORWARDED_FOR,
        H_VIA,
        H_TRANSFER_ENCODING,

        //request-header
        H_TE,
        H_EXPECT,
        H_MAX_FORWARDS,
        H_PROXY_AUTH,

        // general-header
        H_DATE,
        H_TRAILER,
        H_UPGRADE,
        H_WARNING,

        // entity-header
        H_ALLOW,
        H_CONTENT_ENCODING,
        H_CONTENT_LANGUAGE,
        H_CONTENT_LOCATION,
        H_CONTENT_MD5,
        H_CONTENT_RANGE,
        H_EXPIRES,
        H_LAST_MODIFIED,

        // response-header
        /*
        H_ACCEPT_RANGES,
        H_AGE,
        H_ETAG,
        H_LOCATION,
        H_PROXY_AUTHENTICATE,
        H_PROXY_CONNECTION,
        H_RETRY_AFTER,
        H_SERVER,
        H_VARY,
        H_WWW_AUTHENTICATE,
        H_SET_COOKIE,
        H_SET_COOKIE2,
        CGI_STATUS,
        H_LITESPEED_LOCATION,
        H_CONTENT_DISPOSITION,
        H_LITESPEED_CACHE_CONTROL,

        H_HTTP_VERSION,
        */
        H_HEADER_END
    };
    static size_t getIndex(const char *pHeader);
    static size_t getIndex2(const char *pHeader);


    static const char *getHeaderNameLowercase(int iIndex)
    {   return s_pHeaderNamesLowercase[iIndex];    }

private:
    static const char *s_pHeaderNames[H_HEADER_END + 1];
    static const char  *s_pHeaderNamesLowercase[H_HEADER_END + 1];
    static int s_iHeaderLen[H_HEADER_END + 1];

    HttpHeader(const HttpHeader &rhs);
    void operator=(const HttpHeader &rhs);
    HttpHeader();
    ~HttpHeader();

public:
    static int getHeaderStringLen(int iIndex)
    {   return s_iHeaderLen[iIndex];    }

    static const char *getHeaderName(int iIndex)
    {   return s_pHeaderNames[iIndex];    }
};

#endif
