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
#define _GNU_SOURCE
#include <ls.h>
#include <lsr/ls_strtool.h>
#include <lsr/ls_confparser.h>
#include <string.h>
#include <stdlib.h>
#include <memory.h>
#include <ctype.h>

/**********************************************************************
 *
 * This module is for testing params of different context levels.
 * You can set it with different params in server, VHost/module and context
 * under VHost/module, and VHost/context levels, use such as "param1 123\n
 * param2 10\n..."
 * The uri in each context level must have "/test/", such as /test/, /test/1/2/,
 * and so on.
 *
 * You can test "get /test/1/", "get /test/1/2/testfile"
 *
 * The handler can be registered under the VHost/context or by enable the filters
 * somewhere, and then when the context matched the url and then the filter will
 * be called so that the filter will register itself as a handler.
 *
 * The result should be
 * If the hook is enabled, the filer may run and set itself as
 * handler, the result is always the context which match the longest uri,
 * the result is different for different context level.
 *
 **********************************************************************/

#define     MNAME       testparam
lsi_module_t MNAME;


typedef struct _param_st
{
    int param1;
    int param21;
    int param22;
    int param31;
    int param32;
    int param33;
    int param41;
    int param42;
    int param43;
    int param44;
    int param51;
    int param52;
    int param53;
    int param54;
    int param55;
} param_st;

//Setup the below array to let web server know these params
lsi_config_key_t myParam[] =
{
    {"param1",  0, 0},
    {"param2",  0, 0},
    {"param3",  0, 0},
    {"param4",  0, 0},
    {"param5",  0, 0},
    {NULL,  0, 0}   //The last position must have a NULL to indicate end of the array
};

//return 0 for correctly parsing
static int testparam_parseList(module_param_info_t *param, param_st *pConfig)
{
    int *pParam;
    ls_confparser_t confparser;
    ls_confparser(&confparser);
    ls_objarray_t *pList = ls_confparser_line(&confparser, param->val,
                                              param->val + param->val_len);
    
    int count = ls_objarray_getsize(pList);
    assert(count > 0);
    
    //Comment: case param2, maxParamNum is 2, the line should be param2 [21 [22]],
    unsigned long maxParamNum = param->key_index + 1;
    if (maxParamNum > 5)
        maxParamNum = 1;

    ls_str_t *p;
    long val;
    int i;
    
    for (i = 0; i < count && i < maxParamNum; ++i)
    {
        p = (ls_str_t *)ls_objarray_getobj(pList, i);
        val = strtol(ls_str_cstr(p), NULL, 10);

        switch(param->key_index)
        {
        case 0:
            pParam = &pConfig->param1 + i;
            break;
        case 1:
            pParam = &pConfig->param21 + i;
            break;
        case 2:
            pParam = &pConfig->param31 + i;
            break;
        case 3:
            pParam = &pConfig->param41 + i;
            break;
        case 4:
            pParam = &pConfig->param51 + i;
            break;
        }
        *pParam = val;
    }
    
    ls_confparser_d(&confparser);
    return 0;
}


static void *testparam_parseConfig(module_param_info_t *param, int param_count,
                                   void *_initial_config, int level, const char *name)
{
    int i;
    param_st *pInitConfig = (param_st *)_initial_config;
    param_st *pConfig = (param_st *) malloc(sizeof(struct _param_st));
    if (!pConfig)
        return NULL;

    if (pInitConfig)
        memcpy(pConfig, pInitConfig, sizeof(struct _param_st));
    else
        memset(pConfig, 0, sizeof(struct _param_st));

    if (!param)
        return (void *)pConfig;

    for (i=0 ;i<param_count; ++i)
    {
        testparam_parseList(&param[i], pConfig);
    }
    return (void *)pConfig;
}

static void testparam_freeConfig(void *_config)
{
    free(_config);
}

static int testparam_handlerBeginProcess(const lsi_session_t *session)
{
    g_api->set_resp_header(session, LSI_RSPHDR_CONTENT_TYPE, NULL, 0,
                           "text/plain", sizeof("text/plain") - 1, LSI_HEADEROP_SET);

    param_st *pparam_st = (param_st *) g_api->get_config(session,
                          &MNAME);
    char buf[1024];
    int len;
    if (pparam_st)
    {
        sprintf(buf,
                "Current uri is %s.\nContext uri is %s.\nparam1 = %d\nparam2 = %d %d\nparam3 = %d %d %d\nparam4 = %d %d %d %d\nparam5 = %d %d %d %d %d\n",
                g_api->get_req_uri(session, NULL),
                g_api->get_mapped_context_uri(session, &len),
                pparam_st->param1, pparam_st->param21, pparam_st->param22,
                pparam_st->param31, pparam_st->param32, pparam_st->param33,
                pparam_st->param41, pparam_st->param42, pparam_st->param43,
                pparam_st->param44,
                pparam_st->param51, pparam_st->param52, pparam_st->param53,
                pparam_st->param54, pparam_st->param55);

    }
    else
        strcpy(buf,
               "There is no parameters extracted from Module Parameters - check web admin\n");
    g_api->append_resp_body(session, buf, strlen(buf));
    g_api->end_resp(session);
    return 0;
}

static int uri_map_cbf(lsi_param_t *rec)
{
    const char *uri;
    int len;
    uri = g_api->get_req_uri(rec->session, &len);
    if (len >= 10 && strcasestr(uri, "/testparam"))
        g_api->register_req_handler(rec->session, &MNAME, 10);
    return LSI_OK;
}

static lsi_serverhook_t serverHooks[] =
{
    {LSI_HKPT_URI_MAP, uri_map_cbf, LSI_HOOK_EARLY, LSI_FLAG_ENABLED},
    LSI_HOOK_END   //Must put this at the end position
};

static int testparam_init(lsi_module_t *pModule)
{
    param_st *pparam_st = (param_st *) g_api->get_config(NULL, pModule);
    if (pparam_st)
    {
        g_api->log(NULL,  LSI_LOG_INFO,
                   "[testparam]Global level param: param1 = %d param2 = %d %d param3 = %d %d %d param4 = %d %d %d %d param5 = %d %d %d %d %d\n",
                   pparam_st->param1, pparam_st->param21, pparam_st->param22,
                   pparam_st->param31, pparam_st->param32, pparam_st->param33,
                   pparam_st->param41, pparam_st->param42, pparam_st->param43,
                   pparam_st->param44,
                   pparam_st->param51, pparam_st->param52, pparam_st->param53,
                   pparam_st->param54, pparam_st->param55);
    }
    else
        g_api->log(NULL,  LSI_LOG_INFO,
                   "[testparam]Global level NO params, ERROR.\n");

    return 0;
}

lsi_reqhdlr_t testparam_myhandler = { testparam_handlerBeginProcess, NULL, NULL, NULL };
lsi_confparser_t testparam_dealConfig = { testparam_parseConfig, testparam_freeConfig, myParam };
lsi_module_t MNAME = { LSI_MODULE_SIGNATURE, testparam_init, &testparam_myhandler, &testparam_dealConfig, "Version 1.1", serverHooks };
