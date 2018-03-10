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

#include <shm/lsshmhash.h>
#include <shm/lsshmpool.h>

#include <fcntl.h>
#include <time.h>
#include <sys/time.h>

#define LS_LUASHM_MAGIC   0x20140523

//
// LiteSpeed LUA Shared memory interface
//

//
//  Data structure to keep all LUA Shared memory stuff
//  In general all we use are long and double.
//  and small strings buffer...
//  If you need more data than a double link will be used.
//  I would need a timer check function very soon...
//
typedef enum
{
    ls_luashm_nil = 0,
    ls_luashm_long,
    ls_luashm_double,
    ls_luashm_string,
    ls_luashm_boolean
} ls_luashm_type;

struct ls_luashm_s
{
    uint32_t             m_iMagic;
    time_t               m_expireTime;   /* time to expire in sec    */
    int32_t              m_expireTimeUs; /* time to expire in sec    */
    uint32_t             m_iFlags;       /* 32bits flags             */
    uint32_t             m_iValueLen;    /* len of the Value         */
    ls_luashm_type       m_type;         /* type of the Value        */
    union
    {
        double           m_double;
        uint32_t         m_iOffset;      /* offset to the SHM        */
        uint32_t         m_ulong;
        uint32_t         m_ulongArray [2];
        uint16_t         m_ushortArray[4];
        uint16_t         m_ushort;
#define LSSHM_VALUE_MINLEN       8 /* a structure or memory  */
        uint8_t          m_ucharArray [LSSHM_VALUE_MINLEN];
        uint8_t          m_uchar;
        uint8_t          m_boolean;
    };
};
typedef struct ls_luashm_s  ls_luashm_t;


static inline LsShmHash *LsLuaShmOpen(const char *name)
{
    AutoStr2 *pName;
    LsShmHash *pRet;
    LsShm *pShm = LsShm::open(name, 0, NULL);
    if (pShm == NULL)
        return NULL;
    LsShmPool *pPool = pShm->getGlobalPool();
    if (pPool == NULL)
        return NULL;
    pName = new AutoStr2(name);
    pName->append("hash", 4);
    pRet =  pPool->getNamedHash(pName->c_str(), LSSHM_HASHINITSIZE,
                                LsShmHash::hashString, LsShmHash::compString,
                                LSSHM_FLAG_NONE);
    delete pName;
    return pRet;
}


static inline void LsLuaShmClose(LsShmHash *pHash)
{
    pHash->close();
}


static ls_luashm_t *LsLuaShmFind(LsShmHash *pHash,
                                 const char *name)
{
    int retsize;
    LsShmOffset_t key;
    int len = strlen(name) + 1;
    if ((key = pHash->find((const uint8_t *)name, len, &retsize)))
        return (ls_luashm_t *)pHash->offset2ptr(key);
    return NULL;
}


