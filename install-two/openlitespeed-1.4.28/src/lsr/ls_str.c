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

#include <lsr/ls_str.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_xpool.h>
#include <lsr/xxhash.h>

#include <ctype.h>

static ls_str_t *ls_iStr_new(const char *pStr, size_t len, ls_xpool_t *pool);
static ls_str_t *ls_iStr(ls_str_t *pThis, const char *pStr, size_t len,
                         ls_xpool_t *pool);
static void ls_iStr_d(ls_str_t *pThis, ls_xpool_t *pool);
static size_t ls_str_iSetStr(ls_str_t *pThis, const char *pStr, size_t len,
                          ls_xpool_t *pool);
static void ls_str_iAppend(ls_str_t *pThis, const char *pStr,
                           size_t len, ls_xpool_t *pool);


ls_inline void *ls_str_do_alloc(ls_xpool_t *pool, size_t size)
{
    return ((pool != NULL) ? ls_xpool_alloc(pool, size) : ls_palloc(size));
}


ls_inline void ls_str_do_free(ls_xpool_t *pool, void *ptr)
{
    if (pool != NULL)
        ls_xpool_free(pool, ptr);
    else
        ls_pfree(ptr);
    return;
}


ls_str_t *ls_str_new(const char *pStr, size_t len)
{
    return ls_iStr_new(pStr, len, NULL);
}


ls_str_t *ls_str(ls_str_t *pThis, const char *pStr, size_t len)
{
    return ls_iStr(pThis, pStr, len, NULL);
}


ls_str_t *ls_str_copy(ls_str_t *dest, const ls_str_t *src)
{
    assert(dest && src);
    return ls_str(dest, ls_str_cstr(src), ls_str_len(src));
}


void ls_str_d(ls_str_t *pThis)
{
    ls_iStr_d(pThis, NULL);
}


void ls_str_delete(ls_str_t *pThis)
{
    ls_str_d(pThis);
    ls_pfree(pThis);
}


char *ls_str_prealloc(ls_str_t *pThis, size_t size)
{
    char *p = (char *)ls_prealloc(pThis->ptr, size);
    if (p != NULL)
        pThis->ptr = p;
    return p;
}


size_t ls_str_dup(ls_str_t *pThis, const char *pStr, size_t len)
{
    return ls_str_iSetStr(pThis, pStr, len, NULL);
}


void ls_str_append(ls_str_t *pThis, const char *pStr, size_t len)
{
    ls_str_iAppend(pThis, pStr, len, NULL);
}


int ls_str_cmp(const void *pVal1, const void *pVal2)
{
    return strncmp(
               ((ls_str_t *)pVal1)->ptr,
               ((ls_str_t *)pVal2)->ptr,
               ((ls_str_t *)pVal1)->len
           );
}


int ls_str_bcmp(const void *a, const void *b)
{
    int rc = memcmp(((ls_str_t *)a)->ptr, ((ls_str_t *)b)->ptr,
                    ((ls_str_t *)a)->len <= ((ls_str_t *)b)->len 
                        ? ((ls_str_t *)a)->len : ((ls_str_t *)b)->len);
    if (rc)
        return rc;
    else
        return (((ls_str_t *)a)->len > ((ls_str_t *)b)->len) 
                 - (((ls_str_t *)b)->len > ((ls_str_t *)a)->len);
}


ls_hash_key_t ls_str_hf(const void *pKey)
{
    ls_hash_key_t __h = 0;
    const char *p = ((ls_str_t *)pKey)->ptr;
    char ch = *(const char *)p;
    int i = ((ls_str_t *)pKey)->len;
    for (; i > 0 ; --i)
    {
        ch = *((const char *)p++);
        __h = __h * 31 + (ch);
    }
    return __h;
}


ls_hash_key_t ls_str_xh32(const void *pKey)
{
    return XXH32(((ls_str_t *)pKey)->ptr, ((ls_str_t *)pKey)->len, 0);
}


int ls_str_cmpci(const void *pVal1, const void *pVal2)
{
    if (((ls_str_t *)pVal1)->len != ((ls_str_t *)pVal2)->len)
        return ((ls_str_t *)pVal1)->len - ((ls_str_t *)pVal2)->len;
    return strncasecmp(
               ((ls_str_t *)pVal1)->ptr,
               ((ls_str_t *)pVal2)->ptr,
               ((ls_str_t *)pVal1)->len
           );
}


