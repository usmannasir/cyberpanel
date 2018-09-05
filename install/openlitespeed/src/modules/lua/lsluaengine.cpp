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
#include "lsluaengine.h"

#include "lsluaapi.h"
#include "lsluadefs.h"
#include "lsluasession.h"

#include <lsr/ls_confparser.h>
#include <lsr/ls_loopbuf.h>
#include <lsr/ls_strtool.h>

#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

#define LS_LUA_BEGINSTR "package.preload['apache2'] = function() end\n" \
    "local run_ls_lua_fn;\n" \
    "do\n" \
    "  apache2=ls\n" \
    "  ngx=ls\n" \
    "  local _ENV = LS_BOX\n" \
    "  function run_ls_lua_fn(r)\n"

#define LS_LUA_ENDSTR   "    \n" \
    "  end\n" \
    "end\n" \
    "return run_ls_lua_fn"



int             LsLuaEngine::s_iFirstTime = 1;
int             LsLuaEngine::s_iDebugLevel = 0;
int             LsLuaEngine::s_iReady = 0;
lua_State      *LsLuaEngine::s_pSystemState = NULL;

int             LsLuaEngine::s_iMaxRunTime = 0;           // 0 no limit
int             LsLuaEngine::s_iMaxLineCount =
    0;         // default is 0 (10000000 instruction per yield ~ 1000000 lines)
int             LsLuaEngine::s_iJitLineMod = 10000;

int             LsLuaEngine::s_iDebug = 0;
int             LsLuaEngine::s_iPauseTime =
    500;          // pause time 500 msec per yield
char           *LsLuaEngine::s_pLuaLib = NULL;
char            LsLuaEngine::s_aLuaName[0x10] = "LUA";
const char     *LsLuaEngine::s_pSysLuaLib =
    "/usr/local/lib/libluajit-5.1.so"; // default
char           *LsLuaEngine::s_pLuaPath = NULL;
const char     *LsLuaEngine::s_pSysLuaPath =
    "/usr/local/lib/lua"; // default LUA_PATH
char            LsLuaEngine::s_aVersion[0x20] =
    "LUA-NOT-READY"; // default LUA_VERSION

LsLuaEngine::LSLUA_TYPE LsLuaEngine::s_type = LSLUA_ENGINE_REGULAR;
LsLuaEngine::LsLuaEngine()
{
}


LsLuaEngine::~LsLuaEngine()
{
}


int LsLuaEngine::init()
{
    const char *pErr;
    const char *pLibPath;
//     char errbuf[MAX_ERRBUF_SIZE];
    s_iReady = 0;     // set no ready

    pLibPath = s_pLuaLib ? s_pLuaLib : s_pSysLuaLib;

    if ((pErr = LsLuaApi::init(pLibPath)) != NULL)
    {
        g_api->log(NULL, LSI_LOG_ERROR, "[LUA] Failed to load %s "
                   "from module!\n", pErr);
        return LS_FAIL;
    }
    if (LsLuaApi::jitMode())
    {
        s_type = LSLUA_ENGINE_JIT;
        strcpy(s_aLuaName, "JIT");
    }
    else
    {
        s_type = LSLUA_ENGINE_REGULAR;
        strcpy(s_aLuaName, "LUA");
    }
    g_api->log(NULL, LSI_LOG_DEBUG,
               "%s REGISTRYINDEX[%d] GLOBALSINDEX[%d]\n",
               s_aLuaName, LSLUA_REGISTRYINDEX,
               LSLUA_GLOBALSINDEX
              );
    g_api->log(NULL, LSI_LOG_DEBUG,
               "%s lib[%s] luapath[%s]\n", s_aLuaName,
               s_pLuaLib ? s_pLuaLib : "",
               s_pLuaPath ? s_pLuaPath : ""
              );
    g_api->log(NULL, LSI_LOG_DEBUG,
               "%s maxruntime[%d] maxlinecount[%d]\n",
               s_aLuaName, s_iMaxRunTime, s_iMaxLineCount
              );
    g_api->log(NULL, LSI_LOG_DEBUG,
               "%s pause[%dmsec] jitlinemod[%d]\n",
               s_aLuaName, s_iPauseTime, s_iJitLineMod
              );

    if ((s_type == LSLUA_ENGINE_JIT)
        && (LSLUA_REGISTRYINDEX != -10000))
    {
        g_api->log(NULL, LSI_LOG_WARN,
                   "JIT PATCH REGISTRYINDEX IS NOT -10000\n");
        return LS_FAIL;
    }

    s_pSystemState = newLuaConnection();
    if (s_pSystemState == NULL)
        return LS_FAIL;

    injectLsiapi(s_pSystemState);
    LsLuaCreateUD(s_pSystemState);
    LsLuaApi::execLuaCmd(getSystemState(), "ls.set_version(_VERSION)");
    s_iReady = 1;
    return 0;
}


