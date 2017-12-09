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

#include "gmaptest.h"

#include <lsr/ls_xpool.h>
#include <util/gmap.h>
#include "unittest-cpp/UnitTest++.h"

int valcomp(const void *x, const void *y)
{
    return (long)x - (long)y;
}

static int set_two(const void *pKey, void *pValue, void *tmp)
{
    GMap *gm = (GMap *)tmp;
    gm->update(pKey, (void *)2);
    return 0;
}

TEST(GMapTest_test)
{
    GMap::iterator ptr;
    void *retVal;
    int iCount = 20, iDelCount = 12;
    const int aKeys[] = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20};
    int aVals[] = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20};
    int aDelList[] = {3, 13, 7, 2, 12, 11, 10, 1, 19, 15, 16, 6};
    GMap gm(valcomp);
    printf("Start GMapTest\n");
    CHECK(gm.size() == 0);

    CHECK(gm.empty() != 0);

    for (size_t i = 0; i < 3; ++i)
    {
        CHECK(gm.insert((const void *)(long)aKeys[i],
                        (void *)(long)aVals[i]) == 0);
        CHECK(gm.size() == i + 1);
        ptr = gm.find((const void *)(long)aKeys[i]);
        gm.for_each2(gm.begin(), gm.end(), set_two, (void *)&gm);
        CHECK((long)ptr->getValue() == 2);
        ptr = gm.next(ptr);
        CHECK(ptr == NULL);
    }

    CHECK(gm.empty() == 0);
#ifdef GMAP_DEBUG
    GMap::printTree(&gm);
#endif

    for (int i = 2; i >= 0; --i)
    {
        ptr = gm.find((const void *)(long)aKeys[i]);
        retVal = gm.deleteNode(ptr);
        CHECK((long)retVal == 2);
        CHECK(gm.size() == (size_t)i);
#ifdef GMAP_DEBUG
        printf("\n");
        GMap::printTree(&gm);
#endif
    }

    for (int i = 0; i < iCount; ++i)
    {
        CHECK(gm.insert((const void *)(long)aKeys[i],
                        (void *)(long)aVals[i]) == 0);
        CHECK(gm.size() == (size_t)i + 1);
    }
#ifdef GMAP_DEBUG
    GMap::printTree(&gm);
#endif

    ptr = gm.find((const void *)(long)aKeys[4]);
    CHECK((long)ptr->getKey() == aKeys[4]);

    ptr = gm.find((const void *)(long)aKeys[0]);
    CHECK((long)ptr->getKey() == aKeys[0]);

    ptr = gm.find((const void *)(long)40);
    CHECK(ptr == NULL);

    for (int i = 0; i < iDelCount; ++i)
    {
#ifdef GMAP_DEBUG
        printf("\nDeleted %d, i = %d\n", aKeys[ aDelList[i] ], i);
#endif
        ptr = gm.find((const void *)(long)aKeys[ aDelList[i] ]);
        retVal = gm.deleteNode(ptr);
        CHECK((long)retVal == aVals[ aDelList[i] ]);
        CHECK(gm.size() == (size_t)iCount - (size_t)i - 1);
#ifdef GMAP_DEBUG
        GMap::printTree(&gm);
#endif
    }

    retVal = gm.update((const void *)(long)aKeys[8], (void *)(long)aVals[10]);
    CHECK((long)retVal == aVals[8]);

    retVal = gm.update((const void *)(long)aKeys[8], (void *)(long)aVals[8]);
    CHECK((long)retVal == aVals[10]);

    ptr = gm.find((const void *)(long)aKeys[8]);
    retVal = gm.update((const void *)(long)aKeys[8], (void *)(long)aVals[10],
                       ptr);
    CHECK((long)retVal == aVals[8]);

    ptr = gm.find((const void *)(long)aKeys[8]);
    retVal = gm.update((const void *)(long)aKeys[8], (void *)(long)aVals[8],
                       ptr);
    CHECK((long)retVal == aVals[10]);

    retVal = gm.update((const void *)(long)aKeys[2], (void *)(long)aVals[10]);
    CHECK(retVal == NULL);

    ptr = gm.find((const void *)(long)aKeys[4]);
    retVal = gm.update((const void *)(long)aKeys[8], (void *)(long)aVals[10],
                       ptr);
    CHECK(retVal == NULL);

    gm.clear();

    printf("\n");
}

