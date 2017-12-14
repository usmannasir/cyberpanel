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

/*
    Testing junk
    Simple dotty driver for testing purpose... most of the useless code.
*/
static const char *progname;

/* junk from Jit - just want to see...
 */
//#define LUA_REGISTRYINDEX   (-10000)
#define LUA_ENVIRONINDEX    (-10001)
#define LUA_GLOBALSINDEX    (-10002)
//#define lua_upvalueindex(i) (LUA_GLOBALSINDEX-(i))
#define LUA_PROMPT  "> "    /* Interactive prompt. */
#define LUA_PROMPT2 ">> "   /* Continuation prompt. */
#define LUA_MAXINPUT    512 /* Max. input line length. */

static void l_message(const char *pname, const char *msg)
{
    if (pname) fprintf(stderr, "%s: ", pname);
    fprintf(stderr, "%s\n", msg);
    fflush(stderr);
}

static int report(lua_State *L, int status)
{
    if (status && !lua_isnil(L, -1))
    {
        const char *msg = lua_tostring(L, -1);
        if (msg == NULL) msg = "(error object is not a string)";
        l_message(progname, msg);
        lua_pop(L, 1);
    }
    return status;
}

static int traceback(lua_State *L)
{
    if (!lua_isstring(L, 1))   /* Non-string error object? Try metamethod. */
    {
        if (lua_isnoneornil(L, 1) ||
            !luaL_callmeta(L, 1, "__tostring") ||
            !lua_isstring(L, -1))
            return 1;  /* Return non-string error object. */
        lua_remove(L, 1);  /* Replace object by result of __tostring metamethod. */
    }
    luaL_traceback(L, L, lua_tostring(L, 1), 1);
    return 1;
}

static int docall(lua_State *L, int narg, int clear)
{
    int status;
    int base = lua_gettop(L) - narg;  /* function index */
    lua_pushcfunction(L, traceback);  /* push traceback function */
    lua_insert(L, base);  /* put it under chunk and args */

    status = lua_pcall(L, narg, (clear ? 0 : LUA_MULTRET), base);

    lua_remove(L, base);  /* remove traceback function */
    /* force a complete garbage collection in case of errors */
    if (status != 0) lua_gc(L, LUA_GCCOLLECT, 0);
    return status;
}

static void write_prompt(lua_State *L, int firstline)
{
#if 0
    const char *p;
    lua_getfield(L, LUA_GLOBALSINDEX, firstline ? "_PROMPT" : "_PROMPT2");
    p = lua_tostring(L, -1);
    if (p == NULL) p = firstline ? LUA_PROMPT : LUA_PROMPT2;
    fputs(p, stdout);
    fflush(stdout);
    lua_pop(L, 1);  /* remove global */
#endif
    fprintf(stdout, "simon>");
    fflush(stdout);

}


static int incomplete(lua_State *L, int status)
{
    if (status == LUA_ERRSYNTAX)
    {
        size_t lmsg;
        const char *msg = lua_tolstring(L, -1, &lmsg);
        const char *tp = msg + lmsg - (sizeof(LUA_QL("<eof>")) - 1);
        if (strstr(msg, LUA_QL("<eof>")) == tp)
        {
            lua_pop(L, 1);
            return 1;
        }
    }
    return 0;  /* else... */
}

static int pushline(lua_State *L, int firstline)
{
    char buf[LUA_MAXINPUT];
    write_prompt(L, firstline);
    if (fgets(buf, LUA_MAXINPUT, stdin))
    {
        size_t len = strlen(buf);
        if (len > 0 && buf[len - 1] == '\n')
            buf[len - 1] = '\0';
        if (firstline && buf[0] == '=')
            lua_pushfstring(L, "return %s", buf + 1);
        else
            lua_pushstring(L, buf);
        return 1;
    }
    return 0;
}

static int loadline(lua_State *L)
{
    int status;
    lua_settop(L, 0);
    if (!pushline(L, 1))
        return LS_FAIL;  /* no input */
    for (;;)    /* repeat until gets a complete line */
    {
        const char *str = lua_tostring(L, 1);
        status = luaL_loadbuffer(L, str, strlen(str), "=stdin");
        if (!incomplete(L, status)) break;  /* cannot try to add lines? */
        if (!pushline(L, 0))  /* no more input? */
            return LS_FAIL;
        lua_pushliteral(L, "\n");  /* add a new line... */
        lua_insert(L, -2);  /* ...between the two lines */
        lua_concat(L, 3);  /* join them */
    }
    lua_remove(L, 1);  /* remove line */
    return status;
}

void dotty(lua_State *L)
{
    int status;
    const char *oldprogname = progname;
    progname = NULL;
    while ((status = loadline(L)) != -1)
    {
        if (status == 0) status = docall(L, 0, 0);
        report(L, status);
        if (status == 0 && lua_gettop(L) > 0)    /* any result to print? */
        {
            lua_getglobal(L, "print");
            lua_insert(L, 1);
            if (lua_pcall(L, lua_gettop(L) - 1, 0, 0) != 0)
                l_message(progname,
                          lua_pushfstring(L, "error calling " LUA_QL("print") " (%s)",
                                          lua_tostring(L, -1)));
        }
    }
    lua_settop(L, 0);  /* clear stack */
    fputs("\n", stdout);
    fflush(stdout);
    progname = oldprogname;
}


