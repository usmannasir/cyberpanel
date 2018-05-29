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
#include <lsdef.h>
#include <ls.h>
#include <lsr/ls_loopbuf.h>
#include <lsr/ls_objpool.h>
#include <lsr/ls_xpool.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>
#include <lsdef.h>


#define     MODULE_VERSION      "1.1"
#define     INIT_LOOPBUF_SIZE   8192

#define     SENDING_STR     "-->"
#define     RECVING_STR     "<--"
#define     COMPRESS_STR    "---"
#define     DECOMPRESS_STR  "+++"
#define     ZIP_STR         "Gzip"
#define     UNZIP_STR       "un-Gzip"

static ls_objpool_t zpooldeflate;
static ls_objpool_t zpoolinflate;
static int          zpooltimerid = 0;

enum
{
    Z_UNINITED = 0,
    Z_INITED,
    Z_EOF,
    Z_END,
};

typedef struct zbufinfo_s
{
    uint8_t         compresslevel; //0: Decompress, 1-9:compress
    int16_t         zstate;
    z_stream        zstream;
    ls_loopbuf_t    loopbuf;
} zbufinfo_t;

typedef struct zmoddata_s
{
    zbufinfo_t *recv;
    zbufinfo_t *send;
} zmoddata_t;

static void ls_zpool_manage(const void *)
{
    ls_objpool_shrinkto(&zpooldeflate, 10);
    ls_objpool_shrinkto(&zpoolinflate, 10);
}


static void *ls_zbufinfo_new()
{
    zbufinfo_t *pNew = (zbufinfo_t *)malloc(sizeof(zbufinfo_t));
    if (pNew == NULL)
        return NULL;
    memset(pNew, 0, sizeof(zbufinfo_t));
    pNew->zstream.opaque = Z_NULL;
    pNew->zstream.zalloc = Z_NULL;
    pNew->zstream.zfree = Z_NULL;
    if ((ls_loopbuf(&pNew->loopbuf, INIT_LOOPBUF_SIZE)) == NULL)
    {
        free(pNew);
        return NULL;
    }
    return pNew;
}


static void ls_zbufinfo_release(void *pObj)
{
    zbufinfo_t *pBuf = (zbufinfo_t *)pObj;
    ls_loopbuf_d(&pBuf->loopbuf);
    if (pBuf->zstate == Z_INITED || pBuf->zstate == Z_EOF)
    {
        if (pBuf->compresslevel == 0)
            inflateEnd(&pBuf->zstream);
        else
            deflateEnd(&pBuf->zstream);
    }
}


static void ls_zbufinfo_recycle(zbufinfo_t *pBuf)
{
    ls_loopbuf_clear(&pBuf->loopbuf);
    pBuf->zstate = Z_INITED;
    if (pBuf->compresslevel == 0)
    {
        inflateReset(&pBuf->zstream);
        ls_objpool_recycle(&zpoolinflate, pBuf);
    }
    else
    {
        deflateReset(&pBuf->zstream);
        ls_objpool_recycle(&zpooldeflate, pBuf);
    }
}


static zbufinfo_t *ls_zbufinfo_get(lsi_session_t *session,
                                   lsi_module_t *pModule,
                                   uint8_t compresslevel)
{
    zbufinfo_t *pBuf;
    if (compresslevel == 0)
        pBuf = (zbufinfo_t *)ls_objpool_get(&zpoolinflate);
    else
        pBuf = (zbufinfo_t *)ls_objpool_get(&zpooldeflate);
    if (pBuf == NULL)
        return NULL;
    pBuf->compresslevel = compresslevel;
    return pBuf;
}


static int ls_zmoddata_release(void *data)
{
    zmoddata_t *myData = (zmoddata_t *)data;
    if (myData)
    {
        if (myData->recv != NULL)
            ls_zbufinfo_recycle(myData->recv);
        if (myData->send != NULL)
            ls_zbufinfo_recycle(myData->send);
    }
    return LS_OK;
}


static int initstream(z_stream *pStream, uint8_t compresslevel)
{
    pStream->avail_in = 0;
    pStream->next_in = Z_NULL;
    if (compresslevel == 0)
    {
        if (inflateInit2(pStream, 32 + MAX_WBITS) != Z_OK)
            return LS_FAIL;
    }
    else
    {
        if (deflateInit2(pStream, compresslevel, Z_DEFLATED, 16 + MAX_WBITS,
                         8, Z_DEFAULT_STRATEGY) != Z_OK)
            return LS_FAIL;
    }
    return LS_OK;
}