static ls_luashm_t *LsLuaShmSetval(LsShmHash *pHash,
                                   const char *name,
                                   ls_luashm_type type,
                                   const void *pvalue,
                                   int size)
{
    int retsize, remap = 0;
    LsShmOffset_t key;
    ls_luashm_t *pShmValue;

    int len = strlen(name) + 1;

    if (pvalue == NULL)
    {
        pHash->remove(name, len);
        return NULL;
    }
    if (size == 0)
        return NULL;

    if ((key = pHash->find(name, len, &retsize)) == 0)
    {
        ls_luashm_t shmvalue;

        shmvalue.m_iMagic = LS_LUASHM_MAGIC;
        shmvalue.m_expireTime = 0;
        shmvalue.m_expireTimeUs = 0;
        shmvalue.m_iFlags = 0;
        shmvalue.m_type = type;
        shmvalue.m_iValueLen = size;
        if (size > (int)sizeof(double))
        {
            LsShmOffset_t offset;
            offset = pHash->alloc2(size, remap);
            if (offset == 0)
                return NULL;

            shmvalue.m_iOffset = offset;
            memcpy(pHash->offset2ptr(offset), pvalue, size);
        }
        else
            memcpy(shmvalue.m_ucharArray, pvalue, size);

        key = pHash->insert(name, len, &shmvalue, sizeof(shmvalue));
        if (key == 0)
        {
            if (size > (int)sizeof(double))
                pHash->release2(shmvalue.m_iOffset, shmvalue.m_iValueLen);
            return NULL;
        }
        return (ls_luashm_t *)pHash->offset2ptr(key);
    }

    pShmValue = (ls_luashm_t *)pHash->offset2ptr(key);

    if ((size > (int)sizeof(double)))
    {
        // if newsize bigger need double reference
        if ((int)(pShmValue->m_iValueLen) != size)
        {
            LsShmOffset_t offset;
            offset = pHash->alloc2(size, remap);
            if (offset == 0)
                return NULL; // no memory
            if (remap)
                pShmValue = (ls_luashm_t *)pHash->offset2ptr(key);
            if (pShmValue->m_iValueLen > sizeof(double))
                pHash->release2(pShmValue->m_iOffset, pShmValue->m_iValueLen);

            pShmValue->m_iOffset = offset;
            pShmValue->m_iValueLen = size;
        }
        pShmValue->m_type = type;
        memcpy(pHash->offset2ptr(pShmValue->m_iOffset),
               pvalue, size);
        return pShmValue;
    }

    if (pShmValue->m_iValueLen > sizeof(double))
        pHash->release2(pShmValue->m_iOffset, pShmValue->m_iValueLen);

    pShmValue->m_type = type;
    pShmValue->m_iValueLen = size;
    switch (type)
    {
    case ls_luashm_long:
        pShmValue->m_ulong = *((unsigned long *)pvalue);
        break;
    case ls_luashm_double:
        pShmValue->m_double = *((double *)pvalue);
        break;
    case ls_luashm_string:
        memcpy(pShmValue->m_ucharArray, pvalue, size);
        break;
    case ls_luashm_boolean:
        pShmValue->m_boolean = *((unsigned char *)pvalue);
        break;
    default:
        return NULL;
    }
    return pShmValue;
}


inline static int isTimeExpired(ls_luashm_t *pShmValue)
{
    if (pShmValue->m_expireTime == 0)
        return 0;

    time_t t, dt;
    int32_t usec;
    t = g_api->get_cur_time(&usec);

    dt = t - pShmValue->m_expireTime;
    if ((dt > 0)
        || ((!dt) && (usec > pShmValue->m_expireTimeUs)))
        return 1;
    else
        return 0;
}


inline static int setExpirationTime(ls_luashm_t *pShmValue,
                                    double expTime)
{
#define MIN_RESOLUTION 0.001
    if (expTime < MIN_RESOLUTION)
    {
        pShmValue->m_expireTime = 0;
        return 1;
    }
    int sec = (int)expTime;
    int usec = (int)((expTime - sec) * 1000000.0) % 1000000;

    // potential race between sec and usec loading...
    int32_t now_usec;
    time_t t = g_api->get_cur_time(&now_usec);

    time_t curTime = t + sec;
    int curTimeUs = now_usec + usec;
    if (curTimeUs > 1000000)
    {
        curTime++;
        curTimeUs -= 1000000;
    }
    pShmValue->m_expireTime = curTime;
    pShmValue->m_expireTimeUs = curTimeUs;
    return 0;
}


static inline LsShmHash *LsLuaShmGetSelf(lua_State *L, const char *tag)
{
    LsShmHash **pp;
    pp = (LsShmHash **)LsLuaApi::checkudata(L, 1,
                                            LSLUA_SHARED_DATA);
    if (pp == NULL)
    {
        LsLuaLog(L, LSI_LOG_NOTICE, 0, "%s <INVALID LUA UDATA>" , tag);
        return 0;
    }
    return (*pp);
}


static inline LsShmHash *LsLuaShmGetHash(lua_State *L, const char *tag,
        int &numElem, char *keyName,
        int keyLen)
{
    LsShmHash *pShared = LsLuaShmGetSelf(L, tag);
    int num = LsLuaApi::gettop(L);

    if ((num >= numElem) && pShared)
    {
        numElem = num;
        size_t size;
        const char *cp;
        if ((cp = LsLuaApi::tolstring(L, 2, &size))  &&  size)
        {
            keyName[0] = 0;
            if (size >= (size_t)keyLen)
            {
                LsLuaLog(L, LSI_LOG_NOTICE, 0,
                         "%s LUA SHARE NAME [%s] LEN %d too big",
                         tag, keyName, size);
                return NULL;
            }
            snprintf(keyName, keyLen, "%.*s", (int)size, cp);
            if (keyName[0])
                return pShared;
        }
    }
    return NULL;
}


