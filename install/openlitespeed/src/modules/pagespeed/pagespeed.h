/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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

//  Author: dxu@litespeedtech.com (David Shue)

#ifndef LSI_PAGESPEEND_H_
#define LSI_PAGESPEEND_H_

#include "../include/ls.h"
#include "ls_rewrite_driver_factory.h"
#include "out/Release/obj/gen/net/instaweb/public/version.h"
#include "base/logging.h"
#include "pagespeed/kernel/base/string_util.h"
#include "pagespeed/kernel/http/response_headers.h"

#define STRINGIFY0(x) #x
#define STRINGIFY(x) STRINGIFY0(x)
#define MNAME      modpagespeed
#define ModuleName STRINGIFY(MNAME)
#define CACHE_MAX_AGE   30
#define CACHE_MAX_AGE_STR STRINGIFY(CACHE_MAX_AGE)

#define PAGESPEED_MODULEKEY     ModuleName
#define PAGESPEED_MODULEKEYLEN  (sizeof(ModuleName) -1)


extern lsi_module_t MNAME;

using namespace net_instaweb;

namespace net_instaweb
{
class GzipInflater;
class StringAsyncFetch;
class ProxyFetch;
class RewriteDriver;
class RequestHeaders;
class ResponseHeaders;
class InPlaceResourceRecorder;

// s1: AutoStr, s2: string literal
// true if they're equal, false otherwise
#define STR_EQ_LITERAL(s1, s2)          \
    ((s1).len() == (sizeof(s2)-1) &&      \
     strncmp((s1).c_str(), (s2), (sizeof(s2)-1)) == 0)

// s1: AutoStr, s2: string literal
// true if they're equal ignoring case, false otherwise
#define STR_CASE_EQ_LITERAL(s1, s2)     \
    ((s1).len() == (sizeof(s2)-1) &&      \
     strncasecmp((s1).c_str(), (s2), (sizeof(s2)-1)) == 0)


enum PreserveCachingHeaders
{
    kPreserveAllCachingHeaders,  // Cache-Control, ETag, Last-Modified, etc
    kPreserveOnlyCacheControl,   // Only Cache-Control.
    kDontPreserveHeaders,
};

void CopyRespHeadersFromServer(lsi_session_t *session, ResponseHeaders *headers);

void CopyReqHeadersFromServer(lsi_session_t *session, RequestHeaders *headers);

int CopyRespHeadersToServer(lsi_session_t *session,
                            const ResponseHeaders &pagespeed_headers,
                            PreserveCachingHeaders preserve_caching_headers);

int CopyRespBodyToBuf(lsi_session_t *session, GoogleString &str, int done_called);

int DeterminePort(lsi_session_t *session);

}  // namespace net_instaweb


enum REQ_ROUTE
{
    REQ_ROUTE_UNKNOWN,
    REQ_ROUTE_ERROR,
    REQ_ROUTE_STATIC,
    REQ_ROUTE_INVALID_URL,
    REQ_ROUTE_DISABLED,
    REQ_ROUTE_BEACON,
    REQ_ROUTE_STATISTICS,
    REQ_ROUTE_GLOBAL_STATS,
    REQ_ROUTE_CONSOLE,
    REQ_ROUTE_MESSAGE,
    REQ_ROUTE_ADMIN,
    REQ_ROUTE_PURGE,
    REQ_ROUTE_GLOBAL_ADMIN,
    REQ_ROUTE_SUB_REQ,
    REQ_ROUTE_ERR_RESP,
    REQ_ROUTE_RESOURCE,
    REQ_ROUTE_IN_PLACE

};

#endif //LSI_PAGESPEEND_H_