int LsLuaEngine::isReady(const lsi_session_t *session)
{
    return s_iReady;
}


int LsLuaEngine::checkResume(LsLuaSession *pSession, int iRet)
{
    const char *pErrType;
    switch (iRet)
    {
    case 0:
        if (pSession->getLuaExitCode())
        {
            g_api->set_status_code(pSession->getHttpSession(),
                                   pSession->getLuaExitCode());
            iRet = -1;
        }
        g_api->end_resp(pSession->getHttpSession());
        return iRet;
    case LUA_YIELD:
        if (pSession->isFlagSet(LLF_LUADONE))
            g_api->end_resp(pSession->getHttpSession());
        iRet = 0;
        break;
    case LUA_ERRRUN:
        pErrType = "ERRRUN";
        break;
    case LUA_ERRMEM:
        pErrType = "ERRMEM";
        break;
    case LUA_ERRERR:
        pErrType = "ERRERR";
        break;
    default:
        pErrType = "ERROR";
        iRet = LSI_DENY;
    }
    if (iRet)
    {
        g_api->set_status_code(pSession->getHttpSession(), 500);
        g_api->log(pSession->getHttpSession(), LSI_LOG_NOTICE,
                   "RESUMEK %s %d\n", pErrType, iRet);
        LsLuaApi::dumpStack(pSession->getLuaState(),
                            LUA_RESUME_ERROR, 10);
        iRet = 500;
    }
    return iRet;
}


int LsLuaEngine::resumeNcheck(LsLuaSession *pSession, int iArgs)
{
    int ret = LsLuaApi::resume(pSession->getLuaState(), iArgs);
    return LsLuaEngine::checkResume(pSession, ret);
}


int LsLuaEngine::setupSandBox(lua_State *L)
{
    LsLuaApi::pushglobaltable(L);
    if (LsLuaApi::setfenv(L, -2) != 1)
        return 1;
    return 0;
}


void LsLuaEngine::ref(LsLuaSession *pSession)
{
    int *r;

    pSession->setTop(LsLuaApi::gettop(getSystemState()));
    LsLuaApi::pushvalue(getSystemState(), -1);

    r = pSession->getRefPtr();
    *r = LsLuaApi::ref(getSystemState(), LSLUA_REGISTRYINDEX);
}


void LsLuaEngine::unref(LsLuaSession *pSession)
{
    int *r;
    lua_State *thread;

    r = pSession->getRefPtr();
    if (*r == LUA_REFNIL)
        return;

    int from = LsLuaApi::gettop(getSystemState());
    if (from > pSession->getTop())
        from = pSession->getTop();
    while (from > 0)
    {
        if ((thread = LsLuaApi::tothread(getSystemState(),
                                         from)))
        {
            if (thread == pSession->getLuaState())
            {
                LsLuaApi::remove(getSystemState(), from);
                break;
            }
        }
        from--;
    }

    LsLuaApi::unref(getSystemState(), LSLUA_REGISTRYINDEX, *r);
    *r = LUA_REFNIL;
}


int LsLuaEngine::loadRef(LsLuaSession *pSession, lua_State *L)
{
    int *r;
    lua_State *y;
    r = pSession->getRefPtr();
    if (*r == LUA_REFNIL)
        return 0;

    LsLuaApi::rawgeti(getSystemState(), LSLUA_REGISTRYINDEX, *r);

    y = LsLuaApi::tothread(getSystemState(), -1);
    if (y != L)
    {
        g_api->log(pSession->getHttpSession(), LSI_LOG_ERROR,
                   "Session thread %p != %p\n", L, y);
        LsLuaApi::pop(getSystemState(), 1);
        return LS_FAIL;
    }
    else
    {
        LsLuaApi::pop(getSystemState(), 1);
        return 0;
    }
}


