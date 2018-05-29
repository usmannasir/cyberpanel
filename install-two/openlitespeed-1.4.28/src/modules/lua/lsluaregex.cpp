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
#include "lsluasession.h"

#include <ls.h>
#include <lsr/ls_pcreg.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_str.h>
#include <lsr/ls_xpool.h>

#include <ctype.h>


typedef struct ls_luaregex_s
{
    const char         *input;
    const char         *pattern;
    ls_strpair_t      *namedpats;    // Named patterns
    ls_pcre_t          *pcre;
    ls_pcreres_t        res;
    unsigned long       flags;
    int                 inputlen;
    int                 startpos;
    int                 namedpatscount;
    int                 argcount;
    char                findmode;     // Find the offsets only.
    char                dfamode;
    char                cachemode;    // Cache pcre by regex and flags
    char                gmode;        // Selects gsub or gmatch
} ls_luaregex_t;


static int LsLuaRegexMatchHelper(lua_State *L, char iFind);
static int LsLuaRegexSubHelper(lua_State *L, char iGlobal);
static int LsLuaRegexGmatch(lua_State *L);


static int LsLuaRegexMatch(lua_State *L)
{   return LsLuaRegexMatchHelper(L, 0);    }


static int LsLuaRegexFind(lua_State *L)
{    return LsLuaRegexMatchHelper(L, 1);   }


static int LsLuaRegexSub(lua_State *L)
{    return LsLuaRegexSubHelper(L, 0);     }


static int LsLuaRegexGsub(lua_State *L)
{    return LsLuaRegexSubHelper(L, 1);     }


static int LsLuaRegexToString(lua_State *L)
{
    char    buf[0x100];

    snprintf(buf, 0x100, "<ls.re %p>", L);
    LsLuaApi::pushstring(L, buf);
    return 1;
}


static int LsLuaRegexGc(lua_State *L)
{
    LsLuaLog(L, LSI_LOG_NOTICE, 0, "<ls.re GC>");
    return 0;
}


static const luaL_Reg lsluaRegexFuncs[] =
{
    { "find",       LsLuaRegexFind    },
    { "match",      LsLuaRegexMatch   },
    { "gmatch",     LsLuaRegexGmatch  },
    { "sub",        LsLuaRegexSub     },
    { "gsub",       LsLuaRegexGsub    },
    {NULL, NULL}
};


static const luaL_Reg lsluaRegexMetaSub[] =
{
    {"__gc",        LsLuaRegexGc},
    {"__tostring",  LsLuaRegexToString},
    {NULL, NULL}
};


