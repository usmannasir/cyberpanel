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
#include <lsr/ls_loopbuf.h>
#include <lsr/ls_xpool.h>

#include <stdio.h>
#include <stdlib.h>
#include <memory.h>
//#include <zlib.h>
#include <string.h>

/////////////////////////////////////////////////////////////////////////////
//DEFINE the module name, MUST BE the same as .so file name
//ie.  if MNAME is testmodule, then the .so must be testmodule.so
#define     MNAME       updatehttpout
#define     TEST_STRING "_TEST_testmodule_ADD_A_STRING_HERE_<!--->"
/////////////////////////////////////////////////////////////////////////////

lsi_module_t MNAME;
#define MAX_BLOCK_BUFSIZE   8192

typedef struct _MyData
{
    ls_loopbuf_t inWBuf;
    ls_loopbuf_t outWBuf;
} MyData;



int httpRelease(void *data)
{
    g_api->log(NULL, LSI_LOG_DEBUG, "#### mymodulehttp %s\n", "httpRelease");
    return 0;
}

int httpinit(lsi_param_t *rec)
{
    MyData *myData = (MyData *)g_api->get_module_data(rec->session, &MNAME,
                     LSI_DATA_HTTP);
    ls_xpool_t *pool = g_api->get_session_pool(rec->session);
    myData = (MyData *)ls_xpool_alloc(pool, sizeof(MyData));
    ls_loopbuf_x(&myData->inWBuf, MAX_BLOCK_BUFSIZE, pool);
    ls_loopbuf_x(&myData->outWBuf, MAX_BLOCK_BUFSIZE, pool);

    g_api->log(NULL, LSI_LOG_DEBUG, "#### mymodulehttp init\n");
    g_api->set_module_data(rec->session, &MNAME, LSI_DATA_HTTP,
                           (void *)myData);
    return 0;
}

int httprespwrite(lsi_param_t *rec)
{
    MyData *myData = NULL;
    ls_xpool_t *pool = g_api->get_session_pool(rec->session);
    const char *in = rec->ptr1;
    int inLen = rec->len1;
    int written, total = 0;
//    int j;
//    char s[4] = {0};
    myData = (MyData *)g_api->get_module_data(rec->session, &MNAME,
             LSI_DATA_HTTP);

//     for ( j=0; j<inLen; ++j )
//     {
//         sprintf(s, "%c ", (unsigned char)in[j]);
//         ls_loopbuf_xappend( &myData->m_outWBuf, s, 2, pool );
//         total += 2;
//     }

    //If have content, append a string for testing
    if (inLen > 0)
    {
        ls_loopbuf_xappend(&myData->outWBuf, TEST_STRING, sizeof(TEST_STRING) - 1,
                           pool);
        ls_loopbuf_xappend(&myData->outWBuf, in, inLen, pool);
        total = inLen + sizeof(TEST_STRING) - 1;
    }

    ls_loopbuf_xstraight(&myData->outWBuf, pool);

    written = g_api->stream_write_next(rec, ls_loopbuf_begin(&myData->outWBuf),
                                       ls_loopbuf_size(&myData->outWBuf));
    ls_loopbuf_popfront(&myData->outWBuf, written);

    g_api->log(NULL, LSI_LOG_DEBUG,
               "#### mymodulehttp test, next caller written %d, return %d, left %d\n",
               written, total, ls_loopbuf_size(&myData->outWBuf));


    if (!ls_loopbuf_empty(&myData->outWBuf))
    {
        int hasData = 1;
        rec->flag_out = &hasData;
    }
    return inLen; //Because all data used, ruturn thr orignal length
}

static char *getNullEndString(const char *s, int len, char *str,
                              int maxLength)
{
    if (len >= maxLength)
        len = maxLength - 1;
    memcpy(str, s, len);
    str[len] = 0x00;
    return str;
}


int httpreqHeaderRecved(lsi_param_t *rec)
{
    const char *host, *ua, *uri, *accept;
    char *headerBuf;
    int hostLen, uaLen, acceptLen, headerLen;
    char uaBuf[1024], hostBuf[128], acceptBuf[512];
    ls_xpool_t *pPool = g_api->get_session_pool(rec->session);

    uri = g_api->get_req_uri(rec->session, NULL);
    host = g_api->get_req_header(rec->session, "Host", 4, &hostLen);
    ua = g_api->get_req_header(rec->session, "User-Agent", 10, &uaLen);
    accept = g_api->get_req_header(rec->session, "Accept", 6, &acceptLen);
    g_api->log(NULL, LSI_LOG_DEBUG,
               "#### mymodulehttp test, httpreqHeaderRecved URI:%s host:%s, ua:%s accept:%s\n",
               uri, getNullEndString(host, hostLen, hostBuf, 128), getNullEndString(ua,
                       uaLen, uaBuf, 1024), getNullEndString(accept, acceptLen, acceptBuf, 512));

    headerLen = g_api->get_req_raw_headers_length(rec->session);
    headerBuf = (char *)ls_xpool_alloc(pPool, headerLen + 1);
    memset(headerBuf, 0, headerLen + 1);
    g_api->get_req_raw_headers(rec->session, headerBuf, headerLen);
    g_api->log(NULL, LSI_LOG_DEBUG,
               "#### mymodulehttp test, httpreqHeaderRecved whole header: %s, length: %d\n",
               headerBuf, headerLen);

    ls_xpool_free(pPool, headerBuf);
    return 0;

}

static lsi_serverhook_t serverHooks[] =
{
    {LSI_HKPT_HTTP_BEGIN, httpinit, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED},
    {LSI_HKPT_RECV_RESP_BODY, httprespwrite, LSI_HOOK_NORMAL, LSI_FLAG_TRANSFORM | LSI_FLAG_DECOMPRESS_REQUIRED | LSI_FLAG_ENABLED},
    {LSI_HKPT_RCVD_REQ_HEADER, httpreqHeaderRecved, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED},
    LSI_HOOK_END   //Must put this at the end position
};

static int init_module(lsi_module_t *pModule)
{
    g_api->init_module_data(pModule, httpRelease, LSI_DATA_HTTP);
    return 0;
}

lsi_module_t MNAME = { LSI_MODULE_SIGNATURE, init_module, NULL, NULL, "", serverHooks};
