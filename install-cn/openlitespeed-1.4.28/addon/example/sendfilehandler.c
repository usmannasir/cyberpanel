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

#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <string.h>

/**
 * Define the module name, MUST BE the same as .so file name;
 * i.e., if MNAME is testmodule, then the .so must be testmodule.so.
 */

#define MNAME       sendfilehandler
lsi_module_t MNAME;

static char testuri[] = "/sendfile";


static int dummycall(lsi_param_t *param)
{
    const char *in = (const char *)param->ptr1;
    int len = param->len1;
    int sent = g_api->stream_write_next(param,  in, len);
    return sent;
}


static int rcvd_req_header_cbf(lsi_param_t *param)
{
    const char *uri;
    int len;
    uri = g_api->get_req_uri(param->session, &len);
    if ((len >= sizeof(testuri) - 1)
        && (strncasecmp(uri, testuri, sizeof(testuri) - 1) == 0))
        g_api->register_req_handler(param->session, &MNAME, sizeof(testuri) - 1);
    return LSI_OK;
}


static int init_module(lsi_module_t *module)
{
    return 0;
}


static int begin_process(const lsi_session_t *session)
{
    struct stat sb;
    const char *file = "/home/user/ls0312/DEFAULT/html/test1";
    off_t off = 0;
    off_t sz = -1; //-1 set to send all data
    struct iovec vec[5] =
    {
        {"123\r\n", 5}, {"123 ", 4}, {"523", 3}, {"---", 3}, {"1235\r\n", 6}
    };
    static char txthello[] = "Hi, test send file\r\n";
    static char txterror[] = "Sorry, send file error\r\n";
    static char txtlast[] = "<p>The LAST<p>\r\n";

    g_api->append_resp_body(session, txthello, sizeof(txthello) - 1);
    g_api->append_resp_bodyv(session, vec, 5);

    if (stat(file, &sb) == 0)
        sz = sb.st_size - 5;

    if (g_api->send_file(session, file, off, sz) < 0)
        g_api->append_resp_body(session, txterror, sizeof(txterror) - 1);

    g_api->append_resp_body(session, txtlast, sizeof(txtlast) - 1);
    g_api->end_resp(session);
    return 0;
}


static lsi_serverhook_t server_hooks[] =
{
    { LSI_HKPT_RCVD_REQ_HEADER, rcvd_req_header_cbf, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED },
    //{ LSI_HKPT_SEND_RESP_BODY, dummycall, LSI_HOOK_NORMAL, 0 },
    LSI_HOOK_END   //Must put this at the end position
};

static lsi_reqhdlr_t myhandler = { begin_process, NULL, NULL, NULL };

lsi_module_t MNAME =
{
    LSI_MODULE_SIGNATURE, init_module, &myhandler, NULL, "", server_hooks
};