ls_hash_key_t ls_str_hfci(const void *pKey)
{
    ls_hash_key_t __h = 0;
    const char *p = ((ls_str_t *)pKey)->ptr;
    char ch = *(const char *)p;
    int i = ((ls_str_t *)pKey)->len;
    for (; i > 0 ; --i)
    {
        ch = *((const char *)p++);
        __h = __h * 31 + toupper(ch);
    }

    return __h;
}


ls_str_t *ls_str_xnew(const char *pStr, size_t len, ls_xpool_t *pool)
{
    return ls_iStr_new(pStr, len, pool);
}


ls_str_t *ls_str_x(ls_str_t *pThis, const char *pStr, size_t len,
                   ls_xpool_t *pool)
{
    return ls_iStr(pThis, pStr, len, pool);
}


ls_str_t *ls_str_xcopy(ls_str_t *dest, const ls_str_t *src,
                       ls_xpool_t *pool)
{
    assert(dest && src);
    return ls_str_x(dest, ls_str_cstr(src), ls_str_len(src), pool);
}


void ls_str_xd(ls_str_t *pThis, ls_xpool_t *pool)
{
    ls_iStr_d(pThis, pool);
}


void ls_str_xdelete(ls_str_t *pThis, ls_xpool_t *pool)
{
    ls_str_xd(pThis, pool);
    ls_xpool_free(pool, pThis);
}


char *ls_str_xprealloc(ls_str_t *pThis, int size, ls_xpool_t *pool)
{
    char *p = (char *)ls_xpool_realloc(pool, pThis->ptr, size);
    if (p != NULL)
        pThis->ptr = p;
    return p;
}


size_t ls_str_xsetstr(ls_str_t *pThis, const char *pStr, size_t len,
                   ls_xpool_t *pool)
{
    return ls_str_iSetStr(pThis, pStr, len, pool);
}


void ls_str_xappend(ls_str_t *pThis, const char *pStr, size_t len,
                    ls_xpool_t *pool)
{
    ls_str_iAppend(pThis, pStr, len, pool);
}


ls_str_t *ls_iStr_new(const char *pStr, size_t len, ls_xpool_t *pool)
{
    ls_str_t *pThis;
    if ((pThis = (ls_str_t *)ls_str_do_alloc(pool, sizeof(ls_str_t))) != NULL)
    {
        if (ls_iStr(pThis, pStr, len, pool) == NULL)
        {
            ls_str_do_free(pool, pThis);
            return NULL;
        }
    }
    return pThis;
}


void ls_iStr_d(ls_str_t *pThis, ls_xpool_t *pool)
{
    if (pThis != NULL)
    {
        if (pThis->ptr != NULL)
            ls_str_do_free(pool, pThis->ptr);
        ls_str_blank(pThis);
    }
}


static char *ls_str_do_dupstr(const char *pStr, size_t len, ls_xpool_t *pool)
{
    char *p;
    if (pool != NULL)
    {
        if ((p = (char *)ls_xpool_alloc(pool, len + 1)) == NULL)
            return NULL;
    }
    else if ((p = ls_palloc(len + 1)) == NULL)
        return NULL;
    memmove(p, pStr, len);
    *(p + len) = '\0';
    return p;
}


ls_str_t *ls_iStr(ls_str_t *pThis, const char *pStr, size_t len,
                  ls_xpool_t *pool)
{
    if (pStr == NULL)
        ls_str_blank(pThis);
    else if ((pThis->ptr = ls_str_do_dupstr(pStr, len, pool)) == NULL)
        pThis = NULL;
    else
        pThis->len = len;
    return pThis;
}


size_t ls_str_iSetStr(ls_str_t *pThis, const char *pStr, size_t len,
                   ls_xpool_t *pool)
{
    assert(pThis);
    ls_str_do_free(pool, pThis->ptr);
    return ((ls_iStr(pThis, pStr, len, pool) == NULL) ? 0 : pThis->len);
}


void ls_str_iAppend(ls_str_t *pThis, const char *pStr, size_t len,
                    ls_xpool_t *pool)
{
    assert(pThis && pStr);
    char *p;
    if (pool != NULL)
        p = (char *)ls_xpool_realloc(pool, pThis->ptr, pThis->len + len + 1);
    else
        p = (char *)ls_prealloc(pThis->ptr, pThis->len + len + 1);
    if (p != NULL)
    {
        memmove(p + pThis->len, pStr, len);
        pThis->len += len;
        *(p + pThis->len) = 0;
        pThis->ptr = p;
    }
}

