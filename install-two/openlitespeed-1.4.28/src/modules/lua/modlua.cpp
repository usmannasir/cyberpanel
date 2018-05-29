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
#include "lsluaengine.h"
#include "lsluasession.h"

#include <ls.h>

#include <string.h>
#include <unistd.h>
#include <time.h>

#define MODULE_VERSION_INFO     "1.1"

#define     MNAME       mod_lua
extern lsi_module_t MNAME;

/* Module Data */
typedef struct
{
    LsLuaSession *m_pSession;
} luaData_t;

static int releaseLuaData(void *data)
{
    if (data == NULL)
        return 0;

    luaData_t *pData = (luaData_t *)data;
    pData->m_pSession = NULL;
    free(pData);
    return 0;
}


static luaData_t *allocateLuaData(const lsi_session_t *session,
                                  const lsi_module_t *module, int level)
{
    luaData_t *pData = (luaData_t *)malloc(sizeof(luaData_t));
    if (pData == NULL)
        return NULL;
    memset(pData, 0, sizeof(luaData_t));
    g_api->set_module_data(session, module, level, pData);
    return pData;
}


static LsLuaSession *getLuaSess(const lsi_session_t *session)
{
    luaData_t *pData = (luaData_t *)g_api->get_module_data(session, &MNAME,
                       LSI_DATA_HTTP);
    if (pData == NULL)
        return NULL;
    return pData->m_pSession;
}


static int runLuaFilter(lsi_param_t *rec, int index)
{
    LsLuaUserParam *pUser;
    const char *pFile;
    int iFileLen = 0;
    const lsi_session_t *session = rec->session;
    luaData_t *pData = (luaData_t *)g_api->get_module_data(session, &MNAME,
                       LSI_DATA_HTTP);
    if (pData == NULL)
    {
        pData = allocateLuaData(session, &MNAME, LSI_DATA_HTTP);
        if (pData == NULL)
        {
            g_api->log(NULL, LSI_LOG_ERROR,
                       "FAILED TO ALLOCATE MODULE DATA\n");
            return LSI_ERROR;
        }
    }
    pData->m_pSession = NULL;

    pUser = (LsLuaUserParam *)g_api->get_config(session, &MNAME);
    pFile = pUser->getFilterPath(index, iFileLen);
    if (iFileLen <= 0)
    {
        g_api->log(NULL, LSI_LOG_ERROR, "Invalid Lua Filter file.");
        return LSI_ERROR;
    }
    if (index == LSLUA_HOOK_BODY)
    {
        return LsLuaEngine::runFilterScript(rec, pFile, pUser,
                                            &(pData->m_pSession), index);
    }
    return LsLuaEngine::runScript(session, pFile, pUser,
                                  &(pData->m_pSession), index);
}


int prepLuaFilter(lsi_param_t *rec)
{
    int aEnableHkpt[4], iEnableCount = 0;
    const lsi_session_t *session = rec->session;
    LsLuaUserParam *pUser = (LsLuaUserParam *)g_api->get_config(session,
                            &MNAME);
    g_api->set_req_wait_full_body(session);
    //TODO: set resp wait full body?

    if (pUser->isFilterActive(LSLUA_HOOK_REWRITE))
        aEnableHkpt[iEnableCount++] = LSI_HKPT_URI_MAP;

    if (pUser->isFilterActive(LSLUA_HOOK_AUTH))
        aEnableHkpt[iEnableCount++] = LSI_HKPT_HTTP_AUTH;

    if (pUser->isFilterActive(LSLUA_HOOK_HEADER))
        aEnableHkpt[iEnableCount++] = LSI_HKPT_RCVD_RESP_HEADER;

    if (pUser->isFilterActive(LSLUA_HOOK_BODY))
        aEnableHkpt[iEnableCount++] = LSI_HKPT_RECV_RESP_BODY;

    if (iEnableCount > 0)
        return g_api->enable_hook(session, &MNAME, 1,
                                  aEnableHkpt, iEnableCount);
    return LSI_OK;
}


int luaRewrite(lsi_param_t *rec)
{   return runLuaFilter(rec, LSLUA_HOOK_REWRITE);   }


int luaAuthFilter(lsi_param_t *rec)
{   return runLuaFilter(rec, LSLUA_HOOK_AUTH);  }


int luaHeaderFilter(lsi_param_t *rec)
{   return runLuaFilter(rec, LSLUA_HOOK_HEADER);   }


int luaBodyFilter(lsi_param_t *rec)
{   return runLuaFilter(rec, LSLUA_HOOK_BODY);  }


