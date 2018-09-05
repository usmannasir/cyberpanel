/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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

//  Author: dxu@litespeedtech.com (David Shue)

#include <ls.h>
#include <lsr/ls_confparser.h>
#include <modsecurity/modsecurity.h>
#include <modsecurity/transaction.h>
#include <modsecurity/rules.h>

#define MNAME                       mod_security
#define ModuleNameStr               "Mod_Security"
#define VERSIONNUMBER               "1.1"

#define MODULE_VERSION_INFO         ModuleNameStr " " VERSIONNUMBER

#define MAX_RESP_HEADERS_NUMBER     50
#define MAX_REQ_HEADERS_NUMBER      50
#define STATUS_OK                   200
#define CHECKBODYTRUE               (RulesProperties::TrueConfigBoolean)
/////////////////////////////////////////////////////////////////////////////
extern lsi_module_t MNAME;

using namespace modsecurity;

typedef struct msc_conf_t_{
    ModSecurity            *modsec;
    Rules                  *rules_set;
    int                     enable;
    int                     level;
} msc_conf_t;


typedef struct ModData_t
{
    Transaction             *modsec_transaction;
} ModData;


lsi_config_key_t paramArray[] =
{
    {"modsecurity",                 0, 0},
    {"modsecurity_rules",           1, 0},
    {"modsecurity_rules_file",      2, 0},
    {"modsecurity_rules_remote",    3, 0},
    {NULL, 0, 0} //Must have NULL in the last item
};


void ls_modSecLogCb(void *_session, const void *data)
{
    if (data == NULL)
        return ;

    lsi_session_t *session = (lsi_session_t *)_session;
    g_api->log(session, LSI_LOG_DEBUG, "[Module:%s] %s\n", ModuleNameStr,
               (const char *)data);
}


int releaseMData(void *data)
{
    ModData *myData = (ModData *)data;
    if (myData)
    {
        if (myData->modsec_transaction)
            msc_transaction_cleanup(myData->modsec_transaction);
        myData->modsec_transaction = NULL;
        delete myData;
    }
    return 0;
}


//type:  1, rule,   2, file.  3, remote
static int setSecRule(msc_conf_t *pConfig, char *value, int type, char *uri)
{
    int ret = 0;
    const char *error = NULL;

    g_api->log(NULL, LSI_LOG_DEBUG,  "[Module:%s] setSecRule "
               "value: %s, type: %d %s\n",ModuleNameStr, value, type,
               type == 3 ? uri : "");
    
    switch(type)
    {
    case 1:
        ret = msc_rules_add(pConfig->rules_set, value, &error);
        break;
    case 2:
        ret = msc_rules_add_file(pConfig->rules_set, value, &error);
        break;
    case 3:
        ret = msc_rules_add_remote(pConfig->rules_set, value, uri, &error);
        break;
    }

    if (ret < 0) {
        g_api->log(NULL, LSI_LOG_ERROR, "[Module:%s]setSecRule(type %d) %s "
                   "failed, ret %d, reason: '%s'.\n",
                   ModuleNameStr, type, value, ret, error);
    }

    return ret;
}

