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
#include <fcntl.h>

/**
 * Define the module name, MUST BE the same as .so file name;
 * i.e., if MNAME is testmodule, then the .so must be testmodule.so.
 *
 * HOW TO TEST:
 * Go to any url with the query string:
 * ?setrespheader[0123], then you will get different response headers
 *
 * Tests:
 * mycb - The 1 bit in the query string is set.
 *   Is an example of setting a response header.
 *   If 1 bit is not set, it is an example of removing a session hook.
 * mycb2 - The 2 bit in the query string is set.
 *   Is an example of setting a response header.
 * mycb3 - The 4 bit is set.  Is an example of removing response headers.
 * mycb4 - The 8 bit is set.  Is an example of getting response headers.
 */

#define MNAME       setrespheader
lsi_module_t MNAME;

static char testurl[] = "setrespheader";

const char *headers[2] =
{
    "Set-Cookie",
    "Addheader"
};

const int numheaders = sizeof(headers) / sizeof(headers[0]);


//test changing resp header
static int mycb(lsi_param_t *rec)
{
    g_api->set_resp_header(rec->session, LSI_RSPHDR_SERVER, NULL, 0,
                           "/testServer 1.0", sizeof("/testServer 1.0") - 1, LSI_HEADEROP_SET);
    g_api->set_resp_header(rec->session, LSI_RSPHDR_SET_COOKIE, NULL, 0,
                           "An Example Cookie", sizeof("An Example Cookie") - 1, LSI_HEADEROP_ADD);
    g_api->set_resp_header(rec->session, LSI_RSPHDR_SET_COOKIE, NULL, 0,
                           "1 bit set!", sizeof("1 bit set!") - 1, LSI_HEADEROP_ADD);
    g_api->log(NULL, LSI_LOG_DEBUG, "#### mymodule1 test %s\n", "myCb");
    return 0;
}


//test changing resp header
static int mycb2(lsi_param_t *rec)
{
    g_api->set_resp_header2(rec->session, "Addheader: 2 bit set!\r\n",
                            sizeof("Addheader: 2 bit set!\r\n") - 1, LSI_HEADEROP_SET);
    return 0;
}


static int mycb3(lsi_param_t *rec)
{

    g_api->set_resp_header2(rec->session,
                            "Destructheader: 4 bit set! Removing other headers...\r\n",
                            sizeof("Destructheader: 4 bit set! Removing other headers...\r\n") - 1,
                            LSI_HEADEROP_ADD);
    g_api->remove_resp_header(rec->session, LSI_RSPHDR_SET_COOKIE, NULL,
                              0);
    g_api->remove_resp_header(rec->session, -1, "Addheader",
                              sizeof("Addheader") - 1);
    return 0;
}


static int mycb4(lsi_param_t *rec)
{
    int i, j, iov_count = g_api->get_resp_headers_count(rec->session);
    struct iovec iov_key[iov_count], iov_val[iov_count];
    memset(iov_key, 0, sizeof(struct iovec) * iov_count);
    memset(iov_val, 0, sizeof(struct iovec) * iov_count);

    g_api->set_resp_header2(rec->session,
                            "ProtectorHeader: 8 bit set! Duplicating headers for potential removal!\r\n",
                            sizeof("ProtectorHeader: 8 bit set! Duplicating headers for potential removal!\r\n")
                            - 1, LSI_HEADEROP_ADD);
    iov_count = g_api->get_resp_headers(rec->session, iov_key, iov_val,
                                        iov_count);
    for (i = iov_count - 1; i >= 0; --i)
    {
        for (j = 0; j < numheaders; ++j)
        {
            if (strncmp(headers[j], (const char *)iov_key[i].iov_base,
                        iov_key[i].iov_len) == 0)
            {
                char save[256];
                sprintf(save, "SavedHeader: %.*s\r\n",
                        iov_val[i].iov_len, (char *)iov_val[i].iov_base
                       );
                g_api->set_resp_header2(rec->session, save, strlen(save),
                                        LSI_HEADEROP_ADD);
            }
        }
    }
    return 0;
}


int check_type(lsi_param_t *rec)
{
    const char *qs;
    int sessionHookType = 0;
    qs = g_api->get_req_query_string(rec->session, NULL);
    sessionHookType = strtol(qs + sizeof(testurl) - 1, NULL, 10);
    if (sessionHookType & 0x01)
        mycb(rec);
    if (sessionHookType & 0x02)
        mycb2(rec);
    if (sessionHookType & 0x08)
        mycb4(rec);
    if (sessionHookType & 0x04)
        mycb3(rec);
    return LSI_OK;
}


int check_if_remove_session_hook(lsi_param_t *rec)
{
    const char *qs;
    int sessionHookType = 0;
    int iEnableHkpt = LSI_HKPT_SEND_RESP_HEADER;
    qs = g_api->get_req_query_string(rec->session, NULL);
    if (qs && strncasecmp(qs, testurl, sizeof(testurl) - 1) == 0)
    {
        sessionHookType = strtol(qs + sizeof(testurl) - 1, NULL, 10);
        if (sessionHookType & 0x0f)
            g_api->enable_hook(rec->session, &MNAME, 1,
                               &iEnableHkpt, 1);
    }
    return LSI_OK;
}


static int init_module(lsi_module_t *module)
{
    return 0;
}


static lsi_serverhook_t server_hooks[] =
{
    { LSI_HKPT_RCVD_REQ_HEADER, check_if_remove_session_hook, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED },
    { LSI_HKPT_SEND_RESP_HEADER, check_type, LSI_HOOK_NORMAL, 0 },
    LSI_HOOK_END   //Must put this at the end position
};

lsi_module_t MNAME =
{
    LSI_MODULE_SIGNATURE, init_module, NULL, NULL, "", server_hooks
};