LsLuaSession *LsLuaEngine::prepState(const lsi_session_t *session,
                                     const char *scriptpath,
                                     LsLuaUserParam *pUser,
                                     int iCurHook)
{
    int ret;
    LsLuaSession *pSandbox;
    lua_State *L;
    g_api->log(session, LSI_LOG_DEBUG, "maxruntime %d maxlinecount %d\n",
               pUser->getMaxRunTime(),
               pUser->getMaxLineCount());
    if ((ret = LsLuaFuncMap::loadLuaScript(session, getSystemState(),
                                           scriptpath)) != 0)
    {
        g_api->end_resp(session);
        return NULL;
    }
    pSandbox = new LsLuaSession;
    pSandbox->init(session, iCurHook);
    pSandbox->setupLuaEnv(getSystemState(), pUser);
    L = pSandbox->getLuaState();

    LsLuaApi::insert(getSystemState(), -2);
    LsLuaApi::xmove(getSystemState(), L, 1);
    LsLuaEngine::ref(pSandbox);
    if (pSandbox->getRef() == LUA_REFNIL)
    {
        g_api->append_resp_body(session, LUA_ERRSTR_ERROR,
                                strlen(LUA_ERRSTR_ERROR));
        g_api->end_resp(session);
        return NULL;
    }

    if ((LsLuaApi::jitMode())
        && (LsLuaEngine::setupSandBox(L)))
    {
        g_api->log(session, LSI_LOG_ERROR, "%s %d\n",
                   LUA_ERRSTR_SANDBOX, ret);
        g_api->append_resp_body(session, LUA_ERRSTR_SANDBOX,
                                strlen(LUA_ERRSTR_SANDBOX));
        g_api->end_resp(session);
        return NULL;
    }
    return pSandbox;
}


int LsLuaEngine::runState(const lsi_session_t *session, LsLuaSession *pSandbox,
                          int iCurHook)
{
    int ret;
    lua_State *L = pSandbox->getLuaState();
    if ((ret = LsLuaApi::resume(L, 0)) != 0)
    {
        g_api->log(session, LSI_LOG_ERROR, "%s %d, Message: %s\n",
                   LUA_ERRSTR_SCRIPT, ret,
                   LsLuaApi::tolstring(L, -1, NULL)
                  );
        g_api->append_resp_body(session, LUA_ERRSTR_SCRIPT,
                                strlen(LUA_ERRSTR_SCRIPT));
        g_api->end_resp(session);
        return 0;
    }

    // run_ls_lua_fn should be on the stack now.
    if (LsLuaApi::type(L, -1) != LUA_TFUNCTION)
    {
        g_api->log(session, LSI_LOG_ERROR, "%s\n", LUA_ERRSTR_SCRIPT);
        g_api->append_resp_body(session, LUA_ERRSTR_SCRIPT,
                                strlen(LUA_ERRSTR_SCRIPT));
        g_api->end_resp(session);
        return 0;
    }
    LsLuaApi::getglobal(L, LS_LUA_UD);
    return LsLuaApi::resume(L, 1);
}


int LsLuaEngine::filterOut(lsi_param_t *rec, const char *pBuf, int iLen)
{
    int iWritten, iOffset = 0;
    while ((iOffset < iLen)
           && (iWritten = g_api->stream_write_next(rec, pBuf + iOffset,
                          iLen - iOffset)) > 0)
        iOffset += iWritten;
    return iOffset;
}


