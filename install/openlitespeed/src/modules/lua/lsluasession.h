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
#ifndef LSLUAREQ_H
#define LSLUAREQ_H

#include "edluastream.h"
#include "lsluaapi.h"
#include "lsluaengine.h"

#include <ls.h>

#include <stddef.h>
#include <inttypes.h>


class LsLuaStreamData;
class LsLuaTimerData;


//
//  Callback function type - reversed LsLuaSession and lua_State for purpose
//
typedef void (* pf_sleeprestart)(LsLuaSession *, lua_State *);

class LsLuaSession
{
public:
    LsLuaSession();
    ~LsLuaSession();

    void init(const lsi_session_t *pSession, int iCurHook)
    {
        m_pHttpSession = pSession;
        m_pState = NULL;
        m_iCurHook = iCurHook;
    }

    int setupLuaEnv(lua_State *L, LsLuaUserParam *pUser);

    static LsLuaSession *getSelf(lua_State *L);

    inline const lsi_session_t *getHttpSession() const
    {   return m_pHttpSession;      }

    inline lua_State *getLuaState() const
    {   return m_pState;      }

    inline lua_State *getLuaStateMom() const
    {   return m_pStateMom;      }

    inline void clearState()
    {   m_pState = NULL, m_pStateMom = NULL; m_pHttpSession = NULL; }

    // static LsLuaSession *  findByLsiSession ( const lsi_session_t * pSession);
    // static LsLuaSession *  findByLuaState ( const lua_State * L);

    inline void setFlag(uint32_t iFlag)
    {   m_iFlags |= iFlag;  }
    inline int isFlagSet(uint32_t iFlag) const
    {   return m_iFlags & iFlag;    }
    inline void clearFlag(uint32_t iFlag)
    {   m_iFlags &= ~iFlag; }

    inline void setLuaExitCode(int code)
    {   m_iExitCode = code;  }

    inline int getLuaExitCode() const
    {   return m_iExitCode;  }

    inline int key() const
    {   return m_iKey; }

    void    resume(lua_State *, int numarg);

    // schedule a LUA state timer
    void    setTimer(int msec, pf_sleeprestart, lua_State *, int flag);

    static EdLuaStream *newEdLuaStream(lua_State *); // used for allocator
    void closeAllStream();                  // called by end of session
    void markCloseStream(lua_State *,
                         EdLuaStream *);   // called by GC incase LUA GC is active

    inline LsLuaTimerData *endTimer() const
    {   return m_pEndTimer; }

    inline LsLuaTimerData *maxRunTimer() const
    {   return m_pMaxTimer; }

    static inline void trace(const char *tag, LsLuaSession *pSess,
                             lua_State *L)
    {
        LsLuaLog(L, LSI_LOG_NOTICE, 0,
                 "TRACE %s {%p, %p} [%p %p] %d %d",
                 tag, pSess, L,
                 pSess ? pSess->getLuaState() : NULL, pSess->getHttpSession(),
                 pSess->m_iKey,
                 pSess->isFlagSet(LLF_LUADONE)
                );
    }
    inline int *getRefPtr()
    {   return &m_iRef; }
    inline int  getRef() const
    {   return m_iRef; }

    inline int getTop() const
    {   return m_iTop; };
    inline void setTop(int top)
    {   m_iTop = top; };

    //
    // Checks if the Lua session is called before iHkpt
    //
    inline int checkHookBefore(int iHkpt)
    {   return m_iCurHook & iHkpt; }

    static int checkHook(LsLuaSession *pSession, lua_State *L,
                         const char *pSrc, int idx)
    {
        if (pSession->checkHookBefore(idx) == 0)
        {
            LsLuaLog(L, LSI_LOG_DEBUG, 0,
                     "%s: Called at invalid hook point", pSrc);
            return LsLuaApi::error(L, "Called at invalid hook point");
        }
        return 0;
    }

    inline void *getFilterBuf()
    {   return m_pFilterBuf;    }

    inline void setFilterBuf(void *pBuf)
    {   m_pFilterBuf = pBuf;    }

    inline LsLuaUserParam *getUserParam()
    {   return m_pUserParam;    }

    inline lsi_param_t *getModParam()
    {   return m_pModParam;    }

    inline void setUserParam(LsLuaUserParam *pParam)
    {   m_pUserParam = pParam;  }

    inline void setModParam(lsi_param_t *pParam)
    {   m_pModParam = pParam;  }

    void releaseTimer();

    // resp control
    int onWrite(const lsi_session_t *httpSession);     // called by modlua.c
    int wait4RespBuffer(lua_State *L);

    static int endSession(LsLuaSession *);
private:
    lua_State     *m_wait4RespBuf_L;

private:
    LsLuaSession(const LsLuaSession &other);
    LsLuaSession &operator=(const LsLuaSession &other);
    bool operator==(const LsLuaSession &other);

private:
    const lsi_session_t    *m_pHttpSession;
    lua_State        *m_pState;
    lua_State        *m_pStateMom;        // save the parent state

