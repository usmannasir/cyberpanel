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

/**
 * This test module will reply the counter of how many times of your IP accessing,
 * and of the page being accessed, and how many times of this file be accessed
 * If test uri is /testmoduledata/file1, and if /file1 exists in testing vhost directory
 * then the uri will be handled
 */



/***
 * HOW TO TEST
 * Create a file "aaa", "bbb" in the /Example/html,
 * then curl http://127.0.0.1:8088/testmoduledata/aaa and
 * curl http://127.0.0.1:8088/testmoduledata/bbb,
 * you will see the result
 *
 */
#include "../include/ls.h"
#include <lsr/ls_shm.h>
#include <lsr/ls_confparser.h>
#include <lsr/ls_pool.h>

#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#include <unistd.h>
#include <lsdef.h>

#define     MNAME       testmoduledata
lsi_module_t MNAME;

#define URI_PREFIX   "/testmoduledata"
#define URI_PREFIX_LEN  (sizeof(URI_PREFIX) - 1)


#define max_file_len    1024
ls_shmhash_t *pShmHash = NULL;

const char *sharedDataStr = "MySharedData";
const int sharedDataLen = 12;

typedef struct
{
    long count;
} CounterData;

int releaseCounterDataCb(void *data)
{
    if (!data)
        return 0;

    CounterData *pData = (CounterData *)data;
    pData->count = 0;
    ls_pfree(pData);
    return 0;
}

CounterData *allocateMydata(const lsi_session_t *session,
                            const lsi_module_t *module, int level)
{
    CounterData *myData = (CounterData *)ls_palloc(sizeof(CounterData));
    if (myData == NULL)
        return NULL;

    memset(myData, 0, sizeof(CounterData));
    g_api->set_module_data(session, module, level, (void *)myData);
    return myData;
}

int assignHandler(lsi_param_t *rec)
{
    const char *p;
    char path[max_file_len] = {0};
    CounterData *file_data;
    int len;
    const char *uri = g_api->get_req_uri(rec->session, &len);
    if (len >= URI_PREFIX_LEN &&
        strncasecmp(uri, URI_PREFIX, URI_PREFIX_LEN) == 0)
    {
        if (len == URI_PREFIX_LEN)
            p = "/";
        else
            p = uri + URI_PREFIX_LEN;
        if (0 == g_api->get_uri_file_path(rec->session, p, strlen(p), path,
                                          max_file_len) &&
            access(path, 0) != -1)
        {
            g_api->set_req_env(rec->session, "cache-control", 13, "no-cache", 8);
            g_api->register_req_handler(rec->session, &MNAME, 0);
            //set the FILE data here, so that needn't to parse the file path again later
            g_api->init_file_type_mdata(rec->session, &MNAME, path, strlen(path));
            file_data = (CounterData *)g_api->get_module_data(rec->session, &MNAME,
                        LSI_DATA_FILE);
            if (file_data == NULL)
                file_data = allocateMydata(rec->session, &MNAME, LSI_DATA_FILE);
        }
    }
    return 0;
}

static int PsHandlerProcess(const lsi_session_t *session)
{
    CounterData *ip_data = NULL, *vhost_data = NULL, *file_data = NULL;
    char output[128];

    ip_data = (CounterData *)g_api->get_module_data(session, &MNAME,
              LSI_DATA_IP);
    if (ip_data == NULL)
        ip_data = allocateMydata(session, &MNAME, LSI_DATA_IP);
    if (ip_data == NULL)
        return 500;

    vhost_data = (CounterData *)g_api->get_module_data(session, &MNAME,
                 LSI_DATA_VHOST);
    if (vhost_data == NULL)
        vhost_data = allocateMydata(session, &MNAME, LSI_DATA_VHOST);
    if (vhost_data == NULL)
        return 500;

    file_data = (CounterData *)g_api->get_module_data(session, &MNAME,
                LSI_DATA_FILE);
    if (file_data == NULL)
        return 500;

    ++ip_data->count;
    ++file_data->count;
    ++vhost_data->count;


    int len = 1024, flag = 0;
    ls_shmoff_t offset = ls_shmhash_get(pShmHash,
                                        (const uint8_t *)URI_PREFIX, sizeof(URI_PREFIX) - 1, &len, &flag);
    if (offset == 0)
    {
        g_api->log(NULL, LSI_LOG_ERROR,
                   "ls_shmhash_get return 0, so quit.\n");
        return 500;
    }

    char *pBuf = (char *)ls_shmhash_off2ptr(pShmHash, offset);
    int sharedCount = 0;
    if (strncmp(pBuf, sharedDataStr, sharedDataLen) != 0)
    {
        g_api->log(NULL, LSI_LOG_ERROR,
                   "[testmoduledata] Shm Htable returned incorrect"
                   " number of arguments.\n");
        return 500;
    }
    sharedCount = strtol(pBuf + 13, NULL, 10);
    snprintf(pBuf, len, "%s %d\n", sharedDataStr, ++sharedCount);

    sprintf(output,
            "IP counter = %ld\nVHost counter = %ld\nFile counter = %ld\n%s",
            ip_data->count, vhost_data->count, file_data->count, pBuf);
    g_api->append_resp_body(session, output, strlen(output));
    g_api->end_resp(session);
    return 0;
}

static lsi_serverhook_t serverHooks[] =
{
    {LSI_HKPT_RCVD_REQ_HEADER, assignHandler, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED},
    LSI_HOOK_END   //Must put this at the end position
};

static int init_module(lsi_module_t *pModule)
{
    ls_shmpool_t *pShmPool = ls_shm_opengpool("testSharedM", 0);
    if (pShmPool == NULL)
    {
        g_api->log(NULL, LSI_LOG_ERROR,
                   "ls_shm_opengpool return NULL, so quit.\n");
        return LS_FAIL;
    }
    pShmHash = ls_shmhash_open(pShmPool, NULL, 0, NULL, NULL);
    if (pShmHash == NULL)
    {
        g_api->log(NULL, LSI_LOG_ERROR,
                   "ls_shmhash_open return NULL, so quit.\n");
        return LS_FAIL;
    }

    int len = 1024, flag = LSI_SHM_INIT;
    ls_shmoff_t offset = ls_shmhash_get(pShmHash,
                                        (const uint8_t *)URI_PREFIX, sizeof(URI_PREFIX) - 1, &len, &flag);
    if (offset == 0)
    {
        g_api->log(NULL, LSI_LOG_ERROR,
                   "ls_shmhash_get return 0, so quit.\n");
        return LS_FAIL;
    }

    if (flag == LSI_SHM_CREATED)
    {
        //Set the init value to it
        uint8_t *pBuf = ls_shmhash_off2ptr(pShmHash, offset);
        snprintf((char *)pBuf, len, "MySharedData 0\r\n");
    }

    g_api->init_module_data(pModule, releaseCounterDataCb,
                            LSI_DATA_VHOST);
    g_api->init_module_data(pModule, releaseCounterDataCb, LSI_DATA_IP);
    g_api->init_module_data(pModule, releaseCounterDataCb,
                            LSI_DATA_FILE);

    return LS_OK;
}

lsi_reqhdlr_t myhandler = { PsHandlerProcess, NULL, NULL, NULL };
lsi_module_t MNAME = { LSI_MODULE_SIGNATURE, init_module, &myhandler, NULL, "", serverHooks};