static int LsLuaShmToString(lua_State *L)
{
    const char *tag = "ls.shared.tostring";
    char buf[0x100];

    LsShmHash *pShared = LsLuaShmGetSelf(L, tag);
    if (pShared)
        snprintf(buf, 0x100, "%s <%p>", tag, pShared);

    LsLuaApi::pushstring(L, buf);
    return 1;
}


static int LsLuaShmGc(lua_State *L)
{
    const char *tag = "ls.shared.gc";
    LsShmHash *pShared = LsLuaShmGetSelf(L, tag);

    if (pShared)
    {
        LsLuaShmClose(pShared);
        LsLuaLog(L, LSI_LOG_DEBUG, 0,
                 "LsLuaSharedGc %s <%p>",
                 tag, pShared);
    }
    return 0;
}


static int LsLuaShmCreate(lua_State *L , LsShmHash *pHash)
{
    LsShmHash **pp;
    pp = (LsShmHash **)(LsLuaApi::newuserdata(L,
                        sizeof(LsShmHash **)));
    if (pp)
    {
        *pp = pHash;
        LsLuaApi::getfield(L, LSLUA_REGISTRYINDEX, LSLUA_SHARED_DATA);
        LsLuaApi::setmetatable(L, -2);
        return 1;
    }
    return LsLuaApi::userError(L, "shared_index", "Create user data failed.");
}


static int LsLuaShmGetHelper(lua_State *L, int checkExpired)
{
    const char *ptr, *tag = "ls.shared.get_helper";
    char namebuf[0x100];
    int numElem = 2;
    LsShmHash *pShared;
    ls_luashm_t *pVal;

    pShared = LsLuaShmGetHash(L, tag, numElem, namebuf, 0x100);
    if (pShared == NULL)
    {
        LsLuaApi::pushnil(L);
        LsLuaApi::pushstring(L, "not a shared OBJECT");
        return 2;
    }

    pVal = LsLuaShmFind(pShared, namebuf);
    if (pVal == NULL)
    {
        LsLuaApi::pushnil(L);
        LsLuaApi::pushstring(L, "not found");
        return 2;
    }

    if (checkExpired && isTimeExpired(pVal))
    {
        LsLuaApi::pushnil(L);
        LsLuaApi::pushstring(L, "expired");
        return 2;
    }

    switch (pVal->m_type)
    {
    case ls_luashm_long:
        LsLuaApi::pushinteger(L, pVal->m_ulong);
        break;
    case ls_luashm_double:
        LsLuaApi::pushnumber(L, (lua_Number)pVal->m_double);
        break;
    case ls_luashm_string:
        if (pVal->m_iValueLen > sizeof(double))
        {
            ptr = (const char *)pShared->offset2ptr(pVal->m_iOffset);
            LsLuaApi::pushlstring(L, ptr, pVal->m_iValueLen);
        }
        else
        {
            LsLuaApi::pushlstring(L, (const char *)pVal->m_ucharArray,
                                  pVal->m_iValueLen);
        }
        break;

    case ls_luashm_boolean:
        if (pVal->m_boolean)
            LsLuaApi::pushboolean(L, 1);
        else
            LsLuaApi::pushboolean(L, 0);
        break;

    case ls_luashm_nil:
    default:
        LsLuaApi::pushnil(L);
        LsLuaApi::pushstring(L, "not a shared value type");
        return 2;
    }

    if (checkExpired == 0)
    {
        LsLuaApi::pushinteger(L, pVal->m_iFlags);

        if (isTimeExpired(pVal))
            LsLuaApi::pushboolean(L, 1);
        return 3;
    }
    if (pVal->m_iFlags)
    {
        LsLuaApi::pushinteger(L, pVal->m_iFlags);
        return 2;
    }
    else
        return 1;
}


static int LsLuaShmGet(lua_State *L)
{
    return LsLuaShmGetHelper(L, 1);
}


static int LsLuaShmGetStale(lua_State *L)
{
    return LsLuaShmGetHelper(L, 0);
}


