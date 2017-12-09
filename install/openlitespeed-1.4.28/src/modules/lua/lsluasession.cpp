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
#include "lsluasession.h"
#include "edluastream.h"
#include "lsluaapi.h"
#include "lsluaengine.h"

#include <ls.h>
#include <lsr/ls_base64.h>
#include <lsr/ls_md5.h>
#include <lsr/ls_sha1.h>
#include <lsr/ls_str.h>
#include <lsr/ls_strtool.h>
#include <lsr/ls_xpool.h>
#include <util/httputil.h>

#include <ctype.h>
#include <time.h>
#include <stdint.h>


static void LsLuaCreateGlobal(lua_State *);

int LsLuaSession::s_iKey = 0;    // unique session key

LsLuaSession::LsLuaSession()
    : m_wait4RespBuf_L(NULL)
    , m_pHttpSession(NULL)
    , m_pState(NULL)
    , m_pStateMom(NULL)
    , m_iTop(0)
    , m_iCurHook(0)
    , m_pFilterBuf(NULL)
    , m_pEndTimer(NULL)
    , m_pMaxTimer(NULL)
    , m_pStream(NULL)
    , m_pUserParam(NULL)
    , m_pModParam(NULL)
    , m_pTimerList(NULL)
{
    m_iKey = ++s_iKey;    // noted 0 is not used
    m_iRef = LUA_REFNIL;
    clearLuaStatus();
    // add();
}


LsLuaSession::~LsLuaSession()
{
    m_iKey = 0;          // no more timer callback
    if (m_iRef != LUA_REFNIL)
    {
        LsLuaEngine::unref(this);
        m_iRef = LUA_REFNIL;
    }
    // remove();
}


void LsLuaSession::clearLuaStatus()
{
    m_iExitCode = 0;
    m_iFlags = 0;
    m_iLuaLineCount = 0;
}


void LsLuaSession::closeAllStream()
{
    LsLuaStreamData *p_data;
    // LsLuaLog( getLuaState(), LSI_LOG_NOTICE, 0, "closeAllStream HTTP %p session <%p>", getHttpSession(), this);
    for (p_data = m_pStream; p_data; p_data = p_data->next())
        p_data->close(m_pState);
}


//
//  this is slow linear search...
//  If we need performance then we need to change EdLuaStream to set reverse link.
//
void LsLuaSession::markCloseStream(lua_State *L, EdLuaStream *sock)
{
    int            n;
    LsLuaStreamData *p_data;

    // LsLuaLog( L, LSI_LOG_NOTICE, 0, "markCloseStream HTTP %p session <%p>", getHttpSession(), this);
    n = 0;
    for (p_data = m_pStream; p_data; p_data = p_data->next())
    {
        // LsLuaLog( L, LSI_LOG_NOTICE, 0, "markCloseStream item %d ", n);
        if (p_data->isMatch(sock))
        {
            LsLuaLog(L, LSI_LOG_NOTICE, 0, "markCloseStream HTTP %p session <%p> %d",
                     getHttpSession(), this, n);
            p_data->close(L);
            return;
        }
        n++;
    }
}


EdLuaStream *LsLuaSession::newEdLuaStream(lua_State *L)
{
    LsLuaSession *pSession = LsLuaGetSession(L);
    EdLuaStream **p;
    EdLuaStream *p_sock;
    if (!pSession)
        return NULL;
    if (!(p_sock = new EdLuaStream()))
        return  NULL;
    if (!(p = (EdLuaStream **)(LsLuaApi::newuserdata(L,
                               sizeof(EdLuaStream *)))))
    {
        delete p_sock;
        return NULL;
    }
    *p = p_sock;

    LsLuaStreamData *p_data = new LsLuaStreamData(p_sock, pSession->m_pStream);
    pSession->m_pStream = p_data;

    return (p_sock);
}


void LsLuaStreamData::close(lua_State *L)
{
    if (isActive())
    {
        setNotActive();
        m_pSock->forceClose(L);
    }
}
//
// @brief onWrite - call by modlua.c to indicate the resp buffer available to write
// @param[in] httpSession
// @return -1 on failure, 0 no more write, 1 more write
//
int LsLuaSession::onWrite(const lsi_session_t *httpSession)
{
    //
    // if I am waiting for it and there is buffer then process it.
    //
    if (isFlagSet(LLF_WAITRESPBUF)
        && (g_api->is_resp_buffer_available(httpSession) == 1))
    {
        clearFlag(LLF_WAITRESPBUF);   // not waiting for it anymore!
        g_api->set_handler_write_state(httpSession, 0);   // dont call me anymore!
        // Wake up
        LsLuaSession *pSession = LsLuaGetSession(m_wait4RespBuf_L);
        m_wait4RespBuf_L = NULL;
        LsLuaEngine::resumeNcheck(pSession, 0);
        return 1;
    }
    else
        return 1;
}


int LsLuaSession::wait4RespBuffer(lua_State *L)
{
    setFlag(LLF_WAITRESPBUF);                 // enable callback
    g_api->set_handler_write_state(getHttpSession(), 1);   // start to call me
    m_wait4RespBuf_L = L;
    return LsLuaApi::yield(L, 0);
}


//
//  static callback for general purpose LsLuaSession Timer
//
void LsLuaSession::timerCb(const void *data)
{
    LsLuaTimerData   *_data = (LsLuaTimerData *)data;

    LsLuaLog(_data->session()->getLuaState(), LSI_LOG_DEBUG, 0
             , "SESSION timerCb [%p] HTTP %p session %p key %d id %d"
             , _data->session()->getLuaState()
             , _data->session()->getHttpSession()
             , _data->session()
             , _data->key()
             , _data->id()
            );

    // remove from the list...
    _data->session()->rmTimerFromList(_data);

    // checking the key is to make sure we are not attemping to use recycling data
    if ((!_data->flag()) && (_data->key() == _data->session()->key())
        && _data->session()->getLuaState())
        _data->timerCallBack();
    delete _data;
}


//
//  reach User specified endtime - forcely abort here
//
void LsLuaSession::maxRunTimeCb(LsLuaSession *pSession, lua_State *L)
{
    LsLuaLog(L, LSI_LOG_NOTICE, 0,
             "SESSION maxRunTimeCb [%p] HTTP %p session <%p>",
             pSession->getLuaState(), pSession->getHttpSession(),
             pSession);

    LsLuaSession::endSession(pSession);
    pSession->m_pMaxTimer = NULL; // remove myself from check
}


void LsLuaSession::luaLineLooper(LsLuaSession *pSession, lua_State *L)
{
    if (LsLuaEngine::debug() & 0x10)
        LsLuaSession::trace("LINELOOPER", pSession, L);
    pSession->clearFlag(LLF_WAITLINEEXEC);          // enable further again
    LsLuaEngine::resumeNcheck(pSession, 0);
}


void LsLuaSession::luaLineHookCb(lua_State *L, lua_Debug *ar)
{
    // NOTE - since I don't use multiple hookflag point - dont need to check
    // if (ar->event == LUA_HOOKLINE)
    // if (ar->event == LUA_HOOKCOUNT)
    {
        LsLuaSession *pSession;
        if ((pSession = LsLuaGetSession(L)))
        {
            if ((!pSession->getLuaCounter()) && LsLuaApi::jitMode())
            {
                // JIT ignore first hook...
                pSession->upLuaCounter();
                return;
            }
            pSession->upLuaCounter();
            if (!pSession->isFlagSet(LLF_WAITLINEEXEC))
            {
                LsLuaLog(L, LSI_LOG_DEBUG, 0,
                         "SESSION linehook [%p] HTTP %p session <%p> %d",
                         pSession->getLuaState(), pSession->getHttpSession(),
                         pSession, pSession->getLuaCounter());
                pSession->setFlag(LLF_WAITLINEEXEC);          // disable further
                pSession->setTimer(LsLuaEngine::getPauseTime(),
                                   LsLuaSession::luaLineLooper, L,
                                   SET_TIMER_NORMAL);

                LsLuaApi::yield(L, 0);
            }
#if 0 // FOR JIT it is possible to have thing running... so don't brother to send information out
            else
            {
                LsLuaLog(L, LSI_LOG_NOTICE, 0,
                         "ERROR: SESSION IGNORE luahook callback [%p] HTTP %p session <%p> %d",
                         pSession->getLuaState(), pSession->getHttpSession(),
                         pSession, pSession->getLuaCounter());
            }
#endif
        }
    }
}


void LsLuaSession::setTimer(int msec, pf_sleeprestart f, lua_State *L,
                            int flag)
{
    LsLuaTimerData   *data = new LsLuaTimerData(this, f, L);

    data->setId(g_api->set_timer(msec, 0, timerCb, data));
    LsLuaLog(L, LSI_LOG_DEBUG, 0
             , "setTimer %p session <%p> <%d msec> id %d"
             , getHttpSession(), this, msec, data->id());

    switch (flag)
    {
    case SET_TIMER_ENDDELAY:
        m_pEndTimer = data;
        break;
    case SET_TIMER_MAXRUNTIME:
        m_pMaxTimer = data;
        break;
    case SET_TIMER_NORMAL:
        addTimerToList(data);
    }
}


void LsLuaSession::releaseTimer()
{
    releaseTimerList();

    if (m_pMaxTimer)
    {
        LsLuaLog(getLuaState(), LSI_LOG_DEBUG, 0
                 , "REMOVE maxTimer %p %d"
                 , this
                 , m_pMaxTimer->id());

        m_pMaxTimer->setFlag(1);
        g_api->remove_timer(m_pMaxTimer->id());
        delete m_pMaxTimer;
        m_pMaxTimer = NULL;
    }

    if (m_pEndTimer)
    {
        LsLuaLog(getLuaState(), LSI_LOG_DEBUG, 0
                 , "REMOVE endTimer %p %d"
                 , this
                 , m_pEndTimer->id());

        m_pEndTimer->setFlag(1);
        g_api->remove_timer(m_pEndTimer->id());
        delete m_pEndTimer;
        m_pEndTimer = NULL;
    }

}


//
//  Add normal LUA timer to session list
//
void LsLuaSession::addTimerToList(LsLuaTimerData *pTimerData)
{
    pTimerData->setNext(m_pTimerList);
    m_pTimerList = pTimerData;

#if 0
    char buf[0x100];
    snprintf(buf, 0x100, "addTimerToList ADD %3d next %p", pTimerData->id(),
             pTimerData->next());
    dumpTimerList(buf);
#endif
}


//
//  remove normal LUA timer from session list
//
void LsLuaSession::rmTimerFromList(LsLuaTimerData *pTimerData)
{
    LsLuaTimerData *pTimerList;
    LsLuaTimerData *pNext;

#if 0
    char buf[0x100];
    snprintf(buf, 0x100, "rmTimerFromList REMOVE %3d next %p",
             pTimerData->id(),
             pTimerData->next());
#endif
    if ((pTimerList = m_pTimerList))
    {
        if (pTimerData == pTimerList)
        {
            m_pTimerList = pTimerData->next();
            pTimerData->setNext(NULL);
#if 0
            dumpTimerList(buf);
#endif
            return;
        }
        while ((pNext = pTimerList->next()))
        {
            if (pNext == pTimerData)
            {
                pTimerList->setNext(pTimerData->next());
                pTimerData->setNext(NULL);
#if 0
                dumpTimerList(buf);
#endif
                return;
            }
            pTimerList = pNext;
        }
    }
}


void LsLuaSession::releaseTimerList()
{
    LsLuaTimerData *pList;
    LsLuaTimerData *pNext;

#if 0
    LsLuaLog(getLuaState(), LSI_LOG_NOTICE, 0
             , "%s"
             , "RELEASE TIMERLIST");
#endif
    for (pList = m_pTimerList; pList; pList = pNext)
    {
#if 0
        LsLuaLog(getLuaState(), LSI_LOG_NOTICE, 0
                 , "REMOVE TIMER [%3d] next %3d flag %d"
                 , pList->id(), pList->key(), pList->flag());
#endif

        pNext = pList->next();
        g_api->remove_timer(pList->id());
        delete pList;
        pList = pNext;
    }
    m_pTimerList = NULL;
}


void LsLuaSession::dumpTimerList(const char *tag)
{
    LsLuaTimerData *pList;

    LsLuaLog(getLuaState(), LSI_LOG_NOTICE, 0
             , "DUMPTIMERLIST %s"
             , tag);
    for (pList = m_pTimerList; pList; pList = pList->next())
    {
        LsLuaLog(getLuaState(), LSI_LOG_NOTICE, 0
                 , "TIMER-ITEM [%3d] next %3d flag %d"
                 , pList->id(), pList->key(), pList->flag());
    }
}