void LsLuaCreateRegexmeta(lua_State *L)
{
    LsLuaApi::openlib(L, LS_LUA ".re", lsluaRegexFuncs, 0);
    LsLuaApi::newmetatable(L, LSLUA_RE);
    LsLuaApi::openlib(L, NULL, lsluaRegexMetaSub, 0);

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


//
// Internal funcs.
//

static int LsLuaRegexFillTable(lua_State *L, ls_luaregex_t *r,
                               int iNumMatches)
{
    const char *pName, *pVal;
    int i, iNameLen, iValLen, iType, iTableLen, iDup;
#if PCRE_MAJOR > 8 || ( PCRE_MAJOR == 8 && PCRE_MINOR >= 12 )
    iDup = r->flags & PCRE_DUPNAMES;
#else
    iDup = 0;
#endif

    for (i = 0; i < iNumMatches; ++i)
    {
        iValLen = ls_pcreres_getsubstr(&r->res, i, (char **)&pVal);
        LsLuaApi::pushlstring(L, pVal, iValLen);
        LsLuaApi::rawseti(L, -2, i);
    }

    for (i = 0; i < r->namedpatscount; ++i)
    {
        pName = ls_str_buf(&r->namedpats[i].key);
        pVal = ls_str_buf(&r->namedpats[i].val);
        iNameLen = ls_str_len(&r->namedpats[i].key);
        iValLen = ls_str_len(&r->namedpats[i].val);
        LsLuaApi::pushlstring(L, pName, iNameLen);
        if (iDup)
        {
            // Duplicates allowed, create table for multiple values per name
            LsLuaApi::pushvalue(L, -1);
            LsLuaApi::rawget(L, -3);
            iType = LsLuaApi::type(L, -1);
            if (iType == LUA_TNIL)
            {
                LsLuaApi::pop(L, 1);
                LsLuaApi::pushlstring(L, pVal, iValLen);
            }
            else
            {
                if (iType != LUA_TTABLE)
                {
                    LsLuaApi::createtable(L, 2, 0);
                    LsLuaApi::insert(L, -2);
                    LsLuaApi::rawseti(L, -2, 1);
                    iTableLen = 2;
                }
                else
                    iTableLen = LsLuaApi::rawlen(L, -1) + 1;

                LsLuaApi::pushlstring(L, pVal, iValLen);
                LsLuaApi::rawseti(L, -2, iTableLen);
            }
        }
        else
            LsLuaApi::pushlstring(L, pVal, iValLen);
        LsLuaApi::rawset(L, -3);
    }
    return 1;
}


static int LsLuaRegexInitPcre(lua_State *L, ls_luaregex_t *r)
{
    if (r->cachemode)
    {
        if (r->pcre)
            return 1;
        else
            r->pcre = ls_pcre_new();
    }
    else
        ls_pcre(r->pcre);
    if (ls_pcre_compile(r->pcre, r->pattern, r->flags, 0, 0) < 0)
    {
        if (r->cachemode)
            ls_pcre_delete(r->pcre);
        return LsLuaApi::serverError(L, "Regex", "Compile Error.");
    }

    return 1;
}


static void LsLuaRegexFreePcre(ls_luaregex_t *r)
{
    if (r->cachemode
        && ls_pcre_store(r->pcre, r->flags))
        return;

    if (r->cachemode)
        ls_pcre_delete(r->pcre);
    else
        ls_pcre_d(r->pcre);
    r->pcre = NULL;
}


static int LsLuaRegexDoPcre(lua_State *L, LsLuaSession *pSession,
                            ls_luaregex_t *r)
{
    int iRet = 0;
    ls_xpool_t *pool = g_api->get_session_pool(pSession->getHttpSession());

    if ((r->namedpatscount = ls_pcre_getnamedsubcnt(r->pcre)) < 0)
    {
        if (r->cachemode)
            ls_pcre_delete(r->pcre);
        return LsLuaApi::serverError(L, "Regex",
                                     "Getting named subs count error.");
    }

    if (r->dfamode)
    {
        iRet = ls_pcre_dfaexecresult(r->pcre, r->input,
                                     r->inputlen, r->startpos,
                                     0, &r->res);
    }
    else
    {
        iRet = ls_pcre_execresult(r->pcre, r->input,
                                  r->inputlen, r->startpos,
                                  0, &r->res);
    }

    if (!r->findmode && r->namedpatscount)
    {
        r->namedpats = (ls_strpair_t *)ls_xpool_alloc(pool,
                       r->namedpatscount
                       * sizeof(ls_strpair_t));
        r->namedpatscount = ls_pcre_getnamedsubs(r->pcre, &r->res,
                            r->namedpats, r->namedpatscount);
        if (r->namedpatscount < 0)
            return LsLuaApi::userError(L, "Regex", "Get named subs error.");
    }
    return iRet;
}


static int LsLuaRegexParseRet(lua_State *L, ls_luaregex_t *r, int iRet)
{
    int *pVec;

    if (iRet == PCRE_ERROR_NOMATCH)
        return 0;
    else if (iRet < 0)
    {
        LsLuaLog(L, LSI_LOG_INFO, 0, "Regex: Exec Error: %d", iRet);
        LsLuaApi::pushinteger(L, iRet);
        return 1;
    }

    pVec = ls_pcreres_getvector(&r->res);

    if (r->findmode)
    {
        LsLuaApi::pushinteger(L, pVec[0]);   // From
        LsLuaApi::pushinteger(L, pVec[1]);   // to
        return 2;
    }

    r->startpos = pVec[1];
    if (r->argcount > 3)
    {
        LsLuaApi::pushinteger(L, pVec[1] + 1);
        LsLuaApi::setfield(L, 4, "pos");
    }

    if (r->argcount < 5)   // Need to make a table.
        LsLuaApi::createtable(L, iRet, r->namedpatscount);

    return LsLuaRegexFillTable(L, r, iRet);
}


static int LsLuaRegexParseRule(ls_pcresub_t *pThis, const char *pRule)
{
    if (!pRule)
        return LS_FAIL;
    const char     *p = pRule;
    char   c;
    int             entries = 0;
    while ((c = *p++) != '\0')
    {
        if (c == '&')
            ++entries;
        else if (c == '$')
        {
            if (isdigit(*p))
            {
                ++p;
                ++entries;
            }
            else if (*p == '$')
                ++p;
            else if (*p == '{')
            {
                while ((c = *p++) != '\0')
                {
                    if (isdigit(*p))
                        continue;
                    else if (*p == '}')
                        break;
                    else
                        return LS_FAIL;
                }
                if (c == '\0')
                    return LS_FAIL;
                ++p;
                ++entries;
            }
        }
    }
    ++entries;
    int bufSize = strlen(pRule) + 1;
    bufSize = ((bufSize + 7) >> 3) << 3;
    if ((pThis->parsed = (char *)ls_prealloc(pThis->parsed,
                         bufSize + entries * sizeof(ls_pcresubent_t))) == NULL)
        return LS_FAIL;
    pThis->plist = (ls_pcresubent_t *)(pThis->parsed + bufSize);
    memset(pThis->plist, 0xff, entries * sizeof(ls_pcresubent_t));

    char *pDest = pThis->parsed;
    p = pRule;
    ls_pcresubent_t *pEntry = pThis->plist;
    pEntry->strbegin = 0;
    pEntry->strlen = 0;
    while ((c = *p++) != '\0')
    {
        if (c == '&')
            pEntry->param = 0;
        else if (c == '$')
        {
            if (isdigit(*p))
                pEntry->param = *p++ - '0';
            else if (*p == '$')
            {
                *pDest++ = *p++;
                ++(pEntry->strlen);
                continue;
            }
            else if (*p == '{')
            {
                char *pEnd;
                pEntry->param = strtol(++p, &pEnd, 0);
                p = pEnd + 1;
            }
        }
        else
        {
            *pDest++ = c;
            ++(pEntry->strlen);
            continue;
        }
        ++pEntry;
        pEntry->strbegin = pDest - pThis->parsed;
        pEntry->strlen = 0;
    }
    *pDest = 0;
    if (pEntry->strlen == 0)
        --entries;
    else
        ++pEntry;
    pThis->plistend = pEntry;
    assert(pEntry - pThis->plist == entries);
    return 0;
}


static int LsLuaRegexMatchLoad(lua_State *L, ls_luaregex_t *r)
{
    int iRet;
    size_t iOptLen;
    const char *pOpts;

    if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TSTRING, "Regex Match")) != 0)
        return iRet;
    if ((iRet = LsLuaApi::checkArgType(L, 2, LUA_TSTRING, "Regex Match")) != 0)
        return iRet;

    r->input = LsLuaApi::tolstring(L, 1,
                                   (size_t *)&r->inputlen);
    r->pattern = LsLuaApi::tolstring(L, 2, NULL);
    switch (r->argcount)
    {
    case 5: // result table
        if ((iRet = LsLuaApi::checkArgType(L, 5, LUA_TTABLE, "Regex Match")) != 0)
            return iRet;
    // fall through
    case 4: // ctx
        if ((iRet = LsLuaApi::checkArgType(L, 4, LUA_TTABLE, "Regex Match")) != 0)
            return iRet;
        LsLuaApi::getfield(L, 4, "pos");
        iRet = LsLuaApi::type(L, -1);
        if (iRet == LUA_TNUMBER)
        {
            r->startpos = LsLuaApi::tointeger(L, -1);
            if (r->startpos < 0)
                r->startpos = 0;
        }
        else if (r->startpos == LUA_TNIL)
            r->startpos = 0;
        else
            return LsLuaApi::userError(L, "Regex Match", "Invalid Arg Type "
                                       "(arg 4 member).");
        LsLuaApi::pop(L, 1);
    // fall through
    case 3:
        if ((iRet = LsLuaApi::checkArgType(L, 3, LUA_TSTRING, "Regex Match")) != 0)
            return iRet;
        pOpts = LsLuaApi::tolstring(L, 3, &iOptLen);
        if (!pOpts)
            return LsLuaApi::userError(L, "Regex Match", "Invalid Options passed in.");

        if ((iRet = ls_pcre_parseoptions(pOpts, iOptLen,
                                         &r->flags)) < 0)
            return LsLuaApi::serverError(L, "Regex Match", "Parsing options failed.");

        r->dfamode = iRet & LSR_PCRE_DFA_MODE;
        r->cachemode = iRet & LSR_PCRE_CACHE_COMPILED;
    // fall through
    case 2:
        break;
    default:
        return LsLuaApi::serverError(L, "Regex Match", "The Impossible Happened!");
    }
    ls_pcre_result(&r->res);
    ls_pcreres_setbuf(&r->res, r->input);
    return 1;
}


