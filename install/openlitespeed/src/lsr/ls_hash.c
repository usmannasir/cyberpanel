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
#include <lsr/ls_hash.h>
#include "ls_internal.h"
#include <lsr/ls_pool.h>
#include <lsr/ls_xpool.h>

#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <lsdef.h>

enum {    prime_count = 31    };
static const size_t s_prime_list[prime_count] =
{
    7ul,          13ul,         29ul,
    53ul,         97ul,         193ul,       389ul,       769ul,
    1543ul,       3079ul,       6151ul,      12289ul,     24593ul,
    49157ul,      98317ul,      196613ul,    393241ul,    786433ul,
    1572869ul,    3145739ul,    6291469ul,   12582917ul,  25165843ul,
    50331653ul,   100663319ul,  201326611ul, 402653189ul, 805306457ul,
    1610612741ul, 3221225473ul, 4294967291ul
};

static ls_hash_iter ls_hash_find_num(ls_hash_t *pThis, const void *pKey);
static ls_hash_iter ls_hash_insert_num(ls_hash_t *pThis, const void *pKey,
                                       void *pValue);
static ls_hash_iter ls_hash_update_num(ls_hash_t *pThis, const void *pKey,
                                       void *pValue);
static ls_hash_iter ls_hash_insert_p(ls_hash_t *pThis, const void *pKey,
                                     void *pValue);
static ls_hash_iter ls_hash_update_p(ls_hash_t *pThis, const void *pKey,
                                     void *pValue);
static ls_hash_iter ls_hash_find_p(ls_hash_t *pThis, const void *pKey);


ls_inline void *ls_hash_do_alloc(ls_xpool_t *pool, size_t size)
{
    return ((pool != NULL) ? ls_xpool_alloc(pool, size) : ls_palloc(size));
}


ls_inline void ls_hash_do_free(ls_xpool_t *pool, void *ptr)
{
    if (pool != NULL)
        ls_xpool_free(pool, ptr);
    else
        ls_pfree(ptr);
    return;
}


static int find_range(size_t sz)
{
    int i = 1;
    for (; i < prime_count - 1; ++i)
    {
        if (sz <= s_prime_list[i])
            break;
    }
    return i;
}


static size_t round_up(size_t sz)
{
    return s_prime_list[find_range(sz)];
}


ls_hash_t *ls_hash_new(
    size_t init_size, ls_hash_hasher hf, ls_hash_value_compare vc,
    ls_xpool_t *pool)
{
    ls_hash_t *hash;
    if ((hash = (ls_hash_t *)ls_hash_do_alloc(pool,
                sizeof(ls_hash_t))) != NULL)
    {
        if (ls_hash(hash, init_size, hf, vc, pool) == 0)
        {
            ls_hash_do_free(pool, (void *)hash);
            return NULL;
        }
    }
    return hash;
}


ls_hash_t *ls_hash(ls_hash_t *hash,
                   size_t init_size, ls_hash_hasher hf, ls_hash_value_compare vc,
                   ls_xpool_t *pool)
{
    hash->sizemax = 0;
    hash->sizenow = 0;
    hash->load_factor = 2;
    hash->hf_fn = hf;
    hash->vc_fn = vc;
    hash->grow_factor = 2;
    hash->xpool = pool;

    if (hash->hf_fn != NULL)
    {
        assert(hash->vc_fn);
        hash->insert_fn = ls_hash_insert_p;
        hash->update_fn = ls_hash_update_p;
        hash->find_fn = ls_hash_find_p;
    }
    else
    {
        hash->insert_fn = ls_hash_insert_num;
        hash->update_fn = ls_hash_update_num;
        hash->find_fn = ls_hash_find_num;
    }

    init_size = round_up(init_size);
    hash->htable = (ls_hashelem_t **)
                   ls_hash_do_alloc(pool, init_size * sizeof(ls_hashelem_t *));
    if (hash->htable == NULL)
        return NULL;
    memset(hash->htable, 0, init_size * sizeof(ls_hashelem_t *));
    hash->sizemax = init_size;
    hash->htable_end = hash->htable + init_size;

    return hash;
}