//
//  RESUME LUA SESSION
//
void LsLuaSession::resume(lua_State *L, int nargs)
{
    if (isFlagSet(LLF_WAITREQBODY))
    {
        clearFlag(LLF_WAITREQBODY);
        LsLuaEngine::resumeNcheck(this, nargs);
        return;
    }
}


int LsLuaSession::setupLuaEnv(lua_State *L, LsLuaUserParam *pUser)
{
    // it has been initialized
    if (m_pState)
        return 0;
    // 1. create coroutine for this session,
    if (!(m_pState = LsLuaApi::newthread(L)))
        return LS_FAIL;

    // 2. Inherit system level injected APIs if in jit mode.
    LsLuaCreateGlobal(m_pState);

    // 3. create global varaible instance for "ls"
    //    this refers to this LsLuaSession object
    if (LsLuaSetSession(m_pState, this))
        return LS_FAIL;

    setUserParam(pUser);

    // track my mom state
    m_pStateMom = L;
    if (LsLuaEngine::debug() & 0x10)
        LsLuaSession::trace("SETUP", this, m_pState);

    // maxruntime
    if (pUser->getMaxRunTime() > 0)
    {
        setTimer(pUser->getMaxRunTime(), LsLuaSession::maxRunTimeCb, m_pStateMom,
                 SET_TIMER_MAXRUNTIME);
        LsLuaLog(L, LSI_LOG_DEBUG, 0
                 , "HTTP %p session <%p> MAX RUNTIME SET TO <%d msec>"
                 , getHttpSession(), this, pUser->getMaxRunTime());
    }

    //
    // setup maxlinecount - this will the code slower but the server will be a lot happier
    //
    if (pUser->getMaxLineCount() > 0)
    {
        int ret;
        //
        // NOTE - the behavior is different between 5.2 and JIT 2
        //          The JIT doesn't use MASKLINE too well!

        //  Hack - jit mode will divid the counter by 1000000
        //
        int linecount = 0;
        linecount = pUser->getMaxLineCount();
        if ((LsLuaApi::jitMode()) && (LsLuaEngine::getJitLineMod() > 1))
            linecount = pUser->getMaxLineCount() / LsLuaEngine::getJitLineMod();

        ret = LsLuaApi::sethook(getLuaState(),
                                LsLuaSession::luaLineHookCb,
                                // LUA_MASKCOUNT | LUA_MASKLINE,
                                LUA_MASKCOUNT,
                                linecount
                               );

        // LUA_MASKLINE, LsLuaEngine::getMaxLineCount() );
        if (ret != 1)
        {
            LsLuaLog(L, LSI_LOG_NOTICE, 0
                     , "PROBLEM SETHOOK %d HTTP %p <%p> MAX RUNTIME TO <%d msec>"
                     , ret, getHttpSession(), this, pUser->getMaxLineCount());
        }
    }
    return 0;
}


LsLuaSession *LsLuaSession::getSelf(lua_State *L)
{
//     LsLuaApi::checkudata( L, 1, LS_LUA_UDMETA );
    if (LsLuaApi::type(L, 1) == LUA_TUSERDATA)
        LsLuaApi::remove(L, 1);
    return LsLuaGetSession(L);
}


//
//  Meta to track LsLuaSession
//
static int LsLuaSessionToString(lua_State *L)
{
    char    buf[0x100];

    snprintf(buf, 0x100, "<ls %p>", L);
    LsLuaApi::pushstring(L, buf);
    return 1;
}


typedef struct ls_luasess_s
{
    LsLuaSession   *pSession;
    int             active;
    int             key;
} ls_luasess_t;


static int LsLuaSessionGc(lua_State *L)
{
    if (LsLuaEngine::debug() & 0x10)
    {
        ls_luasess_t *p;
        if ((p = (ls_luasess_t *)LsLuaApi::touserdata(L, -1)))
        {
            LsLuaLog(L, LSI_LOG_NOTICE, 0
                     , "<LsLuaSessionGc %p [%d %d]>"
                     , p->pSession, p->active, p->key);

            LsLuaSession *pSession = p->pSession;
            if (p->active && (p->key == pSession->key()))
            {
                LsLuaLog(L, LSI_LOG_NOTICE, 0
                         , "<LsLuaSessionGc RELEASE ACTIVE %p [%d]>"
                         , pSession, p->key);
            }
        }
        else
            LsLuaLog(L, LSI_LOG_NOTICE, 0, "<ls.session GC>");
    }
    return 0;
}


void LsLuaCreateSessionmeta(lua_State *L)
{
    LsLuaApi::newmetatable(L, LSLUA_SESSION_META);        // meta
    LsLuaApi::pushcclosure(L, LsLuaSessionGc, 0);       // meta func
    LsLuaApi::setfield(L, -2, "__gc");                    // meta
    LsLuaApi::pushcclosure(L, LsLuaSessionToString, 0);   // meta func
    LsLuaApi::setfield(L, -2, "__tostring");              // meta
    LsLuaApi::pop(L, 1);
}


LsLuaSession   *LsLuaGetSession(lua_State *L)
{
    ls_luasess_t *p;
    LsLuaSession *pSession = NULL;

    // pSession = LsLuaSession::findByLuaState(L);
    // if (!pSession)
    {
        LsLuaApi::getglobal(L, "__ls_session");
        // pSession = ( LsLuaSession *)LsLuaApi::touserdata(L, -1);
        if ((p = (ls_luasess_t *)LsLuaApi::touserdata(L, -1)))
            pSession = p->pSession;
        else
            LsLuaLog(L, LSI_LOG_NOTICE, 0, "getsession FAILED %p n <%p>", L);
        LsLuaApi::pop(L, 1);
    }
    return pSession;
}


static void LsLuaClearSession(lua_State *L)
{
    ls_luasess_t *p;
    LsLuaApi::getglobal(L, "__ls_session");
    if ((p = (ls_luasess_t *)LsLuaApi::touserdata(L, -1)))
    {
        p->active = 0;
        p->pSession = NULL;
        LsLuaApi::pop(L, 1);
    }
}


int LsLuaSetSession(lua_State *L, LsLuaSession *pSession)
{
    ls_luasess_t *p;
    if (!(p = (ls_luasess_t *)(LsLuaApi::newuserdata(L,
                               sizeof(ls_luasess_t)))))
        return LS_FAIL;
    p->pSession = pSession;
    p->active = pSession->isFlagSet(LLF_LUADONE) ? 0 : 1;
    p->key = pSession->key();
    // LsLuaApi::pushlightuserdata(L, pSession);
    LsLuaApi::getfield(L, LSLUA_REGISTRYINDEX, LSLUA_SESSION_META);
    LsLuaApi::setmetatable(L, -2);
    LsLuaApi::setglobal(L, "__ls_session");
    return 0;
}


typedef struct ls_lualog_s
{
    LsLuaSession *_pLuaSession;
    lua_State     *_L;
    int            _level;
} ls_lualog_t;


int LsLuaLogFlush(void *param, const char *pBuf, int len, int *flag)
{
    ls_lualog_t *pLog = (ls_lualog_t *)param;
    if (pLog->_pLuaSession && pLog->_pLuaSession->getHttpSession())
    {
        const lsi_session_t *pSess = pLog->_pLuaSession->getHttpSession();
        if (!(*flag & LSLUA_PRINT_FLAG_ADDITION))
            g_api->log(pSess, pLog->_level, "[%p] [LUA] ", pSess);
        g_api->lograw(pSess, pBuf, len);
    }
    else
    {
        if (!(*flag & LSLUA_PRINT_FLAG_ADDITION))
            LsLuaLog(pLog->_L, pLog->_level, 1, "");
        LsLuaLogRawbuf(pBuf, len);
    }
    return 0;
}


int  LsLuaLogEx(lua_State *L, int level)
{
    LsLuaSession *p_req = LsLuaGetSession(L);
    ls_lualog_t log_param = { p_req, L, level };
    ls_luaprint_t stream = { &log_param, LsLuaLogFlush, LSLUA_PRINT_FLAG_LF, {0, 0, 0} };
    LsLuaPrint(L, &stream);
    return 0;
}


static int  LsLuaSessLog(lua_State *L)
{
    int level;
    level = LsLuaApi::tointeger(L, 1);
    LsLuaApi::remove(L, 1);
    return LsLuaLogEx(L, level);
}


//
//  For Internal debugging purpose
//
static int  LsLuaSessDebug(lua_State *L)
{
    size_t n;
    LsLuaSession *pSession = LsLuaGetSession(L);
    const char *cp = LsLuaApi::tolstring(L, 1, &n);
    if (cp && n)
    {
        if (!strncmp(cp, "hookcount", 9))
        {
            LsLuaApi::pushinteger(L, pSession->getLuaCounter());
            return 1;
        }
        if (!strncmp(cp, "lua", 3))
        {
            const char *cmd = LsLuaApi::tolstring(L, 2, &n);
            if (cmd)
            {
                if (LsLuaApi::execLuaCmd(L, cmd))
                    return LsLuaApi::userError(L, "debug", "Exec failed.");
                else
                {
                    LsLuaApi::pushinteger(L, 0);
                    return 1;
                }
            }
            else
                return LsLuaApi::userError(L, "debug", "Bad Command");
        }
        else
            return LsLuaApi::userError(L, "debug", "Bad input");
    }
    //
    // default show hookcount
    //
    LsLuaApi::pushinteger(L, pSession->getLuaCounter());
    return 1;
}


int LsLuaRespBodyFlush(void *param, const char *pBuf, int len, int *flag)
{
    LsLuaSession *pSession = (LsLuaSession *)param;
    if (pSession && pSession->getHttpSession())
    {
        const lsi_session_t *pHttpSess = pSession->getHttpSession();
        if (pHttpSess)
            if (g_api->append_resp_body(pHttpSess, pBuf, len) == -1)
                return LS_FAIL;
    }
    else
        return LS_FAIL;

    return 0;
}


//
//  The last place when I remove all the LUA and LsLuaSession
//
static inline void killThisSession(LsLuaSession *pSession)
{
    if (LsLuaEngine::debug() & 0x10)
        LsLuaSession::trace("killThisSession", pSession, NULL);
    if (pSession->getLuaStateMom())
    {
        //
        // should try to remove all socket before close
        //
        pSession->closeAllStream();

//         if (pSession->isUrlRedirected() )
//         {
//             g_api->flush( pSession->getHttpSession() );
//             g_api->end_resp( pSession->getHttpSession() );
//         }

        // Killing/disable the LUA State
//         if (LsLuaApi::jitMode)
//         {
//             if (pSession->getLuaState()
//                     && (!LsLuaEngine::loadRefX(pSession, pSession->getLuaState() )))
//             {
//                 LsLuaClearSession( pSession->getLuaState() );
//                 LsLuaEngine::unrefX( pSession );
//             }
//         }
//         else
//         {
// //            LsLuaApi::close( pSession->getLuaState() );
//             LsLuaApi::close( pSession->getLuaStateMom() );
//         }
        if (pSession->getLuaState()
            && (!LsLuaEngine::loadRef(pSession, pSession->getLuaState())))
        {
            LsLuaClearSession(pSession->getLuaState());
            LsLuaEngine::unref(pSession);
        }
        pSession->clearState();
        pSession->releaseTimer();

        delete pSession;
    }
}


//
//  Detected http end condition - abort current operation
//  This called by module handler
//
void CleanupLuaSession(const void *pHttpSession, LsLuaSession *pSession)
{
    // LsLuaSession *  pSession = LsLuaSession::findByLsiSession( (lsi_session_t *)pHttpSession );

    if (LsLuaEngine::debug() & 0x10)
        LsLuaSession::trace("CleanupLuaSession", pSession, NULL);

    if (pSession)
    {
        if (pSession->endTimer())
            pSession->endTimer()->setFlag(1);
        if (pSession->maxRunTimer())
            pSession->maxRunTimer()->setFlag(1);

        killThisSession(pSession);
    }
    else
    {
        // Can't find corresponding session... ignore!
        ;
    }
}


