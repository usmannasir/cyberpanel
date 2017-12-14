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
#ifndef LSLUAAPI_H
#define LSLUAAPI_H

#include "lsluadefs.h"

#include <ls.h>

#include <string.h>


// #define LSLUA_QUICK_DUMP( L ) LsLuaApi::dumpStack( L, "quick dump", 10 )

class LsLuaSession;
#ifdef __cplusplus
extern "C" {
#endif

typedef struct ls_luabuf_s
{
    char *begin;
    char *end;
    char *cur;

} ls_luabuf_t;

typedef int (*print_flush)(void *pOutput, const char *pBuf,
                           int len, int *pFlag);

typedef struct ls_luaprint_s
{
    void               *param;
    print_flush         flush;
    int                 flag;
    ls_luabuf_t  buffer;
} ls_luaprint_t;

int LsLuaPrint(lua_State *L, ls_luaprint_t *pStream);

void LsLuaLog(lua_State *L, int level, int no_linefeed,
              const char *fmt, ...);

void LsLuaLogRawbuf(const char *pStr, int len);

int  LsLuaLogEx(lua_State *L, int level);

LsLuaSession *LsLuaGetSession(lua_State *L);

int LsLuaSetSession(lua_State *L, LsLuaSession *pSession);

// Lua functions
typedef void (*pf_addlstring)(luaL_Buffer *, const char *, size_t);
typedef void (*pf_addsize)(luaL_Buffer *, size_t);
typedef void (*pf_addstring)(luaL_Buffer *, const char *);
typedef void (*pf_addvalue)(luaL_Buffer *);
typedef void (*pf_buffinit)(lua_State *, luaL_Buffer *);
typedef void        *(*pf_checkudata)(lua_State *, int, const char *);
typedef void (*pf_close)(lua_State *);
typedef void (*pf_concat)(lua_State *, int);
typedef void (*pf_createtable)(lua_State *, int, int);
typedef int (*pf_error)(lua_State *, const char *, ...);
typedef int (*pf_gc)(lua_State *, int, int);
typedef void (*pf_getfenv)(lua_State *, int);
typedef void (*pf_getfield)(lua_State *, int, const char *);
typedef void (*pf_getglobal)(lua_State *, const char *);
typedef int (*pf_getmetatable)(lua_State *, int);
typedef void (*pf_gettable)(lua_State *, int);
typedef int (*pf_gettop)(lua_State *);
typedef int (*pf_insert)(lua_State *, int);
typedef int (*pf_load)(lua_State *, lua_Reader, void *,
                       const char *, const char *);
typedef int (*pf_loadstring)(lua_State *, const char *);
typedef int (*pf_newmetatable)(lua_State *, const char *);
typedef lua_State   *(*pf_newstate)();
typedef lua_State   *(*pf_newthread)(lua_State *);
typedef void        *(*pf_newuserdata)(lua_State *, size_t);
typedef int (*pf_next)(lua_State *, int);
typedef size_t (*pf_objlen)(lua_State *, int);
typedef void (*pf_openlib)(lua_State *, const char *,
                           const luaL_Reg *, int);
typedef void (*pf_openlibs)(lua_State *);
typedef char        *(*pf_prepbuffer)(luaL_Buffer *);
typedef char        *(*pf_prepbuffsize)(luaL_Buffer *, size_t);
typedef void (*pf_pushboolean)(lua_State *, int);
typedef void (*pf_pushcclosure)(lua_State *, lua_CFunction, int);
typedef const char *(*pf_pushfstring)(lua_State *, const char *, ...);
typedef void (*pf_pushinteger)(lua_State *, int);
typedef void (*pf_pushlightuserdata)(lua_State *, void *);
typedef void (*pf_pushlstring)(lua_State *, const char *, size_t);
typedef void (*pf_pushnil)(lua_State *);
typedef void (*pf_pushnumber)(lua_State *, lua_Number);
typedef void (*pf_pushresult)(luaL_Buffer *);
typedef void (*pf_pushstring)(lua_State *, const char *);
typedef void (*pf_pushthread)(lua_State *);
typedef void (*pf_pushvalue)(lua_State *, int);
typedef const char *(*pf_pushvfstring)(lua_State *, const char *,
                                       va_list);
typedef void (*pf_rawget)(lua_State *, int);
typedef void (*pf_rawgeti)(lua_State *, int, int);
typedef size_t (*pf_rawlen)(lua_State *, int);
typedef void (*pf_rawset)(lua_State *, int);
typedef void (*pf_rawseti)(lua_State *, int, int);
typedef int (*pf_ref)(lua_State *, int);
typedef void (*pf_remove)(lua_State *, int);
typedef void (*pf_replace)(lua_State *, int);
typedef int (*pf_setfenv)(lua_State *, int);
typedef int (*pf_setfield)(lua_State *, int, const char *);
typedef void (*pf_setglobal)(lua_State *, const char *);
typedef void (*pf_setmetatable)(lua_State *, int);
typedef void (*pf_settable)(lua_State *, int);
typedef void (*pf_settop)(lua_State *, int);
typedef int (*pf_toboolean)(lua_State *, int);
typedef lua_CFunction(*pf_tocfunction)(lua_State *, int);
typedef const char *(*pf_tolstring)(lua_State *, int, size_t *);
typedef const void *(*pf_topointer)(lua_State *, int);
typedef lua_State   *(*pf_tothread)(lua_State *, int);
typedef void        *(*pf_touserdata)(lua_State *, int);
typedef int (*pf_type)(lua_State *, int);
typedef void (*pf_unref)(lua_State *, int, int);
typedef void (*pf_xmove)(lua_State *, lua_State *, int);

// Patches for 5.1 vs 5.2

typedef int (*pf_loadfile)(lua_State *, const char *);
typedef int (*pf_loadfilex)(lua_State *, const char *, const char *);
typedef int (*pf_pcall)(lua_State *, int, int, int);
typedef int (*pf_pcallk)(lua_State *, int, int, int, int, lua_CFunction);
typedef int (*pf_resume)(lua_State *, int);
typedef int (*pf_resumeP)(lua_State *, lua_State *, int);
typedef int (*pf_tointeger)(lua_State *, int);
typedef int (*pf_tointegerx)(lua_State *, int, int *);
typedef double(*pf_tonumber)(lua_State *, int);
typedef double(*pf_tonumberx)(lua_State *, int, int *);
typedef int (*pf_yield)(lua_State *, int);
typedef int (*pf_yieldk)(lua_State *, int, int, lua_CFunction);

// DEBUG LIB
typedef int (*pf_getinfo)(lua_State *, const char *, lua_Debug *);
typedef int (*pf_sethook)(lua_State *, lua_Hook, int, int);
typedef const char *(*pf_setupvalue)(lua_State *, int, int);

#ifdef __cplusplus
}
#endif


