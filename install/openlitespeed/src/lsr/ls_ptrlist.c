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
#include <lsr/ls_ptrlist.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_swap.h>

#include <errno.h>
#include <string.h>
#include <stdlib.h>

#include <assert.h>

ls_ptrlist_t *ls_ptrlist_new(size_t initSize)
{
    ls_ptrlist_t *pThis;
    if ((pThis = (ls_ptrlist_t *)
                 ls_palloc(sizeof(*pThis))) != NULL)
        ls_ptrlist(pThis, initSize);
    return pThis;
}


void ls_ptrlist(ls_ptrlist_t *pThis, size_t initSize)
{
    if (initSize <= 0)
    {
        memset(pThis, 0, sizeof(ls_ptrlist_t));
        return;
    }
    if (initSize < 8)
        initSize = 8;
    pThis->pend = pThis->pstore = (void **)
                                  ls_palloc(initSize * sizeof(void *));
    pThis->pstoreend =
        (pThis->pstore != NULL) ? pThis->pstore + initSize : NULL;
}


void ls_ptrlist_copy(ls_ptrlist_t *pThis, const ls_ptrlist_t *pRhs)
{
    assert(pRhs);
    pThis->pstore = (void **)
                    ls_palloc(ls_ptrlist_size(pRhs) * sizeof(void *));
    if (pThis->pstore != NULL)
    {
        pThis->pend = pThis->pstoreend =
                          pThis->pstore + ls_ptrlist_size(pRhs);
        memmove(pThis->pstore, pRhs->pstore,
                (const char *)pRhs->pend - (const char *)pRhs->pstore);
    }
}


void ls_ptrlist_d(ls_ptrlist_t *pThis)
{
    if (pThis->pstore != NULL)
        ls_pfree(pThis->pstore);
}


void ls_ptrlist_delete(ls_ptrlist_t *pThis)
{
    ls_ptrlist_d(pThis);
    ls_pfree(pThis);
}


static int ls_ptrlist_allocate(ls_ptrlist_t *pThis, int capacity)
{
    void **pStore = (void **)ls_prealloc(pThis->pstore,
                                         capacity * sizeof(void *));
    if (pStore == NULL)
        return LS_FAIL;
    pThis->pend = pStore + (pThis->pend - pThis->pstore);
    pThis->pstore = pStore;
    pThis->pstoreend = pThis->pstore + capacity;
    return LS_OK;
}


int ls_ptrlist_reserve(ls_ptrlist_t *pThis, size_t sz)
{
    return ls_ptrlist_allocate(pThis, sz);
}


int ls_ptrlist_grow(ls_ptrlist_t *pThis, size_t sz)
{
    return ls_ptrlist_allocate(pThis, sz + ls_ptrlist_capacity(pThis));
}


int ls_ptrlist_resize(ls_ptrlist_t *pThis, size_t sz)
{
    if (ls_ptrlist_capacity(pThis) < sz)
        if (ls_ptrlist_allocate(pThis, sz))
            return LS_FAIL;
    pThis->pend = pThis->pstore + sz;
    return LS_OK;
}


int ls_ptrlist_pushback(ls_ptrlist_t *pThis, void *pPointer)
{
    if (pThis->pend == pThis->pstoreend)
    {
        int n = ls_ptrlist_capacity(pThis) * 2;
        if (n < 16)
            n = 16;
        if (ls_ptrlist_allocate(pThis, n) != LS_OK)
            return LS_FAIL;
    }
    *pThis->pend++ = pPointer;
    return LS_OK;
}


int ls_ptrlist_pushback2(ls_ptrlist_t *pThis, const ls_ptrlist_t *plist)
{
    assert(plist);
    if (pThis->pend + ls_ptrlist_size(plist) > pThis->pstoreend)
    {
        int n = ls_ptrlist_capacity(pThis) + ls_ptrlist_size(plist);
        if (ls_ptrlist_allocate(pThis, n) != LS_OK)
            return LS_FAIL;
    }
    ls_const_ptrlist_iter iter;
    for (iter = ls_ptrlist_begin((ls_ptrlist_t *)plist);
         iter != ls_ptrlist_end((ls_ptrlist_t *)plist); ++iter)
        ls_ptrlist_unsafepushback(pThis, *iter);
    return LS_OK;
}


void ls_ptrlist_unsafepushbackn(ls_ptrlist_t *pThis, void **pPointer,
                                int n)
{
    assert(n > 0);
    assert(pThis->pend + n <= pThis->pstoreend);
    memmove(pThis->pend, pPointer, n * sizeof(void *));
    pThis->pend += n;
}


void ls_ptrlist_unsafepopbackn(ls_ptrlist_t *pThis, void **pPointer, int n)
{
    assert(n > 0);
    assert(pThis->pend - n >= pThis->pstore);
    pThis->pend -= n;
    memmove(pPointer, pThis->pend, n * sizeof(void *));
}


int ls_ptrlist_foreach(
    ls_ptrlist_iter beg, ls_ptrlist_iter end, gpl_for_each_fn fn)
{
    int n = 0;
    ls_ptrlist_iter iterNext = beg;
    ls_ptrlist_iter iter;
    while ((iterNext != NULL) && (iterNext != end))
    {
        iter = iterNext;
        iterNext = iter + 1;
        if (fn(*iter) != LS_OK)
            break;
        ++n;
    }
    return n;
}


ls_const_ptrlist_iter ls_ptrlist_lowerbound(
    const ls_ptrlist_t *pThis,
    const void *pKey, int (*compare)(const void *, const void *))
{
    if (pKey == NULL)
        return ls_ptrlist_end((ls_ptrlist_t *)pThis);
    ls_const_ptrlist_iter e = ls_ptrlist_end((ls_ptrlist_t *)pThis);
    ls_const_ptrlist_iter b = ls_ptrlist_begin((ls_ptrlist_t *)pThis);
    while (b != e)
    {
        ls_const_ptrlist_iter m = b + (e - b) / 2;
        int c = compare(pKey, *m);
        if (c == 0)
            return m;
        else if (c < 0)
            e = m;
        else
            b = m + 1;
    }
    return b;
}


ls_const_ptrlist_iter ls_ptrlist_bfind(
    const ls_ptrlist_t *pThis,
    const void *pKey, int (*compare)(const void *, const void *))
{
    ls_const_ptrlist_iter b = ls_ptrlist_begin((ls_ptrlist_t *)pThis);
    ls_const_ptrlist_iter e = ls_ptrlist_end((ls_ptrlist_t *)pThis);
    while (b != e)
    {
        ls_const_ptrlist_iter m = b + (e - b) / 2;
        int c = compare(pKey, *m);
        if (c == 0)
            return m;
        else if (c < 0)
            e = m;
        else
            b = m + 1;
    }
    return ls_ptrlist_end((ls_ptrlist_t *)pThis);
}


void ls_ptrlist_swap(
    ls_ptrlist_t *pThis, ls_ptrlist_t *pRhs)
{
    void **t;
    assert(pRhs);
    GSWAP(pThis->pstore, pRhs->pstore, t);
    GSWAP(pThis->pstoreend, pRhs->pstoreend, t);
    GSWAP(pThis->pend, pRhs->pend, t);

}


void ls_ptrlist_sort(
    ls_ptrlist_t *pThis, int (*compare)(const void *, const void *))
{
    qsort(ls_ptrlist_begin(pThis),
          ls_ptrlist_size(pThis), sizeof(void **), compare);
}