void ls_hash_d(ls_hash_t *pThis)
{
    ls_hash_clear(pThis);
    if (pThis->htable != NULL)
    {
        ls_hash_do_free(pThis->xpool, (void *)pThis->htable);
        pThis->htable = NULL;
    }
}


void ls_hash_delete(ls_hash_t *pThis)
{
    ls_hash_d(pThis);
    ls_hash_do_free(pThis->xpool, (void *)pThis);
}


ls_hash_key_t ls_hash_hfstring(const void *__s)
{
    return XXH32((const char *)__s, strlen((const char *)__s), 0);
}


int ls_hash_cmpstring(const void *pVal1, const void *pVal2)
{   return strcmp((const char *)pVal1, (const char *)pVal2);  }

ls_hash_key_t ls_hash_hfcistring(const void *__s)
{
    ls_hash_key_t __h = 0;
    const char *p = (const char *)__s;
    char ch = *(const char *)p++;
    for (; ch ; ch = *((const char *)p++))
    {
        if (ch >= 'A' && ch <= 'Z')
            ch += 'a' - 'A';
        __h = __h * 31 + (ch);
    }
    return __h;
}


int ls_hash_cmpcistring(const void *pVal1, const void *pVal2)
{
    return strncasecmp(
               (const char *)pVal1, (const char *)pVal2, strlen((const char *)pVal1));
}


ls_hash_key_t ls_hash_hfipv6(const void *pKey)
{
    ls_hash_key_t key;
    if (sizeof(ls_hash_key_t) == 4)
    {
        key = *((const ls_hash_key_t *)pKey) +
              *(((const ls_hash_key_t *)pKey) + 1) +
              *(((const ls_hash_key_t *)pKey) + 2) +
              *(((const ls_hash_key_t *)pKey) + 3);
    }
    else
    {
        key = *((const ls_hash_key_t *)pKey) +
              *(((const ls_hash_key_t *)pKey) + 1);
    }
    return key;
}


int  ls_hash_cmpipv6(const void *pVal1, const void *pVal2)
{
    return memcmp(pVal1, pVal2, 16);
}


const void *ls_hash_getkey(ls_hashelem_t *pElem)
{
    return pElem->pkey;
}


void *ls_hash_getdata(ls_hashelem_t *pElem)
{
    return pElem->pdata;
}


ls_hash_key_t ls_hash_gethkey(ls_hashelem_t *pElem)
{
    return pElem->hkey;
}


ls_hashelem_t *ls_hash_getnext(ls_hashelem_t *pElem)
{
    return pElem->next;
}


void ls_hash_setdata(ls_hashelem_t *pElem, void *p)
{
    pElem->pdata = p;
}


ls_hash_iter ls_hash_begin(ls_hash_t *pThis)
{
    if (pThis->sizenow == 0)
        return ls_hash_end(pThis);
    ls_hashelem_t **p = pThis->htable;
    while (p < pThis->htable_end)
    {
        if (*p != NULL)
            return *p;
        ++p;
    }
    return NULL;
}


void ls_hash_swap(ls_hash_t *lhs, ls_hash_t *rhs)
{
    char temp[sizeof(ls_hash_t)];
    assert(lhs != NULL && rhs != NULL);
    memmove(temp, lhs, sizeof(ls_hash_t));
    memmove(lhs, rhs, sizeof(ls_hash_t));
    memmove(rhs, temp, sizeof(ls_hash_t));
}


#define ls_hash_getindex( k, n ) (k) % (n)

ls_hash_iter ls_hash_next(ls_hash_t *pThis, ls_hash_iter iter)
{
    if (iter == NULL)
        return ls_hash_end(pThis);
    if (iter->next != NULL)
        return iter->next;
    ls_hashelem_t **p =
        pThis->htable + ls_hash_getindex(iter->hkey, pThis->sizemax) + 1;
    while (p < pThis->htable_end)
    {
        if (*p != NULL)
            return *p;
        ++p;
    }
    return ls_hash_end(pThis);
}