class LsLuaApi
{
public:
    LsLuaApi();
    ~LsLuaApi();

    static const char *init(const char *pModuleName);

    static inline int jitMode()
    {   return s_iJitMode;  }

    static inline void setJitMode(int iJitMode)
    {   s_iJitMode = iJitMode;  }

    inline static void pop(lua_State *L, int n)
    {   LsLuaApi::settop(L, -(n) - 1);    }

    inline static int compileLuaCmd(lua_State *L, const char *cmd)
    {   return LsLuaApi::loadstring(L, cmd);    }

    inline static int execLuaCmd(lua_State *L, const char *cmd)
    {
        int ret = compileLuaCmd(L, cmd);
        if (ret != 0)
            return ret;
        return LsLuaApi::pcall(L, 0, LUA_MULTRET, 0);
    }

    static void pushglobaltable(lua_State *L)
    {
        if (LsLuaApi::jitMode())
            LsLuaApi::pushvalue(L,
                                LSLUA_GLOBALSINDEX);
        else
            LsLuaApi::rawgeti(L,
                              LSLUA_REGISTRYINDEX,
                              LSLUA_RIDX_GLOBALS);
    }

    static int upvalueindex(int i)
    {
        if (LsLuaApi::jitMode())
            return LSLUA_GLOBALSINDEX - i;
        else
            return LSLUA_REGISTRYINDEX - i;
    }

    inline static void dumpStackCount(lua_State *L, const char *tag)
    {
        LsLuaLog(L, LSI_LOG_INFO, 0, "%s STACK[%d]", tag,
                 LsLuaApi::gettop(L));
    }

    static int dumpIdx2Buf(lua_State *L, int idx, char *buf, int bufLen);

    static void dumpStack(lua_State *L, const char *tag, int num);

    static void dumpStack2Http(lsi_session_t *session, lua_State *L,
                               const char *tag, int num);

    //NOTICE: This function assumes that the table is at the top of the stack.
    static void dumpTable(lua_State *L);

    static int doString(lua_State *L, const char *str);

    static int checkArgType(lua_State *L, int idx, int iType,
                            const char *pSrc)
    {
        if (LsLuaApi::type(L, idx) != iType)
        {
            LsLuaLog(L, LSI_LOG_DEBUG, 0, "%s: invalid arg type, arg %d\n",
                     pSrc, idx);
            return LsLuaApi::error(L, "Invalid Arg: %d\n", idx);
        }
        return 0;
    }

    static int invalidNArgError(lua_State *L, const char *pSrc)
    {
        LsLuaLog(L, LSI_LOG_DEBUG, 0,
                 "%s Invalid number of arguments.", pSrc);
        return LsLuaApi::error(L, "Invalid number of args.");
    }

    static int serverError(lua_State *L, const char *pSrc, const char *pMsg)
    {
        LsLuaLog(L, LSI_LOG_INFO, 0, "%s: %s", pSrc, pMsg);
        LsLuaApi::pushnil(L);
        LsLuaApi::pushstring(L, pMsg);
        return 2;
    }

    static int userError(lua_State *L, const char *pSrc, const char *pMsg)
    {
        LsLuaLog(L, LSI_LOG_DEBUG, 0, "%s: %s", pSrc, pMsg);
        return LsLuaApi::error(L, pMsg);
    }