int flushloopbuf(lsi_param_t *rec, int iState, ls_loopbuf_t *pBuf)
{
    int written = 0;
    int sz = 0;
    while (!ls_loopbuf_empty(pBuf))
    {
        sz = g_api->stream_write_next(rec, ls_loopbuf_begin(pBuf),
                                      ls_loopbuf_blksize(pBuf));
        if (sz < 0)
            return LS_FAIL;
        else if (sz > 0)
        {
            ls_loopbuf_popfront(pBuf, sz);
            written += sz;
        }
        else
            break;
    }

    if (ls_loopbuf_empty(pBuf) && iState == Z_END)
    {
        rec->flag_in |= LSI_CBFI_EOF;
        g_api->stream_write_next(rec, NULL, 0);
    }

    return written;
}


static int doCompression(lsi_param_t *rec, zbufinfo_t *pBufInfo,
                         int iDoFlush, const char *pModuleStr,
                         const char *pSendingStr, const char *pCompressStr)
{
    int ret, len, sz, consumed = 0, written = 0;
    ls_loopbuf_t *pBuf = &pBufInfo->loopbuf;
    z_stream *pStream = &pBufInfo->zstream;

    if (!ls_loopbuf_empty(pBuf))
    {
        written = flushloopbuf(rec, pBufInfo->zstate, pBuf);
        if (written == -1)
            return LS_FAIL;
        if (!ls_loopbuf_empty(pBuf))
        {
            if (rec->flag_out != NULL)
                *rec->flag_out |= LSI_CBFO_BUFFERED;
            return 0;
        }
    }

    if (pBufInfo->zstate == Z_END)
        return rec->len1;

    do
    {
        ls_loopbuf_xguarantee(pBuf, 1024,
                              g_api->get_session_pool(rec->session));
        len = ls_loopbuf_contiguous(pBuf);
        pStream->avail_out = len;
        pStream->next_out = (unsigned char *)ls_loopbuf_end(pBuf);

        if (pBufInfo->compresslevel == 0)
            ret = inflate(pStream, iDoFlush);
        else
            ret = deflate(pStream, iDoFlush);

        if (ret >= Z_OK)
        {
            consumed = rec->len1 - pStream->avail_in;
            ls_loopbuf_used(pBuf, len - pStream->avail_out);

            if (pBufInfo->zstate == Z_EOF && ret == Z_STREAM_END)
            {
                pBufInfo->zstate = Z_END;
                g_api->log(rec->session, LSI_LOG_DEBUG,
                           "[%s%s] compressbuf end of stream set.\n",
                           pModuleStr, pCompressStr);
            }

            sz = flushloopbuf(rec, pBufInfo->zstate, pBuf);
            if (sz > 0)
                written += sz;
            else if (sz < 0)
            {
                g_api->log(rec->session, LSI_LOG_ERROR,
                           "[%s%s] compressbuf in %d, return %d (written %d, "
                           "flag in %d)\n", pModuleStr, pCompressStr,
                           rec->len1, sz, written, rec->flag_in);
                return LSI_ERROR;
            }
            if (!ls_loopbuf_empty(pBuf))
                break;
        }
        else
        {
            g_api->log(rec->session, LSI_LOG_ERROR,
                       "[%s%s] compressbuf in %d, inflate/deflate return %d\n",
                       pModuleStr, pCompressStr, rec->len1, ret);
            if (ret != Z_BUF_ERROR)
                return LSI_ERROR;
        }
    }
    while (pBufInfo->zstate != Z_END && pStream->avail_out == 0);

    if (!(ls_loopbuf_empty(pBuf)) || (pBufInfo->zstate != Z_END
                                      && pStream->avail_out == 0))
    {
        if (rec->flag_out != NULL)
            *rec->flag_out |= LSI_CBFO_BUFFERED;
    }

    g_api->log(rec->session, LSI_LOG_DEBUG,
               "[%s%s] compressbuf [%s] in %d, consumed: %d, written %d, "
               "flag in %d, buffer has %d.\n", pModuleStr, pCompressStr,
               pSendingStr, rec->len1, consumed,
               written, rec->flag_in, ls_loopbuf_size(pBuf));
    return consumed;
}