static int LsLuaRegexMatchHelper(lua_State *L, char iFind)
{
    int iRet;
    ls_luaregex_t r;
    ls_pcre_t pcre;
    LsLuaSession *pSession = LsLuaSession::getSelf(L);
    memset(&r, 0, sizeof(ls_luaregex_t));
    r.findmode = iFind;
    r.argcount = LsLuaApi::gettop(L);
    if (r.argcount < 2 || r.argcount > 5)
        return LsLuaApi::invalidNArgError(L, "Regex Match");
    if (!LsLuaRegexMatchLoad(L, &r))
        return 0;
    if (r.cachemode)
        r.pcre = ls_pcre_load(r.pattern, r.flags);
    else
        r.pcre = &pcre;
    if (!LsLuaRegexInitPcre(L, &r))
        return LsLuaApi::serverError(L, "Regex Match", "Init pcre failed.");

    iRet = LsLuaRegexDoPcre(L, pSession, &r);
    iRet = LsLuaRegexParseRet(L, &r, iRet);
    LsLuaRegexFreePcre(&r);
    return iRet;
}


static int LsLuaRegexSubstitute(lua_State *L, LsLuaSession *pSession,
                                ls_luaregex_t *r, const char *pSubRule,
                                char iFunc)
{
    ls_pcre_t pcre;
    ls_pcresub_t sub;
    int iRet, iBufLen, *pVec, iCount = 0;
    char *pBuf = NULL;
    ls_xpool_t *pool = g_api->get_session_pool(pSession->getHttpSession());
    luaL_Buffer buf;

    ls_pcre_sub(&sub);
    if (r->cachemode)
        r->pcre = ls_pcre_load(r->pattern, r->flags);
    else
        r->pcre = &pcre;

    if (LsLuaRegexInitPcre(L, r) == 0)
        return LsLuaApi::serverError(L, "Regex Sub", "Init pcre failed.");

    if (iFunc)
        LsLuaApi::settop(L, 3);
    else if ((LsLuaRegexParseRule(&sub, pSubRule)) != 0)
    {
        ls_pcresub_release(&sub);
        LsLuaRegexFreePcre(r);
        return 0;
    }
    LsLuaApi::buffinit(L, &buf);

    do
    {
        iRet = LsLuaRegexDoPcre(L, pSession, r);
        if (iRet == PCRE_ERROR_NOMATCH)
            break;
        else if (iRet < 0)
        {
            ls_pcresub_release(&sub);
            LsLuaRegexFreePcre(r);
            LsLuaLog(L, LSI_LOG_INFO, 0, "Regex Sub: Exec Error: %d", iRet);
            LsLuaApi::pushinteger(L, iRet);
            return 1;
        }
        pVec = ls_pcreres_getvector(&r->res);

        LsLuaApi::addlstring(&buf, r->input + r->startpos,
                             pVec[0] - r->startpos);
        if (iFunc)
        {
            LsLuaApi::pushvalue(L, -1);
            LsLuaApi::createtable(L, iRet, 0);
            if (!LsLuaRegexFillTable(L, r, iRet))
            {
                ls_pcresub_release(&sub);
                LsLuaRegexFreePcre(r);
                return LsLuaApi::serverError(L, "Regex Sub", "Fill table error.");
            }
            iRet = LsLuaApi::pcall(L, 1, 1, 0);
            if (iRet != 0)
            {
                ls_pcresub_release(&sub);
                LsLuaRegexFreePcre(r);
                return LsLuaApi::serverError(L, "Regex Sub", "Call func error.");
            }
            if (LsLuaApi::type(L, -1) != LUA_TSTRING)
            {
                ls_pcresub_release(&sub);
                LsLuaRegexFreePcre(r);
                return LsLuaApi::serverError(L, "Regex Sub", "Func return not str");
            }
            LsLuaApi::addvalue(&buf);
        }
        else
        {
            iBufLen = ls_pcresub_getlen(&sub, r->input, pVec, iRet);
            pBuf = (char *)ls_xpool_realloc(pool, pBuf, iBufLen);
            ls_pcresub_exec(&sub, r->input, pVec, iRet, pBuf, &iBufLen);
            LsLuaApi::addlstring(&buf, pBuf, iBufLen);
        }
        iCount++;
        r->startpos = pVec[1];
    }
    while (r->gmode);

    LsLuaApi::addlstring(&buf, r->input + r->startpos,
                         r->inputlen - r->startpos);
    LsLuaApi::pushresult(&buf);
    LsLuaApi::pushinteger(L, iCount);
    ls_pcresub_release(&sub);
    LsLuaRegexFreePcre(r);

    return 2;
}