int LsLuaEngine::writeToNextFilter(lsi_param_t *rec,
                                   LsLuaUserParam *pUser,
                                   const char *pOut, int iOutLen)
{
    int ret, len;
    const lsi_session_t *session = rec->session;
    ls_xloopbuf_t *pBuf = pUser->getPendingBuf();
    if (pBuf && ((len = ls_xloopbuf_size(pBuf)) > 0))
    {
        ret = LsLuaEngine::filterOut(rec, ls_xloopbuf_begin(pBuf), len);
        if (ret < 0)
            return ret;
        ls_xloopbuf_popfront(pBuf, ret);

        if (ret < len)
        {
            if (pOut)
                ls_xloopbuf_append(pBuf, pOut, iOutLen);
            if (ls_xloopbuf_getnumseg(pBuf) > 1)
                ls_xloopbuf_straight(pBuf);
            *rec->flag_out = LSI_CBFO_BUFFERED;
            return 0;
        }
        assert(ls_xloopbuf_empty(pBuf));
        *rec->flag_out = 0;
    }
    if (pOut == NULL)
        return 1;

    if ((ret = LsLuaEngine::filterOut(rec, pOut, iOutLen)) == 0)
    {
        if (pBuf == NULL)
            pBuf = ls_xloopbuf_new(iOutLen - ret,
                                   g_api->get_session_pool(session));
        ls_xloopbuf_append(pBuf, pOut + ret, iOutLen - ret);
        pUser->setPendingBuf(pBuf);
        *rec->flag_out = LSI_CBFO_BUFFERED;
    }
    return 1;
}


int LsLuaEngine::runScript(const lsi_session_t *session, const char *scriptpath,
                           LsLuaUserParam *pUser, LsLuaSession **ppSession,
                           int iCurHook)
{
    int ret;
    LsLuaSession *pSandbox;
    lua_State *L;

    pSandbox = LsLuaEngine::prepState(session, scriptpath, pUser, iCurHook);
    if (pSandbox == NULL)
        return 0;
    if (ppSession)
        *ppSession = pSandbox;

    L = pSandbox->getLuaState();
    ret = LsLuaEngine::runState(session, pSandbox, iCurHook);

    switch (ret)
    {
    case 0:
        if (iCurHook == LSLUA_HOOK_HANDLER)
        {
            if (LsLuaApi::jitMode())
                LsLuaApi::getglobal(L, "handle");
            else
            {
                LsLuaApi::getglobal(L, LS_LUA_BOX);
                LsLuaApi::getfield(L, -1, "handle");
            }
            if (LsLuaApi::type(L, -1) == LUA_TFUNCTION)
            {
                LsLuaApi::getglobal(L, LS_LUA_UD);
                ret = LsLuaEngine::resumeNcheck(pSandbox, 1);
                break;
            }
            LsLuaApi::pop(L, 1);
            // Fall through
        }
        else // Rewrite/filter
        {
            if ((LsLuaApi::gettop(L) != 0)
                && (LsLuaApi::type(L, 1) == LUA_TNUMBER))
                ret = LsLuaApi::tointeger(L, 1);
            break;
        }
        //fall through
    default:
        ret = LsLuaEngine::checkResume(pSandbox, ret);
        break;
    }
    return ret;
}


int LsLuaEngine::runFilterScript(lsi_param_t *rec,
                                 const char *scriptpath,
                                 LsLuaUserParam *pUser,
                                 LsLuaSession **ppSession,
                                 int iCurHook)
{
    int ret, len;
    LsLuaSession *pSandbox;
    const lsi_session_t *session = rec->session;

    if ((ret = LsLuaEngine::writeToNextFilter(rec, pUser, NULL, 0)) != 1)
        return ret;
    if (rec->ptr1 == NULL)
        return 0;
    pSandbox = LsLuaEngine::prepState(session, scriptpath, pUser, iCurHook);
    if (pSandbox == NULL)
        return 0;
    if (ppSession)
        *ppSession = pSandbox;

    pSandbox->setModParam(rec);
    len = rec->len1;

    if ((ret = LsLuaEngine::runState(session, pSandbox, iCurHook)) != 0)
        return LsLuaEngine::checkResume(pSandbox, ret);

    if (pSandbox->isFlagSet(LLF_TRYSENDRESP))
        pSandbox->clearFlag(LLF_TRYSENDRESP);
    else
        LsLuaEngine::writeToNextFilter(rec, pUser, (const char *)rec->ptr1,
                                       len);
    if (pSandbox->isFlagSet(LLF_LUADONE))
        return LS_FAIL; // Truncate the response.
    return len;
}