//
//  LsLuaSleepResume - called from lsi_api timerCb
//  This will resume the LUA sleep call
//
static void LsLuaSleepResume(LsLuaSession *pSession, lua_State *L)
{
    if (LsLuaEngine::debug() & 0x10)
        LsLuaSession::trace("LsLuaSleepResume", pSession, L);
    if (pSession->isFlagSet(LLF_LUADONE))
    {
        LsLuaLog(L, LSI_LOG_NOTICE, 0, "RACE LsLuaSleepResume %p <%p>",
                 pSession->getLuaState(), pSession);
        return;
    }

#if 0
    if (LsLuaEngine::loadRefX(pSession, L))
    {
        LsLuaLog(L, LSI_LOG_NOTICE, 0,
                 "PROBLEM: RESUME LsLuaSleepResume %p <%p> ",
                 pSession->getLuaState(), pSession);

        g_api->append_resp_body(pSession->getHttpSession(), "ABORT LUA ERROR",
                                15);
        g_api->end_resp(pSession->getHttpSession());
        return;
    }
#endif

    //
    // 0 - the process finished...
    // LUA_YIELD - it yielded again
    //
//     int ret = LsLuaApi::resume( L, 0 );
    int ret = LsLuaEngine::resumeNcheck(pSession, 0);

#if 0
    LsLuaLog(L, LSI_LOG_NOTICE, 0,
             "RESUME LsLuaSleepResume %p <%p> %d",
             pSession->getLuaState(), pSession, ret);
#endif
    if (ret == 0)
    {
#if 0
        // the co-routine finished.
        LsLuaLog(L, LSI_LOG_NOTICE, 0,
                 "RESUME LsLuaSleepResume %p <%p> %d DONE",
                 pSession->getLuaState(), pSession, ret);
#endif
        ;
    }
    else if (ret == LUA_YIELD)
    {
#if 0
        // the co-routine yielded again.
        LsLuaLog(L, LSI_LOG_NOTICE, 0,
                 "RESUME LsLuaSleepResume %p <%p> %d YIELDED",
                 pSession->getLuaState(), pSession, ret);
#endif
        ;
    }
    else
    {
        LsLuaLog(L, LSI_LOG_NOTICE, 0,
                 "RESUME LsLuaSleepResume %p <%p> %d ERROR",
                 pSession->getLuaState(), pSession, ret);
        g_api->end_resp(pSession->getHttpSession());
    }
}


//
//
//
int LsLuaSession::endSession(LsLuaSession *pSession)
{
    if (!pSession)
        return 0;   //  avoid base session and multiple call
    if (pSession->isFlagSet(LLF_LUADONE))
        return 0;   //  avoid base session and multiple call

    // int level = LsLuaApi::tointegerx( L, 1, NULL );
    // NOTE: level is not used at the moment...
    pSession->setFlag(LLF_LUADONE);
    return 0;
}


//
// Special end inject by LiteSpeed
//
static int  LsLuaSess_End(lua_State *L)
{
    LsLuaSession *pSession = LsLuaGetSession(L);

    return LsLuaSession::endSession(pSession);
}


/**
 * Returns 1 on success, 0 and error message on failure.
 */
static int  LsLuaSessEof(lua_State *L)
{
    LsLuaSession *pSession = LsLuaGetSession(L);

    if (pSession->isFlagSet(LLF_LUADONE))
    {
        LsLuaApi::pushnil(L);
        LsLuaApi::pushstring(L, "Eof: Eof already set.");
        return 2;
    }

    pSession->setFlag(LLF_LUADONE);
    LsLuaApi::pushinteger(L, 1);
    return 1;
}


// Table index must be positive.
static int LsLuaParseQsTable(lua_State *L, int iTableIdx,
                             char *pQs, size_t &iQsLen)
{
    const char *pKey, *pVal;
    size_t iKeyLen, iValLen;
    const int iKeyOff = -2, iValOff = -1;

    iQsLen = 0;

    LsLuaApi::pushnil(L);

    while (LsLuaApi::next(L, iTableIdx) != 0)
    {
        if (LsLuaApi::type(L, iKeyOff) != LUA_TSTRING)
            return LsLuaApi::userError(L, "Parse QS Table", "QS key not a string");

        pKey = LsLuaApi::tolstring(L, iKeyOff, &iKeyLen);

        switch (LsLuaApi::type(L, iValOff))
        {
        case LUA_TNUMBER:
        case LUA_TSTRING:
            pVal = LsLuaApi::tolstring(L, iValOff, &iValLen);
            if (iQsLen + iKeyLen + iValLen + 1 >= LSLUA_SESS_MAXQSLEN)
            {
                --iQsLen;
                return 0;
            }
            iQsLen += HttpUtil::escapeQs(pKey, iKeyLen,
                                         pQs + iQsLen,
                                         LSLUA_SESS_MAXQSLEN - iQsLen);
            pQs[iQsLen++] = '=';
            iQsLen += HttpUtil::escapeQs(pVal, iValLen,
                                         pQs + iQsLen,
                                         LSLUA_SESS_MAXQSLEN - iQsLen);
            pQs[iQsLen++] = '&';
            break;
        case LUA_TBOOLEAN:
            if (!(LsLuaApi::toboolean(L, iValOff)))
            {
                LsLuaApi::pop(L, 1);
                continue;
            }
            if (iQsLen + iKeyLen >= LSLUA_SESS_MAXQSLEN)
            {
                --iQsLen;
                return 0;
            }
            iQsLen += HttpUtil::escapeQs(pKey, iKeyLen,
                                         pQs + iQsLen,
                                         LSLUA_SESS_MAXQSLEN - iQsLen);
            pQs[iQsLen++] = '&';
            break;
        case LUA_TTABLE:
            LsLuaApi::pushnil(L);
            while (LsLuaApi::next(L, iKeyOff) != 0)
            {
                switch (LsLuaApi::type(L, iValOff))
                {
                case LUA_TBOOLEAN:
                    if (!(LsLuaApi::toboolean(L, iValOff)))
                    {
                        LsLuaApi::pop(L, 1);
                        continue;
                    }
                    if (iQsLen + iKeyLen >= LSLUA_SESS_MAXQSLEN)
                    {
                        --iQsLen;
                        return 0;
                    }
                    iQsLen += HttpUtil::escapeQs(pKey, iKeyLen,
                                                 pQs + iQsLen,
                                                 LSLUA_SESS_MAXQSLEN - iQsLen);
                    pQs[iQsLen++] = '&';
                    break;
                case LUA_TNUMBER:
                case LUA_TSTRING:
                    pVal = LsLuaApi::tolstring(L, iValOff, &iValLen);
                    if (iQsLen + iKeyLen + iValLen + 1 >= LSLUA_SESS_MAXQSLEN)
                    {
                        --iQsLen;
                        return 0;
                    }
                    iQsLen += HttpUtil::escapeQs(pKey, iKeyLen,
                                                 pQs + iQsLen,
                                                 LSLUA_SESS_MAXQSLEN - iQsLen);
                    pQs[iQsLen++] = '=';
                    iQsLen += HttpUtil::escapeQs(pVal, iValLen,
                                                 pQs + iQsLen,
                                                 LSLUA_SESS_MAXQSLEN - iQsLen);
                    pQs[iQsLen++] = '&';
                    break;
                default:
                    return LsLuaApi::userError(L, "Parse QS", "QS Value Table's value "
                                               "is an invalid value type.");
                }
                LsLuaApi::pop(L, 1);
            }
            break;
        default:
            return LsLuaApi::userError(L, "Parse QS", "Invalid QS Value type.");
        }
        LsLuaApi::pop(L, 1);
    }
    if (iQsLen)
        --iQsLen;
    return 0;
}


static int LsLuaGetQs(lua_State *L, int iQsOff, char *pQs, size_t &iQsLen)
{
    const char *ptr;
    switch (LsLuaApi::type(L, iQsOff))
    {
    case LUA_TNUMBER:
    case LUA_TSTRING:
        ptr = LsLuaApi::tolstring(L, iQsOff, &iQsLen);
        memmove(pQs, ptr, iQsLen);
        break;
    case LUA_TTABLE:
        return LsLuaParseQsTable(L, iQsOff, pQs, iQsLen);
    default:
        return LsLuaApi::userError(L, "get_qs", "Invalid QS Type.");
    }
    return 0;
}


/**
 * The table must be the top of the stack when the function is called.
 * The table will be at the top of the stack when the function completes,
 */
static int LsLuaAddKvToTable(lua_State *L, const char *pKey, int iKeyLen,
                             const char *pVal, int iValLen)
{
    int iTableSize;
    if (LsLuaApi::type(L, -1) != LUA_TTABLE)
    {
        LsLuaLog(L, LSI_LOG_INFO, 0, "LsLuaReqInsertQs "
                 "Table not on top of stack.");
        return 0;
    }
    LsLuaApi::pushlstring(L, pKey, iKeyLen);
    LsLuaApi::pushvalue(L, -1);
    LsLuaApi::gettable(L, -3);

    if (iValLen < 0)
        LsLuaApi::pushboolean(L, 1);
    else
        LsLuaApi::pushlstring(L, pVal, iValLen);

    switch (LsLuaApi::type(L, -2))
    {
    case LUA_TNIL:
        LsLuaApi::remove(L, -2);
        break;
    case LUA_TTABLE:
        if (LsLuaApi::rawlen)
            iTableSize = LsLuaApi::rawlen(L, -2) + 1;
        else
            iTableSize = LsLuaApi::objlen(L, -2) + 1;
        LsLuaApi::rawseti(L, -2, iTableSize);
        break;
    case LUA_TBOOLEAN:
    case LUA_TNUMBER:
    case LUA_TSTRING:
        LsLuaApi::createtable(L, 2, 0);
        LsLuaApi::insert(L, -3);
        LsLuaApi::rawseti(L, -3, 2);
        LsLuaApi::rawseti(L, -2, 1);
        break;
    default:
        return LsLuaApi::serverError(L, "req_insert_qs",
                                     "The impossible happened.");
    }

    LsLuaApi::settable(L, -3);
    return 1;
}


//
//  set/get elements from header
//
extern int LsLuaHeaderSet(lua_State *);
extern int LsLuaHeaderGet(lua_State *);

static int  LsLuaReqStartTime(lua_State *L)
{
    LsLuaLog(L, LSI_LOG_NOTICE, 0, "req_start_time  not supported yet");
    return LsLuaApi::error(L, "req_start_time not supported yet");
}


static int LsLuaReqHttpVersion(lua_State *L)
{
    int iBufSize = TMPBUFSIZE;
    char aTmpBuf[TMPBUFSIZE];
    LsLuaSession *pSession = LsLuaGetSession(L);
    iBufSize = g_api->get_req_var_by_id(pSession->getHttpSession(),
                                        LSI_VAR_SERVER_PROTO,
                                        aTmpBuf, iBufSize);
    if (iBufSize != 0)
        LsLuaApi::pushlstring(L, aTmpBuf, iBufSize);
    else
        LsLuaApi::pushnil(L);
    return 1;
}


static int LsLuaReqRawHeader(lua_State *L)
{
    int iHeadersLen;
    char *pHeaders;
    LsLuaSession *session = LsLuaGetSession(L);
    const lsi_session_t *pSession = session->getHttpSession();
    iHeadersLen = g_api->get_req_raw_headers_length(pSession);
    pHeaders = (char *)ls_xpool_alloc(g_api->get_session_pool(pSession),
                                      iHeadersLen);
    g_api->get_req_raw_headers(pSession, pHeaders, iHeadersLen);
    LsLuaApi::pushlstring(L, pHeaders, iHeadersLen);
    return 1;
}


static int LsLuaReqClearHeader(lua_State *L)
{
    int    avail;
    avail = LsLuaApi::gettop(L);
    if (avail < 1)
    {
        // nothing to do
        return 0;
    }
    // pop the rest of junk from stack
    if (avail > 1)
        LsLuaApi::pop(L, avail - 1);
    // LsLuaApi::getglobal(L, "ls.header"); // This wont work use nil instead
    LsLuaApi::pushnil(L);
    LsLuaApi::insert(L, -2);
    LsLuaApi::pushnil(L);
    return LsLuaHeaderSet(L);
}


static int LsLuaReqSetHeader(lua_State *L)
{
    int    avail;
    avail = LsLuaApi::gettop(L);
    if (avail < 2)
    {
        // do nothing
        return 0;
    }
    // pop the rest of junk from stack
    if (avail > 2)
        LsLuaApi::pop(L, avail - 2);
    // LsLuaApi::getglobal(L, "ls.header"); // This wont work use nil instead
    LsLuaApi::pushnil(L);
    LsLuaApi::insert(L, -3);
    return LsLuaHeaderSet(L);
}


