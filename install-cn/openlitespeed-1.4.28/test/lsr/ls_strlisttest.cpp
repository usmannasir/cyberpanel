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
#ifdef RUN_TEST

#include <lsr/ls_str.h>
#include <lsr/ls_strlist.h>
#include "unittest-cpp/UnitTest++.h"

#include <stdio.h>
#include <string.h>

/*
 * note the difference between
 * ls_strlist_{push,pop,insert,erase} and ls_strlist_{add,remove,clear,_d}.
 * {push,pop,...} expect user allocated (constructed) ls_str_t objects.
 * {add,remove,...} allocate ls_str_t objects given char *s,
 * and deallocate the objects when called to. do *NOT* mix these mechanisms.
 *
 */
TEST(ls_strlisttest_test)
{
    int size;
    unsigned int capacity;
    ls_strlist_t *pglist1;
    ls_strlist_t glist3;
    ls_str_t *pautostr1;
    ls_str_t autostr3;
    ls_str_t *pstr;
    static const char *myptrs[] = { "ptr333", "ptr22", "ptr4444", "ptr1" };
    char mybuf[256];
    char *p;
    int ret;
    int left;

    pautostr1 = ls_str_new("mystr1", 6);
    CHECK(pautostr1 != NULL);
    ls_str(&autostr3, "mystr2", 6);

    capacity = 15;
    pglist1 = ls_strlist_new(0);
    CHECK(pglist1 != NULL);
    CHECK(ls_strlist_capacity(pglist1) == 0);
    ls_strlist_reserve(pglist1, capacity);
    ls_strlist_pushback(pglist1, pautostr1);
    ls_strlist_pushback(pglist1, &autostr3);
    CHECK(ls_strlist_capacity(pglist1) == capacity);
    CHECK(ls_strlist_size(pglist1) == 2);
    ls_strlist_popfront(pglist1, &pstr, 1);
    CHECK(pstr == pautostr1);
    ls_strlist_unsafepopbackn(pglist1, &pstr, 1);
    CHECK(pstr == &autostr3);
    CHECK(ls_strlist_size(pglist1) == 0);

    for (size = 0; size < (int)(sizeof(myptrs) / sizeof(myptrs[0])); ++size)
        ls_strlist_add(pglist1, myptrs[size], strlen(myptrs[size]));
    CHECK(ls_strlist_capacity(pglist1) == capacity);
    CHECK(ls_strlist_size(pglist1) == size);
    ls_strlist_copy(&glist3, (const ls_strlist_t *)pglist1);
    CHECK(ls_strlist_size(&glist3) == size);
    CHECK(ls_strlist_capacity(&glist3) >= (unsigned)size);
    ls_strlist_clear(pglist1);
    CHECK(ls_strlist_capacity(pglist1) == capacity);
    CHECK(ls_strlist_size(pglist1) == 0);

    ls_strlist_pushback(&glist3, pautostr1);
    ++size;
    CHECK(ls_strlist_capacity(&glist3) >= (unsigned)size);
    CHECK(ls_strlist_popback(&glist3) == pautostr1);
    --size;
    CHECK(ls_strlist_size(&glist3) == size);
    CHECK(sizeof(myptrs) / sizeof(myptrs[0]) == size);

    ls_strlist_sort(&glist3);
    pstr = ls_strlist_bfind(&glist3, myptrs[0]);
    CHECK(pstr != NULL);
    CHECK(pstr == ls_strlist_find(&glist3, myptrs[0]));
    if (pstr)
    {
        CHECK(strncmp(ls_str_cstr((const ls_str_t *)pstr), myptrs[0],
                      ls_str_len((const ls_str_t *)pstr)) == 0);
    }
    ls_strlist_remove(&glist3, myptrs[0]);
    --size;
    CHECK(ls_strlist_size(&glist3) == size);
    CHECK(ls_strlist_find(&glist3, myptrs[0]) == NULL);

    p = mybuf;
    left = sizeof(mybuf);
    for (size = 0; size < (int)(sizeof(myptrs) / sizeof(myptrs[0])); ++size)
    {
        ret = snprintf(p, left, "%s, ", myptrs[size]);
        p += ret;
        left -= ret;
    }
    CHECK(ls_strlist_split(pglist1, (const char *)mybuf, (const char *)p, ",")
          == sizeof(myptrs) / sizeof(myptrs[0]));
    while (size > 0)
    {
        CHECK(ls_strlist_size(pglist1) == size);
        --size;
        CHECK(ls_strlist_find(pglist1, myptrs[size]) != NULL);
        ls_strlist_remove(pglist1, myptrs[size]);
        CHECK(ls_strlist_find(pglist1, myptrs[size]) == NULL);
    }

    ls_str_d(&autostr3);
    ls_str_delete(pautostr1);
    ls_strlist_d(&glist3);
    ls_strlist_delete(pglist1);
}

#endif
