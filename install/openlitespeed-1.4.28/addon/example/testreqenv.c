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
#include <stdlib.h>

#define MNAME       testreqenv
lsi_module_t MNAME;

/** This module will do a test of basic request env setting and getting.
 *
 * After compiling the module with the ccc.sh script, move this module into
 * the $SERVERROOT/modules directory.
 *
 * I tested this by setting a context from the Example virtual host (eg. /env/)
 * Such that it is handled by this module.
 *
 * To test, access that context, i.e. http://localhost:8088/env/
 * and check the log.  There should be an INFO output that should say:
 * Not a match.  Key: thisWillBeDeleted, Orig Val: ifStillHereSomethingWrong, Current Val:
 *
 * If there are any more or it is not there, then there is an error.
 */


static char resp_buf[] = "This part doesn't really matter much to me.\r\n";

static char *pKeys[] =
{
    "myEnvName",
    "myEnvKey",
    "aNewBeginning",
    "keepThemComing",
    "thisWillBeDeleted",
    "fewMoreStarters",
    "wishIWasMoreCreative",
    "needToComeUpWithMore",
    "iThinkOneMoreShouldSuffice",
    "done",
    "justKiddingExactlyTen",
    "!thisWillBeDeleted"
};

static char *pVals[] =
{
    "myEnvTarget",
    "myEnvVal",
    "aNewEnding",
    "keepThemGoing",
    "ifStillHereSomethingWrong",
    "fewMoreFinishers",
    "wishIWasMoreUnimaginative",
    "needToComeUpWithLess",
    "oneMoreIsTooMuch",
    "unfinishedBusiness",
    "justKiddingExactlyEleven"
};

const int iSize = 11;
const int iMaxLen = 256;

static int begin_process(const lsi_session_t *session)
{
    char outBuf[iMaxLen];
    int i, iOut;

    for (i = 0; i < iSize; ++i)
    {
        iOut = g_api->get_req_env(session, pKeys[i], strlen(pKeys[i]),
                                  outBuf, iMaxLen);
        if (strncmp(outBuf, pVals[i], strlen(pVals[i])) != 0)
        {
            g_api->log(session, LSI_LOG_INFO,
                       "Not a match.  Key: %.*s, Orig Val: %.*s, Current Val: %.*s\n",
                       strlen(pKeys[i]), pKeys[i], strlen(pVals[i]), pVals[i],
                       iOut, outBuf);
        }
    }

    g_api->set_status_code(session, 200);
    g_api->set_resp_header(session, LSI_RSPHDR_CONTENT_TYPE, NULL, 0,
                           "text/html", 9, LSI_HEADEROP_SET);
    g_api->append_resp_body(session, resp_buf, sizeof(resp_buf) - 1);
    g_api->end_resp(session);
    return 0;
}


static int beginSession(lsi_param_t *rec)
{
    int i;
    const lsi_session_t *pSession = rec->session;

    for (i = 0; i < iSize; ++i)
    {
        g_api->set_req_env(pSession, pKeys[i], strlen(pKeys[i]), pVals[i],
                           strlen(pVals[i]));
        printf("After addEnv: %.*s\n", strlen(pKeys[i]), pKeys[i]);
    }
    //Delete the ToBeDeleted one
    g_api->set_req_env(pSession, pKeys[i], strlen(pKeys[i]), pVals[4],
                       strlen(pVals[4]));
    printf("After addEnv: %.*s\n", strlen(pKeys[i]), pKeys[i]);
    return 0;
}


static int init_module()
{
    return 0;
}


static lsi_serverhook_t serverHooks[] =
{
    {LSI_HKPT_HTTP_BEGIN, beginSession, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED},
    LSI_HOOK_END   //Must put this at the end position
};

static lsi_reqhdlr_t myhandler = { begin_process, NULL, NULL, NULL };
lsi_module_t MNAME = { LSI_MODULE_SIGNATURE, init_module, &myhandler, NULL, "v1.0",
                       serverHooks
                     };