static int LsLuaReqGetHeaders(lua_State *L)
{
    int i, iRet, iCount, iMaxHeaders = 100;
    struct iovec *pKeys, *pVals;
    LsLuaSession *pSession = LsLuaGetSession(L);
    const lsi_session_t *session = pSession->getHttpSession();
    ls_xpool_t *pool = g_api->get_session_pool(session);
    switch (LsLuaApi::gettop(L))
    {
    case 2:
        if ((iRet = LsLuaApi::checkArgType(L, 2, LUA_TBOOLEAN,
                                           "req_get_headers")) != 0)
            return iRet;
        if (LsLuaApi::toboolean(L, 2) != 0)
        {
            //NOTICE: case not handled yet.
        }
    //Fall through
    case 1:
        if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TNUMBER,
                                           "req_get_headers")) != 0)
            return iRet;
        iCount = LsLuaApi::tointeger(L, 1);
        if (iCount < 0)
            return LsLuaApi::userError(L, "req_get_headers",
                                       "Invalid max headers");
        else
            iMaxHeaders = iCount;
        break;
    case 0:
        break;
    default:
        return LsLuaApi::invalidNArgError(L, "req_get_headers");
    }

    iCount = g_api->get_req_headers_count(session);
    if (iCount <= 0)
    {
        LsLuaApi::pushnil(L);
        return 1;
    }
    if (iCount > iMaxHeaders)
        iCount = iMaxHeaders;

    pKeys = (struct iovec *)ls_xpool_alloc(pool,
                                           iCount * sizeof(struct iovec));
    pVals = (struct iovec *)ls_xpool_alloc(pool,
                                           iCount * sizeof(struct iovec));
    iCount = g_api->get_req_headers(session, pKeys, pVals, iCount);
    if (iCount == 0)
        return LsLuaApi::serverError(L, "req_get_headers",
                                     "Get Headers Failed.");
    LsLuaApi::createtable(L, 0, iCount);
    for (i = 0; i < iCount; ++i)
    {
        LsLuaApi::pushlstring(L, (const char *)pKeys->iov_base,
                              pKeys->iov_len);
        LsLuaApi::pushlstring(L, (const char *)pVals->iov_base,
                              pVals->iov_len);
        LsLuaApi::settable(L, -3);
    }
    ls_xpool_free(pool, pKeys);
    ls_xpool_free(pool, pVals);

    return 1;
}


static int LsLuaReqGetMethod(lua_State *L)
{
    int iBufSize = TMPBUFSIZE;
    char aTmpBuf[TMPBUFSIZE];
    LsLuaSession *pSession = LsLuaGetSession(L);
    iBufSize = g_api->get_req_var_by_id(pSession->getHttpSession(),
                                        LSI_VAR_REQ_METHOD,
                                        aTmpBuf, iBufSize);
    if (iBufSize != 0)
        LsLuaApi::pushlstring(L, aTmpBuf, iBufSize);
    else
        LsLuaApi::pushnil(L);
    return 1;
}


static int LsLuaReqSetMethod(lua_State *L)
{
    LsLuaLog(L, LSI_LOG_NOTICE, 0, "req_set_method  not supported yet");
    return LsLuaApi::error(L, "req_set_method not supported yet");
}


static int LsLuaReqSetUri(lua_State *L)
{
    int iRet;
    const char *pUri, *pQs;
    size_t iUriLen;
    int iQsLen, iArgs = LsLuaApi::gettop(L);
    LsLuaSession *pSession = LsLuaGetSession(L);
    const lsi_session_t *session = pSession->getHttpSession();

    if (iArgs != 1 && iArgs != 2)
        return LsLuaApi::invalidNArgError(L, "req_set_uri");
    if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TSTRING,
                                       "req_set_uri")) != 0)
        return iRet;
    pUri = LsLuaApi::tolstring(L, 1, &iUriLen);
    if (iArgs == 2 && LsLuaApi::toboolean(L, 2))
    {
        //internal redirect
        pQs = g_api->get_req_query_string(session, &iQsLen);
        if (g_api->set_uri_qs(session, LSI_URL_REDIRECT_INTERNAL,
                              pUri, iUriLen, pQs, iQsLen))
            return LsLuaApi::serverError(L, "req_set_uri", "Setting uri failed");
        pSession->setFlag(LLF_URLREDIRECTED);
        return LsLuaApi::yield(L, 0);
    }
    if (g_api->set_uri_qs(session, LSI_URL_REWRITE, pUri, iUriLen, NULL, 0))
        return LsLuaApi::serverError(L, "req_set_uri", "Setting uri failed");

    return 0;
}


static int LsLuaReqSetUriArgs(lua_State *L)
{
    char pQs[LSLUA_SESS_MAXQSLEN];
    size_t iQsLen = 0;
    LsLuaSession *pSession = LsLuaGetSession(L);
    if (LsLuaApi::gettop(L) != 1)
        return LsLuaApi::invalidNArgError(L, "req_set_uri_args");

    LsLuaGetQs(L, 1, pQs, iQsLen);
    if (g_api->set_uri_qs(pSession->getHttpSession()
                          , LSI_URL_NOCHANGE | LSI_URL_QS_SET
                          , NULL, 0
                          , pQs, iQsLen
                         ) < 0
       )
        return LsLuaApi::serverError(L, "req_set_uri_args", "Set qs failed.");

    return 0;
}


static int LsLuaFillTable(lua_State *L, ls_xpool_t *pool,
                          const char *pBegin, const char *pEnd, int iMax)
{
    int iValLen, iCount = 0, iKeyLen = pEnd - pBegin;
    const char *pEquals, *pValEnd;
    char *pDKey = NULL, *pDVal = NULL;

    do
    {
        pValEnd = ls_strnextarg(&pBegin, " \n\r\t&");
        if (!pValEnd)
            pValEnd = pEnd;
        if (pBegin != pValEnd && *pBegin != '=')   // not empty arg
        {
            pEquals = (const char *)memchr(pBegin, '=',
                                           pValEnd - pBegin);
            if (pEquals)   // key and value
            {
                iKeyLen = pEquals - pBegin;
                iValLen = pValEnd - ++pEquals;
                pDVal = (char *)ls_xpool_realloc(pool, pDVal, iValLen);
                if (HttpUtil::unescapeQs(pDVal, iValLen, pEquals) < 0)
                    return LsLuaApi::serverError(L, "fillTable",
                                                 "Escape for QS val failed.");
            }
            else // just a key
            {
                iKeyLen = pValEnd - pBegin;
                iValLen = -1;
            }
            pDKey = (char *)ls_xpool_realloc(pool, pDKey, iKeyLen);
            if (HttpUtil::unescapeQs(pDKey, iKeyLen, pBegin) < 0)
                return LsLuaApi::serverError(L, "fillTable",
                                             "Escape for QS key failed.");

            if (LsLuaAddKvToTable(L, pDKey, iKeyLen,
                                  pDVal, iValLen) == 0)
                return LsLuaApi::serverError(L, "fillTable",
                                             "Adding Key Value pair failed.");
        }
        pBegin = (char *)pValEnd + 1;
    }
    while (pBegin < pEnd && ++iCount < iMax);
    return 1;
}


static int LsLuaReqGetUriArgs(lua_State *L)
{
    int iKeyLen, iMax, iCount = LsLuaApi::gettop(L);
    const char *pBegin;
    const lsi_session_t *pSession = LsLuaGetSession(L)->getHttpSession();
    ls_xpool_t *pool = g_api->get_session_pool(pSession);

    if (iCount != 0 && iCount != 1)
        return LsLuaApi::invalidNArgError(L, "req_get_uri_args");

    if (iCount == 1 && LsLuaApi::type(L, 1) == LUA_TNUMBER)
        iMax = LsLuaApi::tointeger(L, 1);
    else
        iMax = LS_LUA_MAX_ARGS;

    pBegin = g_api->get_req_query_string(pSession, &iKeyLen);
    if (!pBegin)
        return 0;
    LsLuaApi::createtable(L, 0, 0);
    return LsLuaFillTable(L, pool, pBegin, pBegin + iKeyLen, iMax);
}


static int LsLuaReqGetPostArgs(lua_State *L)
{
    char *pBody;
    int iRet, iMax, iBodySize, iBodyLen = 0;
    const lsi_session_t *session;
    ls_xpool_t *pool;
    LsLuaSession *pSession = LsLuaSession::getSelf(L);
    int iArgs = LsLuaApi::gettop(L);

    if (iArgs == 0)
        iMax = LS_LUA_MAX_ARGS;
    else if (iArgs == 1)
        iMax = LsLuaApi::tointeger(L, 1);
    else
        return LsLuaApi::invalidNArgError(L, "get_post_args");

    session = pSession->getHttpSession();
    pool = g_api->get_session_pool(session);
    iBodySize = g_api->get_req_content_length(session);
    pBody = (char *)ls_xpool_alloc(pool, iBodySize);
    while (iBodyLen < iBodySize)
    {
        iRet = g_api->read_req_body(session,
                                    pBody + iBodyLen, iBodySize);
        iBodyLen += iRet;
    }
    if (iBodyLen == 0)
        return 0;
    g_api->reset_body_buf(g_api->get_req_body_buf(session), 0);
    LsLuaApi::createtable(L, 0, iMax);
    iRet = LsLuaFillTable(L, pool, pBody, pBody + iBodyLen, iMax);
    ls_xpool_free(pool, pBody);
    return 1;
}


