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

#include <lsr/ls_objarray.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_xpool.h>


static void *ls_objarray_alloc(ls_objarray_t *pThis, ls_xpool_t *pool,
                               int numObj)
{
    return ((pool != NULL) ?
            ls_xpool_realloc(pool,
                             ls_objarray_getarray(pThis), numObj * ls_objarray_getobjsize(pThis)) :
            ls_prealloc(
                ls_objarray_getarray(pThis), numObj * ls_objarray_getobjsize(pThis)));
}

static void ls_objarray_releasearray(ls_objarray_t *pThis,
                                     ls_xpool_t *pool)
{
    if (pool != NULL)
        ls_xpool_free(pool, ls_objarray_getarray(pThis));
    else
        ls_pfree(ls_objarray_getarray(pThis));
}

void ls_objarray_release(ls_objarray_t *pThis, ls_xpool_t *pool)
{
    if (pThis->parray != NULL)
        ls_objarray_releasearray(pThis, pool);
    pThis->sizemax = 0;
    pThis->sizenow = 0;
    pThis->objsize = 0;
    pThis->parray = NULL;
}

void ls_objarray_setcapacity(ls_objarray_t *pThis, ls_xpool_t *pool,
                             int numObj)
{
    if (pThis->sizemax < numObj)
        pThis->parray = ls_objarray_alloc(pThis, pool, numObj);
    pThis->sizemax = numObj;
}