static int LsLuaRegexSubHelper(lua_State *L, char iGlobal)
{
    ls_luaregex_t r;
    int iRet, iFunc = 0;
    size_t iOptLen;
    const char *pOpts, *pSubRule;
    LsLuaSession *pSession = LsLuaSession::getSelf(L);

    memset(&r, 0, sizeof(ls_luaregex_t));
    r.gmode = iGlobal;
    r.argcount = LsLuaApi::gettop(L);
    if (r.argcount != 3 && r.argcount != 4)
        return LsLuaApi::invalidNArgError(L, "Regex Sub");
    if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TSTRING, "Regex Sub")) != 0)
        return iRet;
    if ((iRet = LsLuaApi::checkArgType(L, 2, LUA_TSTRING, "Regex Sub")) != 0)
        return iRet;

    iFunc = LsLuaApi::type(L, 3);
    if (iFunc == LUA_TSTRING)
        iFunc = 0;
    else if (iFunc == LUA_TFUNCTION)
        iFunc = 1;
    else
        return LsLuaApi::userError(L, "Regex Sub", "Invalid arg type (arg 3).");

    r.input = LsLuaApi::tolstring(L, 1,
                                  (size_t *)&r.inputlen);
    r.pattern = LsLuaApi::tolstring(L, 2, NULL);
    pSubRule = LsLuaApi::tolstring(L, 3, NULL);
    if (r.argcount == 4)
    {
        if ((iRet = LsLuaApi::checkArgType(L, 4, LUA_TSTRING, "Regex Sub")) != 0)
            return iRet;
        pOpts = LsLuaApi::tolstring(L, 4, &iOptLen);
        if ((iRet = ls_pcre_parseoptions(pOpts, iOptLen,
                                         &r.flags)) < 0)
            return LsLuaApi::serverError(L, "Regex Sub", "Parse Options failed.");

        r.dfamode = iRet & LSR_PCRE_DFA_MODE;
        r.cachemode = iRet & LSR_PCRE_CACHE_COMPILED;
    }
    ls_pcre_result(&r.res);
    ls_pcreres_setbuf(&r.res, r.input);
    return LsLuaRegexSubstitute(L, pSession, &r, pSubRule, iFunc);
}