static void *ParseConfig(module_param_info_t *param, int param_count,
                         void *_initial_config, int level, const char *name)
{
    int ret;
    const char *error = NULL;
    msc_conf_t  *pInitConfig = (msc_conf_t *)_initial_config;
    msc_conf_t *pConfig = new msc_conf_t;

    g_api->log(NULL, LSI_LOG_DEBUG,  "[Module:%s] ParseConfig entry, "
                "level %d\n", ModuleNameStr, level);
    if (!pConfig)
        return NULL;

    pConfig->level = level;

    if (level == LSI_CFG_SERVER)
    {
        assert(pInitConfig == NULL);
        pConfig->modsec = msc_init();
        msc_set_connector_info(pConfig->modsec, MODULE_VERSION_INFO);
        msc_set_log_cb(pConfig->modsec, ls_modSecLogCb);
    }
    else 
    {
        assert(pInitConfig);
        pConfig->modsec = pInitConfig->modsec;
    }

    pConfig->rules_set = msc_create_rules_set();
    
    /**
     * Set default enable value to 0.
     */
    pConfig->enable = (pInitConfig ? pInitConfig->enable : 0);

    if (!param || param_count == 0)
    {
        return (void *)pConfig;
    }

    //inherite the rules first
    if (pInitConfig)
    {
        ret = msc_rules_merge(pConfig->rules_set, pInitConfig->rules_set,
                              &error);
        if (ret < 0)
        {
            g_api->log(NULL, LSI_LOG_ERROR, 
                       "[Module:%s]ParseConfig msc_rules_merge failed - "
                       "reason: '%s'.\n",  ModuleNameStr, error);
        }
    }

    for (int i=0 ;i<param_count; ++i)
    {
        g_api->log(NULL, LSI_LOG_DEBUG,  "[Module:%s] ParseConfig "
                    "parameter[%d] %s %s\n", ModuleNameStr, i,
                   paramArray[param[i].key_index].config_key, param[i].val);

        if (param[i].val_len == 0)
            continue;

        if (param[i].key_index == 3) //remote
        {
            ls_confparser_t confparser;
            ls_confparser(&confparser);
            ls_objarray_t *pList = ls_confparser_line(&confparser, param[i].val,
                                                      param[i].val +
                                                      param[i].val_len);
        
            int count = ls_objarray_getsize(pList);
            g_api->log(NULL, LSI_LOG_DEBUG,  "[Module:%s] InRemoteRule "
                       "parameter count: %d (must be 2: license url)\n", 
                       ModuleNameStr, count);
            if (count == 2)
            {
                char *value = NULL;
                char *uri = NULL;
                ls_str_t *p = (ls_str_t *)ls_objarray_getobj(pList, 0);
                value = (char *)ls_str_cstr(p);
                p = (ls_str_t *)ls_objarray_getobj(pList, 1);
                uri= (char *)ls_str_cstr(p);
                setSecRule(pConfig, value, 3, uri);
            }
            ls_confparser_d(&confparser);
        }
        else if (param[i].key_index == 0)
        {
            if (strcasecmp(param[i].val, "on") != 0 &&
                strcasecmp(param[i].val, "off") != 0)
            {
                g_api->log(NULL, LSI_LOG_ERROR,
                           "[Module:%s] ParseConfig error, '%s %s' not"
                           " understood.\n", ModuleNameStr,
                           paramArray[0].config_key,
                           param[i].val);
            }
            else {
                pConfig->enable = (strcasecmp(param[i].val, "on") == 0);
                {
                    g_api->log(NULL, LSI_LOG_DEBUG,  "[Module:%s] Enable flag "
                               "interpreted as %d\n", ModuleNameStr, 
                               pConfig->enable);
                }
            }
        }
        else
        {
            setSecRule(pConfig, param[i].val, param[i].key_index, NULL);
        }
    }
//#define DEBUG
#ifdef DEBUG
    msc_rules_dump(pConfig->rules_set);
#endif
    return (void *)pConfig;
}


static void FreeConfig(void *_config)
{
    msc_conf_t  *pConfig = (msc_conf_t *)_config;

    if (pConfig->level == LSI_CFG_SERVER)
        msc_cleanup(pConfig->modsec);
    msc_rules_cleanup(pConfig->rules_set);
    delete (msc_conf_t *)_config;
}

