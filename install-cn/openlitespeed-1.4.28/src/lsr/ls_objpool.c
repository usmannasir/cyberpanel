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
#include <lsr/ls_objpool.h>
#include <lsr/ls_pool.h>

int ls_objpool_alloc(ls_objpool_t *pThis, int size)
{
    void *pObj;
    if ((int)ls_ptrlist_capacity(&pThis->freelist) < pThis->poolsize + size)
    {
        if (ls_ptrlist_reserve(&pThis->freelist, pThis->poolsize + size) != LS_OK)
            return LS_FAIL;
    }
    int i = 0;
    for (; i < size; ++i)
    {
        if ((pObj = pThis->getnew_fn()) == NULL)
            return LS_FAIL;

        ls_ptrlist_unsafepushback(&pThis->freelist, pObj);
        ++pThis->poolsize;
    }
    return LS_OK;
}


ls_inline void ls_objpool_clear(ls_objpool_t *pThis)
{   ls_ptrlist_clear(&pThis->freelist);    }


void ls_objpool(ls_objpool_t *pThis,
                int chunkSize, ls_objpool_getnewfn getNewFn,
                ls_objpool_releaseobjfn releaseFn)
{
    pThis->chunksize = (chunkSize <= 0) ? 10 : chunkSize;
    pThis->poolsize = 0;
    pThis->getnew_fn = getNewFn;
    pThis->releaseobj_fn = releaseFn;
    ls_ptrlist(&pThis->freelist, 0);
}


void ls_objpool_d(ls_objpool_t *pThis)
{
    ls_objpool_shrinkto(pThis, 0);
    pThis->chunksize = pThis->poolsize = 0;
    ls_ptrlist_d(&pThis->freelist);
}


void *ls_objpool_get(ls_objpool_t *pThis)
{
    if (ls_ptrlist_empty(&pThis->freelist))
    {
        if (ls_objpool_alloc(pThis, pThis->chunksize) != LS_OK)
            return NULL;
    }
    return ls_ptrlist_popback(&pThis->freelist);
}


int ls_objpool_getmulti(ls_objpool_t *pThis, void **pObj, int n)
{
    if ((int)ls_ptrlist_size(&pThis->freelist) < n)
    {
        if (ls_objpool_alloc(
                pThis, (n < pThis->chunksize) ? pThis->chunksize : n) != LS_OK)
            return 0;
    }
    ls_ptrlist_unsafepopbackn(&pThis->freelist, pObj, n);
    return n;
}

