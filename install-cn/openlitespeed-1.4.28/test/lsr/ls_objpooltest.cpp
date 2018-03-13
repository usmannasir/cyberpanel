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


#include <lsr/ls_objpool.h>
#include <lsr/ls_pool.h>

#include <stdio.h>
#include <string.h>
#include "unittest-cpp/UnitTest++.h"


typedef struct ls_objpooltest_s
{
    int key;
    int val;
} ls_objpooltest_t;

void *getNew()
{
    return ls_palloc(sizeof(ls_objpooltest_t));
}

void releaseObj(void *pObj)
{
    ls_pfree(pObj);
}

TEST(ls_objpooltest)
{
    printf("START LSR OBJPOOL TEST\n");
    ls_objpool_t op;
    const int chunk = 10;
    int i;
    ls_objpooltest_t *pObjs[chunk] = { NULL };
    ls_objpool(&op, chunk, getNew, releaseObj);
    CHECK(ls_objpool_size(&op) == 0);
    CHECK(ls_objpool_capacity(&op) == 0);
    CHECK(ls_objpool_poolsize(&op) == 0);
    CHECK(ls_objpool_begin(&op) == ls_objpool_end(&op));

    for (i = 0; i < chunk; ++i)
    {
        pObjs[i] = (ls_objpooltest_t *)ls_objpool_get(&op);
        CHECK(pObjs[i] != NULL);
        CHECK(ls_objpool_size(&op) == chunk - i - 1);
        CHECK(ls_objpool_capacity(&op) == chunk);
        CHECK(ls_objpool_poolsize(&op) == chunk);
    }
    CHECK(ls_objpool_begin(&op) == ls_objpool_end(&op));
    ls_objpooltest_t *p = (ls_objpooltest_t *)ls_objpool_get(&op);
    CHECK(p != NULL);
    CHECK(ls_objpool_size(&op) == chunk - 1);
    CHECK(ls_objpool_capacity(&op) == chunk * 2);
    CHECK(ls_objpool_poolsize(&op) == chunk * 2);
    CHECK(ls_objpool_begin(&op) != ls_objpool_end(&op));

    ls_objpooltest_t *pObjs2[chunk] = { NULL };
    ls_objpool_getmulti(&op, (void **)pObjs2, chunk);
    CHECK(ls_objpool_size(&op) == chunk - 1);
    CHECK(ls_objpool_capacity(&op) == chunk * 3);
    CHECK(ls_objpool_poolsize(&op) == chunk * 3);

    for (i = 0; i < chunk; ++i)
    {
        CHECK(pObjs2[i] != NULL);
        /* For the sake of reducing repetition, I put the following
        * checks in the same for loop.  These are separate tests
        * by nature, but I didn't want to have back to back for loops.
        */
        ls_objpool_recycle(&op, pObjs[i]);
        CHECK(ls_objpool_size(&op) == chunk + i);
        CHECK(ls_objpool_capacity(&op) == chunk * 3);
        CHECK(ls_objpool_poolsize(&op) == chunk * 3);
    }
    ls_objpool_recycle(&op, p);
    ls_objpool_shrinkto(&op, chunk);
    CHECK(ls_objpool_size(&op) == chunk);
    CHECK(ls_objpool_capacity(&op) == chunk * 3);
    CHECK(ls_objpool_poolsize(&op) == chunk * 2);
    CHECK(ls_objpool_begin(&op) + chunk == ls_objpool_end(&op));

    ls_objpool_recyclemulti(&op, (void **)pObjs2, chunk);
    CHECK(ls_objpool_size(&op) == chunk * 2);
    CHECK(ls_objpool_capacity(&op) == chunk * 3);
    CHECK(ls_objpool_poolsize(&op) == chunk * 2);
    CHECK(ls_objpool_begin(&op) + (2 * chunk) == ls_objpool_end(&op));

    ls_objpool_getmulti(&op, (void **)pObjs, chunk);
    CHECK(ls_objpool_size(&op) == chunk);
    CHECK(ls_objpool_capacity(&op) == chunk * 3);
    CHECK(ls_objpool_poolsize(&op) == chunk * 2);

    ls_objpool_getmulti(&op, (void **)pObjs2, chunk);
    CHECK(ls_objpool_size(&op) == 0);
    CHECK(ls_objpool_capacity(&op) == chunk * 3);
    CHECK(ls_objpool_poolsize(&op) == chunk * 2);

    p = (ls_objpooltest_t *)ls_objpool_get(&op);
    CHECK(ls_objpool_size(&op) == chunk - 1);
    CHECK(ls_objpool_capacity(&op) == chunk * 3);
    CHECK(ls_objpool_poolsize(&op) == chunk * 3);

    ls_objpool_recycle(&op, p);
    ls_objpool_recyclemulti(&op, (void **)pObjs, chunk);
    ls_objpool_recyclemulti(&op, (void **)pObjs2, chunk);
    CHECK(ls_objpool_size(&op) == chunk * 3);
    CHECK(ls_objpool_capacity(&op) == chunk * 3);
    CHECK(ls_objpool_poolsize(&op) == chunk * 3);



    ls_objpool_d(&op);
}

#endif
