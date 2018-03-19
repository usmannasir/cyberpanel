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
#include <lsdef.h>
#include <lsr/ls_loopbuf.h>
#include <lsr/ls_xpool.h>

#include <stdlib.h>
#include <string.h>

/**
 * Define the module name, MUST BE the same as .so file name;
 * i.e., if MNAME is testmodule, then the .so must be testmodule.so.
 * You can call the below to set to wait req body read and then start
 * to handle the req either in the filter or in the begin_process()
 * of the handler struct.
 */

#define MNAME       waitfullreqbody
lsi_module_t MNAME;

#define     VERSION     "V1.2"

static char testuri[] = "/waitfullreqbody";

#define     CONTENT_HEAD    "<html><head><title>waitfullreqbody</title></head><body><p>\r\nHead<p>\r\n"
#define     CONTENT_FORMAT  "<tr><td>%s</td><td>%s</td></tr><p>\r\n"
#define     CONTENT_TAIL    "</body></html><p>\r\n"

#define MAX_BLOCK_BUFSIZE   8192

typedef struct mydata_s
{
    ls_loopbuf_t inbuf;
} mydata_t;


static int httprelease(void *data)
{
    g_api->log(NULL, LSI_LOG_DEBUG, "#### waitfullreqbody %s\n",
               "httprelease");
    return 0;
}


static int httpinit(lsi_param_t *param)
{
    mydata_t *mydata;
    ls_xpool_t *pool = g_api->get_session_pool(param->session);
    mydata = ls_xpool_alloc(pool, sizeof(mydata_t));
    ls_loopbuf_x(&mydata->inbuf, MAX_BLOCK_BUFSIZE, pool);
    g_api->log(NULL, LSI_LOG_DEBUG, "#### waitfullreqbody init\n");
    g_api->set_module_data(param->session, &MNAME, LSI_DATA_HTTP,
                           (void *)mydata);
    return 0;
}


/**
 * httpreqread will try to read as much as possible from the next step
 * of the stream and hold the data, then double each char to the buffer.
 * If finally it has hold data, set the hasBufferedData to 1 with *((int *)param->_flag_out) = 1;
 * DO NOT SET TO 0, because the other module may already set to 1 when pass in this function.
 *
 */
static int httpreqread(lsi_param_t *param)
{
    mydata_t *mydata = NULL;
    ls_xpool_t *pool = g_api->get_session_pool(param->session);
    char *pbegin;
    char tmpBuf[MAX_BLOCK_BUFSIZE];
    int len, sz, i;
    char *p = (char *)param->ptr1;

    mydata = (mydata_t *)g_api->get_module_data(param->session, &MNAME,
             LSI_DATA_HTTP);
    if (mydata == NULL)
        return LS_FAIL;

    while ((len = g_api->stream_read_next(param, tmpBuf,
                                          MAX_BLOCK_BUFSIZE)) > 0)
    {
        g_api->log(NULL, LSI_LOG_DEBUG,
                   "#### waitfullreqbody httpreqread, inLn = %d\n", len);
        ls_loopbuf_xappend(&mydata->inbuf, tmpBuf, len, pool);
    }

    while (!ls_loopbuf_empty(&mydata->inbuf)
           && (p - (char *)param->ptr1 < param->len1))
    {
        ls_loopbuf_xstraight(&mydata->inbuf, pool);
        pbegin = ls_loopbuf_begin(&mydata->inbuf);
        sz = ls_loopbuf_size(&mydata->inbuf);

//#define TESTCASE_2
#ifndef TESTCASE_2
        //test case 1: double each cahr
        if (sz > param->len1 / 2)
            sz = param->len1 / 2;
        for (i = 0; i < sz; ++i)
        {
            *p++ = *pbegin;
            *p++ = *pbegin;
            ++pbegin;
        }
#else
        //test case 2: shink to half of the org req body
        if (sz > param->_param_len * 2)
            sz = param->_param_len * 2;
        for (i = 0; i < sz / 2; ++i)
        {
            *p++ = *pbegin;
            pbegin += 2;
        }
#endif

        ls_loopbuf_popfront(&mydata->inbuf, sz);
    }

    param->len1 = p - (char *)param->ptr1;
    if (!ls_loopbuf_empty(&mydata->inbuf))
        *((int *)param->flag_out) = 1;

    return param->len1;
}


static int rcvd_req_header_cbf(lsi_param_t *param)
{
    const char *uri;
    int len;
    uri = g_api->get_req_uri(param->session, &len);
    if ((len >= sizeof(testuri) - 1)
        && (strncasecmp(uri, testuri, sizeof(testuri) - 1) == 0))
    {
        g_api->register_req_handler(param->session, &MNAME, sizeof(testuri) - 1);
        //g_api->set_req_wait_full_body(param->_session);
    }
    return LSI_OK;
}


static int init_module(lsi_module_t *module)
{
    module->about = VERSION;  //set version string
    g_api->init_module_data(module, httprelease, LSI_DATA_HTTP);

    return 0;
}


static int on_read(const lsi_session_t *session)
{
    char buf[MAX_BLOCK_BUFSIZE];
    int ret;
    int count = 0;
    char *txt;
    if (!g_api->is_req_body_finished(session))
    {
        sprintf(buf, CONTENT_FORMAT, "ERROR",
                "You must forget to set wait all req body!!!<p>\r\n");
        g_api->append_resp_body(session, buf, strlen(buf));
        return 1;
    }

    txt = (char *)"<tr><td>";
    g_api->append_resp_body(session, txt, strlen(txt));
    txt = (char *)"WHOLE REQ BODY";
    g_api->append_resp_body(session, txt, strlen(txt));
    txt = "</td><td>";
    g_api->append_resp_body(session, txt, strlen(txt));

    while ((ret = g_api->read_req_body(session, buf, MAX_BLOCK_BUFSIZE)) > 0)
    {
        g_api->append_resp_body(session, buf, ret);
        count += ret;
    }
    txt = (char *)"</td></tr><p>\r\n";
    g_api->append_resp_body(session, txt, strlen(txt));

    sprintf(buf, "<p>total req length read is %d<p>\r\n", count);
    g_api->append_resp_body(session, buf, strlen(buf));
    g_api->end_resp(session);
    return 0;
}


static int begin_process(const lsi_session_t *session)
{
    char *txt;
    g_api->set_req_wait_full_body(session);
    txt = (char *)CONTENT_HEAD;
    g_api->append_resp_body(session, txt, strlen(txt));
    if (g_api->is_req_body_finished(session))
    {
        txt = (char *)"Action in begin_process<p>\r\n";
        g_api->append_resp_body(session, txt, strlen(txt));
        on_read(session);
    }
    else
        g_api->flush(session);

    return 0;
}


static int clean_up(const lsi_session_t *session)
{
    g_api->free_module_data(session, &MNAME, LSI_DATA_HTTP,
                            httprelease);
    return 0;
}


static lsi_serverhook_t server_hooks[] =
{
    { LSI_HKPT_RCVD_REQ_HEADER, rcvd_req_header_cbf, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED },
    { LSI_HKPT_HTTP_BEGIN, httpinit, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED },
    { LSI_HKPT_RECV_REQ_BODY, httpreqread, LSI_HOOK_EARLY, LSI_FLAG_TRANSFORM | LSI_FLAG_ENABLED },

    LSI_HOOK_END   //Must put this at the end position
};

static lsi_reqhdlr_t myhandler = { begin_process, on_read, NULL, clean_up };

lsi_module_t MNAME =
{
    LSI_MODULE_SIGNATURE, init_module, &myhandler, NULL, "", server_hooks
};

