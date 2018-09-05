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

#include <ls.h>
#include <lsr/ls_str.h>
#include <lsr/ls_strtool.h>

#include <stdlib.h>
#include <string.h>
#include <unistd.h>


#define MNAME       modinspector
extern lsi_module_t MNAME;
#define DEF_SCANNER_PATH        "/usr/bin/clamdscan"
#define DEF_SCANNER_PREFIX      "Infected files:"
#define MODULE_VERSION_INFO     "1.1"

struct scanner_param_st
{
    char *path;
    char *prefix;
};


const int paramArrayCount = 2;
lsi_config_key_t paramArray[paramArrayCount + 1] =
{
    {"scannerpath",     0, LSI_CFG_SERVER | LSI_CFG_VHOST},
    {"counterprefix",   1, LSI_CFG_SERVER | LSI_CFG_VHOST},
    {NULL, 0, 0} //Must have NULL in the last item
};


static void *modinspector_parseConfig(module_param_info_t *param, int param_count,
                                      void *_initial_config, int level, const char *name)
{
    scanner_param_st *initConf = (scanner_param_st *)_initial_config;
    scanner_param_st *myConf = (scanner_param_st *) malloc(sizeof(
                                   scanner_param_st));
    if (!myConf)
        return NULL;

    
    memset(myConf, 0, sizeof(scanner_param_st));
    if (param == NULL || param_count <= 0)
    {
        if (access(DEF_SCANNER_PATH, 0) != -1)
        {
            myConf->path = strdup(DEF_SCANNER_PATH);
            myConf->prefix = strdup(DEF_SCANNER_PREFIX);
        }
        return (void *)myConf;
    }

    for (int i=0 ;i<param_count; ++i)
    {
        switch(paramArray[i].id)
        {
        case 0:
            myConf->path = strndup(param[i].val, param[i].val_len);
            break;
        case 1:
            myConf->prefix = strndup(param[i].val, param[i].val_len);
            break;
        }
    }

    if (!myConf->path)
        myConf->path = strdup(initConf ? initConf->path : DEF_SCANNER_PATH);
    if (!myConf->prefix)
        myConf->prefix = strdup(initConf ? initConf->prefix : DEF_SCANNER_PREFIX);

    return (void *)myConf;
}

static void modinspector_freeConfig(void *_config)
{
    scanner_param_st *pConfig = (scanner_param_st *)_config;
    if (pConfig)
    {
        if (pConfig->path)
            free(pConfig->path);
        if (pConfig->prefix)
            free(pConfig->prefix);
        free(pConfig);
    }
}


static int my_cb(lsi_session_t *session, const long lParam, void *pParam)
{
    int len;
    int count = 0;
    const char *prefix = (const char *)lParam;
    char *buf = g_api->get_ext_cmd_res_buf(session, &len);
    g_api->log(session, LSI_LOG_DEBUG,
               "[modinspector]result:\n %.*s\n",
               (len > 1024 ? 1024 : len),  buf);
    char *p = strstr(buf, prefix);
    if (!p)
    {
        g_api->log(session, LSI_LOG_ERROR,
                   "[modinspector]result does NOT contains prefix \"%s\".\n",
                   prefix);
    }
    else
    {
        sscanf(p + strlen(prefix), "%d", &count);
        if (count)
        {
            g_api->log(session, LSI_LOG_WARN,
                       "[modinspector]##--parsed Infections file number: [%d]--##\n", count);
            count = -1;
        }
    }

    g_api->resume(session, count);
    return 0;
}


static int checkFiles(lsi_param_t *param, const char *cmd, int len,
                      const char *prefix)
{
    g_api->log(param->session, LSI_LOG_DEBUG,
               "[modinspector]checkFiles: %.*s\n",
               len, cmd);
    return g_api->exec_ext_cmd(param->session, cmd, len, my_cb, (long)prefix,
                               NULL);
}


static int check_req_uploaded_file(lsi_param_t *param)
{
    char *path;
    int i, file_count = 0;

    scanner_param_st *scanner_st = (scanner_param_st *)
                                   g_api->get_config(param->session,
                                           &MNAME);

    ls_str_t *str = ls_str_new(scanner_st->path, strlen(scanner_st->path));
    int count = g_api->get_req_args_count(param->session);

    for (i = 0; i < count; ++i)
    {
        if (g_api->is_post_file_upload(param->session, i))
        {
            g_api->get_req_arg_by_idx(param->session, i, NULL, &path);
            ls_str_append(str, " ", 1);
            ls_str_append(str, path, strlen(path));
            ++file_count;
        }
    }

    if (file_count > 0)
    {
        int ret = checkFiles(param, ls_str_cstr(str), ls_str_len(str),
                             scanner_st->prefix);
        ls_str_delete(str);
        if (ret == 0)
            return LSI_SUSPEND;
        else
            return LSI_OK;
    }
    else
    {
        ls_str_delete(str);
        return LSI_OK;
    }
}

static int set_session(lsi_param_t *param)
{
    /**
     * If config is not correct, quit!!!
     */
    scanner_param_st *scanner_st = (scanner_param_st *)
                                   g_api->get_config(param->session,
                                           &MNAME);
    if (scanner_st && scanner_st->path && scanner_st->prefix)
    {
        g_api->parse_req_args(param->session, 1, 1, "/tmp/", 0666);

        int aEnableHkpts[1];
        aEnableHkpts[0] = LSI_HKPT_RCVD_REQ_BODY;
        g_api->enable_hook(param->session, &MNAME, 1,
                           aEnableHkpts, 1);
    }
    return LSI_OK;
}

static int _init(lsi_module_t *pModule)
{
    return 0;
}


static lsi_serverhook_t server_hooks[] =
{
    { LSI_HKPT_RCVD_REQ_HEADER, set_session, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED },
    { LSI_HKPT_RCVD_REQ_BODY, check_req_uploaded_file, LSI_HOOK_EARLY, 0 },
    LSI_HOOK_END   //Must put this at the end position
};

lsi_confparser_t testparam_dealConfig = { modinspector_parseConfig,
                                         modinspector_freeConfig,
                                         paramArray };
LSMODULE_EXPORT lsi_module_t MNAME =
{
    LSI_MODULE_SIGNATURE, _init, NULL, &testparam_dealConfig, MODULE_VERSION_INFO, server_hooks, { 0 }
};


