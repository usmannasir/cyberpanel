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
#include "pagespeed.h"
#include "ls_server_context.h"
#include <arpa/inet.h>
#include "ls_message_handler.h"
#include "ls_rewrite_driver_factory.h"
#include "ls_rewrite_options.h"
#include "net/instaweb/rewriter/public/rewrite_driver.h"
#include "pagespeed/system/add_headers_fetcher.h"
#include "pagespeed/system/loopback_route_fetcher.h"
#include "pagespeed/system/system_request_context.h"

namespace net_instaweb
{
LsServerContext::LsServerContext(
    LsiRewriteDriverFactory *factory, StringPiece hostname, int port)
    : SystemServerContext(factory, hostname, port)
{
}

LsServerContext::~LsServerContext() { }

LsiRewriteOptions *LsServerContext::Config()
{
    return LsiRewriteOptions::DynamicCast(global_options());
}

SystemRequestContext *LsServerContext::NewRequestContext(
    const lsi_session_t *session)
{
    int local_port = DeterminePort(session);
    char ip[60] = {0};
    g_api->get_local_sockaddr(session, ip, 60);
    char hostC[512] = {0};
    StringPiece host = DetermineHost(session, hostC, 512);
    StringPiece local_ip = ip;
    g_api->log(NULL, LSI_LOG_DEBUG,
               "NewRequestContext: host %s port %d ip %s\n",
               hostC, local_port, ip);
    return new SystemRequestContext(thread_system()->NewMutex(),
                                    timer(),
                                    host,    //  hostname,
                                    local_port,
                                    local_ip);
}

GoogleString LsServerContext::FormatOption(StringPiece option_name,
        StringPiece args)
{
    return StrCat("pagespeed ", option_name, " ", args);
}

}  // namespace net_instaweb
