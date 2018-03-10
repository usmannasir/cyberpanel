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
#define _GNU_SOURCE
#include "../include/ls.h"
#include <string.h>

#define MNAME       hellohandler2
lsi_module_t MNAME;


static int rcvd_req_header_cbf(lsi_param_t *param)
{
    const char *uri;
    int len;
    uri = g_api->get_req_uri(param->session, &len);
    if (memmem((const void *)uri, len, (const void *)".345", 4) != NULL)
    {
        g_api->register_req_handler(param->session, &MNAME, 0);
        g_api->log(param->session, LSI_LOG_DEBUG,
                   "[hellohandler2:%s] register_req_handler for URI: %s\n",
                   MNAME.about, uri);
    }
    return LSI_OK;
}


static int init_module(lsi_module_t *module)
{
    g_api->log(NULL, LSI_LOG_DEBUG,
               "[hellohandler2:%s] init_module [log in module code]\n",
               MNAME.about);
    return 0;
}


static char resp_buf[] = "Hello module handler2.\r\n";

static int begin_process(const lsi_session_t *session)
{
    g_api->append_resp_body(session, resp_buf, sizeof(resp_buf) - 1);
    g_api->end_resp(session);
    g_api->log(session, LSI_LOG_DEBUG,
               "[hellohandler2:%s] begin_process for URI: %s\n",
               MNAME.about, g_api->get_req_uri(session, NULL));
    return 0;
}


static lsi_serverhook_t server_hooks[] =
{
    { LSI_HKPT_RCVD_REQ_HEADER, rcvd_req_header_cbf, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED },
    LSI_HOOK_END   //Must put this at the end position
};

/**
 * Define a handler, need to provide a struct lsi_reqhdlr_t object, in which
 * the first function pointer should not be NULL
 */
static lsi_reqhdlr_t myhandler = { begin_process, NULL, NULL, NULL };
lsi_module_t MNAME =
{
    LSI_MODULE_SIGNATURE, init_module, &myhandler, NULL, "v1.0", server_hooks
};
