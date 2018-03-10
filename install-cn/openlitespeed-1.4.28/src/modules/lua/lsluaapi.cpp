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
#include "lsluaapi.h"

#include "edluastream.h"
#include "lsluaengine.h"
#include "lsluasession.h"

#include <log4cxx/layout.h>
#include <log4cxx/logger.h>

#include <ctype.h>
#include <dlfcn.h>
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>


// #define LSLUAAPI_DEBUGPRINT

void LsLuaCreateShared(lua_State *);
void LsLuaCreateSharedmeta(lua_State *);

int LsLuaApi::s_iJitMode = 0;
void *LsLuaApi::s_pLib = NULL;


static LOG4CXX_NS::Logger  *s_pLogger           = NULL;
static char                 s_logPattern[40]    = "%d [%p] [LUA] %m";

static LOG4CXX_NS::Logger *getLogger()
{
    if (s_pLogger)
        return s_pLogger;
    s_pLogger = LOG4CXX_NS::Logger::getLogger("LUA");
    LOG4CXX_NS::Layout *pLayout =
        LOG4CXX_NS::Layout::getLayout("lua_log_pattern",
                                      "layout.pattern");

    pLayout->setUData(s_logPattern);
    s_pLogger->setLayout(pLayout);
    s_pLogger->setLevel(LSI_LOG_INFO);   // NOTICE - use member value instead!
    s_pLogger->setParent(LOG4CXX_NS::Logger::getRootLogger());
    return s_pLogger;
}


void LsLuaLog(lua_State *L, int level, int no_linefeed,
              const char *fmt, ...)
{
    if (level >= LsLuaEngine::debugLevel())
    {
        char achNewFmt[1024];
        va_list arglist;
        va_start(arglist, fmt);
        snprintf(achNewFmt, 1023, "[%p] %s", L, fmt);
        getLogger()->vlog(level, achNewFmt, arglist, no_linefeed);
        va_end(arglist);
    }
}


void LsLuaLogRawbuf(const char *pStr, int len)
{
    getLogger()->lograw(pStr, len);
}


static int LsLuaPrintToLog(lua_State *L)
{
    LsLuaLogEx(L, LSI_LOG_INFO);
    return 0;
}


static int LsLuaDummy(lua_State *L)
{
    LsLuaLog(L, LSI_LOG_INFO, 0, "IN DUMMY");
    return 0;
}


int LsLuaApi::doString(lua_State *L, const char *str)
{
    return LsLuaApi::loadstring(L, str)
           || LsLuaApi::pcall(L, 0, LUA_MULTRET, 0);
}



extern void LsLuaCreateHeader(lua_State *);


int LsLuaCppFuncSetup(lua_State *L)
{
    /*
    *   (1) overwritten the print
    *   (2) setup LiteSpeed space
    *   (3) load LiteSpeed functions
    */
    LsLuaApi::pushcclosure(L, LsLuaPrintToLog, 0);
    LsLuaApi::setglobal(L, "print");
    LsLuaApi::pushcclosure(L, LsLuaDummy, 0);
    LsLuaApi::setglobal(L, "dummy");

    LsLuaCreateSession(L);
    LsLuaCreateConstants(L);
    LsLuaCreateTcpsockmeta(L);
    LsLuaCreateReqmeta(L);
    LsLuaCreateRespmeta(L);
    LsLuaCreateRegexmeta(L);
    LsLuaCreateArgTable(L);

    /* put in header */
    LsLuaCreateHeader(L);

    /* put in shared */
    LsLuaCreateSharedmeta(L);
    LsLuaCreateShared(L);

    LsLuaCreateSessionmeta(L);
    return 0;
}


static int LsLuaPrintIdx(lua_State *L, int idx,
                         ls_luaprint_t *pStream);