static int process_intervention (Transaction *t, lsi_param_t *rec)
{
    ModSecurityIntervention intervention;
    intervention.status = STATUS_OK;
    intervention.url = NULL;
    intervention.log = NULL;
    intervention.disruptive = 0;

    int z = msc_intervention(t, &intervention);
    if (z == 0)
        return STATUS_OK;

    if (intervention.url)
    {
        g_api->log(rec->session, LSI_LOG_DEBUG, "[Module:%s]"
                   "Intervention url triggered: %d %s\n", 
                   ModuleNameStr, intervention.status, intervention.url);
        
        if (intervention.status == 301 || intervention.status == 302
            ||intervention.status == 303 || intervention.status == 307)
        {
            //g_api->set_status_code(rec->session, intervention.status);
            g_api->set_resp_header(rec->session,
                                   LSI_RSPHDR_LOCATION,
                                   NULL,
                                   0,
                                   intervention.url,
                                   strlen(intervention.url),
                                   0);
        }
        free(intervention.url);
    }

    if (intervention.log == NULL) {
        intervention.log = (char *)"(no log message was specified)";
        g_api->log(rec->session, LSI_LOG_DEBUG, "[Module:%s]"
                   "No log message specified\n", 
                   ModuleNameStr);
    }
    g_api->log(rec->session, LSI_LOG_DEBUG, "[Module:%s]"
               "Intervention status code triggered: %d\n", 
               ModuleNameStr, intervention.status);
    if (!intervention.url) {
        // NOT always logged in callback
        g_api->log(rec->session, LSI_LOG_DEBUG, "[Module:%s]"
                   "Log Message: %s\n", 
                   ModuleNameStr, intervention.log);
    }
    g_api->set_status_code(rec->session, intervention.status);
    return intervention.status;
}


int EndSession(lsi_param_t *rec)
{
    lsi_session_t *session = (lsi_session_t *)rec->session;
    ModData *myData = (ModData *) g_api->get_module_data(session, &MNAME,
                      LSI_DATA_HTTP);
    if (myData != NULL)
    {
        int code = g_api->get_status_code(rec->session);
        msc_update_status_code(myData->modsec_transaction, code);
        msc_process_logging(myData->modsec_transaction);
        process_intervention(myData->modsec_transaction, rec);

        g_api->log(session, LSI_LOG_DEBUG,
                   "[Module:%s] EndSession, session=%p myData=%p.\n",
                   ModuleNameStr, session, myData);
        g_api->free_module_data(session, &MNAME, LSI_DATA_HTTP, releaseMData);
    }

    return 0;
}


static int createModData(lsi_param_t *rec, msc_conf_t *conf)
{
    ModData *myData = (ModData *) g_api->get_module_data(rec->session, &MNAME,
                      LSI_DATA_HTTP);
    if (myData == NULL)
    {
        Transaction *trans = msc_new_transaction(conf->modsec,
                                                 conf->rules_set,
                                                 (void *)rec->session);
        if (!trans) {
            g_api->log(rec->session, LSI_LOG_ERROR,
                       "[Module:%s]Error in msc_new_transaction\n", 
                       ModuleNameStr);
            return LSI_ERROR;
        }

        myData = new ModData;
        memset(myData, 0, sizeof(ModData));
        myData->modsec_transaction = trans;
    }

    if (myData == NULL)
        return LSI_ERROR;
    else
    {
        g_api->set_module_data(rec->session, &MNAME, LSI_DATA_HTTP,
                               (void *)myData);
        return LSI_OK;
    }
}