static int compressbuf(lsi_param_t *rec, lsi_module_t *pModule,
                       int isSend)
{
    const char *pSendingStr, *pCompressStr, *pZipStr, *pModuleStr;
    zbufinfo_t *pBufInfo;
    z_stream *pStream;
    int ret;
    int finish = Z_NO_FLUSH;
    zmoddata_t *myData = (zmoddata_t *)g_api->get_module_data(
                             rec->session, pModule, LSI_DATA_HTTP);
    if (myData == NULL)
        return LSI_ERROR;
    pSendingStr = isSend ? SENDING_STR : RECVING_STR;
    pBufInfo = isSend ? myData->send : myData->recv;

    if (pBufInfo == NULL)
        return LSI_ERROR;

    pStream = &pBufInfo->zstream;
    pCompressStr = pBufInfo->compresslevel ? COMPRESS_STR : DECOMPRESS_STR;
    pZipStr = pBufInfo->compresslevel ? ZIP_STR : UNZIP_STR;
    pModuleStr = g_api->get_module_name(pModule);

    if (pBufInfo->zstate == Z_UNINITED)
    {
        if (initstream(pStream, pBufInfo->compresslevel) == LS_FAIL)
        {
            g_api->log(rec->session, LSI_LOG_ERROR,
                       "[%s%s] initZstream init method [%s], failed.\n",
                       pModuleStr, pCompressStr, pZipStr);
            ret = LSI_HKPT_RECV_RESP_BODY;
            g_api->enable_hook(rec->session, pModule, 0,
                               &ret, 1); // Disable
            return g_api->stream_write_next(rec, (const char *)rec->ptr1,
                                            rec->len1);
        }
        g_api->log(rec->session, LSI_LOG_DEBUG,
                   "[%s%s] initZstream init method [%s], succeeded.\n",
                   pModuleStr, pCompressStr, pZipStr);
        pBufInfo->zstate = Z_INITED;
    }

    if (pBufInfo->zstate < Z_EOF)
    {
        pStream->avail_in = rec->len1;
        pStream->next_in = (Byte *)rec->ptr1;
        if (rec->flag_in & LSI_CBFI_EOF)
        {
            pBufInfo->zstate = Z_EOF;
            rec->flag_in |= LSI_CBFI_FLUSH;
        }
        else if (rec->flag_in & LSI_CBFI_FLUSH)
            finish = Z_PARTIAL_FLUSH;
    }
    rec->flag_in &= ~LSI_CBFI_EOF;
    if (pBufInfo->zstate == Z_EOF)
        finish = Z_FINISH;
    return doCompression(rec, pBufInfo, finish, pModuleStr, pSendingStr,
                         pCompressStr);
}


static int sendinghook(lsi_param_t *rec)
{
    return compressbuf(rec, (lsi_module_t *)g_api->get_module(rec), 1);
}


static int recvinghook(lsi_param_t *rec)
{
    return compressbuf(rec, (lsi_module_t *)g_api->get_module(rec), 0);
}


static int clearrecv(lsi_param_t *rec)
{
    lsi_module_t *pModule = (lsi_module_t *)g_api->get_module(rec);
    zmoddata_t *myData = (zmoddata_t *)g_api->get_module_data(
                             rec->session, pModule, LSI_DATA_HTTP);
    if (myData)
    {
        if (myData->recv != NULL)
        {
            ls_zbufinfo_recycle(myData->recv);
            myData->recv = NULL;
        }
        if (myData->send == NULL)
            g_api->set_module_data(rec->session, pModule,
                                   LSI_DATA_HTTP, NULL);
    }
    return LSI_OK;
}

static int rmcontentlength(lsi_session_t *session)
{
    g_api->remove_resp_header(session, LSI_RSPHDR_CONTENT_LENGTH, NULL, 0);
    g_api->set_resp_content_length(session, -1);
    return LSI_OK;
}

static int cleardata(lsi_param_t *rec)
{
    g_api->free_module_data(rec->session, g_api->get_module(rec),
                            LSI_DATA_HTTP, ls_zmoddata_release);
    return LSI_OK;
}


static int init(lsi_module_t *pModule)
{
    ls_objpool(&zpooldeflate, 0, ls_zbufinfo_new, ls_zbufinfo_release);
    ls_objpool(&zpoolinflate, 0, ls_zbufinfo_new, ls_zbufinfo_release);
    if (zpooltimerid == 0)
        zpooltimerid = g_api->set_timer(10000, 1, ls_zpool_manage, NULL);
    if (zpooltimerid == LS_FAIL)
        return LSI_ERROR;
    return g_api->init_module_data(pModule, ls_zmoddata_release,
                                   LSI_DATA_HTTP);
}