TEST(GMapPoolTest_test)
{
    GMap::iterator ptr;
    void *retVal;
    int iCount = 20, iDelCount = 12;
    const int aKeys[] = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20};
    int aVals[] = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20};
    int aDelList[] = {3, 13, 7, 2, 12, 11, 10, 1, 19, 15, 16, 6};
    ls_xpool_t *pool = ls_xpool_new();
    GMap gm(valcomp, pool);
    printf("Start GMapPoolTest\n");
    CHECK(gm.size() == 0);

    CHECK(gm.empty() != 0);

    for (size_t i = 0; i < 3; ++i)
    {
        CHECK(gm.insert((const void *)(long)aKeys[i],
                        (void *)(long)aVals[i]) == 0);
        CHECK(gm.size() == i + 1);
        ptr = gm.find((const void *)(long)aKeys[i]);
        gm.for_each2(gm.begin(), gm.end(), set_two, (void *)&gm);
        CHECK((long)ptr->getValue() == 2);
        ptr = gm.next(ptr);
        CHECK(ptr == NULL);
    }

    CHECK(gm.empty() == 0);
#ifdef GMAP_DEBUG
    GMap::printTree(&gm);
#endif

    for (int i = 2; i >= 0; --i)
    {
        ptr = gm.find((const void *)(long)aKeys[i]);
        retVal = gm.deleteNode(ptr);
        CHECK((long)retVal == 2);
        CHECK(gm.size() == (size_t)i);
#ifdef GMAP_DEBUG
        printf("\n");
        GMap::printTree(&gm);
#endif
    }

    for (int i = 0; i < iCount; ++i)
    {
        CHECK(gm.insert((const void *)(long)aKeys[i],
                        (void *)(long)aVals[i]) == 0);
        CHECK(gm.size() == (size_t)i + 1);
    }
#ifdef GMAP_DEBUG
    GMap::printTree(&gm);
#endif

    ptr = gm.find((const void *)(long)aKeys[4]);
    CHECK((long)ptr->getKey() == aKeys[4]);

    ptr = gm.find((const void *)(long)aKeys[0]);
    CHECK((long)ptr->getKey() == aKeys[0]);

    ptr = gm.find((const void *)(long)40);
    CHECK(ptr == NULL);

    for (int i = 0; i < iDelCount; ++i)
    {
#ifdef GMAP_DEBUG
        printf("\nDeleted %d, i = %d\n", aKeys[ aDelList[i] ], i);
#endif
        ptr = gm.find((const void *)(long)aKeys[ aDelList[i] ]);
        retVal = gm.deleteNode(ptr);
        CHECK((long)retVal == aVals[ aDelList[i] ]);
        CHECK(gm.size() == (size_t)iCount - (size_t)i - 1);
#ifdef GMAP_DEBUG
        GMap::printTree(&gm);
#endif
    }

    retVal = gm.update((const void *)(long)aKeys[8], (void *)(long)aVals[10]);
    CHECK((long)retVal == aVals[8]);

    retVal = gm.update((const void *)(long)aKeys[8], (void *)(long)aVals[8]);
    CHECK((long)retVal == aVals[10]);

    ptr = gm.find((const void *)(long)aKeys[8]);
    retVal = gm.update((const void *)(long)aKeys[8], (void *)(long)aVals[10],
                       ptr);
    CHECK((long)retVal == aVals[8]);

    ptr = gm.find((const void *)(long)aKeys[8]);
    retVal = gm.update((const void *)(long)aKeys[8], (void *)(long)aVals[8],
                       ptr);
    CHECK((long)retVal == aVals[10]);

    retVal = gm.update((const void *)(long)aKeys[2], (void *)(long)aVals[10]);
    CHECK(retVal == NULL);

    ptr = gm.find((const void *)(long)aKeys[4]);
    retVal = gm.update((const void *)(long)aKeys[8], (void *)(long)aVals[10],
                       ptr);
    CHECK(retVal == NULL);

    gm.clear();

    printf("\n");
    ls_xpool_delete(pool);
}

#endif

