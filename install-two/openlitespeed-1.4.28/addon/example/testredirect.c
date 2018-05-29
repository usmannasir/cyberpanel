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
#include <lsdef.h>

#define     MNAME       testredirect
#define     TEST_URL       "/testredirect"
#define     TEST_URL_LEN       (sizeof(TEST_URL) -1)

#define DEST_URL        "/index.html"

/* This module tests redirect operations.
 * Valid urls are /testredirect?x-y
 * x is a LSI URL Operation.  Valid operations are outlined in the LSI_URL_OP enum in ls.h
 * y determines who handles the operation, 0 for the server, 1 for module.
 *
 * Note: If y = 1, only the redirect URL Ops are valid.
 */

lsi_module_t MNAME;

int parse_qs(const char *qs, int *action, int *useHandler)
{
    int len;
    const char *pBuf;
    if (!qs || (len = strlen(qs)) <= 0)
        return LS_FAIL;
    *action = strtol(qs, NULL, 10);
    pBuf = memchr(qs, '-', len);
    if (pBuf && useHandler)
        *useHandler = strtol(pBuf + 1, NULL, 10);
    return 0;
}

void report_error(const lsi_session_t *session, const char *qs)
{
    char errBuf[512];
    sprintf(errBuf, "Error: Invalid argument.\n"
            "Query String was %s.\n"
            "Expected d-d, where d is an integer.\n"
            "Valid values for the first d are LSI URL Ops.\n"
            "Valid values for the second d are\n"
            "\t 0 for normal operations,\n"
            "\t 1 for module handled operations.\n"
            "If using module handled operations, can only use redirect URL Ops.\n",
            qs
           );
    g_api->append_resp_body(session, errBuf, strlen(errBuf));
    g_api->end_resp(session);
}

//Checks to make sure URL Action is valid.  0 for valid, -1 for invalid.
int test_range(int action)
{
    action = action & 127;
    if (action == 0 || action == 1)
        return LS_OK;
    else if (action > 16 && action < 23)
        return LS_OK;
    else if (action > 32 && action < 39)
        return LS_OK;
    else if (action > 48 && action < 55)
        return 0;
    return LS_FAIL;
}

int check_if_redirect(lsi_param_t *rec)
{
    const char *uri;
    const char *qs;
    int action = LSI_URL_REWRITE;
    int useHandler = 0;
    int len;
    uri = g_api->get_req_uri(rec->session, &len);
    if (len >= strlen(TEST_URL)
        && strncasecmp(uri, TEST_URL, strlen(TEST_URL)) == 0)
    {
        qs = g_api->get_req_query_string(rec->session, NULL);
        if (parse_qs(qs, &action, &useHandler) < 0)
        {
            report_error(rec->session, qs);
            return LSI_OK;
        }
        if (test_range(action) < 0)
            report_error(rec->session, qs);
        else if (!useHandler)
            g_api->set_uri_qs(rec->session, action, DEST_URL, sizeof(DEST_URL) - 1,
                              "", 0);
        else if (action > 1)
            g_api->register_req_handler(rec->session, &MNAME, TEST_URL_LEN);
        else
            report_error(rec->session, qs);
    }
    return LSI_OK;
}

static lsi_serverhook_t serverHooks[] =
{
    {LSI_HKPT_RCVD_REQ_HEADER, check_if_redirect, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED},
    LSI_HOOK_END   //Must put this at the end position
};

static int init_module(lsi_module_t *pModule)
{
    return LS_OK;
}

static int handlerBeginProcess(const lsi_session_t *session)
{
    const char *qs;
    int action = LSI_URL_REWRITE;
    qs = g_api->get_req_query_string(session, NULL);
    if (parse_qs(qs, &action, NULL) < 0)
    {
        report_error(session, qs);
        return LSI_OK;
    }
    if (action == 17 || action == 33 || action == 49)
        report_error(session, qs);
    else
        g_api->set_uri_qs(session, action, DEST_URL, sizeof(DEST_URL) - 1, "", 0);
    return 0;
}

lsi_reqhdlr_t myhandler = { handlerBeginProcess, NULL, NULL, NULL };
lsi_module_t MNAME = { LSI_MODULE_SIGNATURE, init_module, &myhandler, NULL, "test  redirect v1.0", serverHooks };