lua_State *LsLuaEngine::newLuaConnection()
{
    return LsLuaApi::newstate();
}


lua_State *LsLuaEngine::newLuaThread(lua_State *L)
{
    return LsLuaApi::newthread(L);
}


lua_State *LsLuaEngine::injectLsiapi(lua_State *L)
{
    extern int LsLuaCppFuncSetup(lua_State *);
    lua_State *pState;

    pState = L ? L : LsLuaApi::newstate();
    if (pState)
    {
        LsLuaApi::openlibs(pState);
        LsLuaCppFuncSetup(pState);
    }
    return pState;
}

extern lsi_config_key_t myParam[];
static int setFileHook(int index, module_param_info_t *param,
                       LsLuaUserParam *pUser, const char *name)
{
    struct stat st;
    if (g_api->get_file_stat(NULL, param->val, param->val_len, &st) != 0)
    {
        g_api->log(NULL, LSI_LOG_ERROR,
                   "Lua parseParam: %s invalid.",
                   myParam[param->key_index].config_key);
        return -1;
    }
    
    pUser->setFilterPath(index, param->val, param->val_len);
    g_api->log(NULL, LSI_LOG_NOTICE,
               "%s LUA SET %s = %.*s\n",
               name,
               myParam[param->key_index].config_key,
               (int)param->val_len,
               param->val
              );
    return 0;
}

void *LsLuaEngine::parseParam(module_param_info_t *param, int param_count,
                              void *initial_config, int level,
                              const char *name)
{
    int sec, line;
    char *cp;
    LsLuaUserParam *pParent = (LsLuaUserParam *)initial_config;
    LsLuaUserParam *pUser = new LsLuaUserParam(level);

    if ((pUser == NULL) || (!pUser->isReady()))
    {
        g_api->log(NULL, LSI_LOG_ERROR, "LUA PARSEPARAM NO MEMORY");
        return NULL;
    }
    if (pParent)
        *pUser = *pParent;

    if (param == NULL || param_count <= 0)
    {
        s_iFirstTime = 0;
        return pUser;
    }

    
    for (int i=0; i<param_count; ++i)
    {
        switch(param[i].key_index)
        {
        case 0:
            //"luarewritepath"
            if (s_iFirstTime)
                setFileHook(LSLUA_HOOK_REWRITE, &param[i], pUser, name);
            break;
        case 1:
            //"luaauthpath"
            if (s_iFirstTime)
                setFileHook(LSLUA_HOOK_AUTH, &param[i], pUser, name);
            break;
        case 2:
            //"luaheaderfilterpath"
            if (s_iFirstTime)
                setFileHook(LSLUA_HOOK_HEADER, &param[i], pUser, name);
            break;
        case 3:
            //"luabodyfilterpath"
            if (s_iFirstTime)
                setFileHook(LSLUA_HOOK_BODY, &param[i], pUser, name);
            break;

        case 4:
            //luapath
            if (s_iFirstTime)
            {
                if ((cp = strndup(param[i].val, param[i].val_len)) != NULL)
                {
                    if (s_pLuaPath)
                        free(s_pLuaPath);
                    s_pLuaPath = cp;
                }
                g_api->log(NULL, LSI_LOG_NOTICE,
                   "%s LUA SET %s = %.*s [%s]\n", name,
                       myParam[param[i].key_index].config_key,
                       (int)param[i].val_len,
                       param[i].val,
                       s_pLuaPath ? s_pLuaPath : s_pSysLuaPath);
            }
            break;
        case 5:
            //"lib"
            if (s_iFirstTime)
            {
                if ((cp = strndup(param[i].val, param[i].val_len)) != NULL)
                {
                    if (s_pLuaLib)
                        free(s_pLuaLib);
                    s_pLuaLib = cp;
                }
                g_api->log(NULL, LSI_LOG_NOTICE,
                   "%s LUA SET %s = %.*s [%s]\n", name,
                       myParam[param[i].key_index].config_key,
                       param[i].val_len,
                       param[i].val,
                       s_pLuaLib ? s_pLuaLib : "NULL");
            }
            break;

        case 6:
            //"maxruntime"
            if ((sec = strtol(param[i].val, NULL, 0)) > 0)
            {
                if (s_iFirstTime)
                    s_iMaxRunTime = sec;
                pUser->setMaxRunTime(sec);
            }
            g_api->log(NULL, LSI_LOG_NOTICE,
                       "%s LUA SET %s = %.*s msec [%d %s]\n", name,
                       myParam[param[i].key_index].config_key,
                       param[i].val_len,
                       param[i].val,
                       pUser->getMaxRunTime(),
                       pUser->getMaxRunTime() ? "ENABLED" : "DISABLED");
            break;
            
        case 7:
            //"maxlinecount"
            if ((line = strtol(param[i].val, NULL, 0)) >= 0)
            {
                if (s_iFirstTime)
                    s_iMaxLineCount = line;
                pUser->setMaxLineCount(line);
            }
            g_api->log(NULL, LSI_LOG_NOTICE,
                       "%s LUA SET %s = %.*s [%d %s]\n", name,
                       myParam[param[i].key_index].config_key,
                       param[i].val_len,
                       param[i].val,
                       pUser->getMaxLineCount(),
                       pUser->getMaxLineCount() ? "ENABLED" : "DISABLED");
            break;
            
        case 8:
            //"jitlinemod"
            if ((line = strtol(param[i].val, NULL, 0)) > 0)
                s_iJitLineMod = line;
            g_api->log(NULL, LSI_LOG_NOTICE,
                       "%s LUA SET %s = %.*s [%d]\n", name,
                       myParam[param[i].key_index].config_key,
                       param[i].val_len,
                       param[i].val,
                       s_iJitLineMod);
            break;
            
        case 9:
            //"pause"
            if ((sec = strtol(param[i].val, NULL, 0)) > 0)
                s_iPauseTime = sec;
            g_api->log(NULL, LSI_LOG_NOTICE,
                       "%s LUA SET %s = %.*s [%d]\n", name,
                       myParam[param[i].key_index].config_key,
                       param[i].val_len,
                       param[i].val,
                       s_iPauseTime);
        break;
        }
    }

    s_iFirstTime = 0;
    return (void *)pUser;
}


