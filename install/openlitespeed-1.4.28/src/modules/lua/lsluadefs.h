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
#ifndef LSLUADEFS_H
#define LSLUADEFS_H

#ifdef __cplusplus
extern "C" {
#endif
/* need lua_State * */
#include <luajit.h>
#include <lauxlib.h>
#ifdef __cplusplus
};
#endif

/* NOTE Check this on every release - This valuable according to JIT 5.1
*/
#ifndef LUA_GLOBALSINDEX
#define LUA_GLOBALSINDEX (-10002)
#endif

#if LUA_VERSION_NUM < 502
#define LSLUA_REGISTRYINDEX -10000
#define LSLUA_GLOBALSINDEX  -10002
#define LSLUA_RIDX_GLOBALS  0
#else

#ifndef LUA_RIDX_GLOBALS
#define LUA_RIDX_GLOBALS 2
#endif

#define LSLUA_REGISTRYINDEX LUA_REGISTRYINDEX
#define LSLUA_GLOBALSINDEX  LUA_GLOBALSINDEX
#define LSLUA_RIDX_GLOBALS  LUA_RIDX_GLOBALS
#endif

#define LS_LUA          "lstable"       /* LiteSpeed Name space Table */
#define LS_LUA_FUNCTABLE "_func"        /* LiteSpeed Name space */
#define LS_LUA_HEADER   "header"        /* header */
#define LS_LUA_UD       "ls"            /* LiteSpeed Name Space */
#define LS_LUA_UDMETA   "ls_ud_meta"    /* UserData Meta */
#define LS_LUA_BOX      "LS_BOX"        /* Sandbox */
#define LSLUA_RE        "LS_RE"
#define LSLUA_SESSION_META "LS_SESSMETA"
#define LSLUA_REQ       "LS_REQ"
#define LSLUA_RESP      "LS_RESP"
#define LSLUA_SESSION   "LS_SESSION"
#define LS_HEADER       LS_LUA ".header"

#define LSLUA_RESP_HEADER "LS_RESP_HEADER"
#define LSLUA_RESP "LS_RESP"
#define LSLUA_REQ "LS_REQ"

#define LSLUA_TCPSOCKDATA "LS_TCP"
#define LSLUA_SHARED_DATA "LS_SHARED"

#define LSLUA_OK        0
#define LSLUA_DONE      0
#define LSLUA_DECLINED -1
#define LSLUA_DENY     -2

#define LS_LUA_CLEANUPMSEC 2000    /* specified cleanup time (msec) after _end() 2sec delay*/

#define LS_LUA_MAX_ARGS 128
#define LSLUA_PRINT_MAX_FRAG_SIZE 256
#define LSLUA_SESS_MAXQSLEN     16*1024
#define LSLUA_SESS_MAXURILEN    40*1024
#define MAXFILENAMELEN  0x1000
#define F_PAGESIZE    0x2000
#define TMPBUFSIZE  0x2000
#define MAX_RESP_HEADERS_NUMBER     50

#define LSLUA_PRINT_FLAG_DEBUG      1
#define LSLUA_PRINT_FLAG_VALUE_ONLY 2
#define LSLUA_PRINT_FLAG_KEY_ONLY   4
#define LSLUA_PRINT_FLAG_ADDITION   8
#define LSLUA_PRINT_FLAG_CR         16
#define LSLUA_PRINT_FLAG_LF         32

#define LLF_LUADONE         1<<0
#define LLF_WAITLINEEXEC    1<<1
#define LLF_URLREDIRECTED   1<<2
#define LLF_WAITREQBODY     1<<4
#define LLF_WAITRESPBUF     1<<5
#define LLF_BODYFINISHED    1<<6
#define LLF_TRYSENDRESP     1<<7

// local stuff for TIMER
#define SET_TIMER_NORMAL        0
#define SET_TIMER_ENDDELAY      1
#define SET_TIMER_MAXRUNTIME    2

#define LSLUA_HOOK_REWRITE  1<<0
#define LSLUA_HOOK_AUTH     1<<1
#define LSLUA_HOOK_HANDLER  1<<2
#define LSLUA_HOOK_HEADER   1<<3
#define LSLUA_HOOK_BODY     1<<4


#define LUA_ERRSTR_SANDBOX "\r\nERROR: LUA SANDBOX SETUP\r\n"
#define LUA_ERRSTR_SCRIPT  "\r\nERROR: FAILED TO LOAD LUA SCRIPT\r\n"
#define LUA_ERRSTR_ERROR  "\r\nERROR: LUA ERROR\r\n"

#define LUA_RESUME_ERROR    "LUA RESUME SCRIPT ERROR"



#endif // LSLUADEFS_H