static int UriMapHook(lsi_param_t *rec)
{
    lsi_session_t *session = (lsi_session_t *)rec->session;
    msc_conf_t *conf = (msc_conf_t *)g_api->get_config(session, &MNAME);
    if (!conf)
    {
        g_api->log(session, LSI_LOG_ERROR,
                   "[%s]UriMapHook internal error.\n", ModuleNameStr);
        return LSI_OK;
    }

    if (conf->enable == 0)
    {
        g_api->log(session, LSI_LOG_DEBUG,  "[Module:%s] Disabled.\n",
                   ModuleNameStr);
        return LSI_OK;
    }

    ModData *myData = (ModData *) g_api->get_module_data(session, &MNAME,
                      LSI_DATA_HTTP);
    if (myData == NULL)
    {
        int ret = createModData(rec, conf);
        if (ret == LSI_ERROR)
        {
            g_api->log(session, LSI_LOG_DEBUG, 
                       "[Module:%s] Internal error! createModData failed.\n",
                       ModuleNameStr);
            return LSI_OK;
        }
        else
        {
            myData = (ModData *) g_api->get_module_data(session, &MNAME,
                      LSI_DATA_HTTP);
            assert(myData);
        }
    }

    char host[512] = {0};
    g_api->get_req_var_by_id(session, LSI_VAR_SERVER_NAME, host, 512);
    
    char sport[12] = {0};
    g_api->get_req_var_by_id(session, LSI_VAR_SERVER_PORT, sport, 12);
    
    char cport[12] = {0};
    g_api->get_req_var_by_id(session, LSI_VAR_REMOTE_PORT, cport, 12);
    
    char cip[128] = {0};
    g_api->get_req_var_by_id(session, LSI_VAR_REMOTE_ADDR, cip, 128);

    msc_process_connection(myData->modsec_transaction,
                           cip,  atoi(cport),  host, atoi(sport));
    int ret = process_intervention(myData->modsec_transaction, rec);
    if (ret != STATUS_OK)
    {
        g_api->log(session, LSI_LOG_DEBUG, 
                   "[Module:%s] UriMapHook msc_process_connection failed.\n",
                   ModuleNameStr);
        return LSI_ERROR;
    }

    int qs_len;
    const char *qs = g_api->get_req_query_string(session, &qs_len);
    int uriLen = g_api->get_req_org_uri(session, NULL, 0);
    int uriMaxLen = uriLen + 1 + qs_len + 1;
    char *uri = new char[uriMaxLen];
    memset(uri,0,uriMaxLen);
    g_api->get_req_org_uri(session, uri, uriLen + 1);
    if (qs_len > 0)
    {
        strcat(uri, "?");
        strncat(uri, qs, qs_len);
    }
    char httpMethod[10] = {0};
    g_api->get_req_var_by_id(session, LSI_VAR_REQ_METHOD, httpMethod, 10);

    char *http_version = (char *)"1.1";
    char val[12] = {0};
    int n = g_api->get_req_var_by_id(session, LSI_VAR_SERVER_PROTO, val, 12);
    if (n >= 8)   //should be http/
    {
        http_version = strchr(val, '/');
        if (http_version)
            ++http_version;
        else
            http_version = (char *)"1.1";
    }

    g_api->log(session, LSI_LOG_DEBUG, "[Module:%s] Calling msc_process_uri "
                "with %s %s v%s.\n", ModuleNameStr, httpMethod, uri, http_version);
    msc_process_uri(myData->modsec_transaction, uri, httpMethod, http_version);
    ret = process_intervention(myData->modsec_transaction, rec);
    delete []uri;
    
    if (ret != STATUS_OK)
    {
        g_api->log(session, LSI_LOG_DEBUG, 
                   "[Module:%s] UriMapHook msc_process_connection failed.\n", 
                   ModuleNameStr);
        return LSI_ERROR;
    }

    int count = g_api->get_req_headers_count(session);
    if (count >= MAX_REQ_HEADERS_NUMBER)
        g_api->log(session, LSI_LOG_WARN,
                   "[Module:%s] too many req headers %d, [max defined as %d]\n",
                   ModuleNameStr, count, MAX_REQ_HEADERS_NUMBER);

    struct iovec iov_key[MAX_REQ_HEADERS_NUMBER];
    struct iovec iov_val[MAX_REQ_HEADERS_NUMBER];
    count = g_api->get_req_headers(session, iov_key, iov_val,
                                    MAX_REQ_HEADERS_NUMBER);
    for (int i = 0; i < count; ++i)
    {
        msc_add_n_request_header(myData->modsec_transaction,
                                  (const unsigned char *)iov_key[i].iov_base,
                                  iov_key[i].iov_len,
                                  (const unsigned char *)iov_val[i].iov_base,
                                  iov_val[i].iov_len);
    }
    msc_process_request_headers(myData->modsec_transaction);
    ret = process_intervention(myData->modsec_transaction, rec);
    if (ret != STATUS_OK)
    {
        g_api->log(session, LSI_LOG_DEBUG, "[Module:%s] UriMapHook "
                    "msc_process_request_headers failed.\n", ModuleNameStr);
        return LSI_ERROR;
    }
    
    Rules *rules = myData->modsec_transaction->m_rules;
    bool chkReqBody = rules->m_secRequestBodyAccess == CHECKBODYTRUE;
    bool chkRespBody = rules->m_secResponseBodyAccess == CHECKBODYTRUE;
    g_api->log(session, LSI_LOG_DEBUG, "[Module:%s] RequestBodyAccess: %s "
               "ResponseBodyAccess: %s\n", ModuleNameStr,
               chkReqBody ? "YES" : "NO",
               chkRespBody ? "YES" : "NO");
    
    g_api->set_req_wait_full_body(session);
    int aEnableHkpt[4] = {LSI_HKPT_RCVD_RESP_HEADER,
                          LSI_HKPT_HANDLER_RESTART, };
    int arrCount = 2;
    if (chkReqBody)
        aEnableHkpt[arrCount ++] = LSI_HKPT_RCVD_REQ_BODY;
    if (chkRespBody)
        aEnableHkpt[arrCount ++] = LSI_HKPT_RCVD_RESP_BODY;

    g_api->enable_hook(session, &MNAME, 1, aEnableHkpt, arrCount);
    return LSI_OK;
}


