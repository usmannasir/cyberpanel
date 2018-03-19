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
#include "../include/ls.h"
#include <lsdef.h>

#include <string.h>

#define MNAME       testcontext
lsi_module_t MNAME;

/** This module demonstrates how to assign specific contexts to module handlers
 *
 * After compiling the module with the ccc.sh script, move this module into
 * the $SERVERROOT/modules directory.
 *
 * In the server configuration, enable the module "testcontext"
 *
 * In a virtual host, for example, the Example virtual host, change the vhost
 * configuration to include a context "/testcon*" handled by this module:
context /testcon*{
  type module
  handler testcontext
}
 * Start the server, and if everything was done correctly, access any page
 * matching that context, i.e.
 * http://localhost:8088/testconThisShouldBeTheOutput
 *
 * The response should say something like:
 * The wildcard matched: ThisShouldBeTheOutput
 *
 */

static const char *pPrefix = "/testcon";

const int maxOutLen = 1024;

static int begin_process(const lsi_session_t *session)
{
    const char *uri;
    char out[maxOutLen];
    int iUriLen, iOutLen;
    g_api->set_status_code(session, 200);
    g_api->set_resp_header(session, LSI_RSPHDR_CONTENT_TYPE, NULL, 0,
                           "text/html", 9, LSI_HEADEROP_SET);
    uri = g_api->get_req_uri(session, &iUriLen);
    if (memcmp(uri, pPrefix, strlen(pPrefix)) != 0)
        return LS_FAIL;

    iOutLen = snprintf(out, maxOutLen, "The wildcard matched: %s\n",
                       uri + strlen(pPrefix));
    g_api->append_resp_body(session, out, iOutLen);
    g_api->end_resp(session);
    return 0;
}

static lsi_reqhdlr_t myhandler = { begin_process, NULL, NULL, NULL };
lsi_module_t MNAME = { LSI_MODULE_SIGNATURE, NULL, &myhandler, NULL };


