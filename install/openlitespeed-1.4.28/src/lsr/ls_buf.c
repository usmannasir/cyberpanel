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
#include <lsr/ls_buf.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_xpool.h>
#include <lsdef.h>
#include <errno.h>
#include <stdlib.h>
#include <lsdef.h>

ls_inline void *ls_buf_do_alloc(ls_xpool_t *pool, size_t size)
{
    return ((pool != NULL) ? ls_xpool_alloc(pool, size) : ls_palloc(size));
}


ls_inline void ls_buf_do_free(ls_xpool_t *pool, void *ptr)
{
    if (pool != NULL)
        ls_xpool_free(pool, ptr);
    else
        ls_pfree(ptr);
    return;
}


int ls_buf_xreserve(ls_buf_t *pThis, int size, ls_xpool_t *pool)
{
    char *pBuf;
    if (pThis->pbufend - pThis->pbuf == size)
        return 0;
    if (pool != NULL)
        pBuf = (char *)ls_xpool_realloc(pool, pThis->pbuf, size);
    else
        pBuf = (char *)ls_prealloc(pThis->pbuf, size);
    if ((pBuf != NULL) || (size == 0))
    {
        pThis->pend = pBuf + (pThis->pend - pThis->pbuf);
        pThis->pbuf = pBuf;
        pThis->pbufend = pBuf + size;
        if (pThis->pend > pThis->pbufend)
            pThis->pend = pThis->pbufend;
        return 0;
    }
    return LS_FAIL;
}


static void ls_buf_deallocate(ls_buf_t *pThis, ls_xpool_t *pool)
{
    if (pThis->pbuf != NULL)
    {
        ls_buf_do_free(pool, pThis->pbuf);
        pThis->pbuf = NULL;
    }
}


int ls_buf_popfrontto(ls_buf_t *pThis, char *pBuf, int sz)
{
    if (ls_buf_empty(pThis) == 0)
    {
        int copysize = (ls_buf_size(pThis) < sz) ? ls_buf_size(pThis) : sz;
        memmove(pBuf, pThis->pbuf, copysize);
        ls_buf_popfront(pThis, copysize);
        return copysize;
    }
    return 0;
}


int ls_buf_popfront(ls_buf_t *pThis, int sz)
{
    if (sz >= ls_buf_size(pThis))
        pThis->pend = pThis->pbuf;
    else
    {
        memmove(pThis->pbuf, pThis->pbuf + sz, ls_buf_size(pThis) - sz);
        pThis->pend -= sz;
    }
    return sz;
}


int ls_buf_popend(ls_buf_t *pThis, int sz)
{
    if (sz > ls_buf_size(pThis))
        pThis->pend = pThis->pbuf;
    else
        pThis->pend -= sz;
    return sz;
}


#define SWAP( a, b, t )  do{ t = a; a = b; b = t;  }while(0)
void ls_buf_swap(ls_buf_t *pThis, ls_buf_t *pRhs)
{
    char *pTemp;
    SWAP(pThis->pbuf, pRhs->pbuf, pTemp);

    SWAP(pThis->pbufend, pRhs->pbufend, pTemp);
    SWAP(pThis->pend, pRhs->pend, pTemp);
}


ls_buf_t *ls_buf_xnew(int size, ls_xpool_t *pool)
{
    ls_buf_t *pThis = (ls_buf_t *)ls_buf_do_alloc(pool, sizeof(ls_buf_t));
    if (pThis != NULL)
        ls_buf_x(pThis, size, pool);
    return pThis;
}


int ls_buf_x(ls_buf_t *pThis, int size, ls_xpool_t *pool)
{
    memset(pThis, 0, sizeof(ls_buf_t));
    return ls_buf_xreserve(pThis, size, pool);
}


void ls_buf_xd(ls_buf_t *pThis, ls_xpool_t *pool)
{
    ls_buf_deallocate(pThis, pool);
    pThis->pbuf = NULL;
    pThis->pbufend = NULL;
    pThis->pend = NULL;
}


void ls_buf_xdelete(ls_buf_t *pThis, ls_xpool_t *pool)
{
    ls_buf_xd(pThis, pool);
    ls_buf_do_free(pool, pThis);
}


ls_xbuf_t *ls_xbuf_new(int size, ls_xpool_t *pool)
{
    ls_xbuf_t *pThis = ls_buf_do_alloc(pool, sizeof(ls_xbuf_t));
    if (pThis != NULL)
        ls_xbuf(pThis, size, pool);
    return pThis;
}


int ls_xbuf(ls_xbuf_t *pThis, int size, ls_xpool_t *pool)
{
    memset(&pThis->buf, 0, sizeof(ls_buf_t));
    pThis->pool = pool;
    return ls_buf_xreserve(&pThis->buf, size, pool);
}


void ls_xbuf_d(ls_xbuf_t *pThis)
{
    ls_buf_xd(&pThis->buf, pThis->pool);
    pThis->pool = NULL;
}


void ls_xbuf_delete(ls_xbuf_t *pThis)
{
    ls_xbuf_d(pThis);
    ls_xpool_free(pThis->pool, pThis);
}


void ls_xbuf_swap(ls_xbuf_t *pThis, ls_xbuf_t *pRhs)
{
    ls_xpool_t *tmpPool;
    ls_buf_swap(&pThis->buf, &pRhs->buf);
    tmpPool = pThis->pool;
    pThis->pool = pRhs->pool;
    pRhs->pool = tmpPool;
}


int ls_buf_xappend2(
    ls_buf_t *pThis, const char *pBuf, int size, ls_xpool_t *pool)
{
    if ((pBuf == NULL) || (size < 0))
    {
        errno = EINVAL;
        return LS_FAIL;
    }
    if (size == 0)
        return 0;
    if (size > ls_buf_available(pThis))
    {
        if (ls_buf_xgrow(pThis, size - ls_buf_available(pThis), pool) == -1)
            return LS_FAIL;
    }
    memmove(ls_buf_end(pThis), pBuf, size);
    ls_buf_used(pThis, size);
    return size;
}


int ls_buf_xgrow(ls_buf_t *pThis, int size, ls_xpool_t *pool)
{
    size = ((size + 511) >> 9) << 9;
    return ls_buf_xreserve(pThis, ls_buf_capacity(pThis) + size, pool);
}

