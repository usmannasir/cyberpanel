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

#include <ls.h>

#include <lsr/ls_xpool.h>

#include <string.h>

/**
 * This module tests setting the enable flag during the session.
 * It is recommended to use this along with testenableflag 1, 2, and 4.
 *
 * This one tests: Enabling statically enabled callback functions.
 *
 * To test: After compiling and installing this module, access a dynamically
 * processed page.
 *
 * i.e. curl -i http://localhost:8088/phpinfo.php
 */

#define     MNAME       testenableflag3
lsi_module_t MNAME;
/////////////////////////////////////////////////////////////////////////////
#define     VERSION         "V1.0"

static int addoutput(lsi_param_t *rec, const char *level)
{
    int len = 0, lenNew;
    char *pBuf;
    if (rec->len1 <= 0)
        return g_api->stream_write_next(rec, rec->ptr1, rec->len1);
    pBuf = ls_xpool_alloc(g_api->get_session_pool(rec->session),
                          rec->len1 + strlen(level) + 1);
    snprintf(pBuf, rec->len1 + strlen(level) + 1, "%.*s%.*s",
             rec->len1, (const char *)rec->ptr1, strlen(level) + 1, level);
    lenNew = rec->len1 + strlen(level);
    len = g_api->stream_write_next(rec, pBuf, lenNew);
    if (len < lenNew)
        *rec->flag_out = LSI_CBFO_BUFFERED;
    if (len < rec->len1)
        return len;
    return rec->len1;
}

static int addrecvresp(lsi_param_t *rec)
{   return addoutput(rec, "RECV3: If this appears, good.\n");  }


static int addsendresp(lsi_param_t *rec)
{   return addoutput(rec, "SEND3: If this appears, good.\n");  }

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
    {
        LSI_HKPT_RECV_RESP_BODY, addrecvresp, LSI_HOOK_NORMAL,
        LSI_FLAG_ENABLED | LSI_FLAG_TRANSFORM
    },
    {
        LSI_HKPT_SEND_RESP_BODY, addsendresp, LSI_HOOK_NORMAL,
        LSI_FLAG_ENABLED | LSI_FLAG_TRANSFORM
    },
    LSI_HOOK_END   //Must put this at the end position
};

static int init_module()
{
    MNAME.about = VERSION;  //set version string
    return 0;
}

lsi_module_t MNAME = { LSI_MODULE_SIGNATURE, init_module, NULL, NULL, "", serverHooks};
