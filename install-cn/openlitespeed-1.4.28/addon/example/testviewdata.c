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

#define     MNAME       testviewdata
lsi_module_t MNAME;
/////////////////////////////////////////////////////////////////////////////
#define     VERSION         "V1.0"

static int viewData0(lsi_param_t *rec, const char *level)
{
    if (rec->len1 < 100)
        g_api->log(rec->session, LSI_LOG_INFO,
                   "[testautocompress] viewData [%s] %s\n",
                   level, (const char *)rec->ptr1);
    else
    {
        g_api->log(rec->session, LSI_LOG_INFO,
                   "[testautocompress] viewData [%s] ",  level);
        g_api->lograw(rec->session, rec->ptr1, 40);
        g_api->lograw(rec->session, "(...)", 5);
        g_api->lograw(rec->session, rec->ptr1 + rec->len1 - 40, 40);
        g_api->lograw(rec->session, "\n", 1);
    }
    return g_api->stream_write_next(rec, rec->ptr1, rec->len1);
}

static int viewData1(lsi_param_t *rec) {   return viewData0(rec, "RECV");  }
static int viewData2(lsi_param_t *rec) {   return viewData0(rec, "SEND");  }

static int beginSession(lsi_param_t *rec)
{
    int aEnableHkpts[] = {LSI_HKPT_RECV_RESP_BODY, LSI_HKPT_SEND_RESP_BODY};
    g_api->enable_hook(rec->session, &MNAME, 1,
                       aEnableHkpts, 2);
    return 0;
}

static lsi_serverhook_t serverHooks[] =
{
    {LSI_HKPT_HTTP_BEGIN, beginSession, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED},
    {LSI_HKPT_RECV_RESP_BODY, viewData1, LSI_HOOK_NORMAL, LSI_FLAG_DECOMPRESS_REQUIRED },
    {LSI_HKPT_SEND_RESP_BODY, viewData2, LSI_HOOK_NORMAL, LSI_FLAG_DECOMPRESS_REQUIRED},
    LSI_HOOK_END   //Must put this at the end position
};

static int init_module()
{
    MNAME.about = VERSION;  //set version string
    return 0;
}

lsi_module_t MNAME = { LSI_MODULE_SIGNATURE, init_module, NULL, NULL, "", serverHooks};