    // Lua functions
    static pf_addlstring        addlstring;
    static pf_addsize           addsize;
    static pf_addstring         addstring;
    static pf_addvalue          addvalue;
    static pf_buffinit          buffinit;
    static pf_checkudata        checkudata;
    static pf_close             close;
    static pf_concat            concat;
    static pf_createtable       createtable;
    static pf_error             error;
    static pf_gc                gc;
    static pf_getfenv           getfenv;
    static pf_getfield          getfield;
    static pf_getglobal         getglobal;
    static pf_getmetatable      getmetatable;
    static pf_gettable          gettable;
    static pf_gettop            gettop;
    static pf_insert            insert;
    static pf_load              load;
    static pf_loadstring        loadstring;
    static pf_newmetatable      newmetatable;
    static pf_newstate          newstate;
    static pf_newthread         newthread;
    static pf_newuserdata       newuserdata;
    static pf_next              next;
    static pf_objlen            objlen;
    static pf_openlib           openlib;
    static pf_openlibs          openlibs;
    static pf_prepbuffer        prepbuffer;
    static pf_prepbuffsize      prepbuffsize;
    static pf_pushboolean       pushboolean;
    static pf_pushcclosure      pushcclosure;
    static pf_pushfstring       pushfstring;
    static pf_pushinteger       pushinteger;
    static pf_pushlightuserdata pushlightuserdata;
    static pf_pushlstring       pushlstring;
    static pf_pushnil           pushnil;
    static pf_pushnumber        pushnumber;
    static pf_pushresult        pushresult;
    static pf_pushstring        pushstring;
    static pf_pushthread        pushthread;
    static pf_pushvalue         pushvalue;
    static pf_pushvfstring      pushvfstring;
    static pf_rawget            rawget;
    static pf_rawgeti           rawgeti;
    static pf_rawlen            rawlen;
    static pf_rawset            rawset;
    static pf_rawseti           rawseti;
    static pf_ref               ref;
    static pf_remove            remove;
    static pf_replace           replace;
    static pf_setfenv           setfenv;
    static pf_setfield          setfield;
    static pf_setglobal         setglobal;
    static pf_setmetatable      setmetatable;
    static pf_settable          settable;
    static pf_settop            settop;
    static pf_toboolean         toboolean;
    static pf_tocfunction       tocfunction;
    static pf_tolstring         tolstring;
    static pf_topointer         topointer;
    static pf_tothread          tothread;
    static pf_touserdata        touserdata;
    static pf_type              type;
    static pf_unref             unref;
    static pf_xmove             xmove;

    // Patches
    static pf_loadfile          loadfile;
    static pf_pcall             pcall;
    static pf_resume            resume;
    static pf_tointeger         tointeger;
    static pf_tonumber          tonumber;
    static pf_yield             yield;

    // Debug library
    static pf_getinfo           getinfo;
    static pf_sethook           sethook;
    static pf_setupvalue        setupvalue;

private:
    LsLuaApi(const LsLuaApi &other);
    LsLuaApi &operator=(const LsLuaApi &other);
    bool operator==(const LsLuaApi &other);

    static int s_iJitMode;
    static void *s_pLib;

    // Patched version of functions.
    static pf_loadfilex loadfilex;
    static pf_pcallk pcallk;
    static pf_resumeP resumeP;
    static pf_tointegerx tointegerx;
    static pf_tonumberx tonumberx;
    static pf_yieldk yieldk;

    static const char *loadConditional(void *pLib);

    // Version Patches.
    static inline int lsLoadfilePatch(lua_State *L, const char *filename)
    {   return LsLuaApi::loadfilex(L, filename, NULL);    }

    static inline int lsPcallPatch(lua_State *L, int nargs, int nresults,
                                   int msgh)
    {   return LsLuaApi::pcallk(L, nargs, nresults, msgh, 0, NULL);   }

    static inline char *lsPrepBuffer(luaL_Buffer *B)
    {   return LsLuaApi::prepbuffsize(B, LUAL_BUFFERSIZE);    }

    static inline int lsResumePatch(lua_State *L, int narg)
    {   return LsLuaApi::resumeP(L, NULL, narg); }

    static inline int lsToIntegerPatch(lua_State *L, int index)
    {   return LsLuaApi::tointegerx(L, index, NULL);  }

    static inline double lsToNumberPatch(lua_State *L, int index)
    {   return LsLuaApi::tonumberx(L, index, NULL);  }

    static inline int lsYieldPatch(lua_State *L, int nresults)
    {   return LsLuaApi::yieldk(L, nresults, 0, NULL);    }


    // Define Patches.
    static inline void lsAddSize(luaL_Buffer *B, size_t sz)
    {   luaL_addsize(B, sz);  }

    static inline void lsGetGlobal(lua_State *L, const char *name)
    {   LsLuaApi::getfield(L, LSLUA_GLOBALSINDEX, name);    }

    static inline void lsSetGlobal(lua_State *L, const char *name)
    {   LsLuaApi::setfield(L, LSLUA_GLOBALSINDEX, name);    }


};

#endif // LSLUAAPI_H
