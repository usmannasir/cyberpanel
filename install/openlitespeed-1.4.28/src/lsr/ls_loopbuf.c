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
#define _GNU_SOURCE

#include <lsdef.h>
#include <lsr/ls_loopbuf.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_xpool.h>

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>


static int ls_loopbuf_iAppend(ls_loopbuf_t *pThis, const char *pBuf,
                              int size, ls_xpool_t *pool);
static int ls_loopbuf_iGuarantee(ls_loopbuf_t *pThis, int size,
                                 ls_xpool_t *pool);


static void ls_loopbuf_deallocate(ls_loopbuf_t *pThis, ls_xpool_t *pool)
{
    if (pThis->pbuf != NULL)
    {
        if (pool != NULL)
            ls_xpool_free(pool, pThis->pbuf);
        else
            ls_pfree(pThis->pbuf);
    }
    memset(pThis, 0, sizeof(ls_loopbuf_t));
}


static int ls_loopbuf_allocate(ls_loopbuf_t *pThis, ls_xpool_t *pool,
                               int size)
{
    if ((size == 0) && (pThis->sizemax != size))
        ls_loopbuf_deallocate(pThis, pool);
    else
    {
        size = (size + LSR_LOOPBUFUNIT) / LSR_LOOPBUFUNIT * LSR_LOOPBUFUNIT;
        if (size > pThis->sizemax)
        {
            char *pBuf;
            if (pool != NULL)
                pBuf = (char *)ls_xpool_alloc(pool, size);
            else
                pBuf = (char *)ls_palloc(size);
            if (pBuf == NULL)
            {
                errno = ENOMEM;
                return LS_FAIL;
            }
            else
            {
                int len = 0;
                if (pThis->pbuf != NULL)
                {
                    len = ls_loopbuf_moveto(pThis, pBuf, size - 1);
                    if (pool)
                        ls_xpool_free(pool, pThis->pbuf);
                    else
                        ls_pfree(pThis->pbuf);
                }
                pThis->pbuf = pThis->phead = pBuf ;
                pThis->pend = pThis->pbuf + len;
                pThis->sizemax = size;
                pThis->pbufend = pThis->pbuf + size;
            }
        }
    }
    return LS_OK;
}


ls_loopbuf_t *ls_loopbuf_new(int size)
{
    ls_loopbuf_t *pThis = (ls_loopbuf_t *)ls_palloc(sizeof(ls_loopbuf_t));
    if (pThis == NULL)
        return NULL;
    if (ls_loopbuf(pThis, size) == NULL)
    {
        ls_pfree(pThis);
        return NULL;
    }
    return pThis;
}


ls_loopbuf_t *ls_loopbuf(ls_loopbuf_t *pThis, int size)
{
    if (size == 0)
        size = LSR_LOOPBUFUNIT;
    memset(pThis, 0, sizeof(ls_loopbuf_t));
    ls_loopbuf_reserve(pThis, size);
    return pThis;
}


void ls_loopbuf_delete(ls_loopbuf_t *pThis)
{
    ls_loopbuf_deallocate(pThis, NULL);
    ls_pfree(pThis);
}


int ls_loopbuf_available(const ls_loopbuf_t *pThis)
{
    int ret = pThis->phead - pThis->pend - 1;
    if (ret >= 0)
        return ret;
    return ret + pThis->sizemax;
}


int ls_loopbuf_contiguous(const ls_loopbuf_t *pThis)
{
    if (pThis->phead > pThis->pend)
        return (pThis->phead - pThis->pend - 1);
    else
        return (pThis->phead == pThis->pbuf) ?
               (pThis->pbufend - pThis->pend - 1) : pThis->pbufend - pThis->pend;
}


void ls_loopbuf_used(ls_loopbuf_t *pThis, int size)
{
    int avail = ls_loopbuf_available(pThis);
    if (size > avail)
        size = avail;

    pThis->pend += size;
    if (pThis->pend >= pThis->pbufend)
        pThis->pend -= pThis->sizemax ;
}


int ls_loopbuf_moveto(ls_loopbuf_t *pThis, char *pBuf, int size)
{
    if ((pBuf == NULL) || (size < 0))
    {
        errno = EINVAL;
        return LS_FAIL;
    }
    int len = ls_loopbuf_size(pThis);
    if (len > size)
        len = size ;
    if (len > 0)
    {
        size = pThis->pbufend - pThis->phead ;
        if (size > len)
            size = len ;
        memmove(pBuf, pThis->phead, size);
        pBuf += size;
        size = len - size;
        if (size)
            memmove(pBuf, pThis->pbuf, size);
        ls_loopbuf_popfront(pThis, len);
    }
    return len;
}