static int reqBodyHook(lsi_param_t *rec)
{
    lsi_session_t *session = (lsi_session_t *)rec->session;
    int64_t offset = 0;
    ModData *myData = (ModData *) g_api->get_module_data(session, &MNAME,
                      LSI_DATA_HTTP);
    void *pBuf;
    pBuf = g_api->get_req_body_buf(session);
    int64_t len = g_api->get_body_buf_size(pBuf);
    const char *pTmpBuf;
    
    g_api->log(session, LSI_LOG_DEBUG,
               "[Module:%s] reqBodyHook entry, len: %ld.\n", ModuleNameStr, len);
    
    if (len == 0)
        return LSI_OK;

    do
    {
        len = 0;
        if ((pTmpBuf = g_api->acquire_body_buf_block(pBuf, offset, (int *)&len))
            == NULL)
            break;

        //g_api->log(session, LSI_LOG_DEBUG,
        //           "[Module:%s] reqBodyHook data: %ld bytes.\n", ModuleNameStr, len);
        
        msc_append_request_body(myData->modsec_transaction,
                                (const unsigned char *)pTmpBuf, (size_t)len);
        int ret = process_intervention(myData->modsec_transaction, rec);
        if (ret != STATUS_OK) {
            g_api->log(session, LSI_LOG_DEBUG,
                    "[Module:%s] reqBodyHook failed.\n", ModuleNameStr);
            return LSI_ERROR;
        }
        offset += len;
    }
    while (!g_api->is_body_buf_eof(pBuf, offset)); 
    
    g_api->log(session, LSI_LOG_DEBUG,
               "[Module:%s] reqBodyHook used %ld bytes of %ld\n", 
               ModuleNameStr, offset, len);
    
    g_api->log(session, LSI_LOG_DEBUG,
               "[Module:%s] reqBodyHook final body check.\n", ModuleNameStr);
    msc_process_request_body(myData->modsec_transaction);
    int ret = process_intervention(myData->modsec_transaction, rec);
    if (ret != STATUS_OK) {
       g_api->log(session, LSI_LOG_DEBUG,
                  "[Module:%s] reqBodyHook failed in final intervention.\n", 
                  ModuleNameStr);
       return LSI_ERROR;
    }
    return LSI_OK;
}