static int LsLuaReqReadBody(lua_State *L)
{
    LsLuaSession   *pSession = LsLuaGetSession(L);
    const lsi_session_t *sess = pSession->getHttpSession();
    int iRet;

    if (!pSession)
        return LsLuaApi::userError(L, "req_read_body", "Session not found.");

    if ((iRet = LsLuaSession::checkHook(pSession, L, "req_read_body",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;

    if (g_api->is_req_body_finished(sess))
        return 0;
    g_api->set_req_wait_full_body(
        sess);  // This is supposed to do the reading synchronously.
    return 0;
}


static int LsLuaReqDiscardBody(lua_State *L)
{
    LsLuaSession *pSession = LsLuaGetSession(L);
    int iRet;

    if ((iRet = LsLuaSession::checkHook(pSession, L, "discard_body",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    return 0;
}


static int LsLuaReqGetBodyData(lua_State *L)
{
    int len, count = 0;
    LsLuaSession *pSession = LsLuaGetSession(L);
    void *pBuf;
    int64_t offset = 0;
    const char *pTmpBuf;
    int iRet;

    if ((iRet = LsLuaSession::checkHook(pSession, L, "get_body_data",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;

    pBuf = g_api->get_req_body_buf(pSession->getHttpSession());
    if ((len = g_api->get_body_buf_size(pBuf)) == 0)
    {
        LsLuaApi::pushnil(L);
        return 1;
    }
    do
    {
        if ((pTmpBuf = g_api->acquire_body_buf_block(pBuf, offset, &len))
            == NULL)
            return LsLuaApi::serverError(L, "get_body_data",
                                         "Error acquiring body data.");
        LsLuaApi::pushlstring(L, pTmpBuf, len);
        ++count;
        offset += len;
    }
    while (!g_api->is_body_buf_eof(pBuf, offset));

    if (!count)
        return LsLuaApi::serverError(L, "get_body_data",
                                     "Error acquiring body data (count).");
    LsLuaApi::concat(L, count);
    return 1;
}


static int LsLuaReqGetBodyFile(lua_State *L)
{
    //TODO: Currently, we do not store file names.  May change in future.
    LsLuaSession *pSession = LsLuaGetSession(L);
    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "get_body_file",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;

    LsLuaApi::pushnil(L);
    return 1;
}


static int LsLuaReqSetBodyData(lua_State *L)
{
    // TODO: Need to account for if set wait full req body is not set.
    // Should properly discard the rest of the request body.
    const char *pData;
    size_t iDataLen;
    void *pBuf;
    LsLuaSession *pSession = LsLuaGetSession(L);
    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "set_body_data",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;

    if (LsLuaApi::gettop(L) != 1)
        return LsLuaApi::invalidNArgError(L, "set_body_data");
    if ((iRet = LsLuaApi::checkArgType(L, -1, LUA_TSTRING,
                                       "set_body_data")) != 0)
        return iRet;

    pData = LsLuaApi::tolstring(L, -1, &iDataLen);
    pBuf = g_api->get_new_body_buf(iDataLen);
    if (g_api->append_body_buf(pBuf, pData, iDataLen) != (int)iDataLen)
        return LsLuaApi::serverError(L, "set_body_data",
                                     "Appending to body failed");
    g_api->set_req_body_buf(pSession->getHttpSession(), pBuf);
    return 0;
}


static int LsLuaReqSetBodyFile(lua_State *L)
{
    LsLuaSession *pSession = LsLuaGetSession(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "set_body_file",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    LsLuaLog(L, LSI_LOG_NOTICE, 0, "req_set_body_file  not supported yet");
    return LsLuaApi::error(L, "req_set_body_file not supported yet");
}


static int LsLuaReqInitBody(lua_State *L)
{
    int iInitialSize = 0;
    void *pBuf;
    LsLuaSession *pSession = LsLuaGetSession(L);


    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "req_init_body",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    if (pSession->getFilterBuf())
        return LsLuaApi::userError(L, "req_init_body",
                                   "Body already initialized.");
    switch (LsLuaApi::gettop(L))
    {
    case 0:
        break;
    case 1:
        iInitialSize = LsLuaApi::tointeger(L, 1);
        break;
    default:
        return LsLuaApi::invalidNArgError(L, "req_init_body");
    }

    pBuf = g_api->get_new_body_buf(iInitialSize);
    pSession->setFilterBuf(pBuf);
    return 0;
}


static int LsLuaReqAppendBody(lua_State *L)
{
    void *pBuf;
    const char *pAppend;
    size_t iAppendLen;
    LsLuaSession *pSession = LsLuaGetSession(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "req_append_body",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    if (LsLuaApi::gettop(L) != 1)
        return LsLuaApi::invalidNArgError(L, "req_append_body");
    if (LsLuaApi::type(L, 1) != LUA_TSTRING)
        return LsLuaApi::userError(L, "req_append_body",
                                   "Argument is not a string.");
    if (pSession->isFlagSet(LLF_BODYFINISHED))
        return LsLuaApi::userError(L, "req_append_body",
                                   "Body Finished flag is set.");
    if ((pBuf = pSession->getFilterBuf()) == NULL)
        return LsLuaApi::userError(L, "req_append_body", "Body not initialized.");

    pAppend = LsLuaApi::tolstring(L, 1, &iAppendLen);

    if (g_api->append_body_buf(pBuf, pAppend, iAppendLen) != (int)iAppendLen)
        return LsLuaApi::serverError(L, "req_append_body",
                                     "Append body buf failed.");
    return 0;
}


static int LsLuaReqFinishBody(lua_State *L)
{
    void *pBuf;
    LsLuaSession *pSession = LsLuaGetSession(L);


    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "req_finish_body",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    if ((pBuf = pSession->getFilterBuf()) == NULL)
        return LsLuaApi::userError(L, "req_finish_body", "Body not initialized.");
    pSession->setFlag(LLF_BODYFINISHED);
    g_api->set_req_body_buf(pSession->getHttpSession(), pBuf);
    return 0;
}


static int LsLuaReqSocket(lua_State *L)
{
    LsLuaSession *pSession = LsLuaGetSession(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "req_socket",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    LsLuaLog(L, LSI_LOG_NOTICE, 0, "req_socket  not supported yet");
    return LsLuaApi::error(L, "req_socket not supported yet");
}


static int LsLuaReqToString(lua_State *L)
{
    char    buf[0x100];

    snprintf(buf, 0x100, "<ls.req %p>", L);
    LsLuaApi::pushstring(L, buf);
    return 1;
}


static int LsLuaReqGc(lua_State *L)
{
    LsLuaLog(L, LSI_LOG_NOTICE, 0, "<ls.req GC>");
    return 0;
}


static const luaL_Reg lsluaReqFuncs[] =
{
    { "start_time",     LsLuaReqStartTime    },
    { "http_version",   LsLuaReqHttpVersion  },
    { "raw_header",     LsLuaReqRawHeader    },
    { "clear_header",   LsLuaReqClearHeader  },
    { "set_header",     LsLuaReqSetHeader    },
    { "get_headers",    LsLuaReqGetHeaders   },
    { "get_method",     LsLuaReqGetMethod    },
    { "set_method",     LsLuaReqSetMethod    },
    { "set_uri",        LsLuaReqSetUri       },
    { "set_uri_args",   LsLuaReqSetUriArgs  },
    { "get_uri_args",   LsLuaReqGetUriArgs  },
    { "get_post_args",  LsLuaReqGetPostArgs },
    { "read_body",      LsLuaReqReadBody     },
    { "discard_body",   LsLuaReqDiscardBody  },
    { "get_body_data",  LsLuaReqGetBodyData },
    { "get_body_file",  LsLuaReqGetBodyFile },
    { "set_body_data",  LsLuaReqSetBodyData },
    { "set_body_file",  LsLuaReqSetBodyFile },
    { "init_body",      LsLuaReqInitBody     },
    { "append_body",    LsLuaReqAppendBody   },
    { "finish_body",    LsLuaReqFinishBody   },
    { "socket",         LsLuaReqSocket        },
    {NULL, NULL}
};


static const luaL_Reg lsluaReqMetaSub[] =
{
    {"__gc",        LsLuaReqGc},
    {"__tostring",  LsLuaReqToString},
    {NULL, NULL}
};


void LsLuaCreateReqmeta(lua_State *L)
{
    LsLuaApi::openlib(L, LS_LUA ".req", lsluaReqFuncs, 0);
    LsLuaApi::newmetatable(L, LSLUA_REQ);
    LsLuaApi::openlib(L, NULL, lsluaReqMetaSub, 0);

    // pushliteral
    LsLuaApi::pushlstring(L, "__index", 7);
    LsLuaApi::pushvalue(L, -3);
    LsLuaApi::rawset(L, -3);        // metatable.__index = methods
    // pushliteral
    LsLuaApi::pushlstring(L, "__metatable", 11);
    LsLuaApi::pushvalue(L, -3);
    LsLuaApi::rawset(L, -3);        // metatable.__metatable = methods

    LsLuaApi::settop(L, -3);       // pop 2

}


static int  LsLuaSessExec(lua_State *L)
{
    const char *ptr;
    char pQs[LSLUA_SESS_MAXQSLEN];
    ls_str_t *pUri;
    size_t iLen;
    int iNumArgs = LsLuaApi::gettop(L);
    LsLuaSession *pSession = LsLuaGetSession(L);
    ls_xpool_t *pool = g_api->get_session_pool(pSession->getHttpSession());


    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "exec", LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;

    if (iNumArgs != 1 && iNumArgs != 2)
        return LsLuaApi::invalidNArgError(L, "Exec");
    if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TSTRING, "Exec")) != 0)
        return iRet;
    ptr = LsLuaApi::tolstring(L, 1, &iLen);
    if (iLen == 0)
        return LsLuaApi::userError(L, "Exec", "Uri Len 0.");
    pUri = ls_str_xnew(ptr, iLen, pool);
    iLen = 0;
    if (iNumArgs == 2)
    {
        switch (LsLuaApi::type(L, 2))
        {
        case LUA_TNUMBER:
        case LUA_TSTRING:
            ptr = LsLuaApi::tolstring(L, 2, &iLen);
            memmove(pQs, ptr, iLen);
            break;
        case LUA_TTABLE:
            if (LsLuaGetQs(L, 2, pQs, iLen))
            {
                ls_str_xdelete(pUri, pool);
                return LsLuaApi::serverError(L, "Exec", "Lua Table Returned Error");
            }
            break;
        default:
            ls_str_xdelete(pUri, pool);
            return LsLuaApi::serverError(L, "Exec", "Args are wrong type.");
        }
    }
    if (g_api->set_uri_qs(pSession->getHttpSession()
                          , LSI_URL_REDIRECT_INTERNAL
                          , ls_str_cstr(pUri)
                          , ls_str_len(pUri)
                          , pQs
                          , iLen
                         )
       )
    {
        ls_str_xdelete(pUri, pool);
        return LsLuaApi::serverError(L, "Exec", "Set Uri Error");
    }
    pSession->setFlag(LLF_URLREDIRECTED);
    ls_str_xdelete(pUri, pool);
    return LsLuaApi::yield(L, 0);
}


//
// @belief LsLuaSessRedirect
// @param[in] uri - redirected uri
// @param[in] status - 301, 302, 307, 0 - internal redirect
//
static int  LsLuaSessRedirect(lua_State *L)
{
    LsLuaSession *pSession = LsLuaGetSession(L);
    size_t len;
    const char *cp = LsLuaApi::tolstring(L, 1, &len);
    int status;


    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "redirect",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;

    if (LsLuaApi::gettop(L) != 2)
        status = LSI_URL_REDIRECT_302; //Default to 302
    else
        status = 1 * LsLuaApi::tonumber(L, 2);

    switch (status)
    {
    case LSI_URL_NOCHANGE:          // 0
    case LSI_URL_REWRITE:           // 1
    case LSI_URL_REDIRECT_INTERNAL: // 2
    case LSI_URL_REDIRECT_301:
    case LSI_URL_REDIRECT_302:
    case LSI_URL_REDIRECT_307:
        // don't modify it.
        break;
    case 301:
        status = LSI_URL_REDIRECT_301;
        break;
    case 302:
        status = LSI_URL_REDIRECT_302;
        break;
    case 307:
        status = LSI_URL_REDIRECT_307;
        break;
    default:
        status = LSI_URL_REWRITE;
        break;
    }
    if (g_api->set_uri_qs(pSession->getHttpSession(), status, cp, len, "", 0))
        return LsLuaApi::serverError(L, "sess_redirect",
                                     "Failed to set the new Uri.");

    pSession->setFlag(LLF_URLREDIRECTED);   // disable to flush and end_resp
    return LsLuaApi::yield(L, 0);
}


static int  LsLuaSessSendHeaders(lua_State *L)
{
    LsLuaSession *pSession = LsLuaGetSession(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "send_headers",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;

    if (g_api->is_resp_headers_sent(pSession->getHttpSession()))
    {
        LsLuaApi::pushnil(L);
        LsLuaApi::pushstring(L, "Send Headers: Headers already sent.");
        return 2;
    }
    g_api->end_resp_headers(pSession->getHttpSession());
    LsLuaApi::pushinteger(L, 1);
    return 1;
}


static int  LsLuaSessHeadersSent(lua_State *L)
{
    LsLuaSession *pSession = LsLuaGetSession(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "headers_sent",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    LsLuaApi::pushboolean(L,
                          g_api->is_resp_headers_sent(pSession->getHttpSession()));
    return 1;
}


static int  LsLuaSessPrintHelper(lua_State *L, ls_luaprint_t &s,
                                 LsLuaSession  *pSession)
{
    if (g_api->is_resp_buffer_available(pSession->getHttpSession()) == 1)
    {
        if (LsLuaPrint(L, &s) == -1)
            return -1;
    }
    else
        return pSession->wait4RespBuffer(L);
    return 0;
}


static int  LsLuaSessPrint(lua_State *L)
{
    LsLuaSession *pSession = LsLuaSession::getSelf(L);
    ls_luaprint_t stream = { pSession, LsLuaRespBodyFlush,
                             0, {0, 0, 0}
                           };

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "print",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    return (LsLuaSessPrintHelper(L, stream, pSession));
}


static int  LsLuaSessPuts(lua_State *L)
{    return LsLuaSessPrint(L);  }


static int  LsLuaSessSay(lua_State *L)
{
    LsLuaSession *pSession = LsLuaSession::getSelf(L);
    ls_luaprint_t stream = { pSession, LsLuaRespBodyFlush,
                             LSLUA_PRINT_FLAG_LF, {0, 0, 0}
                           };

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "say", LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    return (LsLuaSessPrintHelper(L, stream, pSession));
}


static int  LsLuaSessWrite(lua_State *L)
{   return LsLuaSessSay(L); }


static int  LsLuaSessFlush(lua_State *L)
{
    LsLuaSession *pSession = LsLuaSession::getSelf(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "flush",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    g_api->flush(pSession->getHttpSession());
    return 0;
}


static int  LsLuaSessExit(lua_State *L)
{
    // may be we should introduce a variable for LUA for exit already indication...
    LsLuaSession *pSession = LsLuaSession::getSelf(L);
    int exitCode = LsLuaApi::tointeger(L, 1);

    if ((!pSession) || pSession->isFlagSet(LLF_LUADONE))
        LsLuaLog(L, LSI_LOG_NOTICE, 0, "ignore EXIT session <%p> value = %d",
                 pSession,
                 exitCode);
    else
    {
        LsLuaLog(L, LSI_LOG_NOTICE, 0, "EXIT session <%p> value = %d", pSession,
                 exitCode);
        pSession->setLuaExitCode(exitCode);
        //
        //  need to send the exit level back to user...
        //
        // LsLuaSess_End( L );
        // LsLuaApi::yield( pSession->getLuaState(), 0 );
        LsLuaSession::endSession(pSession);
        return LsLuaApi::yield(L, 0);
    }
    return 0;
}


static int  LsLuaSessTime(lua_State *L)
{
    time_t  t;
    int32_t us;
    t = g_api->get_cur_time(&us);

    LsLuaApi::pushinteger(L, (int)t);
    LsLuaApi::pushinteger(L, (int)us);
    return 2;
}


static int LsLuaSessClock(lua_State *L)
{
    long long time = 1000000;
    time_t  t;
    int32_t us;
    t = g_api->get_cur_time(&us);
    time = time * t;
    time += us;
    LsLuaApi::pushnumber(L, time);
    return 1;
}


static int  LsLuaSessSetVersion(lua_State *L)
{
    const char *cp;
    size_t len;
    cp = LsLuaApi::tolstring(L, 1, &len);
    if (cp && len)
        LsLuaEngine::setVersion(cp, len);
    return 0;
}


static int  LsLuaSessLogtime(lua_State *L)
{
    char buf[0x100];

    time_t  t;
    int32_t us;
    t = g_api->get_cur_time(&us);

    struct tm *p_tm;
    if ((p_tm = localtime(&t)))
    {
        strftime(buf, sizeof(buf), "%a %d %b %Y %T %z", p_tm);
        LsLuaApi::pushstring(L, buf);
    }
    else
        LsLuaApi::pushnil(L);
    return 1;
}


static int  LsLuaSessSleep(lua_State *L)
{
    LsLuaSession *pSession = LsLuaGetSession(L);
    int avail = LsLuaApi::gettop(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "sleep",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    if (avail < 1)
        return LsLuaApi::invalidNArgError(L, "Sleep");
    int msec = 1000 * LsLuaApi::tonumber(L, 1);
    if (msec < 1)
        return LsLuaApi::userError(L, "Sleep", "Bad sleep time value.");

    LsLuaApi::pushinteger(L, 0);
    LsLuaApi::pushnil(L);
    // LsLuaLog( L, LSI_LOG_NOTICE, 0, "sleep %d msec" , msec);

    if (LsLuaEngine::debug() & 0x10)
        LsLuaSession::trace("SETTIMER", pSession, L);
    pSession->setTimer(msec, LsLuaSleepResume, L, SET_TIMER_NORMAL);
    return LsLuaApi::yield(L, 2);
}


static int  LsLuaSessUSleep(lua_State *L)
{
    LsLuaSession *pSession = LsLuaGetSession(L);
    int avail = LsLuaApi::gettop(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "uSleep",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    if (avail < 1)
        return LsLuaApi::invalidNArgError(L, "uSleep");
    int msec = LsLuaApi::tonumber(L, 1);
    if (msec < 1)
        return LsLuaApi::userError(L, "uSleep", "Bad sleep time value.");

    LsLuaApi::pushinteger(L, 0);
    LsLuaApi::pushnil(L);
    // LsLuaLog( L, LSI_LOG_NOTICE, 0, "sleep %d msec" , msec);

    if (LsLuaEngine::debug() & 0x10)
        LsLuaSession::trace("SETTIMER", pSession, L);
    pSession->setTimer(msec, LsLuaSleepResume, L, SET_TIMER_NORMAL);
    return LsLuaApi::yield(L, 2);
}


static int  LsLuaSessIsSubrequest(lua_State *L)
{
    LsLuaLog(L, LSI_LOG_NOTICE, 0, "sess_is_subrequest  not supported yet");
    return LsLuaApi::error(L, "is_subrequest not supported yet");
}


static int  LsLuaSessOnAbort(lua_State *L)
{
    LsLuaSession *pSession = LsLuaGetSession(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "onAbort",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    LsLuaLog(L, LSI_LOG_NOTICE, 0, "sess_on_abort  not supported yet");
    return LsLuaApi::error(L, "onAbort not supported yet");
}


static int LsLuaSessRequestbody(lua_State *L)
{
    const char *pErr = "LSWS does not support saving to file.";
    LsLuaSession *pSession = LsLuaSession::getSelf(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "requestbody",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    if (LsLuaApi::gettop(L) > 0
        && LsLuaApi::type(L, 1) == LUA_TSTRING)
    {
        LsLuaLog(L, LSI_LOG_INFO, 0, pErr);
        LsLuaApi::pushlstring(L, pErr, strlen(pErr));
        return 1;
    }
    return LsLuaReqGetBodyData(L);
}


static const int LSLUA_NUM_STATS = 6;
static void LsLuaSessFillStat(lua_State *L, struct stat st)
{
    int iFileType;
    LsLuaApi::pushinteger(L, st.st_mtime);
    LsLuaApi::setfield(L, -2, "mtime");

    LsLuaApi::pushinteger(L, st.st_atime);
    LsLuaApi::setfield(L, -2, "atime");

    LsLuaApi::pushinteger(L, st.st_ctime);
    LsLuaApi::setfield(L, -2, "ctime");

    LsLuaApi::pushinteger(L, st.st_size);
    LsLuaApi::setfield(L, -2, "size");

    switch (st.st_mode & S_IFMT)
    {
    case S_IFREG:
        iFileType = 1;
        break;
    case S_IFDIR:
        iFileType = 2;
        break;
    case S_IFCHR:
        iFileType = 3;
        break;
    case S_IFBLK:
        iFileType = 4;
        break;
    case S_IFIFO:
        iFileType = 5;
        break;
    case S_IFLNK:
        iFileType = 6;
        break;
    case S_IFSOCK:
        iFileType = 7;
        break;
    default:
        iFileType = 127;
        break;
    }

    LsLuaApi::pushinteger(L, iFileType);
    LsLuaApi::setfield(L, -2, "filetype");

    LsLuaApi::pushinteger(L, st.st_mode & 0777);
    LsLuaApi::setfield(L, -2, "protection");
}


static int LsLuaSessStat(lua_State *L)
{
    int iRet;
    size_t iPathLen, iArgs;
    const char *pPath;
    struct stat st;
    LsLuaSession *pSession = LsLuaSession::getSelf(L);
    iArgs = LsLuaApi::gettop(L);
    if (iArgs != 1 && iArgs != 2)
        return LsLuaApi::invalidNArgError(L, "stat");
    if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TSTRING, "stat")) != 0)
        return iRet;

    pPath = LsLuaApi::tolstring(L, 1, &iPathLen);
    if (iPathLen <= 0)
        return LsLuaApi::userError(L, "stat", "Invalid path.");

    if (g_api->get_file_stat(pSession->getHttpSession(),
                             pPath, iPathLen, &st) < 0)
        return LsLuaApi::userError(L, "stat", "Invalid file.");

    LsLuaApi::createtable(L, 0, LSLUA_NUM_STATS);
    LsLuaSessFillStat(L, st);
    return 1;
}


static int  LsLuaSessSendFile(lua_State *L)
{
    size_t iPathLen, iRet, iOffset = 0;
    const char *pPath;
    struct stat st;
    LsLuaSession *pSession = LsLuaSession::getSelf(L);

    if ((iRet = LsLuaSession::checkHook(pSession, L, "send_file",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    if (LsLuaApi::gettop(L) != 1)
        return LsLuaApi::invalidNArgError(L, "send_file");
    if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TSTRING, "send_file")) != 0)
        return iRet;
    pPath = LsLuaApi::tolstring(L, 1, &iPathLen);
    if (!iPathLen)
        return LsLuaApi::userError(L, "send_file", "Invalid path.");

    if (g_api->get_file_stat(pSession->getHttpSession(), pPath, iPathLen,
                             &st) < 0
        || st.st_size <= 0)
        return LsLuaApi::userError(L, "send_file", "Invalid file.");
    iRet = g_api->send_file(pSession->getHttpSession(), pPath, iOffset,
                            st.st_size);
    if (iRet)
    {
        LsLuaLog(L, LSI_LOG_INFO, 0
                 , "send_file send file returned %d", iRet);
    }
    LsLuaApi::pushinteger(L, iRet);
    return 1;
}


static int LsLuaSessEscapeHtml(lua_State *L)
{
    const char *pSrc;
    char pDest[LSLUA_SESS_MAXURILEN];
    size_t iSrcLen, iDestLen;
    int iRet;
    LsLuaSession::getSelf(L);
    if (LsLuaApi::gettop(L) != 1)
        return LsLuaApi::invalidNArgError(L, "escape_html");
    if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TSTRING,
                                       "escape_html")) != 0)
        return iRet;

    pSrc = LsLuaApi::tolstring(L, 1, &iSrcLen);
    if (iSrcLen <= 0)
        return LsLuaApi::userError(L, "escape_html", "Invalid arg.");

    iDestLen = HttpUtil::escapeHtml(pSrc, pSrc + iSrcLen, pDest,
                                    LSLUA_SESS_MAXURILEN);
    if (iDestLen <= 0)
        return LsLuaApi::serverError(L, "escape_html", "Error escaping.");

    LsLuaApi::pushlstring(L, pDest, iDestLen);
    return 1;
}


static int LsLuaSessEscapeUri(lua_State *L)
{
    const char *pSrc;
    char pDest[LSLUA_SESS_MAXURILEN];
    size_t iSrcLen, iDestLen;
    int iRet;
    LsLuaSession::getSelf(L);
    if (LsLuaApi::gettop(L) != 1)
        return LsLuaApi::invalidNArgError(L, "escape_uri");
    if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TSTRING, "escape_uri")) != 0)
        return iRet;

    pSrc = LsLuaApi::tolstring(L, 1, &iSrcLen);
    if (iSrcLen <= 0)
        return LsLuaApi::userError(L, "escape_uri", "Invalid arg.");

    iDestLen = HttpUtil::escapeRFC3986(pSrc, iSrcLen, pDest,
                                       LSLUA_SESS_MAXURILEN);
    if (iDestLen <= 0)
        return LsLuaApi::serverError(L, "escape_uri", "Error escaping.");

    LsLuaApi::pushlstring(L, pDest, iDestLen);
    return 1;
}


static int LsLuaSessUnescapeUri(lua_State *L)
{
    const char *pSrc;
    char pDest[LSLUA_SESS_MAXURILEN];
    size_t iSrcLen, iDestLen;
    int iRet;
    LsLuaSession::getSelf(L);
    if (LsLuaApi::gettop(L) != 1)
        return LsLuaApi::invalidNArgError(L, "unescape_uri");
    if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TSTRING,
                                       "unescape_uri")) != 0)
        return iRet;

    pSrc = LsLuaApi::tolstring(L, 1, &iSrcLen);
    if (iSrcLen <= 0)
        return LsLuaApi::userError(L, "unescape_uri", "Invalid arg.");
    iDestLen = HttpUtil::unescape(pSrc, iSrcLen, pDest,
                                  LSLUA_SESS_MAXURILEN);
    if (iDestLen <= 0)
        return LsLuaApi::serverError(L, "unescape_uri", "Error unescaping.");

    LsLuaApi::pushlstring(L, pDest, iDestLen);
    return 1;
}


static int LsLuaSessEscape(lua_State *L)
{
    const char *pSrc;
    char pDest[LSLUA_SESS_MAXURILEN];
    size_t iSrcLen, iDestLen;
    int iRet;
    LsLuaSession::getSelf(L);
    if (LsLuaApi::gettop(L) != 1)
        return LsLuaApi::invalidNArgError(L, "escape");
    if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TSTRING, "escape")) != 0)
        return iRet;

    pSrc = LsLuaApi::tolstring(L, 1, &iSrcLen);
    if (iSrcLen <= 0)
        return LsLuaApi::userError(L, "escape", "Invalid arg.");
    iDestLen = HttpUtil::escapeQs(pSrc, iSrcLen, pDest,
                                  LSLUA_SESS_MAXURILEN);
    if (iDestLen <= 0)
        return LsLuaApi::serverError(L, "escape", "Error escaping.");

    LsLuaApi::pushlstring(L, pDest, iDestLen);
    return 1;
}


static int LsLuaSessUnescape(lua_State *L)
{
    const char *pSrc;
    char pDest[LSLUA_SESS_MAXURILEN];
    size_t iSrcLen, iDestLen;
    int iRet;
    LsLuaSession::getSelf(L);
    if (LsLuaApi::gettop(L) != 1)
        return LsLuaApi::invalidNArgError(L, "unescape");
    if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TSTRING, "unescape")) != 0)
        return iRet;

    pSrc = LsLuaApi::tolstring(L, 1, &iSrcLen);
    if (iSrcLen <= 0)
        return LsLuaApi::userError(L, "unescape", "Invalid arg.");
    iDestLen = HttpUtil::unescapeQs(pSrc, iSrcLen, pDest,
                                    LSLUA_SESS_MAXURILEN);
    if (iDestLen <= 0)
        return LsLuaApi::serverError(L, "unescape", "Error unescaping.");

    LsLuaApi::pushlstring(L, pDest, iDestLen);
    return 1;
}