    //
    //  LUA status
    //
    uint32_t          m_iFlags;
    int               m_iExitCode;       // from ls.exit
    int               m_iKey;            // my key
    int               m_iRef;            // my ref for LUA
    int               m_iTop;
    int               m_iCurHook;       // Current hook point.
    void             *m_pFilterBuf;
    LsLuaTimerData   *m_pEndTimer;      // track the last endTimer
    LsLuaTimerData   *m_pMaxTimer;      // track the maxTimer
    LsLuaStreamData *m_pStream;         // my stream pool
    LsLuaUserParam   *m_pUserParam;
    lsi_param_t   *m_pModParam;

    // Need to track all LUA installed timer
    LsLuaTimerData   *m_pTimerList;
    void addTimerToList(LsLuaTimerData *pTimerData);
    void rmTimerFromList(LsLuaTimerData *pTimerData);
    void releaseTimerList();
    void dumpTimerList(const char *tag);

    //
    // We don't allow to use std::map...
    // Then build a linear list to track the session for now.
    //
    void clearLuaStatus();
    static int  s_iKey;              // System wide unique key

    // callback timer
    static void timerCb(const void *);

    // reach max runtime callback
    // static void maxruntimeCb(void *);
    static void maxRunTimeCb(LsLuaSession *pSession, lua_State *L);

    //
    // Hook point for LUA line hook + Lsi timer callback
    //
    static void luaLineLooper(LsLuaSession *pSession, lua_State *L);
    static void luaLineHookCb(lua_State *L, lua_Debug *ar);
    inline void upLuaCounter()
    { m_iLuaLineCount++; }
    u_int32_t m_iLuaLineCount;    // counter how many time this got called
public:
    u_int32_t getLuaCounter()
    { return m_iLuaLineCount; }
};

void LsLuaCreateConstants(lua_State *L);
void LsLuaCreateUD(lua_State *L);
void LsLuaCreateSession(lua_State *L);
void LsLuaCreateRegexmeta(lua_State *L);
void LsLuaCreateReqmeta(lua_State *L);
void LsLuaCreateRespmeta(lua_State *L);
void LsLuaCreateSessionmeta(lua_State *L);
void LsLuaCreateArgTable(lua_State *L);

//
//  keep track of EdStream
//
class LsLuaStreamData
{
public: // no need to protect myself
    LsLuaStreamData(EdLuaStream *sock, LsLuaStreamData *_next)
        : m_pSock(sock)
        , m_pNext(_next)
        , m_pActive(1)
    {
    }
    inline EdLuaStream *stream() const
    { return m_pSock; }
    inline int isActive() const
    {   return m_pActive; }
    inline void setNotActive()
    { m_pActive = 0; }
    inline LsLuaStreamData *next() const
    { return m_pNext; }
    inline int isMatch(EdLuaStream *sock)
    { return sock == m_pSock; }
    void close(lua_State *);
private:
    LsLuaStreamData();
    LsLuaStreamData(const LsLuaStreamData &other);
    LsLuaStreamData &operator=(const LsLuaStreamData &other);
    bool operator==(const LsLuaStreamData &other);
private:
    EdLuaStream *m_pSock;
    LsLuaStreamData *m_pNext;
    int m_pActive; // the stream still active
};

//
//  for Timer callback
//
class LsLuaTimerData
{
public: // no need to protect myself
    LsLuaTimerData(LsLuaSession *pSession, pf_sleeprestart func, lua_State *L)
    {
        m_iKey = pSession->key();
        m_pFunc = func;
        m_pSession = pSession;
        m_pState = L;
        m_iDeleteFlag = 0;
        m_iTimerId = 0;
        m_pNext = NULL;
    }
    ~LsLuaTimerData() { m_iKey = 0; }
    int key() const
    {   return m_iKey; }
    LsLuaSession *session() const
    {   return m_pSession; }
    lua_State *L() const
    {   return m_pState; }
    void timerCallBack() const
    {   (*m_pFunc)(m_pSession, m_pState); }
    int flag() const
    {   return m_iDeleteFlag; }
    void setFlag(int flag)
    {   m_iDeleteFlag = flag; }
    int id() const
    {   return m_iTimerId; }
    void setId(int id)
    {   m_iTimerId = id; }

    LsLuaTimerData *next()
    {   return m_pNext; }

    void setNext(LsLuaTimerData *pTimerData)
    {   m_pNext = pTimerData; }

private:
    LsLuaTimerData();
    LsLuaTimerData(const LsLuaTimerData &other);
    LsLuaTimerData &operator=(const LsLuaTimerData &other);
    bool operator==(const LsLuaTimerData &other);
private:
    int             m_iDeleteFlag;         // Session deleted
    int             m_iKey;
    pf_sleeprestart m_pFunc;
    LsLuaSession   *m_pSession;
    lua_State      *m_pState;
    int             m_iTimerId;
    LsLuaTimerData *m_pNext;       // track the timer by each LUA Session
};

#endif // LSLUAREQ_H