int ls_hash_foreach(ls_hash_t *pThis,
                    ls_hash_iter beg, ls_hash_iter end, ls_hash_foreach_fn fun)
{
    if (fun == NULL)
    {
        errno = EINVAL;
        return LS_FAIL;
    }
    if (beg == NULL)
        return 0;
    int n = 0;
    ls_hash_iter iterNext = beg;
    ls_hash_iter iter;
    while ((iterNext != NULL) && (iterNext != end))
    {
        iter = iterNext;
        iterNext = ls_hash_next(pThis, iterNext);
        if (fun(iter->pkey, iter->pdata) != 0)
            break;
        ++n;
    }
    return n;
}


int ls_hash_foreach2(ls_hash_t *pThis,
                     ls_hash_iter beg, ls_hash_iter end, ls_hash_foreach2_fn fun, void *pUData)
{
    if (fun == NULL)
    {
        errno = EINVAL;
        return LS_FAIL;
    }
    if (beg  == NULL)
        return 0;
    int n = 0;
    ls_hash_iter iterNext = beg;
    ls_hash_iter iter ;
    while ((iterNext != NULL) && (iterNext != end))
    {
        iter = iterNext;
        iterNext = ls_hash_next(pThis, iterNext);
        if (fun(iter->pkey, iter->pdata, pUData) != 0)
            break;
        ++n;
    }
    return n;
}


static void ls_hash_rehash(ls_hash_t *pThis)
{
    int range = find_range(pThis->sizemax);
    int newSize = s_prime_list[range + pThis->grow_factor];
    ls_hashelem_t **newTable;
    newTable = (ls_hashelem_t **)
               ls_hash_do_alloc(pThis->xpool, newSize * sizeof(ls_hashelem_t *));
    if (newTable == NULL)
        return;
    memset(newTable, 0, sizeof(ls_hashelem_t *) * newSize);
    ls_hash_iter iterNext = ls_hash_begin(pThis);

    while (iterNext != ls_hash_end(pThis))
    {
        ls_hash_iter iter = iterNext;
        iterNext = ls_hash_next(pThis, iter);
        ls_hashelem_t **pElem =
            newTable + ls_hash_getindex(iter->hkey, newSize);
        iter->next = *pElem;
        *pElem = iter;
    }
    ls_hash_do_free(pThis->xpool, (void *)pThis->htable);
    pThis->htable = newTable;
    pThis->sizemax = newSize;
    pThis->htable_end = pThis->htable + newSize;
}


static int ls_hash_release_hash_elem(ls_hash_t *pThis, ls_hash_iter iter)
{
    ls_hash_do_free(pThis->xpool, (void *)iter);
    return 0;
}


void ls_hash_clear(ls_hash_t *pThis)
{
    ls_hash_iter end = ls_hash_end(pThis);
    ls_hash_iter iterNext = ls_hash_begin(pThis);
    ls_hash_iter iter;
    while ((iterNext != NULL) && (iterNext != end))
    {
        iter = iterNext;
        iterNext = ls_hash_next(pThis, iterNext);
        if (ls_hash_release_hash_elem(pThis, iter) != 0)
        {
            fprintf(stderr, "ls_hash_clear() error!\n");
            break;
        }
    }
    if (pThis->htable != NULL)
        memset(pThis->htable, 0, sizeof(ls_hashelem_t *) * pThis->sizemax);
    pThis->sizenow = 0;
}


void ls_hash_erase(ls_hash_t *pThis, ls_hash_iter iter)
{
    if (iter == NULL)
        return;
    size_t index = ls_hash_getindex(iter->hkey, pThis->sizemax);
    ls_hashelem_t *pElem = pThis->htable[index];
    if (pElem == iter)
        pThis->htable[index] = iter->next;
    else
    {
        if (pElem == NULL)
            return;
        while (1)
        {
            if (pElem->next == NULL)
                return;
            if (pElem->next == iter)
                break;
            pElem = pElem->next;
        }
        pElem->next = iter->next;
    }
    ls_hash_do_free(pThis->xpool, (void *)iter);
    --pThis->sizenow;
}