static int LsLuaSessParseArgs(lua_State *L)
{
    LsLuaSession::getSelf(L);
    if (LsLuaReqGetUriArgs(L) != 1)
    {
        LsLuaApi::pushnil(L);
        return 1;
    }

    LsLuaApi::createtable(L, 0, 0);
    LsLuaApi::pushnil(L);
    while (LsLuaApi::next(L, -3) != 0)
    {
        const char *pKey = LsLuaApi::tolstring(L, -2, NULL);
        if (LsLuaApi::type(L, -1) == LUA_TTABLE)
        {
            LsLuaApi::settable(L, -3);
            LsLuaApi::pushnil(L);
            LsLuaApi::setfield(L, -3, pKey);
            LsLuaApi::pushnil(L);
        }
        else
            LsLuaApi::pop(L, 1);
    }

    return 2;
}


static int LsLuaSessSetCookie(lua_State *L)
{
    const char  *pKey = NULL,
                 *pValue = NULL,
                  *pPath = NULL,
                   *pDomain = NULL;
    int i, iExpires = 0, iSecure = 0, iHttpOnly = 0;
    LsLuaSession *pSession = LsLuaSession::getSelf(L);
    int iNumArgs = LsLuaApi::gettop(L);


    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "set_cookie",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    if (iNumArgs == 2
        && LsLuaApi::type(L, -1) == LUA_TSTRING
        && LsLuaApi::type(L, -2) == LUA_TSTRING)
    {
        pKey = LsLuaApi::tolstring(L, -2, NULL);
        pValue = LsLuaApi::tolstring(L, -1, NULL);
    }
    else if (iNumArgs == 1
             && LsLuaApi::type(L, -1) == LUA_TTABLE)
    {
        LsLuaApi::getfield(L, -1, "key");
        if (LsLuaApi::type(L, -1) == LUA_TSTRING)
            pKey = LsLuaApi::tolstring(L, -1, NULL);

        LsLuaApi::getfield(L, -2, "value");
        if (LsLuaApi::type(L, -1) == LUA_TSTRING)
            pValue = LsLuaApi::tolstring(L, -1, NULL);

        LsLuaApi::getfield(L, -3, "path");
        if (LsLuaApi::type(L, -1) == LUA_TSTRING)
            pPath = LsLuaApi::tolstring(L, -1, NULL);

        LsLuaApi::getfield(L, -4, "domain");
        if (LsLuaApi::type(L, -1) == LUA_TSTRING)
            pDomain = LsLuaApi::tolstring(L, -1, NULL);

        LsLuaApi::getfield(L, -5, "expires");
        if (LsLuaApi::type(L, -1) == LUA_TNUMBER)
            iExpires = LsLuaApi::tointeger(L, -1);

        LsLuaApi::getfield(L, -6, "secure");
        if (LsLuaApi::type(L, -1) == LUA_TBOOLEAN)
            iSecure = LsLuaApi::toboolean(L, -1);

        LsLuaApi::getfield(L, -7, "httponly");
        if (LsLuaApi::type(L, -1) == LUA_TBOOLEAN)
            iHttpOnly = LsLuaApi::toboolean(L, -1);
        LsLuaApi::pop(L, 7);
    }
    else
        return LsLuaApi::userError(L, "set_cookie", "Invalid args.");

    if (pDomain == NULL)
        pDomain = "/";
    i = g_api->set_resp_cookies(pSession->getHttpSession(), pKey, pValue,
                                pPath, pDomain, iExpires, iSecure,
                                iHttpOnly);

    LsLuaApi::pushinteger(L, i);
    return 1;
}