static int LsLuaShmSetHelper(lua_State *L, LsShmHash *pShared,
                             int numElem, const char *keyName)
{

    /* NOTE: elements 3 = value, 4 = expTime, 5 = flags */
    ls_luashm_t *p_Val = NULL;
    const char *p_string;
    size_t len;
    int valueType = LsLuaApi::type(L, 3);

    switch (valueType)
    {
    case LUA_TNIL:
        p_Val = LsLuaShmSetval(pShared, keyName, ls_luashm_nil, NULL, 0);
        LsLuaApi::pushboolean(L, 1);
        LsLuaApi::pushnil(L);
        LsLuaApi::pushboolean(L, 0);
        return 3;

    case LUA_TNUMBER:
        double myDouble;
        long myLong;
        p_string = LsLuaApi::tolstring(L, 3, &len);
        if (memchr(p_string, '.', len))
        {
            myDouble = LsLuaApi::tonumber(L, 3);
            p_Val = LsLuaShmSetval(pShared, keyName, ls_luashm_double,
                                   &myDouble, sizeof(myDouble));
        }
        else
        {
            myLong = LsLuaApi::tonumber(L, 3);
            p_Val = LsLuaShmSetval(pShared, keyName, ls_luashm_long,
                                   &myLong, sizeof(myLong));
        }
        break;

    case LUA_TBOOLEAN:
        char myBool;
        if (LsLuaApi::toboolean(L, 3))
            myBool = 1;
        else
            myBool = 0;
        p_Val = LsLuaShmSetval(pShared, keyName, ls_luashm_boolean,
                               &myBool, sizeof(myBool));
        break;

    case LUA_TSTRING:
        p_string = LsLuaApi::tolstring(L, 3, &len);
        p_Val = LsLuaShmSetval(pShared, keyName, ls_luashm_string,
                               p_string, len);
        break;

    case LUA_TNONE:
    case LUA_TTABLE:
    case LUA_TFUNCTION:
    case LUA_TUSERDATA:
    case LUA_TTHREAD:
    case LUA_TLIGHTUSERDATA:
    default:
        LsLuaApi::pushboolean(L, 0);
        LsLuaApi::pushstring(L, "bad value type");
        LsLuaApi::pushboolean(L, 0);
        return 3;
    }

    if (p_Val)
    {
        if (numElem > 3)
        {
            lua_Number tValue = LsLuaApi::tonumber(L, 4);
            setExpirationTime(p_Val, tValue);

            if (numElem > 4)
                p_Val->m_iFlags = LsLuaApi::tointeger(L, 5);
        }
        LsLuaApi::pushboolean(L, 1);
        LsLuaApi::pushnil(L);
        LsLuaApi::pushboolean(L, 0);
        return 3;
    }
    LsLuaApi::pushboolean(L, 0);
    LsLuaApi::pushstring(L, "bad hashkey");
    LsLuaApi::pushboolean(L, 0);
    return 3;
}


static int  LsLuaShmSet(lua_State *L)
{
    const char *tag = "ls.shared.set";
    char namebuf[0x100];
    int numElem = 3;
    LsShmHash *pShared;

    pShared = LsLuaShmGetHash(L, tag, numElem, namebuf, 0x100);
    if (pShared)
        return LsLuaShmSetHelper(L, pShared, numElem, namebuf);
    LsLuaApi::pushboolean(L, 0);
    LsLuaApi::pushstring(L, "bad parameters");
    LsLuaApi::pushboolean(L, 0);
    return 3;
}


static int LsLuaShmSetSafe(lua_State *L)
{
    return LsLuaShmSet(L);
}


static int LsLuaShmAdd(lua_State *L)
{
    const char *tag = "ls.shared.add";
    char namebuf[0x100];
    int numElem = 3;
    LsShmHash *pShared;

    pShared = LsLuaShmGetHash(L, tag, numElem, namebuf, 0x100);
    if (pShared)
    {
        ls_luashm_t *pShmValue = LsLuaShmFind(pShared, namebuf);
        if ((pShmValue == NULL) || isTimeExpired(pShmValue))
            return LsLuaShmSetHelper(L, pShared, numElem, namebuf);
        else
        {
            LsLuaApi::pushboolean(L, 0);
            LsLuaApi::pushstring(L, "exists");
            LsLuaApi::pushboolean(L, 0);
        }
        return 3;
    }
    else
    {
        LsLuaApi::pushboolean(L, 0);
        LsLuaApi::pushstring(L, "bad parameters");
        LsLuaApi::pushboolean(L, 0);
        return 3;
    }
}


static int LsLuaShmAddSafe(lua_State *L)
{
    return LsLuaShmAdd(L);
}


