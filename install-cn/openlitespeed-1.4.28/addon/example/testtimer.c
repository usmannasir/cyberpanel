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
#include <time.h>
#include <string.h>

/**
 * HOW TO TEST
 * test url ....../testtimer wit Get or post, request also can have a request body.
 * One line response will be displayed in browser and suspend,
 * and after 5 seconds, it will continue to display the left. *
 * If with a req body, it will be displayed in the browser
 *
 */
/////////////////////////////////////////////////////////////////////////////
//DEFINE the module name, MUST BE the same as .so file name
//ie.  if MNAME is testmodule, then the .so must be testmodule.so
#define     MNAME       testtimer
/////////////////////////////////////////////////////////////////////////////

lsi_module_t MNAME;
static int onReadEvent(const lsi_session_t *session);

int uri_map_cbf(lsi_param_t *rec)
{
    const char *uri;
    int len;
    uri = g_api->get_req_uri(rec->session, &len);
    if (len >= 11 && strncasecmp(uri, "/testtimer/", 11) == 0)
    {
        g_api->register_req_handler(rec->session, &MNAME, 10);
        g_api->set_req_env(rec->session, "cache-control", 13, "max-age 20", 10);
    }
    return LSI_OK;
}

static lsi_serverhook_t serverHooks[] =
{
    {LSI_HKPT_URI_MAP, uri_map_cbf, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED},
    LSI_HOOK_END   //Must put this at the end position
};

int nullRelease(void *p)
{
    return 0;
}

static int init(lsi_module_t *pModule)
{
    g_api->init_module_data(pModule, nullRelease, LSI_DATA_HTTP);
    return 0;
}

void timer_cb(const void *session)
{
    char buf[1024];
    sprintf(buf, "Timer Triggered(1 second), time: %ld<br>\n",
            (long)(time(NULL)));
    g_api->append_resp_body((const lsi_session_t *)session, buf, strlen(buf));
}

void repeat_cb(const void *session)
{
    char buf[1024];
    sprintf(buf, "Repeating timer(200ms)!, time: %ld<br>\n",
            (long)(time(NULL)));
    g_api->append_resp_body((const lsi_session_t *)session, buf, strlen(buf));
}

void finish_cb(const void *session)
{
    int id;
    char buf[1024];
    const lsi_session_t *pSession = (const lsi_session_t *)session;
    id = (int)(long)g_api->get_module_data(session, &MNAME, LSI_DATA_HTTP);
    g_api->remove_timer(id);
    sprintf(buf, "Finishing timer(5 seconds)!, time: %ld<br>\n",
            (long)(time(NULL)));
    g_api->append_resp_body(pSession, buf, strlen(buf));
    g_api->set_handler_write_state(pSession, 1);

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
    sprintf(buf, "This test will take 5 seconds, now time is %ld\n<p>",
            (long)(time(NULL)));
    g_api->append_resp_body(session, buf, strlen(buf));
    g_api->flush(session);
    g_api->set_handler_write_state(session, 0);
    int id = g_api->set_timer(200, 1, repeat_cb, session);
    g_api->set_timer(1000, 0, timer_cb, session);
    g_api->set_timer(2000, 0, timer_cb, session);
    g_api->set_timer(3000, 0, timer_cb, session);
    g_api->set_timer(4000, 0, timer_cb, session);
    g_api->set_timer(5000, 0, finish_cb, session);
    g_api->set_module_data(session, &MNAME, LSI_DATA_HTTP,
                           (void *)(long)id);
    return 0;
}

static int onReadEvent(const lsi_session_t *session)
{
    char buf[8192];
    g_api->append_resp_body(session, "I got req body:<br>\n",
                            sizeof("I got req body:<br>\n") - 1);
    int ret;
    while ((ret = g_api->read_req_body(session, buf, 8192)) > 0)
        g_api->append_resp_body(session, buf, ret);
    return 0;
}

static int onWriteEvent(const lsi_session_t *session)
{
    g_api->append_resp_body(session, "<br>Writing finished, bye.\n<p>",
                            sizeof("<br>Writing finished, bye.\n<p>") - 1);
    return LSI_RSP_DONE;
}

static int onCleanUp(const lsi_session_t *session)
{
    int id = (int)(long)g_api->get_module_data(session, &MNAME,
             LSI_DATA_HTTP);
    g_api->remove_timer(id);
    g_api->set_module_data(session, &MNAME, LSI_DATA_HTTP, NULL);
    return 0;
}

lsi_reqhdlr_t myhandler = { PsHandlerProcess, onReadEvent, onWriteEvent, onCleanUp };
lsi_module_t MNAME = { LSI_MODULE_SIGNATURE, init, &myhandler, NULL, "", serverHooks};