static int LsLuaSessGetCookie(lua_State *L)
{
    size_t iKeyLen;
    int iValLen;
    int iRet;
    const char *pKey, *pVal;
    LsLuaSession *pSession = LsLuaSession::getSelf(L);
    if (LsLuaApi::gettop(L) != 1)
        return LsLuaApi::invalidNArgError(L, "get_cookie");
    if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TSTRING, "get_cookie")) != 0)
        return iRet;

    pKey = LsLuaApi::tolstring(L, 1, &iKeyLen);
    if (iKeyLen <= 0)
        return LsLuaApi::userError(L, "get_cookie", "Invalid arg.");

    pVal = g_api->get_cookie_value(pSession->getHttpSession()
                                   , pKey, iKeyLen, &iValLen);
    if (pVal)
        LsLuaApi::pushlstring(L, pVal, iValLen);
    else
        LsLuaApi::pushnil(L);
    return 1;
}


// Keepalive should be set by server only.
static int LsLuaSessSetKeepAlive(lua_State *L)
{
    LsLuaApi::pushboolean(L, 0);
    return 1;
}


// No ETags for dynamic responses.
static int LsLuaSessMakeEtag(lua_State *L)
{
    LsLuaApi::pushinteger(L, 0);
    return 1;
}


static int LsLuaSessEncodeBase64(lua_State *L)
{
    int iNewLen;
    int iRet;
    size_t iLen;
    const char *pBuf;
    char *pEncodedBuf;
    const lsi_session_t *pSession = LsLuaSession::getSelf(L)->getHttpSession();

    if (LsLuaApi::gettop(L) != 1)
        return LsLuaApi::invalidNArgError(L, "encode_base64");
    if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TSTRING,
                                       "encode_base64")) != 0)
        return iRet;

    pBuf = LsLuaApi::tolstring(L, 1, &iLen);
    if (iLen <= 0)
        return LsLuaApi::userError(L, "encode_base64", "Invalid arg.");

    iNewLen = ls_base64_encodelen(iLen);
    pEncodedBuf = (char *)ls_xpool_alloc(g_api->get_session_pool(pSession)
                                         , iNewLen);
    iNewLen = ls_base64_encode(pBuf, iLen, pEncodedBuf);
    LsLuaApi::pushlstring(L, pEncodedBuf, iNewLen);
    return 1;
}


static int LsLuaSessDecodeBase64(lua_State *L)
{
    int iRet;
    size_t iLen;
    const char *pBuf;
    char *pDecodedBuf;
    const lsi_session_t *pSession = LsLuaSession::getSelf(L)->getHttpSession();

    if (LsLuaApi::gettop(L) != 1)
        return LsLuaApi::invalidNArgError(L, "decode_base64");
    if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TSTRING,
                                       "decode_base64")) != 0)
        return iRet;
    pBuf = LsLuaApi::tolstring(L, 1, &iLen);
    if (iLen <= 0)
        return LsLuaApi::userError(L, "decode_base64", "Invalid arg.");

    pDecodedBuf = (char *)ls_xpool_alloc(g_api->get_session_pool(pSession)
                                         , iLen);
    iLen = ls_base64_decode(pBuf, iLen, pDecodedBuf);
    LsLuaApi::pushlstring(L, pDecodedBuf, iLen);
    return 1;
}


static int LsLuaSessMd5(lua_State *L)
{
    const unsigned char *pSrc;
    size_t iLen;
    int iRet;
    uint8_t pResult[LSR_MD5_DIGEST_LEN];
    char pHex[2 * LSR_MD5_DIGEST_LEN + 1];

    LsLuaSession::getSelf(L);
    if (LsLuaApi::gettop(L) != 1)
        return LsLuaApi::invalidNArgError(L, "md5");
    if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TSTRING, "md5")) != 0)
        return iRet;
    pSrc = (unsigned char *)LsLuaApi::tolstring(L, 1, &iLen);
    if (iLen <= 0)
        return LsLuaApi::userError(L, "md5", "Invalid arg.");

    if (!ls_md5(pSrc, iLen, pResult))
        return LsLuaApi::serverError(L, "md5", "Creating MD5 failed.");

    iLen = ls_hexencode((const char *)pResult
                        , LSR_MD5_DIGEST_LEN
                        , pHex);

    LsLuaApi::pushlstring(L
                          , (const char *)pHex
                          , iLen);
    return 1;
}


static int LsLuaSessMd5Bin(lua_State *L)
{
    const unsigned char *pSrc;
    size_t iSrcLen;
    uint8_t pResult[LSR_MD5_DIGEST_LEN];

    if (LsLuaApi::gettop(L) != 1)
        return LsLuaApi::invalidNArgError(L, "md5_bin");

    switch (LsLuaApi::type(L, 1))
    {
    case LUA_TSTRING:
        pSrc = (uint8_t *)LsLuaApi::tolstring(L, 1, &iSrcLen);
        if (pSrc || iSrcLen)
            break;
    // fall through
    case LUA_TNIL:
        pSrc = (uint8_t *) "";
        iSrcLen = 0;
        break;
    default:
        return LsLuaApi::userError(L, "md5_bin", "Invalid arg");
    }

    if (!ls_md5(pSrc, iSrcLen, pResult))
        return LsLuaApi::serverError(L, "md5_bin", "Creating MD5 failed.");

    LsLuaApi::pushlstring(L,
                          (const char *)pResult,
                          LSR_MD5_DIGEST_LEN);
    return 1;
}


//
//  Using OPENSSL SHA1 implementation
//
static int LsLuaSessSha1Bin(lua_State *L)
{
    const uint8_t          *src;
    uint8_t                 shaBuf[SHA_DIGEST_LENGTH];
    size_t                  len;

    if (LsLuaApi::gettop(L) != 1)
        return LsLuaApi::invalidNArgError(L, "sha1_bin");

    switch (LsLuaApi::type(L, 1))
    {
    case LUA_TSTRING:
        src = (uint8_t *)LsLuaApi::tolstring(L, 1, &len);
        if (src || len)
            break;
    // fall through
    case LUA_TNIL:
        src = (uint8_t *) "";
        len = 0;
        break;
    default:
        return LsLuaApi::userError(L, "sha1_bin", "Invalid arg");
    }

    if (!ls_sha1(src, len, shaBuf))
        return LsLuaApi::serverError(L, "sha1_bin", "Creating SHA1 failed.");
    LsLuaApi::pushlstring(L, (const char *)shaBuf, SHA_DIGEST_LENGTH);
    return 1;
}


static int LsLuaSessToString(lua_State *L)
{
    char    buf[0x100];

    snprintf(buf, 0x100, "<LsluaSess %p>", L);
    LsLuaApi::pushstring(L, buf);
    return 1;
}


static int LsLuaSessGc(lua_State *L)
{
    // LsLuaLog( L, LSI_LOG_NOTICE, 0, "<ls.session GC>");
    if (LsLuaEngine::debug() & 0x10)
    {
        LsLuaSession *pSession = LsLuaGetSession(L);
        LsLuaSession::trace("<LsLuaSess Gc>", pSession, L);
    }
    return 0;
}