static int LsLuaRegexGmatchIter(lua_State *L)
{
    int iRet;
    ls_luaregex_t *r = (ls_luaregex_t *)LsLuaApi::touserdata(L,
                       LsLuaApi::upvalueindex(1));
    if (!r)
        return LsLuaApi::serverError(L, "GMatch Iter",
                                     "Upvalue was null or no more "
                                     "to iterate.");
    iRet = LsLuaRegexDoPcre(L, LsLuaGetSession(L), r);
    iRet = LsLuaRegexParseRet(L, r, iRet);
    if (iRet < 0)
    {
        if (r->cachemode)
            ls_pcre_store(r->pcre, r->flags);
        else
        {
            ls_pcre_release(r->pcre);
            ls_pcre_delete(r->pcre);
        }
        LsLuaApi::pushnil(L);
        LsLuaApi::replace(L, LsLuaApi::upvalueindex(1));
        ls_pfree(r);
    }

    return iRet;
}


//
// Alternate Implementations.
//

int LsLuaRegexGmatch(lua_State *L)
{
    int iArgs;
    ls_luaregex_t *r;
    LsLuaSession::getSelf(L);
    iArgs = LsLuaApi::gettop(L);
    if (iArgs != 2 && iArgs != 3)
        return LsLuaApi::invalidNArgError(L, "GMatch");
    r = (ls_luaregex_t *)ls_palloc(sizeof(ls_luaregex_t));
    memset(r, 0, sizeof(ls_luaregex_t));
    r->argcount = iArgs;
    r->gmode = 1;
    if (!LsLuaRegexMatchLoad(L, r))
        return 0;
    if (r->cachemode)
        r->pcre = ls_pcre_load(r->pattern, r->flags);
    else
        r->pcre = ls_pcre_new();
    if (!LsLuaRegexInitPcre(L, r))
        return LsLuaApi::serverError(L, "GMatch", "Init pcre failed.");

    LsLuaApi::pushlightuserdata(L, r);
    LsLuaApi::pushcclosure(L, LsLuaRegexGmatchIter, 1);
    return 1;
}