static int LsLuaShmReplace(lua_State *L)
{
    const char *tag = "ls.shared.add";
    char namebuf[0x100];
    int numElem = 3;
    LsShmHash *pShared;

    pShared = LsLuaShmGetHash(L, tag, numElem, namebuf, 0x100);
    if (pShared)
    {
        ls_luashm_t *pShmValue = LsLuaShmFind(pShared, namebuf);
        if ((pShmValue) && (!isTimeExpired(pShmValue)))
            return LsLuaShmSetHelper(L, pShared, numElem, namebuf);
        else
        {
            LsLuaApi::pushboolean(L, 0);
            LsLuaApi::pushstring(L, "not found");
            LsLuaApi::pushboolean(L, 0);
            return 3;
        }
    }
    else
    {
        LsLuaApi::pushboolean(L, 0);
        LsLuaApi::pushstring(L, "bad parameters");
        LsLuaApi::pushboolean(L, 0);
        return 3;
    }
}


static int LsLuaShmIncr(lua_State *L)
{
    const char *tag = "ls.shared.incr";
    char namebuf[0x100];
    int numElem = 2;
    LsShmHash *pShared;

    pShared = LsLuaShmGetHash(L, tag, numElem, namebuf, 0x100);
    if (pShared)
    {
        ls_luashm_t *pShmValue = LsLuaShmFind(pShared, namebuf);
        if ((pShmValue) && (!isTimeExpired(pShmValue)))
        {
            if (pShmValue->m_type == ls_luashm_long)
            {
                pShmValue->m_ulong++;
                LsLuaApi::pushinteger(L, pShmValue->m_ulong);
                LsLuaApi::pushnil(L);
            }
            else if (pShmValue->m_type == ls_luashm_double)
            {
                pShmValue->m_double += 1.0;
                LsLuaApi::pushnumber(L, pShmValue->m_double);
                LsLuaApi::pushnil(L);
            }
            else
            {
                LsLuaApi::pushnil(L);
                LsLuaApi::pushstring(L, "not a number");
            }
            return 2;
        }
        else
        {
            LsLuaApi::pushnil(L);
            LsLuaApi::pushstring(L, "not found");
            return 2;
        }
    }
    LsLuaApi::pushnil(L);
    LsLuaApi::pushstring(L, "bad parameters");
    return 2;
}


static int LsLuaShmDelete(lua_State *L)
{
    int num = LsLuaApi::gettop(L);
    if (num > 2)
        LsLuaApi::pop(L, num - 2);
    LsLuaApi::pushnil(L);
    return LsLuaShmSet(L);
}


typedef struct ls_luashm_scanner_s
{
    LsShmHash  *handle;
    const char *key;
    int         maxcheck;
    int         numchecked;
} ls_luashm_scanner_t;


int LsLuaShmFlushAllCb(LsShmHash::iteroffset iterOff, void *pUData)
{
    ls_luashm_scanner_t *pScanner = (ls_luashm_scanner_t *)pUData;
    LsShmHash::iterator iter = pScanner->handle->offset2iterator(iterOff);
    ls_luashm_t *pVal = (ls_luashm_t *)iter->getVal();
//     printf( "%s, %x\n", iter->getKey(), pVal->m_iMagic);
    if ((iter->getValLen() != sizeof(ls_luashm_t))
        || (pVal->m_iMagic != LS_LUASHM_MAGIC))
        return 0;

    if (strcmp(pScanner->key, "flush_all") == 0)
        pVal->m_expireTime = 1;
    else
        pVal->m_expireTime = 2;
    return 0;
}


int LsLuaShmFlushExpCb(LsShmHash::iteroffset iterOff, void *pUData)
{
    ls_luashm_scanner_t *pScanner = (ls_luashm_scanner_t *)pUData;
    LsShmHash::iterator iter = pScanner->handle->offset2iterator(iterOff);
    ls_luashm_t *pVal = (ls_luashm_t *)iter->getVal();

    if ((iter->getValLen() != sizeof(ls_luashm_t))
        || (pVal->m_iMagic != LS_LUASHM_MAGIC))
        return 0;

    if (isTimeExpired(pVal))
    {
        pVal->m_iMagic = 0;
        if (pVal->m_iValueLen > sizeof(double))
            pScanner->handle->release2(pVal->m_iOffset, pVal->m_iValueLen);
        pScanner->handle->eraseIterator(iterOff);
        ++pScanner->numchecked;
        if ((pScanner->maxcheck)
            && (pScanner->numchecked >= pScanner->maxcheck))
            return 1;
    }
    return 0;
}


