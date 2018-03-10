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

#include <lsr/ls_map.h>
#include <lsr/ls_xpool.h>
#include "unittest-cpp/UnitTest++.h"


int ls_map_valcomp(const void *x, const void *y)
{
    return (long)x - (long)y;
}

static int set_two(const void *pKey, void *pValue, void *tmp)
{
    ls_map_t *gm = (ls_map_t *)tmp;
    gm->update_fn(gm, pKey, (void *)2, NULL);
    return 0;
}

TEST(ls_maptest_test)
{
    ls_map_iter ptr;
    void *retVal;
    int iCount = 20, iDelCount = 12;
    const int aKeys[] = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20};
    int aVals[] = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20};
    int aDelList[] = {3, 13, 7, 2, 12, 11, 10, 1, 19, 15, 16, 6};
#ifdef LSR_MAP_DEBUG
    printf("\nStart LSR Map Test\n");
#endif
    ls_map_t *gm = ls_map_new(ls_map_valcomp, NULL);
    CHECK(ls_map_size(gm) == 0);
    CHECK(ls_map_empty(gm) != 0);

    for (size_t i = 0; i < 3; ++i)
    {
        CHECK(gm->insert_fn(gm, (const void *)(long)aKeys[i],
                            (void *)(long)aVals[i]) == 0);
        CHECK(ls_map_size(gm) == i + 1);
        ptr = gm->find_fn(gm, (const void *)(long)aKeys[i]);
        ls_map_foreach2(gm, ls_map_begin(gm), ls_map_end(gm), set_two, (void *)gm);
        CHECK((long)ls_map_getnodeval(ptr) == 2);
        ptr = ls_map_next(gm, ptr);
        CHECK(ptr == NULL);
    }
    CHECK(ls_map_empty(gm) == 0);

    ls_map_t *gm2 = ls_map_new(ls_map_valcomp, NULL);
    CHECK(ls_map_size(gm2) == 0);
    CHECK(ls_map_empty(gm2) != 0);
    ls_map_swap(gm, gm2);
    CHECK(ls_map_size(gm) == 0);
    CHECK(ls_map_size(gm2) != 0);
    ls_map_swap(gm, gm2);
    CHECK(ls_map_size(gm2) == 0);
    CHECK(ls_map_size(gm) != 0);
    ls_map_delete(gm2);

#ifdef LSR_MAP_DEBUG
    ls_map_printTree(gm);
#endif

    for (int i = 2; i >= 0; --i)
    {
        ptr = gm->find_fn(gm, (const void *)(long)aKeys[i]);
        retVal = ls_map_deletenode(gm, ptr);
        CHECK((long)retVal == 2);
        CHECK(ls_map_size(gm) == (size_t)i);
#ifdef LSR_MAP_DEBUG
        printf("\n");
        ls_map_printTree(gm);
#endif
    }
    for (int i = 0; i < iCount; ++i)
    {
        CHECK(gm->insert_fn(gm, (const void *)(long)aKeys[i],
                            (void *)(long)aVals[i]) == 0);
        CHECK(ls_map_size(gm) == (size_t)i + 1);
    }
#ifdef LSR_MAP_DEBUG
    ls_map_printTree(gm);
#endif

    ptr = gm->find_fn(gm, (const void *)(long)aKeys[4]);
    CHECK((long)ls_map_getnodekey(ptr) == aKeys[4]);
    ptr = gm->find_fn(gm, (const void *)(long)40);
    CHECK(ptr == NULL);
    ptr = gm->find_fn(gm, (const void *)(long)aKeys[0]);
    CHECK((long)ls_map_getnodekey(ptr) == aKeys[0]);

    for (long i = 2; i <= iCount; ++i)
    {
        ptr = ls_map_next(gm, ptr);
        CHECK((long)ls_map_getnodekey(ptr) == i);
    }
    for (int i = 0; i < iDelCount; ++i)
    {
#ifdef LSR_MAP_DEBUG
        printf("\nDeleted %d, i = %d\n", aKeys[ aDelList[i] ], i);
#endif
        ptr = gm->find_fn(gm, (const void *)(long)aKeys[ aDelList[i] ]);
        retVal = ls_map_deletenode(gm, ptr);
        CHECK((long)retVal == aVals[ aDelList[i] ]);
        CHECK(ls_map_size(gm) == (size_t)iCount - (size_t)i - 1);
#ifdef LSR_MAP_DEBUG
        ls_map_printTree(gm);
#endif
    }

    retVal = gm->update_fn(gm, (const void *)(long)aKeys[8],
                           (void *)(long)aVals[10], NULL);
    CHECK((long)retVal == aVals[8]);
    retVal = gm->update_fn(gm, (const void *)(long)aKeys[8],
                           (void *)(long)aVals[8], NULL);
    CHECK((long)retVal == aVals[10]);
    ptr = gm->find_fn(gm, (const void *)(long)aKeys[8]);
    retVal = gm->update_fn(gm, (const void *)(long)aKeys[8],
                           (void *)(long)aVals[10], ptr);
    CHECK((long)retVal == aVals[8]);
    ptr = gm->find_fn(gm, (const void *)(long)aKeys[8]);
    retVal = gm->update_fn(gm, (const void *)(long)aKeys[8],
                           (void *)(long)aVals[8], ptr);
    CHECK((long)retVal == aVals[10]);
    retVal = gm->update_fn(gm, (const void *)(long)aKeys[2],
                           (void *)(long)aVals[10], NULL);
    CHECK(retVal == NULL);
    ptr = gm->find_fn(gm, (const void *)(long)aKeys[4]);
    retVal = gm->update_fn(gm, (const void *)(long)aKeys[8],
                           (void *)(long)aVals[10], ptr);
    CHECK(retVal == NULL);

    ls_map_delete(gm);
}