int ls_loopbuf_popback(ls_loopbuf_t *pThis, int size)
{
    if (size < 0)
    {
        errno = EINVAL;
        return LS_FAIL;
    }
    if (size > 0)
    {
        int len = ls_loopbuf_size(pThis);
        if (size >= len)
        {
            size = len ;
            pThis->phead = pThis->pend = pThis->pbuf;
        }
        else
        {
            pThis->pend -= size ;
            if (pThis->pend < pThis->pbuf)
                pThis->pend += pThis->sizemax ;
        }
    }
    return size;
}


int ls_loopbuf_popfront(ls_loopbuf_t *pThis, int size)
{
    if (size < 0)
    {
        errno = EINVAL;
        return LS_FAIL;
    }
    if (size > 0)
    {
        int len = ls_loopbuf_size(pThis);
        if (size >= len)
        {
            size = len ;
            pThis->phead = pThis->pend = pThis->pbuf;
        }
        else
        {
            pThis->phead += size;
            if (pThis->phead >= pThis->pbufend)
                pThis->phead -= pThis->sizemax;
        }
    }
    return size;
}


void ls_loopbuf_swap(ls_loopbuf_t *lhs, ls_loopbuf_t *rhs)
{
    assert(rhs);
    char temp[sizeof(ls_loopbuf_t) ];
    memmove(temp, lhs, sizeof(ls_loopbuf_t));
    memmove(lhs, rhs, sizeof(ls_loopbuf_t));
    memmove(rhs, temp, sizeof(ls_loopbuf_t));
}


void ls_loopbuf_update(ls_loopbuf_t *pThis, int offset, const char *pBuf,
                       int size)
{
    char *p = ls_loopbuf_getptr(pThis, offset);
    const char *pEnd = pBuf + size;
    while (pBuf < pEnd)
    {
        *p++ = *pBuf++;
        if (p == pThis->pbufend)
            p = pThis->pbuf;
    }
}


char *ls_loopbuf_search(ls_loopbuf_t *pThis, int offset,
                        const char *accept, int acceptLen)
{
    char   *pSplitStart,
           *ptr = NULL,
            *pIter = ls_loopbuf_getptr(pThis, offset);
    const char *pAcceptPtr = accept;
    int iMiss = 0;

    if (acceptLen > ls_loopbuf_size(pThis))
        return NULL;
    if (pIter <= pThis->pend)
        return (char *)memmem(pIter, pThis->pend - pIter, accept, acceptLen);

    if (acceptLen <= pThis->pbufend - pIter)
    {
        if ((ptr = (char *)memmem(pIter, pThis->pbufend - pIter, accept,
                                  acceptLen)) != NULL)
            return ptr;
        pIter = pThis->pbufend - (acceptLen - 1);
    }
    pSplitStart = pIter;

    while ((pIter > pThis->pend) || (pAcceptPtr != accept))
    {
        if (*pIter == *pAcceptPtr)
        {
            if (pAcceptPtr == accept)
                ptr = pIter;
            if (++pAcceptPtr - accept == acceptLen)
                return ptr;
        }
        else
        {
            pAcceptPtr = accept;
            pIter = pSplitStart + iMiss++;
        }
        if (++pIter >= pThis->pbufend)
            pIter = pThis->pbuf;
    }
    return (char *)memmem(pThis->pbuf, pThis->pend - pThis->pbuf, accept,
                          acceptLen);
}


int ls_loopbuf_insiov(ls_loopbuf_t *pThis, struct iovec *vect, int count)
{
    if ((pThis->pend > pThis->phead) && (count == 1))
    {
        vect->iov_base = pThis->phead;
        vect->iov_len = pThis->pend - pThis->phead;
    }
    else if ((pThis->pend < pThis->phead) && (count == 2))
    {
        vect->iov_base = pThis->phead;
        vect->iov_len = pThis->pbufend - pThis->phead;

        (++vect)->iov_base = pThis->pbuf;
        vect->iov_len = pThis->pend - pThis->pbuf;
    }
    else
    {
        errno = EINVAL;
        return LS_FAIL;
    }
    return LS_OK;
}


ls_loopbuf_t *ls_loopbuf_xnew(int size, ls_xpool_t *pool)
{
    ls_loopbuf_t *pThis;
    if (pool == NULL)
        return NULL;

    pThis = (ls_loopbuf_t *)ls_xpool_alloc(pool, sizeof(ls_loopbuf_t));
    if (pThis == NULL)
        return NULL;
    if (!ls_loopbuf_x(pThis, size, pool))
    {
        ls_xpool_free(pool, pThis);
        return NULL;
    }
    return pThis;
}


ls_loopbuf_t *ls_loopbuf_x(ls_loopbuf_t *pThis, int size, ls_xpool_t *pool)
{
    if (size == 0)
        size = LSR_LOOPBUFUNIT;
    memset(pThis, 0, sizeof(ls_loopbuf_t));
    ls_loopbuf_xreserve(pThis, size, pool);
    return pThis;
}