void LsLuaEngine::removeParam(void *config)
{
    g_api->log(NULL, LSI_LOG_DEBUG, "REMOVE PARAMETERS [%p]\n", config);
    if (s_pLuaLib)
    {
        free(s_pLuaLib);
        s_pLuaLib = NULL;
    }
}


int LsLuaEngine::execLuaCmd(const char *cmd)
{
    lua_State *L;

    if ((L = LsLuaApi::newthread(s_pSystemState)) == NULL)
        return LS_FAIL;

    if (LsLuaApi::compileLuaCmd(L, cmd) != 0)
    {
        LsLuaApi::close(L);
        return LS_FAIL;
    }
    LsLuaApi::resume(L, 0);
    return 0;
}


//
//  Test driver
//
int LsLuaEngine::testCmd()
{
    static int loopCount = 0;

    ++loopCount;
    switch (loopCount)
    {
    case 1: // Testing dual socket
        execLuaCmd(
            "print('ls=', ls) "
            "local sock,err =ls.socket.tcp() print('sock.tcp=', sock) "
            "local code,err = sock:connect('61.135.169.125', 80) "
            "if code == 1 then "
            "  print ('FIRST  sock.connect = ', sock) "
            "    local ysock, err = ls.socket.tcp() print('sock.tcp=', ysock) "
            "    local code,err = ysock:connect('61.135.169.125', 80)"
            "    if code == 1 then "
            "      print ('SECOND sock.connect = ', ysock) "
            "      sock:send('GET /index.php HTTP/1.0\\r\\n\\r\\n') "
            "      ysock:send('GET /index.php HTTP/1.0\\r\\n\\r\\n') "
            "      y = '' "
            "      while y ~= nil do "
            "        y, err = ysock:receive() ls.puts(y) "
            "      end "
            "      code,err = ysock:close() print('close ', code, str) "
            "    else "
            "      ls.puts('SECOND CONNECTION FAILED') "
            "      ls.puts(err) "
            "    end "
            "  y = '' "
            "  while y ~= nil do "
            "    y = sock:receive() ls.puts(y) "
            "  end "
            "  ls.puts('BYE LiteSpeed') "
            "  sock:close() "
            "  code,err = sock:close() print('close ', code, str) "
            "else "
            "  ls.puts('BYE CONNECTION FAILED') "
            "  ls.puts(err) "
            "end "
            "print('collectgarbage=', collectgarbage('count')*1024) "
            "ls.exit(0)"
        );
        break;
    case 4:
        execLuaCmd(
            "print('ls=', ls) "
            "function sockproc() "
            "  local sock "
            "    sock = ls.socket.tcp() print('sock.tcp=', sock) "
            "  local code, err "
            "    code, err = sock:connect('61.135.169.125', 80) "
            "  if code == 1 then "
            "    sock:send('GET /index.php HTTP/1.0\\r\\n\\r\\n') "
            "    y = '' "
            "    while y ~= nil do "
            "        y = sock:receive() ls.puts(y) "
            "    end "
            "  code,err = sock:close() print('close ', code, str) "
            "  ls.puts('BYE LiteSpeed') "
            "  else "
            "     ls.puts('ERROR CONNECTION FAILED') "
            "     ls.puts(err) "
            "  end "
            "end "
            "sockproc()"
            "print('collectgarbage=', collectgarbage('count')*1024)"
            " collectgarbage() "
            "print('collectgarbage=', collectgarbage('count')*1024)"
            "ls.exit(0) "
        );
        break;
    default:
        break;
    }
    return 0;
}


