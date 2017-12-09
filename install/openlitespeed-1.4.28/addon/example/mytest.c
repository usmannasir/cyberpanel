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
#include <string.h>

#define MNAME       mytest
lsi_module_t MNAME;


static int rcvd_req_header_cbf(lsi_param_t *param)
{
    const char *uri;
    int len;
    uri = g_api->get_req_uri(param->session, &len);
    if ((len >= 7) && (strncasecmp(uri, "/mytest", 7) == 0))
        g_api->register_req_handler(param->session, &MNAME, 7);
    return LSI_OK;
}


static int init_module()
{
    return 0;
}


static int begin_process(const lsi_session_t *session)
{
    g_api->append_resp_body(session, "MyTest!\n", 8);
    g_api->end_resp(session);
    return 0;
}


static lsi_serverhook_t server_hooks[] =
{
    {LSI_HKPT_RCVD_REQ_HEADER, rcvd_req_header_cbf, LSI_HOOK_FIRST, LSI_FLAG_ENABLED},
    LSI_HOOK_END   //Must put this at the end position
};

static lsi_reqhdlr_t myhandler = { begin_process, NULL, NULL, NULL };
lsi_module_t MNAME =
{
    LSI_MODULE_SIGNATURE, init_module, &myhandler, NULL, "", server_hooks
};

