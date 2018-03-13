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

#include "../include/ls.h"
#include <string.h>
#include <stdint.h>
#include "stdlib.h"
#include <unistd.h>

#define     MNAME       testserverhook
lsi_module_t MNAME;

int write_log(const char *sHookName)
{
    g_api->log(NULL, LSI_LOG_DEBUG,
               "[Module:testserverhook] launch point %s\n", sHookName);
    return 0;
}

int writeALog1(lsi_param_t *rec) {   return write_log("LSI_HKPT_MAIN_INITED"); }
int writeALog2(lsi_param_t *rec) {   return write_log("LSI_HKPT_MAIN_PREFORK"); }
int writeALog3(lsi_param_t *rec) {   return write_log("LSI_HKPT_MAIN_POSTFORK"); }
int writeALog4(lsi_param_t *rec) {   return write_log("LSI_HKPT_WORKER_INIT"); }
int writeALog5(lsi_param_t *rec) {   return write_log("LSI_HKPT_WORKER_ATEXIT"); }
int writeALog6(lsi_param_t *rec) {   return write_log("LSI_HKPT_MAIN_ATEXIT"); }


static lsi_serverhook_t serverHooks[] =
{
    { LSI_HKPT_MAIN_INITED,    writeALog1, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED},
    { LSI_HKPT_MAIN_PREFORK,   writeALog2, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED},
    { LSI_HKPT_MAIN_POSTFORK,  writeALog3, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED},
    { LSI_HKPT_WORKER_INIT,    writeALog4, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED},
    { LSI_HKPT_WORKER_ATEXIT,  writeALog5, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED},
    { LSI_HKPT_MAIN_ATEXIT,    writeALog6, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED},
    LSI_HOOK_END   //Must put this at the end position
};

static int init_module(lsi_module_t *pModule)
{
    return 0;
}

lsi_module_t MNAME = { LSI_MODULE_SIGNATURE, init_module, NULL, NULL, "testserverhook v1.0", serverHooks};
