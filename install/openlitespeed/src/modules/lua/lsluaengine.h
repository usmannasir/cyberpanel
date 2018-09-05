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
#ifndef LSLUAENGINE_H
#define LSLUAENGINE_H

#include <ls.h>
#include <lsr/ls_str.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

struct lua_State;
class LsLuaFuncMap;
class LsLuaScript;
class LsLuaState;
class LsLuaSession;
class LsLuaFunc;
class LsLuaUserParam;
typedef struct ls_xloopbuf_s ls_xloopbuf_t;

class LsLuaEngine
{
public:
    enum LSLUA_TYPE
    {
        LSLUA_ENGINE_REGULAR = 0,
        LSLUA_ENGINE_JIT = 1,
    };
    LsLuaEngine();
    ~LsLuaEngine();

    static void setVersion(const char *buf, size_t len)
    {
        snprintf(s_aVersion, sizeof(s_aVersion) - 1, "%s %.*s",
                 s_aLuaName, (int)len, buf);
    }
    static const char *version()
    {   return s_aVersion;  }

    static int init();
    static int isReady(const lsi_session_t *session);

    static int runScript(const lsi_session_t *session, const char *scriptpath,
                         LsLuaUserParam *pUser, LsLuaSession **ppSession,
                         int iCurHook);
    static int runFilterScript(lsi_param_t *rec, const char *scriptpath,
                               LsLuaUserParam *pUser, LsLuaSession **ppSession,
                               int iCurHook);
    static int writeToNextFilter(lsi_param_t *rec, LsLuaUserParam *pUser,
                                 const char *pOut, int iOutLen);
    static void ref(LsLuaSession *pSession);
    static void unref(LsLuaSession *pSession);
    static int  loadRef(LsLuaSession *pSession, lua_State *L);

    static int resume(lua_State *L, int iArgs);
    static int checkResume(LsLuaSession *pSession, int iRet);
    static int resumeNcheck(LsLuaSession *pSession, int iArgs);

    static int testCmd();

    static lua_State *injectLsiapi(lua_State *L);

    static void *parseParam(module_param_info_t *param  , int param_count,
                            void *initial_config, int level,
                            const char *name);
    static void removeParam(void *config);

    static int getMaxRunTime()
    {   return s_iMaxRunTime;   }

    static int getMaxLineCount()
    {   return s_iMaxLineCount; }

    static int getPauseTime()
    {   return s_iPauseTime;    }

    static int getJitLineMod()
    {   return s_iJitLineMod;   }

    static const char *getLuaName()
    {   return s_aLuaName;      }

    static int debugLevel()
    {   return s_iDebugLevel;   }

    static void setDebugLevel(int level)
    {   s_iDebugLevel = level;  }

    static int debug()
    {   return s_iDebug;        }

private:
    static lua_State *getSystemState()
    {   return s_pSystemState;  }
    static void setupUD(lua_State *L);
    static int setupSandBox(lua_State *L);
    static int execLuaCmd(const char *cmd);
    static lua_State *newLuaConnection();
    static lua_State *newLuaThread(lua_State *L);
    static LsLuaSession *prepState(const lsi_session_t *session,
                                   const char *scriptpath,
                                   LsLuaUserParam *pUser,
                                   int iCurHook);
    static int runState(const lsi_session_t *session, LsLuaSession *pSandbox,
                        int iCurHook);
    static int respFilterSetup(lsi_param_t *rec, lua_State *L);
    static int filterOut(lsi_param_t *rec, const char *pBuf, int iLen);

private:
    LsLuaEngine(const LsLuaEngine &other);
    LsLuaEngine &operator=(const LsLuaEngine &other);
    bool operator==(const LsLuaEngine &other);
private:
    static const char  *s_pSysLuaLib;
    static const char  *s_pSysLuaPath;
    static lua_State   *s_pSystemState;
    static LSLUA_TYPE   s_type;
    static int          s_iReady;
    //
    //  module parameters
    //
    static char        *s_pLuaLib;
    static char        *s_pLuaPath;
    static int
    s_iDebug;        // note: this is internal debug for LUA
    static int          s_iMaxRunTime;   // max allowable runtime in msec
    static int          s_iMaxLineCount; // time to throddle
    static int          s_iPauseTime;    // time to pause in msec
    static int          s_iJitLineMod;   // modifier for JIT
    static int
    s_iFirstTime;    // detect very first time parameter parsing
    static int          s_iDebugLevel;   // current web server debug level
    static char         s_aLuaName[0x10];// 15 bytes to save the name
    static char         s_aVersion[0x20];// 31 bytes for LUA information
};

