/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2017  LiteSpeed Technologies, Inc.                 *
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
#include <lsdef.h>
#include <ls.h>
#include <lsr/ls_confparser.h>
#include <util/autostr.h>
#include <util/stringtool.h>
#include <string.h>
#include <stdlib.h>

#define MNAME                modreqparser
#define ModuleNameStr        "modreqparser"
#define MODULE_VERSION_INFO  "1.0"

#define TMPDIR          "uploadTmpDir"
#define TMPPERMISSON    "uploadTmpFilePermission"
#define BYPATH          "uploadPassByPath"

extern lsi_module_t MNAME;
/***
 * Set the config of this module in SERVER, VHOST and context level as below
 * uploadTmpDir              /tmp/lshttpd/ 
 * uploadTmpFilePermission   666
 * uploadPassByPath          1
 */

typedef struct param_st
{
    AutoStr2   *tmpDir;
    uint8_t     byPath;
    uint8_t     ownDir; //AutoStr2   *tmpDir is own or not
    uint16_t    permission;
} param_t;

//Setup the below array to let web server know these params
lsi_config_key_t myParam[] =
{
    {TMPDIR,        0,},
    {TMPPERMISSON,  1,},
    {BYPATH,        2,},
    {NULL} //Must have NULL in the last item
};

uint16_t paramArrayCount = sizeof(myParam) / sizeof(lsi_config_key_t) - 1;

static void *_parseConfig(module_param_info_t *param, int param_count,
                          void *_initial_config, int level, const char *name)
{
    param_t *pInitConfig = (param_t *)_initial_config;
    param_t *pConfig = new param_t;
    if (!pConfig)
        return NULL;

    if (pInitConfig)
    {
        memcpy(pConfig, pInitConfig, sizeof(param_t));
        pConfig->ownDir = 0;
    }
    else
    {
        pConfig->permission = 0666;
        pConfig->byPath = 1;
        pConfig->tmpDir = new AutoStr2;
        pConfig->tmpDir->setStr( "/tmp/lshttpd/" );
        pConfig->ownDir = 1;
    }

    if (!param || param_count == 0)
        return (void *)pConfig;

    for (int i=0; i<param_count; ++i)
    {
        switch(param[i].key_index)
        {
        case 0:
            pConfig->tmpDir = new AutoStr2;
            pConfig->tmpDir->setStr(param[i].val, param[i].val_len);
            pConfig->ownDir = 1;
            break;


        case 1:
            pConfig->permission = strtol(param[i].val, NULL, 8);
            break;
            
        case 2:
            pConfig->byPath = strtol(param[i].val, NULL, 10);
            break;
        }
    }

    return (void *)pConfig;
}

static void _freeConfig(void *_config)
{
    param_t *pConfig = (param_t *)_config;
    if (pConfig->ownDir)
        delete pConfig->tmpDir;
    delete pConfig;
}


static int enableReqParser(lsi_param_t *rec)
{
    param_t *pConfig = (param_t *)g_api->get_config(rec->session, &MNAME);
    if (!pConfig)
    {
        g_api->log(rec->session, LSI_LOG_ERROR,
                   "[%s]enableReqParser error 1.\n", ModuleNameStr);
        return 0;
    }
    
    g_api->parse_req_args(rec->session, 1, pConfig->byPath, pConfig->tmpDir->c_str(),
                          pConfig->permission);
    return 0;
}

static int _init(lsi_module_t *module)
{
    return 0;
}

static lsi_serverhook_t server_hooks[] =
{
    { LSI_HKPT_RCVD_REQ_HEADER, enableReqParser, LSI_HOOK_FIRST, LSI_FLAG_ENABLED },
    LSI_HOOK_END   //Must put this at the end position
};

lsi_confparser_t _dealConfig = { _parseConfig, _freeConfig, myParam };
lsi_module_t MNAME = { LSI_MODULE_SIGNATURE, _init, NULL, &_dealConfig,
                       MODULE_VERSION_INFO, server_hooks, {0} };

                       