LsLuaFuncMap *LsLuaFuncMap::s_pMap = {NULL};
int LsLuaFuncMap::s_iMapCnt = 0;


int LsLuaFuncMap::loadLuaScript(const lsi_session_t *session, lua_State *L,
                                const char *scriptName)
{
    LsLuaFuncMap *p;

    for (p = s_pMap; p != NULL; p = p->m_pNext)
    {
        if (strcmp(scriptName, p->scriptName()) == 0)
        {
            struct stat scriptStat;
            if (stat(scriptName, &scriptStat) == 0)
            {
                if ((scriptStat.st_mtime == p->m_stat.st_mtime)
                    && (scriptStat.st_ino == p->m_stat.st_ino)
                    && (scriptStat.st_size == p->m_stat.st_size))
                {
                    p->loadLuaFunc(L);
                    return 0;
                }
                // File was changed, reload new script.
                p->unloadLuaFunc(L);
                p->remove();
                delete p;

                return loadLuaScript(session, L, scriptName);
            }
            p->loadLuaFunc(L);
            return 0;
        }
    }
    p = new LsLuaFuncMap(session, L, scriptName);
    if (p->isReady())
    {
        g_api->log(session, LSI_LOG_NOTICE,
                   "LUA LOAD FROM SRC SAVED TO CACHE %s\n", scriptName);
        return 0;
    }
    else
    {
        int ret = p->m_iStatus;
        g_api->log(session, LSI_LOG_NOTICE, "LUA FAILED TO LOAD %s %d\n",
                   scriptName, ret);
        delete p;
        return ret;
    }
}


typedef struct
{
    FILE   *fp;
    char    buf[F_PAGESIZE];
    size_t  size;
    int     state;          // 0 - not ready, 1 - begin, 2 - data, 3 - end
} luaFile_t;


