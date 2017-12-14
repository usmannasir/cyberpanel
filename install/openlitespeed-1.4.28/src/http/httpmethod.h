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
#ifndef HTTPMETHOD_H
#define HTTPMETHOD_H


typedef int http_method_t;

class HttpMethod
{
public:
    enum
    {
        HTTP_UNKNOWN = 0,
        HTTP_OPTIONS,
        HTTP_GET ,
        HTTP_HEAD,
        HTTP_POST,
        HTTP_PUT ,
        HTTP_DELETE,
        HTTP_TRACE,
        HTTP_CONNECT,
        HTTP_MOVE,
        HTTP_PATCH,
        DAV_PROPFIND,
        DAV_PROPPATCH,
        DAV_MKCOL,
        DAV_COPY,
        DAV_LOCK,
        DAV_UNLOCK,
        DAV_VERSION_CONTROL,
        DAV_REPORT,
        DAV_CHECKIN,
        DAV_CHECKOUT,
        DAV_UNCHECKOUT,
        DAV_UPDATE,
        DAV_MKWORKSPACE,
        DAV_LABEL,
        DAV_MERGE,
        DAV_BASELINE_CONTROL,
        DAV_MKACTIVITY,
        DAV_BIND,
        DAV_SEARCH,
        HTTP_PURGE,
        HTTP_REFRESH,
        HTTP_METHOD_END
    };

    static http_method_t parse2(const char *pMethod);
    static http_method_t parse(const char *pMethod);
    static const char *get(http_method_t method)
    {
        //assert(( method >= HTTP_OPTIONS )&&( method <= HTTP_MOVE ));
        return s_psMethod[method];
    }

    static int getLen(http_method_t method)
    {
        //assert(( method >= HTTP_OPTIONS )&&( method <= HTTP_MOVE ));
        return s_iMethodLen[method];

    }

private:
    static const char *s_psMethod[HTTP_METHOD_END];
    static int s_iMethodLen[HTTP_METHOD_END];
    HttpMethod() {};
    ~HttpMethod() {};
    HttpMethod(const HttpMethod &rhs);
    void operator=(const HttpMethod &rhs);
};

#endif