static int luaHandler(const lsi_session_t *session)
{
    char *uri;
    char luafile[MAXFILENAMELEN];
    int n;
    LsLuaUserParam *pUser;
    luaData_t *pData;

    pData = (luaData_t *)g_api->get_module_data(session, &MNAME,
            LSI_DATA_HTTP);
    if (pData == NULL)
    {
        pData = allocateLuaData(session, &MNAME, LSI_DATA_HTTP);
        if (pData == NULL)
        {
            g_api->log(NULL, LSI_LOG_ERROR,
                       "FAILED TO ALLOCATE MODULE DATA\n");
            return 500;
        }
    }
    pData->m_pSession = NULL;
    pUser = (LsLuaUserParam *)g_api->get_config(session, &MNAME);
    uri = (char *)g_api->get_req_uri(session, NULL);

    n = g_api->get_req_var_by_id(session, LSI_VAR_DOC_ROOT, luafile,
                                 MAXFILENAMELEN);
    memmove(luafile + n, uri, strlen(uri));
    n += strlen(uri);

    g_api->set_handler_write_state(session, 0);
    int debLevel = 0;
    if (*g_api->_log_level_ptr >= LSI_LOG_DEBUG)
        debLevel = (*g_api->_log_level_ptr - LSI_LOG_DEBUG) / 10; 
    LsLuaEngine::setDebugLevel(debLevel);
    return LsLuaEngine::runScript(session, luafile, pUser,
                                  &(pData->m_pSession), LSLUA_HOOK_HANDLER);

}


static int onCleanupEvent(const lsi_session_t *session)
{
    extern void CleanupLuaSession(const void *, LsLuaSession *);

    CleanupLuaSession(session, getLuaSess(session));
    return 0;
}


static int onReadEvent(const lsi_session_t *session)
{
    LsLuaSession *pSession = getLuaSess(session);
    if (pSession == NULL)
    {
        g_api->log(session, LSI_LOG_NOTICE,
                   "ERROR: LUA onReadEvent Session NULL\n");
        return 0;
    }

    // TODO: Fix this when everything is settled with what we expect for lua.
    if (g_api->is_req_body_finished(session))
    {
        char buf[8192];
#define     CONTENT_FORMAT  "<tr><td>%s</td><td>%s</td></tr><p>\r\n"
        snprintf(buf, 8192, CONTENT_FORMAT, "ERROR",
                 "Must set wait full request body!<p>\r\n");
        g_api->append_resp_body(session, buf, strlen(buf));
        return 0;
    }
    if ((pSession->isFlagSet(LLF_WAITREQBODY))
        && (!pSession->isFlagSet(LLF_LUADONE)))
        pSession->resume(pSession->getLuaState(), 0);
    return 0;
}


static int onWriteEvent(const lsi_session_t *session)
{
    LsLuaSession *pSession = getLuaSess(session);

    if ((pSession != NULL)
        && (pSession->onWrite(session) == 1))
        return LSI_RSP_MORE;
    return LSI_RSP_DONE;
}


static lsi_serverhook_t serverHooks[] =
{
    {
        LSI_HKPT_HTTP_BEGIN, prepLuaFilter, LSI_HOOK_EARLY,
        LSI_FLAG_ENABLED
    },
    { LSI_HKPT_URI_MAP, luaRewrite, LSI_HOOK_EARLY, 0 },
    { LSI_HKPT_HTTP_AUTH, luaAuthFilter, LSI_HOOK_EARLY, 0 },
    { LSI_HKPT_RCVD_RESP_HEADER, luaHeaderFilter, LSI_HOOK_EARLY, 0 },
    { LSI_HKPT_RECV_RESP_BODY, luaBodyFilter, LSI_HOOK_EARLY, 0 },
    LSI_HOOK_END
};


static int _init(lsi_module_t *pModule)
{
    if (LsLuaEngine::init() != 0)
        return LS_FAIL;
    pModule->about = LsLuaEngine::version();
    g_api->log(NULL, LSI_LOG_NOTICE, "LUA: %s ENGINE READY\n",
               LsLuaEngine::getLuaName());
    g_api->init_module_data(pModule, releaseLuaData, LSI_DATA_HTTP);
    return 0;
}

lsi_config_key_t myParam[] =
{
    {"luarewritepath", },
    {"luaauthpath", },
    {"luaheaderfilterpath", },
    {"luabodyfilterpath", },
    {"luapath", },
    {"lib", },
    {"maxruntime", },
    {"maxlinecount", },
    {"jitlinemod", },
    {"pause", }, 
    {NULL, }
};

static lsi_reqhdlr_t lslua_mod_handler = { luaHandler, onReadEvent,
                                           onWriteEvent, onCleanupEvent
                                         };

static lsi_confparser_t lslua_mod_config = { LsLuaEngine::parseParam,
                                             LsLuaEngine::removeParam,
                                             myParam
                                           };

lsi_module_t MNAME = { LSI_MODULE_SIGNATURE,
                       _init,
                       &lslua_mod_handler,
                       &lslua_mod_config,
                       MODULE_VERSION_INFO,
                       serverHooks,
{0}
                     };
