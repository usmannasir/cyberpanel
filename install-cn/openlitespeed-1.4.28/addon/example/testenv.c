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
#include <stdint.h>
#include "stdlib.h"
#include <unistd.h>

#define     MNAME       testenv
lsi_module_t MNAME;

#define URI_PREFIX   "/testenv"
#define max_file_len    1024

/**
 * HOW TO TEST
 * //testenv?modcompress:S1P-3000R1P-3000&moddecompress:S1P3000R1P3000
 */

int assignHandler(lsi_param_t *rec)
{
    int len;
    const char *p;
    const char *pEnd;
    const char *uri = g_api->get_req_uri(rec->session, &len);
    const char *nameStart;
    char name[128];
    int nameLen;
    const char *valStart;
    char val[128];
    int valLen;
    if (len < strlen(URI_PREFIX) ||
        strncasecmp(uri, URI_PREFIX, strlen(URI_PREFIX)) != 0)
        return 0;

    g_api->register_req_handler(rec->session, &MNAME, 0);
    p = g_api->get_req_query_string(rec->session, &len);
    pEnd = p + len;
    while (p && p < pEnd)
    {
        nameStart = p;
        p = strchr(p, ':');
        if (p)
        {
            nameLen = p - nameStart;
            strncpy(name, nameStart, nameLen);
            name[nameLen] = 0x00;
            ++p;

            valStart = p;
            p = strchr(p, '&');
            if (p)
            {
                valLen = p - valStart;
                ++p;
            }
            else
            {
                valLen = pEnd - valStart;
                p = pEnd;
            }

            strncpy(val, valStart, valLen);
            val[valLen] = 0x00;

            g_api->set_req_env(rec->session, name, nameLen, val, valLen);
            g_api->log(rec->session, LSI_LOG_INFO,
                       "[Module:testEnv] setEnv name[%s] val[%s]\n", name, val);

        }
        else
            break;
    }

    return 0;
}

static int PsHandlerProcess(const lsi_session_t *session)
{
    int i;
    //200KB
    char buf[51] = {0};
    int count = 0;
    for (i = 0; i < 2000; ++i)
    {
        snprintf(buf, 51, "%04d--0123456789012345678901234567890123456789**\r\n",
                 ++count);
        g_api->append_resp_body(session, buf, 50);
    }
    g_api->end_resp(session);
    return 0;
}

static lsi_serverhook_t serverHooks[] =
{
    {LSI_HKPT_RCVD_REQ_HEADER, assignHandler, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED},
    LSI_HOOK_END   //Must put this at the end position
};

static int init_module(lsi_module_t *pModule)
{
    return 0;
}

lsi_reqhdlr_t myhandler = { PsHandlerProcess, NULL, NULL, NULL };
lsi_module_t MNAME = { LSI_MODULE_SIGNATURE, init_module, &myhandler, NULL, "", serverHooks };
