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


#include <util/objpool.h>
#include <lsr/ls_pool.h>

#include <stdio.h>
#include <string.h>
#include "unittest-cpp/UnitTest++.h"

class ObjPoolTest
{
public:
    int key;
    int val;
};

void stressTest(ObjPool<ObjPoolTest> &op, int chunk)
{
    int i;
    ObjPoolTest ***pManyArrays;
    pManyArrays = (ObjPoolTest ** *)ls_palloc(sizeof(ObjPoolTest **) * chunk);
    for (i = 0; i < chunk; ++i)
    {
        pManyArrays[i] = (ObjPoolTest **)ls_palloc(sizeof(ObjPoolTest *)
                         * chunk * 10);
        op.get(pManyArrays[i], chunk * 10);
    }

    for (i = 0; i < chunk / 2; ++i)
        op.recycle((void **)pManyArrays[i], chunk * 10);

    for (i = 0; i < chunk / 2; ++i)
        op.get(pManyArrays[i], chunk * 10);

    for (i = 0; i < chunk / 2; ++i)
        op.recycle((void **)pManyArrays[i], chunk * 10);


    op.shrinkTo(chunk);

    for (i = 0; i < chunk / 2; ++i)
        op.get(pManyArrays[i], chunk * 10);

    for (i = 0; i < chunk / 2; ++i)
        op.recycle((void **)pManyArrays[i], chunk * 10);

    op.shrinkTo(chunk);

    for (i = chunk / 2; i < chunk; ++i)
        op.recycle((void **)pManyArrays[i], chunk * 10);

    op.shrinkTo(chunk);

    for (i = 0; i < chunk; ++i)
        ls_pfree(pManyArrays[i]);
    ls_pfree(pManyArrays);
}

TEST(objpooltest)
{
    printf("START OBJPOOL TEST\n");
    ObjPool<ObjPoolTest> op(0);
    const int chunk = 10;
    int i;
    ObjPoolTest *pObjs[chunk] = { NULL };
    CHECK(op.size() == 0);
    CHECK(op.getPoolCapacity() == 0);
    CHECK(op.getPoolSize() == 0);
    CHECK(op.begin() == op.end());

    for (i = 0; i < chunk; ++i)
    {
        pObjs[i] = op.get();
        CHECK(pObjs[i] != NULL);
        CHECK(op.size() == chunk - i - 1);
        CHECK(op.getPoolCapacity() == chunk);
        CHECK(op.getPoolSize() == chunk);
    }
    CHECK(op.begin() == op.end());
    ObjPoolTest *p = op.get();
    CHECK(p != NULL);
    CHECK(op.size() == chunk - 1);
    CHECK(op.getPoolCapacity() == chunk * 2);
    CHECK(op.getPoolSize() == chunk * 2);
    CHECK(op.begin() != op.end());

    ObjPoolTest *pObjs2[chunk] = { NULL };
    op.get(pObjs2, chunk);
    CHECK(op.size() == chunk - 1);
    CHECK(op.getPoolCapacity() == chunk * 3);
    CHECK(op.getPoolSize() == chunk * 3);

    for (i = 0; i < chunk; ++i)
    {
        CHECK(pObjs2[i] != NULL);
        /* For the sake of reducing repetition, I put the following
        * checks in the same for loop.  These are separate tests
        * by nature, but I didn't want to have back to back for loops.
        */
        op.recycle(pObjs[i]);
        CHECK(op.size() == chunk + i);
        CHECK(op.getPoolCapacity() == chunk * 3);
        CHECK(op.getPoolSize() == chunk * 3);
    }
    op.recycle(p);
    op.shrinkTo(chunk);
    CHECK(op.size() == chunk);
    CHECK(op.getPoolCapacity() == chunk * 3);
    CHECK(op.getPoolSize() == chunk * 2);
    CHECK(op.begin() + chunk == op.end());

    op.recycle((void **)pObjs2, chunk);
    CHECK(op.size() == chunk * 2);
    CHECK(op.getPoolCapacity() == chunk * 3);
    CHECK(op.getPoolSize() == chunk * 2);
    CHECK(op.begin() + (2 * chunk) == op.end());

    op.get(pObjs, chunk);
    CHECK(op.size() == chunk);
    CHECK(op.getPoolCapacity() == chunk * 3);
    CHECK(op.getPoolSize() == chunk * 2);

    op.get(pObjs2, chunk);
    CHECK(op.size() == 0);
    CHECK(op.getPoolCapacity() == chunk * 3);
    CHECK(op.getPoolSize() == chunk * 2);

    p = op.get();
    CHECK(op.size() == chunk - 1);
    CHECK(op.getPoolCapacity() == chunk * 3);
    CHECK(op.getPoolSize() == chunk * 3);

    op.recycle(p);
    op.recycle((void **)pObjs, chunk);
    op.recycle((void **)pObjs2, chunk);
    CHECK(op.size() == chunk * 3);
    CHECK(op.getPoolCapacity() == chunk * 3);
    CHECK(op.getPoolSize() == chunk * 3);

//     stressTest(op, chunk);
}



#endif