TEST(ls_mappooltest_test)
{
    ls_map_iter ptr;
    ls_xpool_t *pool = ls_xpool_new();
    void *retVal;
    int iCount = 20, iDelCount = 12;
    const int aKeys[] = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20};
    int aVals[] = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20};
    int aDelList[] = {3, 13, 7, 2, 12, 11, 10, 1, 19, 15, 16, 6};
#ifdef LSR_MAP_DEBUG
    printf("\nStart LSR Map Pool Test\n");
#endif
    ls_map_t *gm = ls_map_new(ls_map_valcomp, pool);
    CHECK(ls_map_size(gm) == 0);
    CHECK(ls_map_empty(gm) != 0);

    for (size_t i = 0; i < 3; ++i)
    {
        CHECK(gm->insert_fn(gm, (const void *)(long)aKeys[i],
                            (void *)(long)aVals[i]) == 0);
        CHECK(ls_map_size(gm) == i + 1);
        ptr = gm->find_fn(gm, (const void *)(long)aKeys[i]);
        ls_map_foreach2(gm, ls_map_begin(gm), ls_map_end(gm), set_two, (void *)gm);
        CHECK((long)ls_map_getnodeval(ptr) == 2);
        ptr = ls_map_next(gm, ptr);
        CHECK(ptr == NULL);
    }
    CHECK(ls_map_empty(gm) == 0);

    ls_map_t *gm2 = ls_map_new(ls_map_valcomp, pool);
    CHECK(ls_map_size(gm2) == 0);
    CHECK(ls_map_empty(gm2) != 0);
    ls_map_swap(gm, gm2);
    CHECK(ls_map_size(gm) == 0);
    CHECK(ls_map_size(gm2) != 0);
    ls_map_swap(gm, gm2);
    CHECK(ls_map_size(gm2) == 0);
    CHECK(ls_map_size(gm) != 0);
    ls_map_delete(gm2);

#ifdef LSR_MAP_DEBUG
    ls_map_printTree(gm);
#endif

    for (int i = 2; i >= 0; --i)
    {
        ptr = gm->find_fn(gm, (const void *)(long)aKeys[i]);
        retVal = ls_map_deletenode(gm, ptr);
        CHECK((long)retVal == 2);
        CHECK(ls_map_size(gm) == (size_t)i);
#ifdef LSR_MAP_DEBUG
        printf("\n");
        ls_map_printTree(gm);
#endif
    }
    for (int i = 0; i < iCount; ++i)
    {
        CHECK(gm->insert_fn(gm, (const void *)(long)aKeys[i],
                            (void *)(long)aVals[i]) == 0);
        CHECK(ls_map_size(gm) == (size_t)i + 1);
    }
#ifdef LSR_MAP_DEBUG
    ls_map_printTree(gm);
#endif

    ptr = gm->find_fn(gm, (const void *)(long)aKeys[4]);
    CHECK((long)ls_map_getnodekey(ptr) == aKeys[4]);
    ptr = gm->find_fn(gm, (const void *)(long)40);
    CHECK(ptr == NULL);
    ptr = gm->find_fn(gm, (const void *)(long)aKeys[0]);
    CHECK((long)ls_map_getnodekey(ptr) == aKeys[0]);

    for (long i = 2; i <= iCount; ++i)
    {
        ptr = ls_map_next(gm, ptr);
        CHECK((long)ls_map_getnodekey(ptr) == i);
    }
    for (int i = 0; i < iDelCount; ++i)
    {
#ifdef LSR_MAP_DEBUG
        printf("\nDeleted %d, i = %d\n", aKeys[ aDelList[i] ], i);
#endif
        ptr = gm->find_fn(gm, (const void *)(long)aKeys[ aDelList[i] ]);
        retVal = ls_map_deletenode(gm, ptr);
        CHECK((long)retVal == aVals[ aDelList[i] ]);
        CHECK(ls_map_size(gm) == (size_t)iCount - (size_t)i - 1);
#ifdef LSR_MAP_DEBUG
        ls_map_printTree(gm);
#endif
    }

    retVal = gm->update_fn(gm, (const void *)(long)aKeys[8],
                           (void *)(long)aVals[10], NULL);
    CHECK((long)retVal == aVals[8]);
    retVal = gm->update_fn(gm, (const void *)(long)aKeys[8],
                           (void *)(long)aVals[8], NULL);
    CHECK((long)retVal == aVals[10]);
    ptr = gm->find_fn(gm, (const void *)(long)aKeys[8]);
    retVal = gm->update_fn(gm, (const void *)(long)aKeys[8],
                           (void *)(long)aVals[10], ptr);
    CHECK((long)retVal == aVals[8]);
    ptr = gm->find_fn(gm, (const void *)(long)aKeys[8]);
    retVal = gm->update_fn(gm, (const void *)(long)aKeys[8],
                           (void *)(long)aVals[8], ptr);
    CHECK((long)retVal == aVals[10]);
    retVal = gm->update_fn(gm, (const void *)(long)aKeys[2],
                           (void *)(long)aVals[10], NULL);
    CHECK(retVal == NULL);
    ptr = gm->find_fn(gm, (const void *)(long)aKeys[4]);
    retVal = gm->update_fn(gm, (const void *)(long)aKeys[8],
                           (void *)(long)aVals[10], ptr);
    CHECK(retVal == NULL);

    ls_map_delete(gm);
    ls_xpool_delete(pool);
}



#endif

