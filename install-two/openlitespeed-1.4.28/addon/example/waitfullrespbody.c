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
#include <stdlib.h>
#include <string.h>

#define MNAME       waitfullrespbody
lsi_module_t MNAME;

#define     VERSION     "V1.0"


static char testuri[] = "waitfullrespbody";
static char desturl[] = "/index.html";

static int type2hook[] =
{
    LSI_HKPT_RCVD_RESP_HEADER,
    LSI_HKPT_RECV_RESP_BODY,
    LSI_HKPT_RCVD_RESP_BODY,
    LSI_HKPT_SEND_RESP_HEADER,
    LSI_HKPT_RCVD_RESP_HEADER,
    LSI_HKPT_RECV_RESP_BODY,
    LSI_HKPT_RCVD_RESP_BODY,
    LSI_HKPT_SEND_RESP_HEADER,
};


static int internal_redir(lsi_param_t *param)
{
    int action = LSI_URL_REDIRECT_INTERNAL;
    g_api->set_uri_qs(
        param->session, action, desturl, sizeof(desturl) - 1, "", 0);
    return LSI_OK;
}


static int deny_access(lsi_param_t *param)
{
    g_api->set_status_code(param->session, 406);
    return LSI_ERROR;
}


static int get_testtype(lsi_param_t *param)
{
    int type = 0;
    int len;
    const char *qs = g_api->get_req_query_string(param->session, &len);
    char buf[256];
    if ((len >= sizeof(testuri) - 1)
        && (strncasecmp(qs, testuri, sizeof(testuri) - 1) == 0))
        type = strtol(qs + sizeof(testuri) - 1, NULL, 10);
    else
        return 0;

    if ((type < 1) || (type > 10))
    {
        snprintf(buf, sizeof(buf),
                 "Error: Invalid argument. There must be a number\n"
                 "between 1 and 10 (inclusive) after \'waitfullrespbody\'.\n"
                 "Query String: [%.*s].\n", len, qs);
        g_api->append_resp_body(param->session, buf, strlen(buf));
        g_api->end_resp(param->session);
        return 0;
    }

    g_api->set_resp_wait_full_body(param->session);
    if (type <= 8)
    {
        g_api->enable_hook(param->session, &MNAME, 1,
                           &type2hook[type - 1], 1);
    }

    return 0;
}


static int init_module(lsi_module_t *module)
{
    module->about = VERSION;  //set version string
    return 0;
}


static int session_hook_func(lsi_param_t *param)
{
    int len;
    const char *qs = g_api->get_req_query_string(param->session, &len);
    if ((qs == NULL) || (len < sizeof(testuri)))
        return 0;

    int type = strtol(qs + sizeof(testuri) - 1, NULL, 10);
    return (type < 5) ? internal_redir(param) : deny_access(param);
}


static lsi_serverhook_t server_hooks[] =
{
    { LSI_HKPT_RCVD_REQ_HEADER, get_testtype, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED },

    { LSI_HKPT_RCVD_RESP_HEADER, session_hook_func, LSI_HOOK_NORMAL, 0 },
    { LSI_HKPT_RECV_RESP_BODY, session_hook_func, LSI_HOOK_NORMAL, 0 },
    { LSI_HKPT_RCVD_RESP_BODY, session_hook_func, LSI_HOOK_NORMAL, 0 },
    { LSI_HKPT_SEND_RESP_HEADER, session_hook_func, LSI_HOOK_NORMAL, 0 },

    LSI_HOOK_END   //Must put this at the end position
};

lsi_module_t MNAME =
{
    LSI_MODULE_SIGNATURE, init_module, NULL, NULL, "", server_hooks
};