static ls_hash_iter ls_hash_find_num(ls_hash_t *pThis, const void *pKey)
{
    size_t index = ls_hash_getindex((ls_hash_key_t)pKey, pThis->sizemax);
    ls_hashelem_t *pElem = pThis->htable[index];
    while ((pElem != NULL) && (pKey != pElem->pkey))
        pElem = pElem->next;
    return pElem;
}


static ls_hash_iter ls_hash_find2(
    ls_hash_t *pThis, const void *pKey, ls_hash_key_t key)
{
    size_t index = ls_hash_getindex(key, pThis->sizemax);
    ls_hashelem_t *pElem = pThis->htable[index];
    while (pElem != NULL)
    {
        assert(pElem->pkey);
        if ((*pThis->vc_fn)(pKey, pElem->pkey) != 0)
            pElem = pElem->next;
        else
        {
            assert(!((pElem->hkey != key) && (pKey == pElem->pkey)));
            break;
        }
    }
    return pElem;
}


static ls_hash_iter ls_hash_insert2(
    ls_hash_t *pThis, const void *pKey, void *pValue, ls_hash_key_t key)
{
    if (pThis->sizenow * pThis->load_factor > pThis->sizemax)
        ls_hash_rehash(pThis);
    ls_hashelem_t *pNew;
    pNew = (ls_hashelem_t *)
           ls_hash_do_alloc(pThis->xpool, sizeof(ls_hashelem_t));
    if (pNew == NULL)
        return ls_hash_end(pThis);
    pNew->pkey = pKey;
    pNew->pdata = pValue;
    pNew->hkey = key;
    ls_hashelem_t **pElem =
        pThis->htable + ls_hash_getindex(key, pThis->sizemax);
    pNew->next = *pElem;
    *pElem = pNew;
    ++pThis->sizenow;
    return pNew;
}


static ls_hash_iter ls_hash_insert_num(
    ls_hash_t *pThis, const void *pKey, void *pValue)
{
    ls_hash_iter iter = ls_hash_find_num(pThis, pKey);
    if (iter != NULL)
        return ls_hash_end(pThis);
    return ls_hash_insert2(pThis, pKey, pValue, (ls_hash_key_t)pKey);
}


static ls_hash_iter ls_hash_update_num(
    ls_hash_t *pThis, const void *pKey, void *pValue)
{
    ls_hash_iter iter = ls_hash_find_num(pThis, pKey);
    if (iter != ls_hash_end(pThis))
    {
        iter->pdata = pValue;
        return iter;
    }
    return ls_hash_insert2(pThis, pKey, pValue, (ls_hash_key_t)pKey);
}


static ls_hash_iter ls_hash_insert_p(
    ls_hash_t *pThis, const void *pKey, void *pValue)
{
    ls_hash_key_t key = (*pThis->hf_fn)(pKey);
    ls_hash_iter iter = ls_hash_find2(pThis, pKey, key);
    if (iter != NULL)
        return ls_hash_end(pThis);
    return ls_hash_insert2(pThis, pKey, pValue, key);
}


static ls_hash_iter ls_hash_update_p(
    ls_hash_t *pThis, const void *pKey, void *pValue)
{
    ls_hash_key_t key = (*pThis->hf_fn)(pKey);
    ls_hash_iter iter = ls_hash_find2(pThis, pKey, key);
    if (iter != NULL)
    {
        iter->pkey = pKey;
        iter->pdata = pValue;
        return iter;
    }
    return ls_hash_insert2(pThis, pKey, pValue, key);
}


static ls_hash_iter ls_hash_find_p(ls_hash_t *pThis, const void *pKey)
{
    return ls_hash_find2(pThis, pKey, (*pThis->hf_fn)(pKey));
}