int LsLuaRegexRegex(lua_State *L)
{
    int iRet;
    ls_luaregex_t r;
    ls_pcre_t pcre;
    LsLuaSession *pSession = LsLuaSession::getSelf(L);

    memset(&r, 0, sizeof(ls_luaregex_t));
    r.argcount = LsLuaApi::gettop(L);
    if (r.argcount != 2 && r.argcount != 3)
        return LsLuaApi::invalidNArgError(L, "Regex");

    if ((iRet = LsLuaApi::checkArgType(L, 1, LUA_TSTRING, "Regex")) != 0)
        return iRet;
    if ((iRet = LsLuaApi::checkArgType(L, 2, LUA_TSTRING, "Regex")) != 0)
        return iRet;

    r.pcre = &pcre;
    r.input = LsLuaApi::tolstring(L, 1, (size_t *)&r.inputlen);
    r.pattern = LsLuaApi::tolstring(L, 2, NULL);
    if (r.argcount == 3)
    {
        if ((iRet = LsLuaApi::checkArgType(L, 3, LUA_TNUMBER, "Regex")) != 0)
            return iRet;
        r.flags = LsLuaApi::tointeger(L, 3);
    }
    ls_pcre_result(&r.res);
    ls_pcreres_setbuf(&r.res, r.input);
    if (LsLuaRegexInitPcre(L, &r) == 0)
        return LsLuaApi::serverError(L, "Regex", "Init pcre failed.");

    iRet = LsLuaRegexDoPcre(L, pSession, &r);
    iRet = LsLuaRegexParseRet(L, &r, iRet);
    LsLuaRegexFreePcre(&r);
    return iRet;
}