LsLuaFuncMap::LsLuaFuncMap(const lsi_session_t *session, lua_State *L,
                           const char *scriptName)
{
    char funcName[0x100];
    int ret;
    int top;
    luaFile_t   loadData;

    if (s_iMapCnt == 0)
    {
        LsLuaApi::createtable(L, 0, 0);
        LsLuaApi::setglobal(L, LS_LUA_FUNCTABLE);
    }
    s_iMapCnt++;
    m_pScriptName = strdup(scriptName);
    snprintf(funcName, 0x100, "x%07d", s_iMapCnt);
    m_pFuncName = strdup(funcName);
    m_iStatus = 0;

    top = LsLuaApi::gettop(L);
    if ((loadData.fp = fopen(m_pScriptName, "r")) == NULL)
    {
        m_iStatus = -1;
        goto errout;
    }
    loadData.size = sizeof(loadData.buf);
    loadData.state = 1;

    stat(m_pScriptName, &m_stat);

    ret = LsLuaApi::load(L, textFileReader, (void *)&loadData,
                         m_pScriptName, NULL);
    fclose(loadData.fp);
    if (ret)
    {
        size_t len;
        const char *cp = LsLuaApi::tolstring(L, top + 1, &len);
        if ((cp != NULL) && (len != 0))
            g_api->append_resp_body(session, cp, len);
        if (ret == LUA_ERRSYNTAX)
            m_iStatus = -2;
        else
            m_iStatus = -3;
        goto errout;
    }
    if (LsLuaApi::type(L, -1) != LUA_TFUNCTION)
        goto errout;

    LsLuaApi::getglobal(L, LS_LUA_FUNCTABLE);
    LsLuaApi::pushstring(L, m_pFuncName);
    LsLuaApi::pushvalue(L, -3);
    LsLuaApi::settable(L, -3);
    LsLuaApi::pop(L, 1);
    add();

    m_iStatus = 1;
    return;
errout:
    LsLuaApi::dumpStack(L, "ERROR: LOADSCRIPT FAILED", 10);
    LsLuaApi::settop(L, top);
    g_api->append_resp_body(session, LUA_ERRSTR_SCRIPT,
                            strlen(LUA_ERRSTR_SCRIPT));
}


LsLuaFuncMap::~LsLuaFuncMap()
{
    if (m_pScriptName)
        free(m_pScriptName);
    if (m_pFuncName)
        free(m_pFuncName);
    m_iStatus = 0;
}


void LsLuaFuncMap::loadLuaFunc(lua_State *L)
{
    LsLuaApi::getglobal(L, LS_LUA_FUNCTABLE);
    LsLuaApi::getfield(L, -1, m_pFuncName);
    LsLuaApi::remove(L, -2);
}


void LsLuaFuncMap::unloadLuaFunc(lua_State *L)
{
    LsLuaApi::getglobal(L, LS_LUA_FUNCTABLE);
    LsLuaApi::pushnil(L);
    LsLuaApi::setfield(L, -2, m_pFuncName);
    LsLuaApi::remove(L, -1);
}


void LsLuaFuncMap::add()
{
    m_pNext = s_pMap;
    s_pMap = this;
}


void LsLuaFuncMap::remove()
{
    LsLuaFuncMap *p;

    if (this == s_pMap)
    {
        s_pMap = m_pNext;
        return;
    }

    for (p = s_pMap; p->m_pNext; p = p->m_pNext)
    {
        if (p->m_pNext == this)
        {
            p->m_pNext = m_pNext;
            return;
        }
    }
}


const char *LsLuaFuncMap::textFileReader(lua_State *L, void *d,
        size_t *retSize)
{
    luaFile_t *p_d = (luaFile_t *)d;
    switch (p_d->state)
    {
    case 1:
        *retSize = strlen(LS_LUA_BEGINSTR);
        memcpy(p_d->buf, LS_LUA_BEGINSTR, *retSize);
        p_d->state = 2;
        break;
    case 2:
        int num;
        num = fread(p_d->buf, 1, p_d->size, p_d->fp);
        if (num > 0)
            *retSize = num;
        else
        {
            *retSize = strlen(LS_LUA_ENDSTR);
            memcpy(p_d->buf, LS_LUA_ENDSTR, *retSize);
            p_d->state = 0;
        }
        break;
    default:
        *retSize = 0;
    }
    return p_d->buf;
}


ls_str_t *LsLuaUserParam::getPathBuf(int index)
{
    switch (index)
    {
    case LSLUA_HOOK_REWRITE:
        return &m_rewritePath;
    case LSLUA_HOOK_AUTH:
        return &m_authPath;
    case LSLUA_HOOK_HEADER:
        return &m_headerFilterPath;
    case LSLUA_HOOK_BODY:
        return &m_bodyFilterPath;
    default:
        return NULL;
    }
}
