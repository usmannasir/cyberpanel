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

#include <util/gpointerlist.h>
#include "unittest-cpp/UnitTest++.h"

#include <string.h>

static int s_mycmp(const void *p1, const void *p2)
{
    return (strcmp(*(char **)p1, *(char **)p2));
}

static int f_mycmp(const void *p1, const void *p2)
{
    return (strcmp((char *)p1, (char *)p2));
}

TEST(GPointerListTest_test)
{
    int size;
    unsigned int capacity;
    GPointerList *pglist2;
    GPointerList glist3;
    GPointerList::const_iterator iter;
    static const char *myptrs[] = { "ptr3", "ptr2", "ptr4", "ptr1" };
    char *ptrs[sizeof(myptrs) / sizeof(myptrs[0])];

    capacity = 10;
    pglist2 = new GPointerList(capacity);
    CHECK(pglist2 != NULL);
    CHECK(pglist2->capacity() == capacity);
    capacity *= 3;
    pglist2->reserve(capacity);
    CHECK(pglist2->capacity() == capacity);
    CHECK(pglist2->size() == 0);
    pglist2->unsafe_push_back((void **)myptrs, 2);
    CHECK(pglist2->size() == 2);
    pglist2->unsafe_pop_back((void **)ptrs, 1);
    CHECK(pglist2->size() == 1);
    CHECK(ptrs[0] == myptrs[1]);
    pglist2->clear();
    CHECK(pglist2->capacity() == capacity);
    CHECK(pglist2->size() == 0);

    capacity = 15;
    CHECK(glist3.capacity() == 0);
    glist3.reserve(capacity);
    for (size = 0; size < (int)(sizeof(myptrs) / sizeof(myptrs[0])); ++size)
    {
        glist3.push_back((void *)myptrs[size]);
        pglist2->push_back((void *)myptrs[size]);
    }
    CHECK(glist3.capacity() == capacity);
    CHECK(glist3.size() == size);
    glist3.reserve(size);
    CHECK(glist3.capacity() == (unsigned)size);
    CHECK(glist3.size() == size);
    CHECK(pglist2->size() == size);

    --size;
    glist3.pop_front((void **)ptrs, size);
    while (--size >= 0)
        CHECK(ptrs[size] == myptrs[size]);

    glist3.push_back(*pglist2);
    size = sizeof(myptrs) / sizeof(myptrs[0]) + 1;
    CHECK(glist3.size() == size);

    glist3.push_back((void *)myptrs[0]);
    ++size;
    CHECK(glist3.capacity() >= (unsigned)size);
    glist3.pop_front((void **)ptrs, 1);
    --size;
    CHECK(glist3.pop_back() == (void *)myptrs[0]);
    --size;
    CHECK(glist3.size() == size);
    CHECK(sizeof(myptrs) / sizeof(myptrs[0]) == size);

    glist3.sort(s_mycmp);
    iter = glist3.bfind((const void *)myptrs[0], f_mycmp);
    CHECK(*(const char **)iter == myptrs[0]);
    glist3.erase((GPointerList::iterator)iter);
    --size;
    CHECK(glist3.size() == size);

    delete pglist2;
}

#endif
