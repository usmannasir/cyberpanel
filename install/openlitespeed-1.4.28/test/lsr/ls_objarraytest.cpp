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

#include <lsr/ls_objarray.h>
#include <lsr/ls_xpool.h>

#include <stdio.h>
#include <string.h>
#include "unittest-cpp/UnitTest++.h"

typedef struct testpair_s
{
    int key;
    int val;
} testpair_t;


TEST(ls_ObjArrayTest_test)
{
    int i;
    ls_objarray_t array;
    ls_xpool_t *pool = ls_xpool_new();
    ls_objarray_init(&array, sizeof(testpair_t));

    CHECK(ls_objarray_getcapacity(&array) == 0);
    CHECK(ls_objarray_getsize(&array) == 0);
    CHECK(ls_objarray_getarray(&array) == NULL);
    ls_objarray_guarantee(&array, pool, 10);
    CHECK(ls_objarray_getcapacity(&array) == 10);
    CHECK(ls_objarray_getsize(&array) == 0);
    CHECK(ls_objarray_getarray(&array) != NULL);
    for (i = 0; i < 10; ++i)
    {
        testpair_t *buf = (testpair_t *)ls_objarray_getnew(&array);
        buf->key = buf->val = i + 1;
    }
    CHECK(ls_objarray_getsize(&array) == 10);
    CHECK(ls_objarray_getcapacity(&array) == 10);
    CHECK(ls_objarray_getnew(&array) == NULL);
    for (i = 0; i < 10; ++i)
    {
        testpair_t *buf = (testpair_t *)ls_objarray_getobj(&array, i);
        CHECK(buf->key == i + 1 && buf->val == i + 1);
    }
    CHECK(ls_objarray_getobj(&array, 0) == ls_objarray_getarray(&array));
    CHECK(ls_objarray_getobj(&array, -1) == NULL);
    CHECK(ls_objarray_getobj(&array, 11) == NULL);
    ls_objarray_guarantee(&array, pool, 20);
    CHECK(ls_objarray_getcapacity(&array) == 20);
    CHECK(ls_objarray_getsize(&array) == 10);
    CHECK(ls_objarray_getarray(&array) != NULL);
    CHECK(ls_objarray_getobj(&array, 15) == NULL);
    for (i = 10; i < 20; ++i)
    {
        testpair_t *buf = (testpair_t *)ls_objarray_getnew(&array);
        buf->key = buf->val = i + 1;
    }
    for (i = 0; i < 20; ++i)
    {
        testpair_t *buf = (testpair_t *)ls_objarray_getobj(&array, i);
        CHECK(buf->key == i + 1 && buf->val == i + 1);
    }
    ls_objarray_setcapacity(&array, pool, 30);
    CHECK(ls_objarray_getcapacity(&array) == 30);
    CHECK(ls_objarray_getsize(&array) == 20);
    CHECK(ls_objarray_getarray(&array) != NULL);
    for (i = 20; i < 30; ++i)
    {
        testpair_t *buf = (testpair_t *)ls_objarray_getnew(&array);
        buf->key = buf->val = i - 1;
    }
    for (i = 0; i < 20; ++i)
    {
        testpair_t *buf = (testpair_t *)ls_objarray_getobj(&array, i);
        CHECK(buf->key == i + 1 && buf->val == i + 1);
    }
    for (i = 20; i < 30; ++i)
    {
        testpair_t *buf = (testpair_t *)ls_objarray_getobj(&array, i);
        CHECK(buf->key == i - 1 && buf->val == i - 1);
    }

    ls_objarray_release(&array, pool);
    ls_xpool_delete(pool);

    ls_objarray_init(&array, sizeof(testpair_t));

    CHECK(ls_objarray_getcapacity(&array) == 0);
    CHECK(ls_objarray_getsize(&array) == 0);
    CHECK(ls_objarray_getarray(&array) == NULL);
    ls_objarray_guarantee(&array, NULL, 10);
    CHECK(ls_objarray_getcapacity(&array) == 10);
    CHECK(ls_objarray_getsize(&array) == 0);
    CHECK(ls_objarray_getarray(&array) != NULL);
    for (i = 0; i < 10; ++i)
    {
        testpair_t *buf = (testpair_t *)ls_objarray_getnew(&array);
        buf->key = buf->val = i + 1;
    }
    CHECK(ls_objarray_getsize(&array) == 10);
    CHECK(ls_objarray_getcapacity(&array) == 10);
    CHECK(ls_objarray_getnew(&array) == NULL);
    for (i = 0; i < 10; ++i)
    {
        testpair_t *buf = (testpair_t *)ls_objarray_getobj(&array, i);
        CHECK(buf->key == i + 1 && buf->val == i + 1);
    }
    CHECK(ls_objarray_getobj(&array, 0) == ls_objarray_getarray(&array));
    CHECK(ls_objarray_getobj(&array, -1) == NULL);
    CHECK(ls_objarray_getobj(&array, 11) == NULL);
    ls_objarray_guarantee(&array, NULL, 20);
    CHECK(ls_objarray_getcapacity(&array) == 20);
    CHECK(ls_objarray_getsize(&array) == 10);
    CHECK(ls_objarray_getarray(&array) != NULL);
    ls_objarray_release(&array, NULL);

}


TEST(ls_ObjArrayTest_test2)
{
    int i;
    ls_objarray_t array;
    ls_xpool_t *pool = ls_xpool_new();
    ls_objarray_init(&array, sizeof(testpair_t));

    CHECK(ls_objarray_getcapacity(&array) == 0);
    CHECK(ls_objarray_getsize(&array) == 0);
    CHECK(ls_objarray_getarray(&array) == NULL);
    ls_objarray_guarantee(&array, pool, 20);


    for (i = 0; i < 20; ++i)
    {
        testpair_t *buf = (testpair_t *)ls_objarray_getnew(&array);
        buf->key = buf->val = i + 1;
    }
    for (i = 0; i < 20; ++i)
    {
        testpair_t *buf = (testpair_t *)ls_objarray_getobj(&array, i);
        CHECK(buf->key == i + 1 && buf->val == i + 1);
    }
    ls_objarray_guarantee(&array, pool, 20);
    ls_objarray_guarantee(&array, pool, 40);
    ls_objarray_guarantee(&array, pool, 50);
    ls_objarray_guarantee(&array, pool, 80);
    ls_objarray_guarantee(&array, pool, 60);
    ls_objarray_guarantee(&array, pool, 40);
    ls_objarray_guarantee(&array, pool, 20);
    ls_objarray_guarantee(&array, pool, 24);

    for (i = 0; i < 20; ++i)
    {
        testpair_t *buf = (testpair_t *)ls_objarray_getobj(&array, i);
        CHECK(buf->key == i + 1 && buf->val == i + 1);
    }


    ls_objarray_release(&array, pool);
    CHECK(1);
}



#endif