static int LsLuaPrintTable(lua_State *L, ls_luaprint_t *pStream)
{
    int iKey, iMaxIdx = 0;

    LsLuaApi::pushnil(L);
    while (LsLuaApi::next(L, -2))
    {
        if (LsLuaApi::type(L, -2) != LUA_TNUMBER)
        {
            LsLuaApi::pop(L, 2);
            return LS_FAIL;
        }
        iKey = LsLuaApi::tointeger(L, -2);
        if (iKey > iMaxIdx)
            iMaxIdx = iKey;
        LsLuaApi::pop(L, 1);
    }

    for (iKey = 1; iKey <= iMaxIdx; ++iKey)
    {
        LsLuaApi::rawgeti(L, -1, iKey);
        LsLuaPrintIdx(L, -1, pStream);
        LsLuaApi::pop(L, 1);
    }
    return 0;
}


static int LsLuaPrintIdx(lua_State *L, int idx,
                         ls_luaprint_t *pStream)
{
    void           *pUData;
    size_t          iSize;
    int    iType;
    const char     *pString;
    ls_luabuf_t *pBuf = &pStream->buffer;

    if (pBuf->end - pBuf->cur <= LSLUA_PRINT_MAX_FRAG_SIZE)
    {
        if (pStream->flush(pStream->param, pBuf->begin,
                           pBuf->cur - pBuf->begin,
                           &pStream->flag) == -1)
            return LS_FAIL;
        pBuf->cur = pBuf->begin;
    }

    iType = LsLuaApi::type(L, idx);
    switch (iType)
    {
    case LUA_TNONE:
        *pBuf->cur++ = 'n';
        *pBuf->cur++ = 'o';
        *pBuf->cur++ = 'n';
        *pBuf->cur++ = 'e';
        break;
    case LUA_TNIL:
        *pBuf->cur++ = 'n';
        *pBuf->cur++ = 'i';
        *pBuf->cur++ = 'l';
        break;
    case LUA_TSTRING:
        pString = LsLuaApi::tolstring(L, idx, &iSize);
        if (iSize < LSLUA_PRINT_MAX_FRAG_SIZE)
        {
            memcpy(pBuf->cur, pString, iSize);
            pBuf->cur += iSize;
        }
        else
        {
            if (pBuf->cur - pBuf->begin > 0)
            {
                if (pStream->flush(pStream->param, pBuf->begin,
                                   pBuf->cur - pBuf->begin,
                                   &pStream->flag) == -1)
                    return LS_FAIL;
                pBuf->cur = pBuf->begin;
            }
            if (pStream->flush(pStream->param, pString, iSize,
                               &pStream->flag) == -1)
                return LS_FAIL;
        }
        break;
    case LUA_TBOOLEAN:
        if (LsLuaApi::toboolean(L, idx))
        {
            *pBuf->cur++ = 't';
            *pBuf->cur++ = 'r';
            *pBuf->cur++ = 'u';
            *pBuf->cur++ = 'e';
        }
        else
        {
            *pBuf->cur++ = 'f';
            *pBuf->cur++ = 'a';
            *pBuf->cur++ = 'l';
            *pBuf->cur++ = 's';
            *pBuf->cur++ = 'e';
        }
        break;
    case LUA_TNUMBER:
        pBuf->cur += snprintf(pBuf->cur, pBuf->end - pBuf->cur, "%g",
                              LsLuaApi::tonumber(L, idx));
        break;
    case LUA_TTABLE:
        LsLuaApi::pushvalue(L, idx);
        LsLuaPrintTable(L, pStream);
        LsLuaApi::pop(L, 1);
        break;
    case LUA_TFUNCTION:
        *pBuf->cur++ = '(';
        *pBuf->cur++ = ')';
        break;
    case LUA_TUSERDATA:
        pUData = LsLuaApi::touserdata(L, idx);
        pBuf->cur += snprintf(pBuf->cur, pBuf->end - pBuf->cur,
                              "<%p>", pUData);
        break;
    case LUA_TLIGHTUSERDATA:
        pUData = LsLuaApi::touserdata(L, idx);
        pBuf->cur += snprintf(pBuf->cur, pBuf->end - pBuf->cur,
                              "[%p]", pUData);
        break;
    case LUA_TTHREAD:
        *pBuf->cur++ = 'T';
        *pBuf->cur++ = 'T';
        *pBuf->cur++ = 'H';
        *pBuf->cur++ = 'R';
        *pBuf->cur++ = 'E';
        *pBuf->cur++ = 'A';
        *pBuf->cur++ = 'D';
        break;
    default:
        pBuf->cur += snprintf(pBuf->cur, pBuf->end - pBuf->cur,
                              "TYPE[%d]", iType);
        break;
    }
    return iType;
}