static int LsLuaShmFlushAll(lua_State *L)
{
    ls_luashm_scanner_t scanner;
    LsShmHash *pShared = LsLuaShmGetSelf(L,
                                         "lsLua_shared_flush_all");

    if (pShared == NULL)
    {
        LsLuaApi::pushnil(L);
        LsLuaApi::pushstring(L, "bad parameters");
        return 2;
    }
    scanner.handle = pShared;
    scanner.key = "flush_all";
    scanner.maxcheck = 0;
    scanner.numchecked = 0;
    pShared->for_each2(pShared->begin(), pShared->end(), LsLuaShmFlushAllCb,
                       &scanner);
    return 0;
}


static int LsLuaShmFlushExpired(lua_State *L)
{
    ls_luashm_scanner_t scanner;
    LsShmHash *pShared = LsLuaShmGetSelf(L,
                                         "lsLua_shared_flush_all");

    if (pShared == NULL)
    {
        LsLuaApi::pushinteger(L, 0);
        return 1;
    }
    else
    {
        int numOut = 0;
        numOut = LsLuaApi::tointeger(L, 2);

        if (numOut < 0)
            numOut = 0;
        scanner.handle = pShared;
        scanner.key = NULL;
        scanner.maxcheck = numOut;
        scanner.numchecked = 0;
        int n = pShared->for_each2(pShared->begin(), pShared->end(),
                                   LsLuaShmFlushExpCb, &scanner);

        LsLuaApi::pushinteger(L, n);
        return 1;
    }
}


static int LsLuaShmNewhash(lua_State *L)
{
    size_t len = 0;
    const char *cp;

    cp = LsLuaApi::tolstring(L, 2, &len);
    if (cp && len && (len < LSSHM_MAXNAMELEN))
    {
        char buf[0x100];
        snprintf(buf, 0x100, "%.*s", (int)len, cp);

        LsShmHash *pHash = LsLuaShmOpen(buf);
        if (pHash == NULL)
        {
            return LsLuaApi::serverError(L, "shared_index", "Opening shared "
                                         "memory failed.");
        }

        return LsLuaShmCreate(L , pHash);
    }
    return LsLuaApi::userError(L, "shared_index", "Invalid input name");
}


static const luaL_Reg LsLuaShmLib[] =
{
    {   "get",             LsLuaShmGet},
    {   "get_stale",       LsLuaShmGetStale},
    {   "set",             LsLuaShmSet},
    {   "safe_set",        LsLuaShmSetSafe},
    {   "add",             LsLuaShmAdd},
    {   "safe_add",        LsLuaShmAddSafe},
    {   "replace",         LsLuaShmReplace},

    {   "incr",            LsLuaShmIncr},
    {   "delete",          LsLuaShmDelete},
    {   "flush_all",       LsLuaShmFlushAll},
    {   "flush_expired",   LsLuaShmFlushExpired},
    {NULL, NULL}
};

static const luaL_Reg LsLuaShmMeta[] =
{
    {   "__gc",        LsLuaShmGc},
    {   "__tostring",  LsLuaShmToString},
    {NULL, NULL}
};

void LsLuaCreateSharedmeta(lua_State *L)
{
    LsLuaApi::openlib(L, LS_LUA ".shared", LsLuaShmLib, 0);
    LsLuaApi::newmetatable(L, LSLUA_SHARED_DATA);
    LsLuaApi::openlib(L, NULL, LsLuaShmMeta, 0);

    LsLuaApi::pushlstring(L, "__index", 7);
    LsLuaApi::pushvalue(L, -3);
    LsLuaApi::rawset(L, -3);
    // pushliteral
    LsLuaApi::pushlstring(L, "__metatable", 11);
    LsLuaApi::pushvalue(L, -3);
    LsLuaApi::rawset(L, -3);

    LsLuaApi::settop(L, -3);
}

void LsLuaCreateShared(lua_State *L)
{
    LsLuaApi::createtable(L, 0, 0);
    LsLuaApi::createtable(L, 0, 2);
    LsLuaApi::pushcclosure(L, LsLuaShmNewhash, 0);
    LsLuaApi::setfield(L, -2, "__index");
    LsLuaApi::setmetatable(L, -2);
    LsLuaApi::setfield(L, -2, "shared");
}


