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
#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#include <edio/multiplexer.h>
#include <edio/multiplexerfactory.h>

#include <errno.h>
#include <string.h>
#include <sys/stat.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <ctype.h>


/* Generic LUA headers
*/
#include <math.h>
#ifdef __cplusplus
extern "C" {
#endif
#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>
#ifdef __cplusplus
};
#endif

int lsLua_load(lua_State *);

/* The following codes for reference only... no use
*/
/* interest one... this will call math.sin(x) for answer
*/
static int  xsin(lua_State *L)
{
    double  d, z;

    d = lua_tonumber(L, 1);     /* pop an argument */
    lua_pcall(L, 0, 0, 0);

    lua_getglobal(L, "testsin");
    lua_pushnumber(L, d);

    if (lua_pcall(L, 1, 1, 0))
    {
        /* problem... */
        fprintf(stderr, "ERROR: call lua_pcall [%s]\n",  lua_tostring(L, -1));
    }

    z = lua_tonumber(L, -1);

    lua_pop(L, 1); /* pop the return value */

    lua_pushnumber(L, z);   /* push return to LUA*/
    return 1;
}

static int  ysin(lua_State *L)
{
    char    bigbuf[0x100];
    double  d, z;

    d = lua_tonumber(L, 1);     /* pop an argument */
    lua_pcall(L, 0, 0, 0);

    sprintf(bigbuf, "print(\"math.sin(%g)=\", math.sin(%g))", d, d);
    printf("Going to execute[%s]\n", bigbuf);
    luaL_dostring(L, bigbuf);

    lua_getglobal(L, "math.sin");
    lua_pushnumber(L, d);

    if (lua_pcall(L, 1, 1, 0))
    {
        /* problem... */
        fprintf(stderr, "ERROR: call lua_pcall [%s]\n",  lua_tostring(L, -1));
    }

    z = lua_tonumber(L, -1);

    lua_pop(L, 1); /* pop the return value */

    lua_pushnumber(L, z);   /* push return to LUA*/
    return 1;
}


static int  test_sin(lua_State *L)
{
    double  d;

    d = lua_tonumber(L, 1);     /* pop an argument */
    lua_pushnumber(L, sin(d));  /* push return to LUA*/

    return 1;                   /* number of results */
}

static int  test_sumInt(lua_State *L)
{
    int total = 0;
    int num;
    int pop = 1;

    num = lua_tonumber(L, pop++);
    while (--num >= 0)
        total += lua_tonumber(L, pop++);
    lua_pushnumber(L, total);
    return 1;
}


/* set my c function for LUA
*/
static void luaMySetup(lua_State *L)
{
    printf("Loading my special c functions\n");
    lua_pushcfunction(L, test_sin);
    lua_setglobal(L, "testsin");

    lua_pushcfunction(L, test_sumInt);
    lua_setglobal(L, "testsumint");

    lua_pushcfunction(L, xsin);
    lua_setglobal(L, "xsin");

    lua_pushcfunction(L, ysin);
    lua_setglobal(L, "ysin");
}

int luaFile(char *filename)
{
    lua_State *L;
    int         ret = 0;

    L = luaL_newstate();

    /* version dependant here */
#if 0
    luaopen_base(L);
    luaopen_io(L);
    luaopen_table(L);
    luaopen_string(L);
    luaopen_math(L);
#endif
    luaL_openlibs(L);

    lsLua_load(L);
    if (luaL_dofile(L, filename))
    {
        /* bad filename */
        ret = -1;
    }
    lua_close(L);
    return ret;
}

int luaCmd(char *cmdline)
{
    static lua_State *L;

    if (!L)
    {
        if (L = luaL_newstate())
            return LS_FAIL;
        luaL_openlibs(L);
        lsLua_load(L);
    }
    if (luaL_dostring(L, cmdline))
    {
        /* bad command */
        return LS_FAIL;
    }
    return 0;
}

/*
    LiteSpeed LUA functions
*/
static int lsLusLen(lua_State *L)
{
    size_t      len;

    luaL_checklstring(L, 1, &len);
    lua_pushinteger(L, (lua_Integer)len);

    return 1;
}

/* Convert string to upper case
*/
static int lsLua2Upper(lua_State *L)
{
    size_t      len;
    luaL_Buffer tmp;

    const char *s = luaL_checklstring(L, 1, &len);

    char *p = luaL_buffinitsize(L, &tmp, len);
    for (int i = 0; i < len; i++)
        p[i] = toupper((unsigned char)s[i]);
    luaL_pushresultsize(&tmp, len);
    return 1;
}

/* Sum all the numbers
*/
static int  lsLuaSum(lua_State *L)
{
    int total = 0;
    int num;
    int pop = 1;

    while (1)
    {
        if (lua_isnumber(L, pop))
            total += lua_tonumber(L, pop++);
        else
        {
            lua_pushnumber(L, total);
            return 1;
        }
    }
}

static char lsLuaVersionStr [] =
{
    "LiteSpeed LUA V0.1"
};

static int  lsLuaVersion(lua_State *L)
{
    lua_pushstring(L, lsLuaVersionStr);
    return 1;
}

/*
    Should put all the litespeed supported LUA functions here
*/
static const luaL_Reg lsLuaLib[] =
{
    {"version",     lsLuaVersion},
    {"len",         lsLusLen},
    {"upper",       lsLua2Upper},
    {"sum",         lsLuaSum},
    {NULL, NULL}
};

/*
    lsLua_load - load all the LiteSpeed LUA libraries here
*/
int lsLua_load(lua_State *L)
{
    const luaL_Reg *p;

    lua_newtable(L);
    for (p = &lsLuaLib[0]; p->name; p++)
        luaL_setfuncs(L, p, 0);
    lua_setglobal(L, "ls");

    /* Addition setup for testing - not need in the future
    */
    luaMySetup(L);
    return 0;
}


/*  lsLua testing world start from here
*/
extern void dotty(lua_State *L);
void onIdleTime()
{
    lua_State *L;

    L = luaL_newstate();
    luaL_openlibs(L);

    lsLua_load(L);      /* load lsLua package */

    dotty(L);           /* Enable interactive */
    lua_close(L);
}