//
//  @Container for all loaded LUA functions
//  @loadLuaScript - load LUA script file into the container, return status (see below)
//
//  @ scriptName - return the name of the script
//  @ funcName - LiteSpeed internal name of the script
//  @ status - 1 good. 0 not ready, -1 syntax error, -2 LUA error
//
class LsLuaFuncMap
{
public:
    static int loadLuaScript(const lsi_session_t *session, lua_State *L,
                             const char *scriptName);

    const char *scriptName() const
    {   return m_pScriptName;   }
    const char *funcName() const
    {   return m_pFuncName;     }

    int isReady() const
    {   return m_iStatus == 1 ? 1 : 0;  }

    int status() const
    {   return m_iStatus;   }

private:
    LsLuaFuncMap(const lsi_session_t *session, lua_State *L,
                 const char *scriptName);
    LsLuaFuncMap();
    ~LsLuaFuncMap();

    LsLuaFuncMap(const LsLuaFuncMap &other);
    LsLuaFuncMap &operator=(const LsLuaFuncMap &other);
    bool operator==(const LsLuaFuncMap &other);

    void add();
    void remove();
    void loadLuaFunc(lua_State *L);
    void unloadLuaFunc(lua_State *L);

    static const char *textFileReader(lua_State *L, void *d,
                                      size_t *retSize);

    char                *m_pScriptName;
    char                *m_pFuncName;
    int                  m_iStatus;
    LsLuaFuncMap        *m_pNext;
    struct stat          m_stat;

    static LsLuaFuncMap *s_pMap;
    static int           s_iMapCnt;
};

class LsLuaUserParam
{
public:
    LsLuaUserParam(int level)
        : m_iMaxRunTime(LsLuaEngine::getMaxRunTime())
        , m_iMaxLineCount(LsLuaEngine::getMaxLineCount())
        , m_iLevel(level)
        , m_iReady(1)
        , m_pPendingBuf(NULL)
    {
        ls_str(&m_rewritePath, NULL, 0);
        ls_str(&m_authPath, NULL, 0);
        ls_str(&m_headerFilterPath, NULL, 0);
        ls_str(&m_bodyFilterPath, NULL, 0);
    }

    ~LsLuaUserParam()
    {
        ls_str_d(&m_rewritePath);
        ls_str_d(&m_authPath);
        ls_str_d(&m_headerFilterPath);
        ls_str_d(&m_bodyFilterPath);
    };

    int isReady() const
    {   return m_iReady;    }

    void setReady(int flag)
    {   m_iReady = flag;    }

    void setLevel(int level)
    {   m_iLevel = level;   }

    int getLevel() const
    {   return m_iLevel;    }

    int getMaxRunTime() const
    {   return m_iMaxRunTime;   }

    int getMaxLineCount() const
    {   return m_iMaxLineCount; }

    void setMaxRunTime(int maxTime)
    {   m_iMaxRunTime = maxTime; }

    void setMaxLineCount(int maxLine)
    {   m_iMaxLineCount = maxLine; }

    int isFilterActive(int index)
    {
        ls_str_t *pBuf = getPathBuf(index);
        if (!pBuf)
            return 0;
        return (ls_str_cstr(getPathBuf(index)) ? 1 : 0);
    }

    const char *getFilterPath(int index, int &iPathLen)
    {
        ls_str_t *pBuf = getPathBuf(index);
        if (!pBuf)
            return NULL;
        iPathLen = ls_str_len(pBuf);
        return ls_str_cstr(pBuf);
    }

    void setFilterPath(int index, const char *path, int iPathLen)
    {
        ls_str_t *pBuf = getPathBuf(index);
        if (!pBuf)
            return;
        ls_str_dup(pBuf, path, iPathLen);
    }

    ls_xloopbuf_t *getPendingBuf()
    {   return m_pPendingBuf;    }

    void setPendingBuf(ls_xloopbuf_t *pBuf)
    {   m_pPendingBuf = pBuf;    }

    void clearPendingBuf()
    {   m_pPendingBuf = NULL;    }

    LsLuaUserParam &operator= (const LsLuaUserParam &other)
    {
        m_iMaxRunTime = other.m_iMaxRunTime;
        m_iMaxLineCount = other.m_iMaxLineCount;
        m_iReady = other.m_iReady;
        return *this;
    }
private:
    LsLuaUserParam(const LsLuaUserParam &other);
    bool operator==(const LsLuaUserParam &other);

    ls_str_t *getPathBuf(int index);

    int         m_iMaxRunTime;   // max allowable runtime in msec
    int         m_iMaxLineCount; // time to throddle
    int         m_iLevel;
    int         m_iReady;
    ls_str_t   m_rewritePath;
    ls_str_t   m_authPath;
    ls_str_t   m_headerFilterPath;
    ls_str_t   m_bodyFilterPath;
    ls_xloopbuf_t *m_pPendingBuf;
};

#endif // LSLUAENGINE_H