void ls_loopbuf_xd(ls_loopbuf_t *pThis, ls_xpool_t *pool)
{
    ls_loopbuf_deallocate(pThis, pool);
    pThis->pbuf = NULL;
    pThis->pbufend = NULL;
    pThis->phead = NULL;
    pThis->pend = NULL;
    pThis->sizemax = 0;
}


void ls_loopbuf_xdelete(ls_loopbuf_t *pThis, ls_xpool_t *pool)
{
    ls_loopbuf_xd(pThis, pool);
    ls_xpool_free(pool, pThis);
}


int ls_loopbuf_xreserve(ls_loopbuf_t *pThis, int size, ls_xpool_t *pool)
{
    return ls_loopbuf_allocate(pThis, pool, size);
}


int ls_loopbuf_xappend(ls_loopbuf_t *pThis, const char *pBuf, int size,
                       ls_xpool_t *pool)
{
    return ls_loopbuf_iAppend(pThis, pBuf, size, pool);
}


int ls_loopbuf_xguarantee(ls_loopbuf_t *pThis, int size, ls_xpool_t *pool)
{
    return ls_loopbuf_iGuarantee(pThis, size, pool);
}


void ls_loopbuf_xstraight(ls_loopbuf_t *pThis, ls_xpool_t *pool)
{
    ls_loopbuf_t bufTmp;
    memset(&bufTmp, 0, sizeof(ls_loopbuf_t));
    ls_loopbuf_xguarantee(&bufTmp, ls_loopbuf_size(pThis), pool);
    ls_loopbuf_used(&bufTmp, ls_loopbuf_size(pThis));
    ls_loopbuf_moveto(pThis, ls_loopbuf_begin(&bufTmp),
                      ls_loopbuf_size(pThis));
    ls_loopbuf_swap(pThis, &bufTmp);
    ls_loopbuf_xd(&bufTmp, pool);
}


ls_xloopbuf_t *ls_xloopbuf_new(int size, ls_xpool_t *pool)
{
    ls_xloopbuf_t *pThis;
    if (pool == NULL)
        return NULL;

    pThis = (ls_xloopbuf_t *)ls_xpool_alloc(pool, sizeof(ls_xloopbuf_t));
    if (pThis == NULL)
        return NULL;
    if (ls_xloopbuf(pThis, size, pool) == NULL)
    {
        ls_xpool_free(pool, pThis);
        return NULL;
    }
    return pThis;
}


ls_xloopbuf_t *ls_xloopbuf(ls_xloopbuf_t *pThis, int size,
                           ls_xpool_t *pool)
{
    if (size == 0)
        size = LSR_LOOPBUFUNIT;
    memset(&pThis->loopbuf, 0, sizeof(ls_loopbuf_t));
    pThis->pool = pool;
    ls_xloopbuf_reserve(pThis, size);
    return pThis;
}


void ls_xloopbuf_d(ls_xloopbuf_t *pThis)
{
    ls_loopbuf_t *pBuf = &pThis->loopbuf;
    pBuf->pbuf = NULL;
    pBuf->pbufend = NULL;
    pBuf->phead = NULL;
    pBuf->pend = NULL;
    pBuf->sizemax = 0;
    pThis->pool = NULL;
}


void ls_xloopbuf_delete(ls_xloopbuf_t *pThis)
{
    ls_xpool_t *pool = pThis->pool;
    ls_loopbuf_deallocate(&pThis->loopbuf, pool);
    ls_xpool_free(pool, pThis);
}


void ls_xloopbuf_swap(ls_xloopbuf_t *lhs, ls_xloopbuf_t *rhs)
{
    assert(rhs);
    char temp[sizeof(ls_xloopbuf_t) ];
    memmove(temp, lhs, sizeof(ls_xloopbuf_t));
    memmove(lhs, rhs, sizeof(ls_xloopbuf_t));
    memmove(rhs, temp, sizeof(ls_xloopbuf_t));
}


int ls_loopbuf_iAppend(ls_loopbuf_t *pThis, const char *pBuf, int size,
                       ls_xpool_t *pool)
{
    if ((pBuf == NULL) || (size < 0))
    {
        errno = EINVAL;
        return LS_FAIL;
    }
    if (size > 0)
    {
        if (ls_loopbuf_xguarantee(pThis, size, pool) != LS_OK)
            return LS_FAIL ;
        int len = ls_loopbuf_contiguous(pThis);
        if (len > size)
            len = size;

        memmove(pThis->pend, pBuf, len);
        pBuf += len ;
        len = size - len;

        if (len != 0)
            memmove(pThis->pbuf, pBuf, len);
        ls_loopbuf_used(pThis, size);
    }
    return size;
}


int ls_loopbuf_iGuarantee(ls_loopbuf_t *pThis, int size, ls_xpool_t *pool)
{
    int avail = ls_loopbuf_available(pThis);
    if (size <= avail)
        return LS_OK;
    return ls_loopbuf_xreserve(pThis, size + ls_loopbuf_size(pThis) + 1, pool);
}


