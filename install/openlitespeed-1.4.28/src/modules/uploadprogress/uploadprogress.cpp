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
#include <ls.h>
#include <lsr/ls_shm.h>
#include <lsr/xxhash.h>
#include <string.h>
#include <stdlib.h>

#define MNAME               uploadprogress
#define ModuleNameStr       "mod-uploadprogress"
#define MOD_QS              "X-Progress-ID="
#define MOD_QS_LEN          (sizeof(MOD_QS) -1)
#define MAX_BUF_LENG        20
#define EXPIRE_TIME         (30 * 1000)
#define MODULE_VERSION_INFO  "1.1"

DECL_COMPONENT_LOG(ModuleNameStr);

ls_shmhash_t *pShmHash = NULL;
extern lsi_module_t MNAME;

enum
{
    UPLOAD_START = 0,
    UPLOAD_ERROR,
    UPLOAD_UPLOADING,
    UPLOAD_DONE,
};

enum HTTPMETHOD
{
    METHOD_UNKNOWN = 0,
    METHOD_GET,
    METHOD_POST,
};

typedef struct _MyMData
{
    char       *pBuffer;
    char       *pProgressID;  //be malloc when POST, and free in timerCB
    int64_t     iWholeLength;
    int64_t     iFinishedLength;
} MyMData;


static int releaseMData(void *data)
{
    MyMData *myData = (MyMData *)data;
    if (myData)
        delete myData;
    return 0;
}


static void removeShmEntry(const void *progressID)
{
    ls_shmhash_delete(pShmHash, (const uint8_t *)progressID,
                      strlen((char *)progressID));
    free((char *)progressID);
}


static int releaseModuleData(lsi_param_t *rec)
{
    MyMData *myData = (MyMData *)g_api->get_module_data(rec->session, &MNAME,
                      LSI_DATA_HTTP);
    if (myData)
    {
        /**
         * Set a timer to clean the shm data in 30 seconds
         */
        g_api->set_timer(EXPIRE_TIME, 0, removeShmEntry, myData->pProgressID);
        g_api->free_module_data(rec->session, &MNAME, LSI_DATA_HTTP,
                                releaseMData);
        LSC_DBG( rec->session,"releaseModuleData.\n" );
    }
    return 0;
}


static int setProgress(MyMData *pData)
{
    snprintf(pData->pBuffer, MAX_BUF_LENG, "%llX:%llX",
             (long long)pData->iWholeLength, (long long)pData->iFinishedLength);
    return 0;
}

static const char *getProgressId(const lsi_session_t *session, int &idLen)
{
    const char *pQS = g_api->get_req_query_string(session, &idLen);
    if (!pQS || strncasecmp(MOD_QS, pQS, MOD_QS_LEN) != 0
        || (size_t)idLen <= MOD_QS_LEN)
        return NULL;

    idLen -= MOD_QS_LEN;
    return (pQS + MOD_QS_LEN);
}

static lsi_hash_key_t hashBuf(const void *__s, size_t len)
{
    return XXH32(__s, len, 0);
}


static int _init(lsi_module_t *module)
{
    ls_shmpool_t *pShmPool = ls_shm_opengpool("moduploadp", 0);
    if (pShmPool == NULL)
    {
        LSC_ERR(NULL, "shm_pool_init return NULL, quit.\n");
        return LS_FAIL;
    }
    pShmHash = ls_shmhash_open(pShmPool, NULL, 0, hashBuf, memcmp);
    if (pShmHash == NULL)
    {
        LSC_ERR(NULL, "shm_htable_init return NULL, quit.\n");
        return LS_FAIL;
    }

    g_api->init_module_data(module, releaseMData, LSI_DATA_HTTP);
    return LS_OK;
}


static int reqBodyRead(lsi_param_t *rec)
{
    MyMData *myData = (MyMData *)g_api->get_module_data(rec->session, &MNAME,
                      LSI_DATA_HTTP);
    int len = g_api->stream_read_next(rec, (char *)rec->ptr1,
                                      rec->len1);
    myData->iFinishedLength += len;
    setProgress(myData);
    return len;
}


/**
 * Check if is a uploading, we will handle the below case:
 * POST(GET) /xxxxxxxx?X-Progress-ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
 */
