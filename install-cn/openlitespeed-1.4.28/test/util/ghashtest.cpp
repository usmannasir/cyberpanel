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

#include "ghashtest.h"

#include <lsr/ls_xpool.h>
#include <util/ghash.h>
#include "unittest-cpp/UnitTest++.h"

static int  plus_int(const void *pKey, void *pData, void *pUData)
{
    ((GHash *)pUData)->update(pKey, (void *)((char *)pData + (long)10));
    return 0;
}

TEST(GHashTest_test)
{
    GHash hash(10, NULL, NULL);
    CHECK(hash.size() == 0);
    CHECK(hash.capacity() == 13);
    GHash::iterator iter = hash.insert((void *)0, (void *)0);
    CHECK(iter != hash.end());
    CHECK((long)iter->getKey() == 0);
    CHECK((long)iter->getData() == 0);
    CHECK(iter->getHKey() == 0);
    CHECK(iter->getNext() == NULL);
    CHECK(hash.size() == 1);

    GHash::iterator iter1 = hash.insert((void *)13, (void *)13);
    CHECK(iter1 != hash.end());
    CHECK((long)iter1->getKey() == 13);
    CHECK((long)iter1->getData() == 13);
    CHECK(iter1->getHKey() == 13);
    CHECK(iter1->getNext() == iter);
    CHECK(hash.size() == 2);

    GHash::iterator iter4 = hash.insert((void *)26, (void *)26);
    CHECK(iter4 != hash.end());
    CHECK((long)iter4->getKey() == 26);
    CHECK((long)iter4->getData() == 26);
    CHECK(iter4->getHKey() == 26);
    CHECK(iter4->getNext() == iter1);
    CHECK(hash.size() == 3);

    GHash::iterator iter2 = hash.insert((void *)15, (void *)15);
    CHECK(iter2 != hash.end());
    CHECK((long)iter2->getKey() == 15);
    CHECK((long)iter2->getData() == 15);
    CHECK(iter2->getHKey() == 15);
    CHECK(iter2->getNext() == NULL);
    CHECK(hash.size() == 4);

    GHash::iterator iter3;
    iter3 = hash.find((void *)0);
    CHECK(iter3 == iter);
    iter3 = hash.find((void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash.find((void *)15);
    CHECK(iter3 == iter2);
    iter3 = hash.find((void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash.find((void *)39);
    CHECK(iter3 == NULL);
    iter3 = hash.find((void *)28);
    CHECK(iter3 == NULL);

    iter3 = hash.begin();
    CHECK(iter3 == iter4);
    iter3 = hash.next(iter3);
    CHECK(iter3 == iter1);
    iter3 = hash.next(iter3);
    CHECK(iter3 == iter);
    iter3 = hash.next(iter3);
    CHECK(iter3 == iter2);
    iter3 = hash.next(iter3);
    CHECK(iter3 == hash.end());

    int n = hash.for_each2(hash.begin(), hash.end(), plus_int, &hash);
    CHECK(n == 4);
    CHECK((long)iter->getData() == 10);
    CHECK((long)iter1->getData() == 23);
    CHECK((long)iter2->getData() == 25);
    CHECK((long)iter4->getData() == 36);

    hash.erase(iter);
    CHECK(hash.size() == 3);
    CHECK(iter1->getNext() == NULL);
    CHECK(iter4->getNext() == iter1);
    iter3 = hash.find((void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash.find((void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash.find((void *)0);
    CHECK(iter3 == NULL);

    iter = hash.insert((void *)0, (void *)0);
    CHECK(iter != hash.end());
    CHECK(hash.size() == 4);
    CHECK(iter->getNext() == iter4);
    CHECK(iter4->getNext() == iter1);
    CHECK(iter1->getNext() == NULL);
    iter3 = hash.find((void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash.find((void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash.find((void *)0);
    CHECK(iter3 == iter);

    hash.erase(iter);
    CHECK(hash.size() == 3);
    CHECK(iter1->getNext() == NULL);
    CHECK(iter4->getNext() == iter1);
    iter3 = hash.find((void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash.find((void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash.find((void *)0);
    CHECK(iter3 == NULL);

    iter = hash.insert((void *)0, (void *)0);
    CHECK(iter != hash.end());
    CHECK(hash.size() == 4);
    CHECK(iter->getNext() == iter4);
    CHECK(iter4->getNext() == iter1);
    CHECK(iter1->getNext() == NULL);
    iter3 = hash.find((void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash.find((void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash.find((void *)0);
    CHECK(iter3 == iter);

    hash.erase(iter4);
    CHECK(hash.size() == 3);
    iter3 = hash.find((void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash.find((void *)26);
    CHECK(iter3 == NULL);
    iter3 = hash.find((void *)0);
    CHECK(iter3 == iter);
    CHECK(iter->getNext() == iter1);
    CHECK(iter1->getNext() == NULL);

    iter4 = hash.insert((void *)26, (void *)26);
    CHECK(iter4 != hash.end());
    CHECK(iter4->getNext() == iter);
    CHECK(iter->getNext() == iter1);
    CHECK(iter1->getNext() == NULL);
    CHECK(hash.size() == 4);


    GHash::iterator iter5 = hash.insert((void *)5, (void *)5);
    CHECK(hash.capacity() == 13);
    GHash::iterator iter6 = hash.insert((void *)6, (void *)6);
    CHECK(hash.capacity() == 13);
    GHash::iterator iter7 = hash.insert((void *)7, (void *)7);
    CHECK(hash.capacity() == 13);
    GHash::iterator iter8 = hash.insert((void *)8, (void *)8);
    CHECK(hash.capacity() == 53);
    CHECK(iter->getNext() == NULL);
    CHECK(iter1->getNext() == NULL);
    CHECK(iter2->getNext() == NULL);
    CHECK(iter4->getNext() == NULL);
    CHECK(iter5->getNext() == NULL);
    CHECK(iter6->getNext() == NULL);
    CHECK(iter7->getNext() == NULL);
    CHECK(iter8->getNext() == NULL);

    iter3 = hash.find((void *)0);
    CHECK(iter3 == iter);
    iter3 = hash.find((void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash.find((void *)15);
    CHECK(iter3 == iter2);
    iter3 = hash.find((void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash.find((void *)28);
    CHECK(iter3 == NULL);
}

TEST(GHashPoolTest_test)
{
    ls_xpool_t *pool = ls_xpool_new();
    {
        GHash hash(10, NULL, NULL, pool);
        CHECK(hash.size() == 0);
        CHECK(hash.capacity() == 13);
        GHash::iterator iter = hash.insert((void *)0, (void *)0);
        CHECK(iter != hash.end());
        CHECK((long)iter->getKey() == 0);
        CHECK((long)iter->getData() == 0);
        CHECK(iter->getHKey() == 0);
        CHECK(iter->getNext() == NULL);
        CHECK(hash.size() == 1);

        GHash::iterator iter1 = hash.insert((void *)13, (void *)13);
        CHECK(iter1 != hash.end());
        CHECK((long)iter1->getKey() == 13);
        CHECK((long)iter1->getData() == 13);
        CHECK(iter1->getHKey() == 13);
        CHECK(iter1->getNext() == iter);
        CHECK(hash.size() == 2);

        GHash::iterator iter4 = hash.insert((void *)26, (void *)26);
        CHECK(iter4 != hash.end());
        CHECK((long)iter4->getKey() == 26);
        CHECK((long)iter4->getData() == 26);
        CHECK(iter4->getHKey() == 26);
        CHECK(iter4->getNext() == iter1);
        CHECK(hash.size() == 3);

        GHash::iterator iter2 = hash.insert((void *)15, (void *)15);
        CHECK(iter2 != hash.end());
        CHECK((long)iter2->getKey() == 15);
        CHECK((long)iter2->getData() == 15);
        CHECK(iter2->getHKey() == 15);
        CHECK(iter2->getNext() == NULL);
        CHECK(hash.size() == 4);

        GHash::iterator iter3;
        iter3 = hash.find((void *)0);
        CHECK(iter3 == iter);
        iter3 = hash.find((void *)13);
        CHECK(iter3 == iter1);
        iter3 = hash.find((void *)15);
        CHECK(iter3 == iter2);
        iter3 = hash.find((void *)26);
        CHECK(iter3 == iter4);
        iter3 = hash.find((void *)39);
        CHECK(iter3 == NULL);
        iter3 = hash.find((void *)28);
        CHECK(iter3 == NULL);

        iter3 = hash.begin();
        CHECK(iter3 == iter4);
        iter3 = hash.next(iter3);
        CHECK(iter3 == iter1);
        iter3 = hash.next(iter3);
        CHECK(iter3 == iter);
        iter3 = hash.next(iter3);
        CHECK(iter3 == iter2);
        iter3 = hash.next(iter3);
        CHECK(iter3 == hash.end());

        int n = hash.for_each2(hash.begin(), hash.end(), plus_int, &hash);
        CHECK(n == 4);
        CHECK((long)iter->getData() == 10);
        CHECK((long)iter1->getData() == 23);
        CHECK((long)iter2->getData() == 25);
        CHECK((long)iter4->getData() == 36);

        hash.erase(iter);
        CHECK(hash.size() == 3);
        CHECK(iter1->getNext() == NULL);
        CHECK(iter4->getNext() == iter1);
        iter3 = hash.find((void *)13);
        CHECK(iter3 == iter1);
        iter3 = hash.find((void *)26);
        CHECK(iter3 == iter4);
        iter3 = hash.find((void *)0);
        CHECK(iter3 == NULL);

        iter = hash.insert((void *)0, (void *)0);
        CHECK(iter != hash.end());
        CHECK(hash.size() == 4);
        CHECK(iter->getNext() == iter4);
        CHECK(iter4->getNext() == iter1);
        CHECK(iter1->getNext() == NULL);
        iter3 = hash.find((void *)13);
        CHECK(iter3 == iter1);
        iter3 = hash.find((void *)26);
        CHECK(iter3 == iter4);
        iter3 = hash.find((void *)0);
        CHECK(iter3 == iter);

        hash.erase(iter);
        CHECK(hash.size() == 3);
        CHECK(iter1->getNext() == NULL);
        CHECK(iter4->getNext() == iter1);
        iter3 = hash.find((void *)13);
        CHECK(iter3 == iter1);
        iter3 = hash.find((void *)26);
        CHECK(iter3 == iter4);
        iter3 = hash.find((void *)0);
        CHECK(iter3 == NULL);

        iter = hash.insert((void *)0, (void *)0);
        CHECK(iter != hash.end());
        CHECK(hash.size() == 4);
        CHECK(iter->getNext() == iter4);
        CHECK(iter4->getNext() == iter1);
        CHECK(iter1->getNext() == NULL);
        iter3 = hash.find((void *)13);
        CHECK(iter3 == iter1);
        iter3 = hash.find((void *)26);
        CHECK(iter3 == iter4);
        iter3 = hash.find((void *)0);
        CHECK(iter3 == iter);

        hash.erase(iter4);
        CHECK(hash.size() == 3);
        iter3 = hash.find((void *)13);
        CHECK(iter3 == iter1);
        iter3 = hash.find((void *)26);
        CHECK(iter3 == NULL);
        iter3 = hash.find((void *)0);
        CHECK(iter3 == iter);
        CHECK(iter->getNext() == iter1);
        CHECK(iter1->getNext() == NULL);

        iter4 = hash.insert((void *)26, (void *)26);
        CHECK(iter4 != hash.end());
        CHECK(iter4->getNext() == iter);
        CHECK(iter->getNext() == iter1);
        CHECK(iter1->getNext() == NULL);
        CHECK(hash.size() == 4);


        GHash::iterator iter5 = hash.insert((void *)5, (void *)5);
        CHECK(hash.capacity() == 13);
        GHash::iterator iter6 = hash.insert((void *)6, (void *)6);
        CHECK(hash.capacity() == 13);
        GHash::iterator iter7 = hash.insert((void *)7, (void *)7);
        CHECK(hash.capacity() == 13);
        GHash::iterator iter8 = hash.insert((void *)8, (void *)8);
        CHECK(hash.capacity() == 53);
        CHECK(iter->getNext() == NULL);
        CHECK(iter1->getNext() == NULL);
        CHECK(iter2->getNext() == NULL);
        CHECK(iter4->getNext() == NULL);
        CHECK(iter5->getNext() == NULL);
        CHECK(iter6->getNext() == NULL);
        CHECK(iter7->getNext() == NULL);
        CHECK(iter8->getNext() == NULL);

        iter3 = hash.find((void *)0);
        CHECK(iter3 == iter);
        iter3 = hash.find((void *)13);
        CHECK(iter3 == iter1);
        iter3 = hash.find((void *)15);
        CHECK(iter3 == iter2);
        iter3 = hash.find((void *)26);
        CHECK(iter3 == iter4);
        iter3 = hash.find((void *)28);
        CHECK(iter3 == NULL);
    }
    ls_xpool_delete(pool);
}

#endif

