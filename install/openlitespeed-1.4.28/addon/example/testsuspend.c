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
/**
 * HOW TO TEST
 * /testsuspend/..... to set to suspend, and ?11 to set to handle
 *
 */

#define _GNU_SOURCE
#include "../../include/ls.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <time.h>
#include <string.h>
#include <pthread.h>
#include <stdlib.h>
#include <memory.h>

#define     MNAME       testsuspend
extern lsi_module_t MNAME;


void timer_callback(const void *session)
{

    int len;
    const char *qs = g_api->get_req_query_string((const lsi_session_t *)session,
                     &len);
    if (len > 1 && strstr(qs, "11"))
        g_api->register_req_handler((const lsi_session_t *)session, &MNAME, 12);


    g_api->create_session_resume_event((const lsi_session_t *)session, &MNAME);
}

void *thread_callback(void *session)
{
    sleep(5);
    timer_callback(session);
    pthread_exit(NULL);
}

int suspendFunc(lsi_param_t *rec)
{
    const char *uri;
    int len;
    uri = g_api->get_req_uri(rec->session, &len);
    if (len >= 12 && strcasestr(uri, "/testsuspend"))
    {

// //#define USE_TIMER_HERE
// #ifdef  USE_TIMER_HERE
//         g_api->set_timer(5000, timer_callback, (void *)rec->_session);
//         return LSI_SUSPEND;
// #else
//         pthread_t mythread;
//         int rc = pthread_create(&mythread, NULL, thread_callback,  (void *)rec->_session);
//         if (rc == 0)
//         {
//             return LSI_SUSPEND; //If ret LSI_SUSPEND, should set a timer or a thread to call hookResumeCallback()
//         }
// #endif

        pthread_t mythread;
        int rc = pthread_create(&mythread, NULL, thread_callback,
                                (void *)rec->session);
        if (rc == 0)
        {
            return LSI_SUSPEND; //If ret LSI_SUSPEND, should set a timer or a thread to call hookResumeCallback()
        }
    }

    return LSI_OK;
}


static lsi_serverhook_t serverHooks[] =
{
    {LSI_HKPT_RCVD_REQ_HEADER, suspendFunc, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED},
    LSI_HOOK_END   //Must put this at the end position
};

static int init_module(lsi_module_t *pModule)
{
    return 0;
}


//The first time the below function will be called, then onWriteEvent will be called next and next
static int PsHandlerProcess(const lsi_session_t *session)
{
    char tmBuf[30];
    time_t t;
    struct tm *tmp;
    t = time(NULL);
    tmp = gmtime(&t);
    strftime(tmBuf, 30, "%a, %d %b %Y %H:%M:%S GMT", tmp);
    g_api->set_resp_header(session, LSI_RSPHDR_CONTENT_TYPE, NULL, 0,
                           "text/html", sizeof("text/html") - 1, LSI_HEADEROP_SET);
    g_api->set_resp_header(session, LSI_RSPHDR_LAST_MODIFIED, NULL, 0,
                           tmBuf, 29, LSI_HEADEROP_SET);

    char buf[1024];
    sprintf(buf,
            "This test suspend for 5 seconds and resume, now time is %ld<p>",
            (long)(time(NULL)));
    g_api->append_resp_body(session, buf, strlen(buf));
    g_api->end_resp(session);
    return 0;
}

lsi_reqhdlr_t myhandler = { PsHandlerProcess, NULL, NULL, NULL };
lsi_module_t MNAME = { LSI_MODULE_SIGNATURE, init_module, &myhandler, NULL, "", serverHooks};