int LsLuaPrint(lua_State *L, ls_luaprint_t *pStream)
{
    char            buf[0x1000];
    int             nArgs;
    int    i;
    ls_luabuf_t *pStreamBuf = &pStream->buffer;

    pStreamBuf->begin = buf;
    pStreamBuf->cur = buf;
    pStreamBuf->end = &buf[sizeof(buf)];

    nArgs = LsLuaApi::gettop(L);
    for (i = 1; i <= nArgs; i++)
    {
        if (LsLuaPrintIdx(L, i, pStream) == -1)
            return LS_FAIL;
        if (i < nArgs)
            *pStreamBuf->cur++ = ' ';
    }
    if (pStream->flag & LSLUA_PRINT_FLAG_CR)
        *pStreamBuf->cur = '\r';
    if (pStream->flag & LSLUA_PRINT_FLAG_LF)
        *pStreamBuf->cur++ = '\n';
    if (pStreamBuf->cur != pStreamBuf->begin)
    {
        return pStream->flush(pStream->param, buf,
                              pStreamBuf->cur - pStreamBuf->begin,
                              &pStream->flag);
    }
    return 0;
}


void LsLuaApi::dumpStack(lua_State *L, const char *pTag, int iDumpCount)
{
    char            buf[0x1000];
    int    nArg;
    int    i;
    int    nb;

    nArg = LsLuaApi::gettop(L);
    if (iDumpCount > nArg)
        iDumpCount = nArg;

    LsLuaLog(L, LSI_LOG_INFO, 0, "[%p] %s STACK[%d]", L, pTag, nArg);
#ifdef LSLUAAPI_DEBUGPRINT
    printf("[%p] %s STACK[%d]\r\n", L, pTag, nArg);
#endif
    for (i = nArg - iDumpCount + 1; i <= nArg; i++)
    {
        if ((nb = dumpIdx2Buf(L, i, buf, 0x1000)) != 0)
        {
#ifdef LSLUAAPI_DEBUGPRINT
            printf("%s\n", buf);
#endif
            LsLuaLog(L, LSI_LOG_INFO, 0, buf);
        }
    }
}


int LsLuaApi::dumpIdx2Buf(lua_State *L, int idx, char *buf, int bufLen)
{
    int    nb = 0;
    size_t          size;
    int    iType;

    iType = LsLuaApi::type(L, idx);
    switch (iType)
    {
    case LUA_TNONE:
        nb = snprintf(buf, bufLen, "STACK <%d> TNONE", idx);
        break;
    case LUA_TNIL:
        nb = snprintf(buf, bufLen, "STACK <%d> TNIL", idx);
        break;
    case LUA_TSTRING:
        nb = snprintf(buf, bufLen, "STACK <%d> %s", idx,
                      LsLuaApi::tolstring(L, idx, &size));
        break;
    case LUA_TNUMBER:
        nb = snprintf(buf, bufLen, "STACK <%d> %g", idx,
                      LsLuaApi::tonumber(L, idx));
        break;
    case LUA_TBOOLEAN:
        nb = snprintf(buf, bufLen, "STACK <%d> %s", idx,
                      LsLuaApi::toboolean(L, idx)
                      ? "true" : "false");
        break;
    case LUA_TTABLE:
        nb = snprintf(buf, bufLen, "STACK <%d> TTABLE", idx);
        break;
    case LUA_TFUNCTION:
        nb = snprintf(buf, bufLen, "STACK <%d> TFUNCTION", idx);
        break;
    case LUA_TUSERDATA:
        nb = snprintf(buf, bufLen, "STACK <%d> TUSERDATA", idx);
        break;
    case LUA_TTHREAD:
        nb = snprintf(buf, bufLen, "STACK <%d> TTHREAD", idx);
        break;
    default:
        nb = snprintf(buf, bufLen, "STACK <%d> TUNKNOWN %d", idx, iType);
        break;
    }
    return nb;
}