extern int LsLuaRegexRegex(lua_State *);
static const luaL_Reg lsluaSessionFuncs[] =
{
//  { "status",         LsLuaSessStatus           },
    { "debug",          LsLuaSessDebug            }, // special function to dump info
    { "exec",           LsLuaSessExec             },
    { "redirect",       LsLuaSessRedirect         },
    { "send_headers",   LsLuaSessSendHeaders     },
    { "headers_sent",   LsLuaSessHeadersSent     },
    { "print",          LsLuaSessPrint            },
    { "puts",           LsLuaSessPuts             },
    { "say",            LsLuaSessSay              },
    { "write",          LsLuaSessWrite            },
    { "log",            LsLuaSessLog              },
    { "flush",          LsLuaSessFlush            },
    { "exit",           LsLuaSessExit             },
    { "_end",           LsLuaSess_End             },  // internal ls special end
    { "eof",            LsLuaSessEof              },
    { "sleep",          LsLuaSessSleep            },
    { "usleep",         LsLuaSessUSleep           },
    { "requestbody",    LsLuaSessRequestbody      },
    { "stat",           LsLuaSessStat             },
    { "sendfile",       LsLuaSessSendFile        },
    { "escape_html",    LsLuaSessEscapeHtml      },
    { "escape_uri",     LsLuaSessEscapeUri       },
    { "unescape_uri",   LsLuaSessUnescapeUri     },
    { "escape",         LsLuaSessEscape           },
    { "unescape",       LsLuaSessUnescape         },
    { "parseargs",      LsLuaSessParseArgs       },
    { "setcookie",      LsLuaSessSetCookie       },
    { "getcookie",      LsLuaSessGetCookie       },
    { "set_keepalive",  LsLuaSessSetKeepAlive    },
    { "make_etag",      LsLuaSessMakeEtag        },
    { "regex",          LsLuaRegexRegex           },
    { "encode_base64",  LsLuaSessEncodeBase64    },
    { "base64_encode",  LsLuaSessEncodeBase64    },
    { "decode_base64",  LsLuaSessDecodeBase64    },
    { "base64_decode",  LsLuaSessDecodeBase64    },

    { "time",           LsLuaSessTime             },
    { "clock",          LsLuaSessClock            },
    { "logtime",        LsLuaSessLogtime          },
    { "set_version",    LsLuaSessSetVersion      },
    { "is_subrequest",  LsLuaSessIsSubrequest    },
    { "on_abort",       LsLuaSessOnAbort         },

    { "md5",            LsLuaSessMd5              },
    { "md5_bin",        LsLuaSessMd5Bin          },
    { "sha1_bin",       LsLuaSessSha1Bin         },

    {NULL, NULL}
};


//
//  ls.status SESSION
//
static int LsLuaGet(lua_State *L)
{
    size_t          len;
    const char     *cp;
    // const char * tag = "LsLuaGet";
    LsLuaSession *pSession = LsLuaGetSession(L);
    cp = LsLuaApi::tolstring(L, 2, &len);
    if (cp && len)
    {
        // only support status for now!
        if (!strncmp(cp, "status", 6))
        {
            if (pSession && pSession->getHttpSession())
            {
                int status = g_api->get_status_code(pSession->getHttpSession());
                LsLuaApi::pushinteger(L, status);
                return 1;
            }
        }
        else
            LsLuaLog(L, LSI_LOG_NOTICE, 0, "ls GET %s notready", cp);
    }
    else
        LsLuaLog(L, LSI_LOG_NOTICE, 0, "ls GET BADSTACK");
    LsLuaApi::pushinteger(L, -1);
    return 1;
}


static int LsLuaSet(lua_State *L)
{
    size_t          len;
    const char     *cp;
    LsLuaSession *pSession = LsLuaGetSession(L);
    cp = LsLuaApi::tolstring(L, 2, &len);
    if (cp && len)
    {
        // only support status for now!
        if (!strncmp(cp, "status", 6))
        {
            if (pSession && pSession->getHttpSession())
            {
                int status = LsLuaApi::tointeger(L, 3);

                g_api->set_status_code(pSession->getHttpSession(), status);
                LsLuaApi::pushinteger(L, status);
                return 1;
            }
        }
        else
            LsLuaLog(L, LSI_LOG_NOTICE, 0, "ls SET %s notready", cp);
    }
    else
        LsLuaLog(L, LSI_LOG_NOTICE, 0, "ls SET BADSTACK");
    return 1;
}


void LsLuaCreateSession(lua_State *L)
{
    LsLuaApi::openlib(L, LS_LUA, lsluaSessionFuncs, 0);

    // push constant here
    LsLuaApi::pushlightuserdata(L, NULL);
    LsLuaApi::setfield(L, -2, "null");
}


void LsLuaCreateGlobal(lua_State *L)
{
    LsLuaApi::createtable(L, 0, 1);
    LsLuaApi::pushvalue(L, -1);
    LsLuaApi::setfield(L, -2, "_G");

    LsLuaApi::createtable(L, 0, 1);
    LsLuaApi::pushglobaltable(L);
    LsLuaApi::setfield(L, -2, "__index");
    LsLuaApi::setmetatable(L, -2);
    if (LsLuaApi::jitMode())
        LsLuaApi::replace(L, LSLUA_GLOBALSINDEX);
    else
        LsLuaApi::setglobal(L, LS_LUA_BOX);
}


void LsLuaCreateSessMeta(lua_State *L)
{
    LsLuaApi::createtable(L, 0, 2);
    LsLuaApi::pushcclosure(L, LsLuaGet, 0);
    LsLuaApi::setfield(L, -2, "__index");
    LsLuaApi::pushcclosure(L, LsLuaSet, 0);
    LsLuaApi::setfield(L, -2, "__newindex");
    LsLuaApi::pushcclosure(L, LsLuaSessGc, 0);
    LsLuaApi::setfield(L, -2, "__gc");
    LsLuaApi::pushcclosure(L, LsLuaSessToString, 0);
    LsLuaApi::setfield(L, -2, "__tostring");
    LsLuaApi::setmetatable(L, -2);
}


//
//  resp SECTION
//
static int LsLuaRespGetHeaders(lua_State *L)
{
    LsLuaSession *pSession = LsLuaGetSession(L);
    struct iovec iov_key[MAX_RESP_HEADERS_NUMBER];
    struct iovec iov_val[MAX_RESP_HEADERS_NUMBER];
    char bigout[0x1000];
    int size = 0;
    char *cp = bigout;

    int count = g_api->get_resp_headers(pSession->getHttpSession(),
                                        iov_key, iov_val, MAX_RESP_HEADERS_NUMBER);
    for (int i = 0; i < count; ++i)
    {
        memcpy(cp, iov_key[i].iov_base, iov_key[i].iov_len);
        cp += iov_key[i].iov_len;
        memcpy(cp, ": ", 2);
        cp += 2;
        memcpy(cp, iov_val[i].iov_base, iov_val[i].iov_len);
        cp += iov_val[i].iov_len;
        memcpy(cp, "\r\n", 2);
        cp += 2;
        *cp++ = '+';
        size += iov_key[i].iov_len + iov_val[i].iov_len + 5;
    }
    // *cp = 0;
    if (size)
    {
        --cp;
        --size;
        *cp = 0;
        LsLuaApi::pushlstring(L, bigout, size);
    }
    else
        LsLuaApi::pushnil(L);

    return 1;
}


static int LsLuaRespToString(lua_State *L)
{
    char    buf[0x100];

    snprintf(buf, 0x100, "<ls.resp %p>", L);
    LsLuaApi::pushstring(L, buf);
    return 1;
}


static int LsLuaRespGc(lua_State *L)
{
    LsLuaLog(L, LSI_LOG_NOTICE, 0, "<ls.resp GC>");
    return 0;
}


static const luaL_Reg lsluaRespFuncs[] =
{
    { "get_headers",    LsLuaRespGetHeaders  },
    {NULL, NULL}
};


static const luaL_Reg lsluaRespMetaSub[] =
{
    {"__gc",        LsLuaRespGc},
    {"__tostring",  LsLuaRespToString},
    {NULL, NULL}
};


void LsLuaCreateRespmeta(lua_State *L)
{
    LsLuaApi::openlib(L, LS_LUA ".resp", lsluaRespFuncs, 0);
    LsLuaApi::newmetatable(L, LSLUA_RESP);
    LsLuaApi::openlib(L, NULL, lsluaRespMetaSub, 0);

    // pushliteral
    LsLuaApi::pushlstring(L, "__index", 7);
    LsLuaApi::pushvalue(L, -3);
    LsLuaApi::rawset(L, -3);        // metatable.__index = methods
    // pushliteral
    LsLuaApi::pushlstring(L, "__metatable", 11);
    LsLuaApi::pushvalue(L, -3);
    LsLuaApi::rawset(L, -3);        // metatable.__metatable = methods

    LsLuaApi::settop(L, -3);       // pop 2
}


void LsLuaCreateConstants(lua_State *L)
{
    LsLuaApi::pushinteger(L, 0);
    LsLuaApi::setfield(L, -2, "OK");
    LsLuaApi::pushinteger(L, -1);
    LsLuaApi::setfield(L, -2, "DECLINED");
    LsLuaApi::pushinteger(L, 0);
    LsLuaApi::setfield(L, -2, "DONE");
    LsLuaApi::pushinteger(L, -2);
    LsLuaApi::setfield(L, -2, "DENY");
}


void LsLuaCreateUD(lua_State *L)
{
    LsLuaApi::newuserdata(L, sizeof(char));
    LsLuaApi::newmetatable(L, LS_LUA_UDMETA);
    LsLuaApi::pushvalue(L, -3);
    LsLuaApi::setfield(L, -2, "__index");
    LsLuaApi::setmetatable(L, -2);
    LsLuaApi::setglobal(L, LS_LUA_UD);
    LsLuaApi::pop(L, 1);
    LsLuaApi::getglobal(L, LS_LUA_UD);
}


static int LsLuaGetArg(lua_State *L)
{
    int idx;
    lsi_param_t *rec;
    luaL_Buffer buf;
    LsLuaSession *pSession = LsLuaGetSession(L);
    int iRet;

    if ((iRet = LsLuaSession::checkHook(pSession, L, "getArg",
                                        LSLUA_HOOK_BODY)) != 0)
        return iRet;
    if (LsLuaApi::gettop(L) != 2)
        return LsLuaApi::invalidNArgError(L, "getArg");
    if ((iRet = LsLuaApi::checkArgType(L, 2, LUA_TNUMBER, "getArg")) != 0)
        return iRet;
    idx = LsLuaApi::tointeger(L, -1);
    if (idx == 1)
    {
        rec = pSession->getModParam();
        LsLuaApi::buffinit(L, &buf);
        LsLuaApi::addlstring(&buf,
                             (const char *)rec->ptr1,
                             rec->len1);
        LsLuaApi::pushresult(&buf);
    }
    else if (idx == 2)
        LsLuaApi::pushboolean(L,
                              pSession->isFlagSet(LLF_LUADONE));
    else
        return LsLuaApi::userError(L, "getArg", "Invalid index.");
    return 1;
}


static int LsLuaSetArg(lua_State *L)
{
    int idx;
    size_t len;
    const char *pOut;
    LsLuaSession *pSession = LsLuaGetSession(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "setArg",
                                        LSLUA_HOOK_BODY)) != 0)
        return iRet;
    if (LsLuaApi::gettop(L) != 3)
        return LsLuaApi::invalidNArgError(L, "setArg");

    if ((iRet = LsLuaApi::checkArgType(L, 2, LUA_TNUMBER, "setArg")) != 0)
        return iRet;
    idx = LsLuaApi::tointeger(L, 2);
    if (idx == 2)
    {

        if ((iRet = LsLuaApi::checkArgType(L, 3, LUA_TBOOLEAN, "setArg")) != 0)
            return iRet;
        if (LsLuaApi::toboolean(L, 3))
            pSession->setFlag(LLF_LUADONE);
        return 0;
    }
    else if (idx != 1)
        return LsLuaApi::userError(L, "setArg", "Invalid index.");

    if ((iRet = LsLuaApi::checkArgType(L, 3, LUA_TSTRING, "setArg")) != 0)
        return iRet;
    pOut = LsLuaApi::tolstring(L, 3, &len);
    pSession->setFlag(LLF_TRYSENDRESP);
    if (LsLuaEngine::writeToNextFilter(pSession->getModParam(),
                                       pSession->getUserParam(),
                                       pOut, len) < 0)
        return LsLuaApi::serverError(L, "setArg", "Writing to next filter"
                                     " resulted in an error");
    return 0;
}


void LsLuaCreateArgTable(lua_State *L)
{
    LsLuaApi::createtable(L, 0, 0);
    LsLuaApi::createtable(L, 0, 2);
    LsLuaApi::pushcclosure(L, LsLuaGetArg, 0);
    LsLuaApi::setfield(L, -2, "__index");
    LsLuaApi::pushcclosure(L, LsLuaSetArg, 0);
    LsLuaApi::setfield(L, -2, "__newindex");
    LsLuaApi::setmetatable(L, -2);
    LsLuaApi::setfield(L, -2, "arg");
}







