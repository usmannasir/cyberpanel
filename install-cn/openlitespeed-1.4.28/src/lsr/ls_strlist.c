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

#include <lsr/ls_strlist.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_str.h>
#include <lsr/ls_strtool.h>
#include <stdlib.h>
#include <string.h>


void ls_strlist_copy(ls_strlist_t *pThis, const ls_strlist_t *pRhs)
{
    ls_strlist(pThis, 0);
    ls_const_strlist_iter iter =
        (ls_const_strlist_iter)ls_strlist_begin((ls_strlist_t *)pRhs);
    for (; iter != ls_strlist_end((ls_strlist_t *)pRhs); ++iter)
    {
        ls_strlist_add(pThis,
                       ls_str_cstr(*iter), ls_str_len(*iter));
    }
}


ls_strlist_t *ls_strlist_new(size_t initSize)
{
    ls_strlist_t *pThis;
    if ((pThis = (ls_strlist_t *)
                 ls_palloc(sizeof(*pThis))) != NULL)
        ls_strlist(pThis, initSize);
    return pThis;
}


void ls_strlist_d(ls_strlist_t *pThis)
{
    ls_strlist_releaseobjs(pThis);
    ls_ptrlist_d(pThis);
}


void ls_strlist_delete(ls_strlist_t *pThis)
{
    ls_strlist_d(pThis);
    ls_pfree(pThis);
}


void ls_strlist_releaseobjs(ls_strlist_t *pThis)
{
    ls_strlist_iter iter = ls_strlist_begin(pThis);
    for (; iter < ls_strlist_end(pThis); ++iter)
    {
        if (*iter)
            ls_str_delete(*iter);
    }
    ls_ptrlist_clear(pThis);
}


const ls_str_t *ls_strlist_add(
    ls_strlist_t *pThis, const char *pStr, int len)
{
    ls_str_t *pTemp = ls_str_new(pStr, len);
    if (pTemp == NULL)
        return NULL;
    ls_strlist_pushback(pThis, pTemp);
    return pTemp;
}


void ls_strlist_remove(ls_strlist_t *pThis, const char *pStr)
{
    ls_strlist_iter iter = ls_strlist_begin(pThis);
    for (; iter != ls_strlist_end(pThis); ++iter)
    {
        if (strcmp(ls_str_cstr(*iter), pStr) == 0)
        {
            ls_str_delete(*iter);
            ls_strlist_erase(pThis, iter);
            break;
        }
    }
}


void ls_strlist_clear(ls_strlist_t *pThis)
{
    ls_strlist_releaseobjs(pThis);
}


static int compare(const void *val1, const void *val2)
{
    return strcmp(ls_str_cstr(*(const ls_str_t **)val1),
                  ls_str_cstr(*(const ls_str_t **)val2));
}


void ls_strlist_sort(ls_strlist_t *pThis)
{
    qsort(ls_strlist_begin(pThis),
          ls_strlist_size(pThis), sizeof(ls_str_t *), compare);
}


void ls_strlist_insert(ls_strlist_t *pThis, ls_str_t *pDir)
{
    ls_strlist_pushback(pThis, pDir);
    ls_strlist_sort(pThis);
}


const ls_str_t *ls_strlist_find(const ls_strlist_t *pThis,
                                const char *pStr)
{
    if (pStr != NULL)
    {
        ls_const_strlist_iter iter =
            (ls_const_strlist_iter)ls_strlist_begin((ls_strlist_t *)pThis);
        for (; iter != ls_strlist_end((ls_strlist_t *)pThis); ++iter)
        {
            if (strcmp(ls_str_cstr(*iter), pStr) == 0)
                return *iter;
        }
    }
    return NULL;
}


ls_const_strlist_iter ls_strlist_lowerbound(
    const ls_strlist_t *pThis, const char *pStr)
{
    if (pStr == NULL)
        return NULL;
    ls_const_strlist_iter e =
        (ls_const_strlist_iter)ls_strlist_end((ls_strlist_t *)pThis);
    ls_const_strlist_iter b =
        (ls_const_strlist_iter)ls_strlist_begin((ls_strlist_t *)pThis);
    while (b < e)
    {
        ls_const_strlist_iter m = b + (e - b) / 2;
        int c = strcmp(pStr, ls_str_cstr(*m));
        if (c == 0)
            return m;
        else if (c < 0)
            e = m;
        else
            b = m + 1;
    }
    return b;
}


ls_str_t *ls_strlist_bfind(const ls_strlist_t *pThis, const char *pStr)
{
    ls_const_strlist_iter p = ls_strlist_lowerbound((ls_strlist_t *)pThis,
                              pStr);
    if ((p != ls_strlist_end((ls_strlist_t *)pThis))
        && (strcmp(pStr, ls_str_cstr(*p)) == 0))
        return *p;
    return NULL;
}


int ls_strlist_split(
    ls_strlist_t *pThis, const char *pBegin, const char *pEnd,
    const char *delim)
{
    const char *p;
    ls_parse_t strparse;
    ls_parse(&strparse, pBegin, pEnd, delim);
    while (!ls_parse_isend(&strparse))
    {
        p = ls_parse_trimparse(&strparse);
        if (p == NULL)
            break;
        if (p != ls_parse_getstrend(&strparse))
        {
            if (ls_strlist_add(
                    pThis, p, ls_parse_getstrend(&strparse) - p) == NULL)
                break;
        }
    }
    return ls_strlist_size(pThis);
}