void LsLuaApi::dumpStack2Http(lsi_session_t *session, lua_State *L,
                              const char *tag, int iDumpCount)
{
    char            buf[0x1000];
    int    nArg;
    int    nb;
    int    i;

    nArg = LsLuaApi::gettop(L);
    if (iDumpCount > nArg)
        iDumpCount = nArg;

    if ((nb = snprintf(buf, 0x1000, "[%p] %s STACK[%d]\r\n",
                       L, tag, nArg)) != 0)
        g_api->append_resp_body(session, buf, nb);
    for (i = nArg - iDumpCount + 1; i <= nArg; i++)
    {
        if ((nb = dumpIdx2Buf(L, i, buf, 0x1000)) != 0)
        {
            g_api->append_resp_body(session, buf, nb);
            g_api->append_resp_body(session, "\r\n", 2);
        }
    }
}


void LsLuaApi::dumpTable(lua_State *L)
{
    LsLuaApi::pushnil(L);
#ifdef LSLUAAPI_DEBUGPRINT
    printf("Dump Table\n");
#endif
    while (LsLuaApi::next(L, -2) != 0)
    {
        const char *pKey, *pVal;
        if (LsLuaApi::type(L, -2) == LUA_TSTRING)
            pKey = LsLuaApi::tolstring(L, -2, NULL);
        else
            pKey = "not a string";
        switch (LsLuaApi::type(L, -1))
        {
        case LUA_TNIL:
            pVal = "nil";
            break;
        case LUA_TNUMBER:
            pVal = "number";
            break;
        case LUA_TSTRING:
            pVal = "string";
            break;
        case LUA_TFUNCTION:
            pVal = "function";
            break;
        case LUA_TUSERDATA:
            pVal = "udata";
            break;
        case LUA_TTABLE:
            pVal = "table";
            break;
        case LUA_TLIGHTUSERDATA:
            pVal = "lightudata";
            break;
        default:
            pVal = "not listed";
            break;
        }
#ifdef LSLUAAPI_DEBUGPRINT
        printf("Key: %s, val: %s\n", pKey, pVal);
#endif
        LsLuaLog(L, LSI_LOG_INFO, 0, "Key: %s, Val: %s",
                 pKey, pVal);
        LsLuaApi::pop(L, 1);
    }
}