static lsi_serverhook_t compresshooks[] =
{
    {
        LSI_HKPT_SEND_RESP_BODY, sendinghook, 3000,
        LSI_FLAG_PROCESS_STATIC | LSI_FLAG_TRANSFORM
    },
    { LSI_HKPT_RECV_RESP_BODY, recvinghook, 3000, 1 },
    { LSI_HKPT_RCVD_RESP_BODY, clearrecv, 3000, 0 },
    { LSI_HKPT_HTTP_END, cleardata, LSI_HOOK_NORMAL, 0 },
    { LSI_HKPT_HANDLER_RESTART, cleardata, LSI_HOOK_NORMAL, 0 },
    LSI_HOOK_END  //Must put this at the end position
};


static lsi_serverhook_t decompresshooks[] =
{
    {
        LSI_HKPT_SEND_RESP_BODY, sendinghook, -3000,
        LSI_FLAG_PROCESS_STATIC | LSI_FLAG_TRANSFORM
    },
    { LSI_HKPT_RECV_RESP_BODY, recvinghook, -3000, 1 },
    { LSI_HKPT_RCVD_RESP_BODY, clearrecv, -3000, 0 },
    { LSI_HKPT_HTTP_END, cleardata, LSI_HOOK_NORMAL, 0 },
    { LSI_HKPT_HANDLER_RESTART, cleardata, LSI_HOOK_NORMAL, 0 },
    LSI_HOOK_END  //Must put this at the end position
};

lsi_module_t modcompress = { LSI_MODULE_SIGNATURE, init, NULL, NULL,
                             MODULE_VERSION, compresshooks, {0}
                           };
lsi_module_t moddecompress = { LSI_MODULE_SIGNATURE, init, NULL, NULL,
                               MODULE_VERSION, decompresshooks, {0}
                             };


static int enablehook(lsi_session_t *session, lsi_module_t *pModule,
                      int isSend, uint8_t compresslevel)
{
    int ret, aEnableHkpt[5], iEnableCount = 0;
    zmoddata_t *myData = (zmoddata_t *)g_api->get_module_data(session,
                         pModule, LSI_DATA_HTTP);
    ls_xpool_t *pPool = g_api->get_session_pool(session);
    if (myData == NULL)
    {
        myData = (zmoddata_t *)ls_xpool_alloc(pPool, sizeof(zmoddata_t));
        if (myData == NULL)
        {
            g_api->log(session, LSI_LOG_ERROR,
                       "[%s] AddHooks failed: not enough memory.\n",
                       g_api->get_module_name(pModule));
            return LS_FAIL;
        }
        else
            memset(myData, 0, sizeof(*myData));
    }

    ret = LS_FAIL;
    if (isSend)
    {
        if ((myData->send != NULL)
            || ((myData->send = ls_zbufinfo_get(session, pModule,
                                                compresslevel)) != NULL))
            aEnableHkpt[iEnableCount++] = LSI_HKPT_SEND_RESP_BODY;
    }
    else
    {
        if ((myData->recv != NULL)
            || ((myData->recv = ls_zbufinfo_get(session, pModule,
                                                compresslevel)) != NULL))
        {
            aEnableHkpt[iEnableCount++] = LSI_HKPT_RECV_RESP_BODY;
            aEnableHkpt[iEnableCount++] = LSI_HKPT_RCVD_RESP_BODY;
        }
    }

    aEnableHkpt[iEnableCount++] = LSI_HKPT_HTTP_END;
    aEnableHkpt[iEnableCount++] = LSI_HKPT_HANDLER_RESTART;
    ret = g_api->enable_hook(session, pModule, 1, aEnableHkpt,
                             iEnableCount);
    if (ret == LS_OK)
    {
        rmcontentlength(session);
        g_api->set_module_data(session, pModule, LSI_DATA_HTTP,
                               (void *)myData);
        return ret;
    }
    if (myData->recv != NULL)
    {
        myData->recv->compresslevel = 0;
        ls_objpool_recycle(&zpooldeflate, myData->recv);
    }
    if (myData->send != NULL)
    {
        myData->send->compresslevel = 0;
        ls_objpool_recycle(&zpooldeflate, myData->send);
    }

    g_api->log(session, LSI_LOG_ERROR,
               "[%s] AddHooks failed: not enough memory or "
               "enable hooks failed.\n", g_api->get_module_name(pModule));
    return LS_FAIL;
}


int addModgzipFilter(lsi_session_t *session, int isSend,
                     uint8_t compresslevel)
{
    if (compresslevel == 0)
        return enablehook(session, &moddecompress, isSend, 0);
    else
        return enablehook(session, &modcompress, isSend, compresslevel);
}