static int checkReqHeader(lsi_param_t *rec)
{
    int idLen;
    const char *progressID = getProgressId(rec->session, idLen);
    long long contentLength = g_api->get_req_content_length(rec->session);
    if (progressID && contentLength <= 0)
    {
        //GET, must disable cache module
        g_api->set_req_env(rec->session, "cache-control", 13, "no-cache", 8);
        return 0;
    }
    if (!progressID || contentLength <= 0)
        return 0;

    char buf[MAX_BUF_LENG], *pBuffer;
    sprintf(buf, "%llX:0", contentLength);
    ls_shmoff_t offset = ls_shmhash_insert(pShmHash,
                                           (const uint8_t *)progressID, idLen, (const uint8_t *)buf, MAX_BUF_LENG);
    pBuffer = (char *)ls_shmhash_off2ptr(pShmHash, offset);
    if (!offset || !pBuffer)
    {
        LSC_ERR(rec->session, "checkReqHeader can't add shm entry.\n");
        return 0;
    }

    MyMData *myData = (MyMData *) g_api->get_module_data(rec->session, &MNAME,
                      LSI_DATA_HTTP);
    if (!myData)
    {
        myData = new MyMData;
        if (!myData)
        {
            LSC_ERR(rec->session, "checkReqHeader out of memory.\n");
            return 0;
        }
        memset(myData, 0, sizeof(MyMData));
    }

    myData->pProgressID = strndup(progressID, idLen);
    myData->iWholeLength = contentLength;
    myData->iFinishedLength = 0;
    myData->pBuffer = pBuffer;
    g_api->set_module_data(rec->session, &MNAME, LSI_DATA_HTTP,
                           (void *)myData);

    int aEnableHkpt[] = {LSI_HKPT_RECV_REQ_BODY, LSI_HKPT_HTTP_END };
    g_api->enable_hook(rec->session, &MNAME, 1, aEnableHkpt,
                       sizeof(aEnableHkpt) / sizeof(int));
    return LSI_OK;
}


static int getState(int64_t iWholeLength, int64_t iFinishedLength)
{
    if (iWholeLength <= 0)
        return UPLOAD_ERROR;
    else if (iFinishedLength >= iWholeLength)
        return UPLOAD_DONE;
    else if (iFinishedLength == 0)
        return UPLOAD_START;
    else
        return UPLOAD_UPLOADING;
}


/**
 * We will handle the below case:
 * GET /progress?X-Progress-ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
 * Otherwise return error 40X
 */
static int begin_process(const lsi_session_t *session)
{
    int idLen;
    const char *progressID = getProgressId(session, idLen);
    if (!progressID)
        return 400; //Bad Request

    int valLen;
    ls_shmoff_t offset = ls_shmhash_find(pShmHash,
                                         (const uint8_t *)progressID,
                                         idLen, &valLen);
    if (offset == 0 || valLen <= 2)  //At least 3 bytes
    {
        LSC_ERR(session, "begin_process error, can't find shm entry.\n");
        return 500;
    }

    char *p = (char *)ls_shmhash_off2ptr(pShmHash, offset);
    long long iWholeLength, iFinishedLength;
    sscanf(p, "%llX:%llX", &iWholeLength, &iFinishedLength);
    int state = getState(iWholeLength, iFinishedLength);

    char buf[100] = {0}; //enough
    g_api->set_resp_header(session, LSI_RSPHDR_CONTENT_TYPE, NULL, 0,
                           "application/json", 16, LSI_HEADEROP_SET);
    if (state == UPLOAD_ERROR)
        strcpy(buf, "{ \"state\" : \"error\", \"status\" : 500 }\r\n");
    else if (state == UPLOAD_START)
        strcpy(buf, "{ \"state\" : \"starting\" }\r\n");
    else if (state == UPLOAD_DONE)
        strcpy(buf, "{ \"state\" : \"done\" }\r\n");
    else
        snprintf(buf, 100,
                 "{ \"state\" : \"uploading\", \"size\" : %lld, \"received\" : %lld }\r\n",
                 iWholeLength, iFinishedLength);

    g_api->append_resp_body(session, buf, strlen(buf));
    g_api->end_resp(session);
    LSC_DBG(session, "processed for URI: %s\n", g_api->get_req_uri(session, NULL));
    return 0;
}


static lsi_serverhook_t server_hooks[] =
{
    { LSI_HKPT_RCVD_REQ_HEADER, checkReqHeader, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED },
    { LSI_HKPT_RECV_REQ_BODY, reqBodyRead, LSI_HOOK_NORMAL, 0 },
    { LSI_HKPT_HTTP_END, releaseModuleData, LSI_HOOK_LAST, 0},
    LSI_HOOK_END   //Must put this at the end position
};

static lsi_reqhdlr_t myhandler = { begin_process, NULL, NULL, NULL };
lsi_module_t MNAME =
{ LSI_MODULE_SIGNATURE, _init, &myhandler, NULL, MODULE_VERSION_INFO, server_hooks, {0} };