static int respHeaderHook(lsi_param_t *rec)
{
    lsi_session_t *session = (lsi_session_t *)rec->session;
    ModData *myData = (ModData *) g_api->get_module_data(session, &MNAME,
                      LSI_DATA_HTTP);
    int count = g_api->get_resp_headers_count(rec->session);
    if (count >= MAX_RESP_HEADERS_NUMBER)
        g_api->log(rec->session, LSI_LOG_WARN,
                   "[Module:%s] too many resp headers %d, [max defined as %d]\n",
                   ModuleNameStr, count, MAX_RESP_HEADERS_NUMBER);

    struct iovec iov_key[MAX_RESP_HEADERS_NUMBER];
    struct iovec iov_val[MAX_RESP_HEADERS_NUMBER];
    count = g_api->get_resp_headers(rec->session, iov_key, iov_val,
                                    MAX_RESP_HEADERS_NUMBER);
    for (int i = 0; i < count; ++i)
    {
        msc_add_n_response_header(myData->modsec_transaction,
                                  (const unsigned char *)iov_key[i].iov_base,
                                  iov_key[i].iov_len,
                                  (const unsigned char *)iov_val[i].iov_base,
                                  iov_val[i].iov_len);
    }
    int code = g_api->get_status_code(rec->session);
    msc_process_response_headers(myData->modsec_transaction, code,  "HTTP 1.1");
    
    int ret = process_intervention(myData->modsec_transaction, rec);
    if (ret != STATUS_OK)
    {
        g_api->log(session, LSI_LOG_ERROR,
                   "[Module:%s]respHeaderHook failed.\n", ModuleNameStr);
        return LSI_ERROR;
    }

    return LSI_OK;
}

 static int respBodyHook(lsi_param_t *rec)
 {
    lsi_session_t *session = (lsi_session_t *)rec->session;
    ModData *myData = (ModData *) g_api->get_module_data(session, &MNAME,
                      LSI_DATA_HTTP);

    //long iCahcedSize = 0;
    off_t offset = 0;
    const char *pBuf;
    int len = 0;
    void *pRespBodyBuf = g_api->get_resp_body_buf(rec->session);
    int ret;
    while (!g_api->is_body_buf_eof(pRespBodyBuf, offset))
    {
        len = 0;
        pBuf = g_api->acquire_body_buf_block(pRespBodyBuf, offset, &len);
        if (!pBuf || len <= 0)
            break;

        msc_append_response_body(myData->modsec_transaction,
                                 (const unsigned char *)pBuf, len);

        g_api->release_body_buf_block(pRespBodyBuf, offset);
        offset += len;
    }

    msc_process_response_body(myData->modsec_transaction);
    ret = process_intervention(myData->modsec_transaction, rec);
    if (ret != STATUS_OK)
    {
        g_api->log(session, LSI_LOG_ERROR,
                   "[Module:%s]respBodyHook failed.\n", ModuleNameStr);
        return LSI_ERROR;
    }

    return LSI_OK;
 }


static lsi_serverhook_t serverHooks[] =
{
    { LSI_HKPT_URI_MAP,         UriMapHook,     LSI_HOOK_NORMAL,    LSI_FLAG_ENABLED },
    { LSI_HKPT_RCVD_REQ_BODY,   reqBodyHook,    LSI_HOOK_FIRST,     0},
    { LSI_HKPT_RCVD_RESP_HEADER,respHeaderHook, LSI_HOOK_FIRST,     0},
    { LSI_HKPT_HANDLER_RESTART, EndSession,     LSI_HOOK_NORMAL,    0},
    { LSI_HKPT_HTTP_END,        EndSession,     LSI_HOOK_NORMAL,    LSI_FLAG_ENABLED },
    { LSI_HKPT_RCVD_RESP_BODY,  respBodyHook,   LSI_HOOK_LAST + 1,  0},
    LSI_HOOK_END   //Must put this at the end position
};

static int init(lsi_module_t *pModule)
{
    g_api->init_module_data(pModule, releaseMData, LSI_DATA_HTTP);
    return 0;
}

lsi_confparser_t configSt = { ParseConfig, FreeConfig, paramArray };
LSMODULE_EXPORT lsi_module_t MNAME = { LSI_MODULE_SIGNATURE, init, NULL, &configSt,
                        MODULE_VERSION_INFO, serverHooks, {0} };

