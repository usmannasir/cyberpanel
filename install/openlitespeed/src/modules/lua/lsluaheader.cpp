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
#include "lsluaapi.h"
#include "lsluasession.h"

#include <ls.h>
#include <lsr/ls_xpool.h>

#include <ctype.h>

static int LsLuaHeaderDummy(lua_State *L)
{
    LsLuaApi::dumpStack(L, "ls.header dummy ", 10);
    return 0;
}


static int LsLuaHeaderToString(lua_State *L)
{
    char    buf[0x100];

    snprintf(buf, 0x100, "<ls.header %p>", L);
    LsLuaApi::pushstring(L, buf);
    return 1;
}


static int LsLuaHeaderGc(lua_State *L)
{
    LsLuaLog(L, LSI_LOG_INFO, 0, "<ls.header GC>");
    return 0;
}


static const luaL_Reg LsLuaHeaderFuncs[] =
{
    {   "dummy",       LsLuaHeaderDummy       },
    {NULL, NULL}
};


static const luaL_Reg LsLuaHeaderMetaSub[] =
{
    {   "__gc",        LsLuaHeaderGc          },
    {   "__tostring",  LsLuaHeaderToString    },
    {NULL, NULL}
};


static const char *LsLuaHeaderTransformKey(const lsi_session_t *session,
        const char *pInput,
        size_t len)
{
    char *pTmp;
    int i;
    ls_xpool_t *pool = g_api->get_session_pool(session);

    if (memchr(pInput, '_', len) == NULL)
        return pInput;
    pTmp = (char *)ls_xpool_alloc(pool, len);
    for (i = 0; i < (int)len; ++i)
    {
        if (pInput[i] == '_')
            pTmp[i] = '-';
        else
            pTmp[i] = pInput[i];
    }
    return pTmp;
}


int LsLuaHeaderGet(lua_State *L)
{
    const int       iMaxHeaders = 0x100;
    struct iovec    iov[iMaxHeaders];
    size_t          len;
    const char     *pInput, *pKey;
    int             i, iHeaderCount, iRet;
    LsLuaSession   *pSession = LsLuaGetSession(L);
    const lsi_session_t  *session = pSession->getHttpSession();
    if ((iRet = LsLuaApi::checkArgType(L, 2, LUA_TSTRING, "header_get")) != 0)
        return iRet;

    pInput = LsLuaApi::tolstring(L, 2, &len);

    if (pInput == NULL || len == 0)
        return LsLuaApi::userError(L, "header_get", "Header Key not valid.");

    pKey = LsLuaHeaderTransformKey(session, pInput, len);

    iHeaderCount = g_api->get_resp_header(session, LSI_RSPHDR_UNKNOWN,
                                          pKey, len, iov, iMaxHeaders);
    if (iHeaderCount <= 0)
        LsLuaApi::pushnil(L);
    else if (iHeaderCount == 1)
    {
        LsLuaApi::pushlstring(L, (const char *)iov[0].iov_base,
                              iov[0].iov_len);
    }
    else
    {
        LsLuaApi::createtable(L, iHeaderCount, 0);
        for (i = 0; i < iHeaderCount; ++i)
        {
            LsLuaApi::pushlstring(L, (const char *)iov[i].iov_base,
                                  iov[i].iov_len);
            LsLuaApi::rawseti(L, -2, i + 1);
        }
    }
    return 1;
}


int LsLuaHeaderSet(lua_State *L)
{
    const char *pInput, *pKey, *pVal;
    unsigned int iHeaderId, iAddOp;
    size_t iKeyLen, iValLen;
    int i, iTableLen, iRet;
    LsLuaSession *pSession = LsLuaGetSession(L);
    const lsi_session_t *session = pSession->getHttpSession();

    if ((iRet = LsLuaApi::checkArgType(L, 2, LUA_TSTRING, "header_set")) != 0)
        return iRet;

    pInput = LsLuaApi::tolstring(L, 2, &iKeyLen);

    if (pInput == NULL || iKeyLen == 0)
        return LsLuaApi::userError(L, "header_set", "Header Key not valid.");

    pKey = LsLuaHeaderTransformKey(session, pInput, iKeyLen);

    iHeaderId = g_api->get_resp_header_id(session, pKey);
    switch (iHeaderId)
    {
    case LSI_RSPHDR_SET_COOKIE:
    case LSI_RSPHDR_UNKNOWN:
        iAddOp = LSI_HEADEROP_APPEND;
        break;
    default:
        iAddOp = LSI_HEADEROP_SET;
        break;
    }
    switch (LsLuaApi::type(L, 3))
    {
    case LUA_TTABLE:
        if ((iTableLen = LsLuaApi::objlen(L, 3)) != 0)
            break;
    //fall through
    case LUA_TNIL:
        g_api->remove_resp_header(session, LSI_RSPHDR_UNKNOWN,
                                  pKey, iKeyLen);
        return 0;
    case LUA_TSTRING:
    case LUA_TNUMBER:
        pVal = LsLuaApi::tolstring(L, 3, &iValLen);
        g_api->set_resp_header(session, iHeaderId, pKey, iKeyLen,
                               pVal, iValLen, iAddOp);
        return 0;
    default:
        return LsLuaApi::userError(L, "header_set", "Value argument not valid.");
    }

    for (i = 1; i <= iTableLen; ++i)
    {
        LsLuaApi::rawgeti(L, 3, i);
        switch (LsLuaApi::type(L, -1))
        {
        case LUA_TSTRING:
        case LUA_TNUMBER:
            pVal = LsLuaApi::tolstring(L, -1, &iValLen);
            g_api->set_resp_header(session, iHeaderId, pKey, iKeyLen,
                                   pVal, iValLen, iAddOp);
            break;
        default:
            return LsLuaApi::userError(L, "header_set", "Value argument not valid.");
        }
        LsLuaApi::pop(L, 1);
    }
    return 0;
}


void LsLuaCreateHeader(lua_State *L)
{
    LsLuaApi::createtable(L, 0, 0);
    LsLuaApi::createtable(L, 0, 2);
    LsLuaApi::pushcclosure(L, LsLuaHeaderSet, 0);
    LsLuaApi::setfield(L, -2, "__newindex");
    LsLuaApi::pushcclosure(L, LsLuaHeaderGet, 0);
    LsLuaApi::setfield(L, -2, "__index");
    LsLuaApi::setmetatable(L, -2);
    LsLuaApi::setfield(L, -2, "header");
}