#define LSLUAAPI_DL( name ) \
    LsLuaApi::name = (pf_##name)dlsym( pLib, "lua_"#name )


#define LSLUAAPI_DL2( name ) \
    LsLuaApi::name = (pf_##name)dlsym( pLib, "luaL_"#name )

const char *LsLuaApi::loadConditional(void *pLib)
{
    // Multi Condition.
    if (((LSLUAAPI_DL(objlen)) == NULL)
        && ((LSLUAAPI_DL(rawlen)) == NULL))
        return "objlen and rawlen";

    // Version Patches.
    if (LsLuaApi::jitMode())
    {
        if ((LSLUAAPI_DL(getfenv)) == NULL)
            return "getfenv";
        if ((LSLUAAPI_DL(setfenv)) == NULL)
            return "setfenv";
        if ((LSLUAAPI_DL(pcall)) == NULL)
            return "pcall";
        if ((LSLUAAPI_DL(resume)) == NULL)
            return "resume";
        if ((LSLUAAPI_DL(tointeger)) == NULL)
            return "tointeger";
        if ((LSLUAAPI_DL(tonumber)) == NULL)
            return "tonumber";
        if ((LSLUAAPI_DL(yield)) == NULL)
            return "yield";

        if ((LSLUAAPI_DL2(loadfile)) == NULL)
            return "loadfile";
        if ((LSLUAAPI_DL2(prepbuffer)) == NULL)
            return "prepbuffer";

        // Defined As Macros
        LsLuaApi::getglobal = LsLuaApi::lsGetGlobal;
        LsLuaApi::setglobal = LsLuaApi::lsSetGlobal;
    }
    else
    {
        if ((LSLUAAPI_DL(getglobal)) == NULL)
            return "getglobal";
        if ((LSLUAAPI_DL(pcallk)) == NULL)
            return "pcallk";
        if ((LSLUAAPI_DL(resumeP)) == NULL)
            return "resume";
        if ((LSLUAAPI_DL(setglobal)) == NULL)
            return "setglobal";
        if ((LSLUAAPI_DL(tointegerx)) == NULL)
            return "tointegerx";
        if ((LSLUAAPI_DL(tonumberx)) == NULL)
            return "tonumberx";
        if ((LSLUAAPI_DL(yieldk)) == NULL)
            return "yieldk";

        if ((LSLUAAPI_DL2(loadfilex)) == NULL)
            return "loadfilex";
        if ((LSLUAAPI_DL2(prepbuffsize)) == NULL)
            return "prepbuffsize";

        // Macro Defined.
        LsLuaApi::loadfile = LsLuaApi::lsLoadfilePatch;
        LsLuaApi::pcall = LsLuaApi::lsPcallPatch;
        LsLuaApi::prepbuffer = LsLuaApi::lsPrepBuffer;
        LsLuaApi::resume = LsLuaApi::lsResumePatch;
        LsLuaApi::tointeger = LsLuaApi::lsToIntegerPatch;
        LsLuaApi::tonumber = LsLuaApi::lsToNumberPatch;
        LsLuaApi::yield = LsLuaApi::lsYieldPatch;
    }

    return NULL;
}


const char *LsLuaApi::init(const char *pModuleName)
{
    void *pLib = dlopen(pModuleName, RTLD_LOCAL | RTLD_LAZY);
    if (pLib == NULL)
        return dlerror();
    LsLuaApi::s_pLib = pLib;

    if (dlsym(pLib, "luaJIT_setmode") != NULL)
        LsLuaApi::setJitMode(1);
    else
        LsLuaApi::setJitMode(0);

    // Lua Library.
    if ((LSLUAAPI_DL(close)) == NULL)
        return "close";
    if ((LSLUAAPI_DL(concat)) == NULL)
        return "concat";
    if ((LSLUAAPI_DL(createtable)) == NULL)
        return "createtable";
    if ((LSLUAAPI_DL(gc)) == NULL)
        return "gc";
    if ((LSLUAAPI_DL(getfield)) == NULL)
        return "getfield";
    if ((LSLUAAPI_DL(getmetatable)) == NULL)
        return "getmetatable";
    if ((LSLUAAPI_DL(gettable)) == NULL)
        return "gettable";
    if ((LSLUAAPI_DL(gettop)) == NULL)
        return "gettop";
    if ((LSLUAAPI_DL(insert)) == NULL)
        return "insert";
    if ((LSLUAAPI_DL(load)) == NULL)
        return "load";
    if ((LSLUAAPI_DL(newthread)) == NULL)
        return "newthread";
    if ((LSLUAAPI_DL(newuserdata)) == NULL)
        return "newuserdata";
    if ((LSLUAAPI_DL(next)) == NULL)
        return "next";
    if ((LSLUAAPI_DL(pushboolean)) == NULL)
        return "pushboolean";
    if ((LSLUAAPI_DL(pushcclosure)) == NULL)
        return "pushcclosure";
    if ((LSLUAAPI_DL(pushfstring)) == NULL)
        return "pushfstring";
    if ((LSLUAAPI_DL(pushinteger)) == NULL)
        return "pushinteger";
    if ((LSLUAAPI_DL(pushlightuserdata)) == NULL)
        return "pushlightuserdata";
    if ((LSLUAAPI_DL(pushlstring)) == NULL)
        return "pushlstring";
    if ((LSLUAAPI_DL(pushnil)) == NULL)
        return "pushnil";
    if ((LSLUAAPI_DL(pushnumber)) == NULL)
        return "pushnumber";
    if ((LSLUAAPI_DL(pushstring)) == NULL)
        return "pushstring";
    if ((LSLUAAPI_DL(pushthread)) == NULL)
        return "pushthread";
    if ((LSLUAAPI_DL(pushvalue)) == NULL)
        return "pushvalue";
    if ((LSLUAAPI_DL(pushvfstring)) == NULL)
        return "pushvfstring";
    if ((LSLUAAPI_DL(rawget)) == NULL)
        return "rawget";
    if ((LSLUAAPI_DL(rawgeti)) == NULL)
        return "rawgeti";
    if ((LSLUAAPI_DL(rawset)) == NULL)
        return "rawset";
    if ((LSLUAAPI_DL(rawseti)) == NULL)
        return "rawseti";
    if ((LSLUAAPI_DL(remove)) == NULL)
        return "remove";
    if ((LSLUAAPI_DL(replace)) == NULL)
        return "replace";
    if ((LSLUAAPI_DL(setfield)) == NULL)
        return "setfield";
    if ((LSLUAAPI_DL(setmetatable)) == NULL)
        return "setmetatable";
    if ((LSLUAAPI_DL(settable)) == NULL)
        return "settable";
    if ((LSLUAAPI_DL(settop)) == NULL)
        return "settop";
    if ((LSLUAAPI_DL(toboolean)) == NULL)
        return "toboolean";
    if ((LSLUAAPI_DL(tocfunction)) == NULL)
        return "tocfunction";
    if ((LSLUAAPI_DL(tolstring)) == NULL)
        return "tolstring";
    if ((LSLUAAPI_DL(topointer)) == NULL)
        return "topointer";
    if ((LSLUAAPI_DL(tothread)) == NULL)
        return "tothread";
    if ((LSLUAAPI_DL(touserdata)) == NULL)
        return "touserdata";
    if ((LSLUAAPI_DL(type)) == NULL)
        return "type";
    if ((LSLUAAPI_DL(xmove)) == NULL)
        return "xmove";

    // Auxillary Library.
    LsLuaApi::addsize = LsLuaApi::lsAddSize;
    if ((LSLUAAPI_DL2(addlstring)) == NULL)
        return "addlstring";
    if ((LSLUAAPI_DL2(addstring)) == NULL)
        return "addstring";
    if ((LSLUAAPI_DL2(addvalue)) == NULL)
        return "addvalue";
    if ((LSLUAAPI_DL2(buffinit)) == NULL)
        return "buffinit";
    if ((LSLUAAPI_DL2(checkudata)) == NULL)
        return "checkudata";
    if ((LSLUAAPI_DL2(error)) == NULL)
        return "error";
    if ((LSLUAAPI_DL2(loadstring)) == NULL)
        return "loadstring";
    if ((LSLUAAPI_DL2(newmetatable)) == NULL)
        return "newmetatable";
    if ((LSLUAAPI_DL2(newstate)) == NULL)
        return "newstate";
    if ((LSLUAAPI_DL2(openlib)) == NULL)
        return "openlib";
    if ((LSLUAAPI_DL2(openlibs)) == NULL)
        return "openlibs";
    if ((LSLUAAPI_DL2(pushresult)) == NULL)
        return "pushresult";
    if ((LSLUAAPI_DL2(ref)) == NULL)
        return "ref";
    if ((LSLUAAPI_DL2(unref)) == NULL)
        return "unref";

    // Debug Library.
    if ((LSLUAAPI_DL(getinfo)) == NULL)
        return "getinfo";
    if ((LSLUAAPI_DL(sethook)) == NULL)
        return "sethook";
    if ((LSLUAAPI_DL(setupvalue)) == NULL)
        return "setupvalue";

    return LsLuaApi::loadConditional(pLib);
}


pf_addlstring           LsLuaApi::addlstring = NULL;
pf_addsize              LsLuaApi::addsize = NULL;
pf_addstring            LsLuaApi::addstring = NULL;
pf_addvalue             LsLuaApi::addvalue = NULL;
pf_buffinit             LsLuaApi::buffinit = NULL;
pf_checkudata           LsLuaApi::checkudata = NULL;
pf_close                LsLuaApi::close = NULL;
pf_concat               LsLuaApi::concat = NULL;
pf_createtable          LsLuaApi::createtable = NULL;
pf_error                LsLuaApi::error = NULL;
pf_gc                   LsLuaApi::gc = NULL;
pf_getfenv              LsLuaApi::getfenv = NULL;
pf_getfield             LsLuaApi::getfield = NULL;
pf_getglobal            LsLuaApi::getglobal = NULL;
pf_getmetatable         LsLuaApi::getmetatable = NULL;
pf_gettable             LsLuaApi::gettable = NULL;
pf_gettop               LsLuaApi::gettop = NULL;
pf_insert               LsLuaApi::insert = NULL;
pf_load                 LsLuaApi::load = NULL;
pf_loadstring           LsLuaApi::loadstring = NULL;
pf_newmetatable         LsLuaApi::newmetatable = NULL;
pf_newstate             LsLuaApi::newstate = NULL;
pf_newthread            LsLuaApi::newthread = NULL;
pf_newuserdata          LsLuaApi::newuserdata = NULL;
pf_next                 LsLuaApi::next = NULL;
pf_objlen               LsLuaApi::objlen = NULL;
pf_openlib              LsLuaApi::openlib = NULL;
pf_openlibs             LsLuaApi::openlibs = NULL;
pf_prepbuffer           LsLuaApi::prepbuffer = NULL;
pf_prepbuffsize         LsLuaApi::prepbuffsize = NULL;
pf_pushboolean          LsLuaApi::pushboolean = NULL;
pf_pushcclosure         LsLuaApi::pushcclosure = NULL;
pf_pushfstring          LsLuaApi::pushfstring = NULL;
pf_pushinteger          LsLuaApi::pushinteger = NULL;
pf_pushlightuserdata    LsLuaApi::pushlightuserdata = NULL;
pf_pushlstring          LsLuaApi::pushlstring = NULL;
pf_pushnil              LsLuaApi::pushnil = NULL;
pf_pushnumber           LsLuaApi::pushnumber = NULL;
pf_pushresult           LsLuaApi::pushresult = NULL;
pf_pushstring           LsLuaApi::pushstring = NULL;
pf_pushthread           LsLuaApi::pushthread = NULL;
pf_pushvalue            LsLuaApi::pushvalue = NULL;
pf_pushvfstring         LsLuaApi::pushvfstring = NULL;
pf_rawget               LsLuaApi::rawget = NULL;
pf_rawgeti              LsLuaApi::rawgeti = NULL;
pf_rawlen               LsLuaApi::rawlen = NULL;
pf_rawset               LsLuaApi::rawset = NULL;
pf_rawseti              LsLuaApi::rawseti = NULL;
pf_ref                  LsLuaApi::ref = NULL;
pf_remove               LsLuaApi::remove = NULL;
pf_replace              LsLuaApi::replace = NULL;
pf_setfenv              LsLuaApi::setfenv = NULL;
pf_setfield             LsLuaApi::setfield = NULL;
pf_setglobal            LsLuaApi::setglobal = NULL;
pf_setmetatable         LsLuaApi::setmetatable = NULL;
pf_settable             LsLuaApi::settable = NULL;
pf_settop               LsLuaApi::settop = NULL;
pf_toboolean            LsLuaApi::toboolean = NULL;
pf_tocfunction          LsLuaApi::tocfunction = NULL;
pf_tolstring            LsLuaApi::tolstring = NULL;
pf_topointer            LsLuaApi::topointer = NULL;
pf_tothread             LsLuaApi::tothread = NULL;
pf_touserdata           LsLuaApi::touserdata = NULL;
pf_type                 LsLuaApi::type = NULL;
pf_unref                LsLuaApi::unref = NULL;
pf_xmove                LsLuaApi::xmove = NULL;

pf_loadfile             LsLuaApi::loadfile = NULL;
pf_loadfilex            LsLuaApi::loadfilex = NULL;
pf_pcall                LsLuaApi::pcall = NULL;
pf_pcallk               LsLuaApi::pcallk = NULL;
pf_resume               LsLuaApi::resume = NULL;
pf_resumeP              LsLuaApi::resumeP = NULL;
pf_tointeger            LsLuaApi::tointeger = NULL;
pf_tointegerx           LsLuaApi::tointegerx = NULL;
pf_tonumber             LsLuaApi::tonumber = NULL;
pf_tonumberx            LsLuaApi::tonumberx = NULL;
pf_yield                LsLuaApi::yield = NULL;
pf_yieldk               LsLuaApi::yieldk = NULL;

pf_getinfo              LsLuaApi::getinfo = NULL;
pf_sethook              LsLuaApi::sethook = NULL;
pf_setupvalue           LsLuaApi::setupvalue = NULL;



