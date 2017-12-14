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

#include <lsr/ls_pool.h>

#include <stdio.h>
#include <string.h>
#include "unittest-cpp/UnitTest++.h"

#define LSR_POOL_SMFREELIST_MAXBYTES  4096
#define LSR_POOL_LGFREELIST_MAXBYTES  (64*1024)

TEST(ls_PoolTest_test)
{
    static int sizes[] =
    {
        24, 3, 32, LSR_POOL_SMFREELIST_MAXBYTES,
        LSR_POOL_SMFREELIST_MAXBYTES + 1, LSR_POOL_SMFREELIST_MAXBYTES + 512,
        LSR_POOL_LGFREELIST_MAXBYTES, LSR_POOL_LGFREELIST_MAXBYTES + 1,
    };
    char *ptrs[sizeof(sizes) / sizeof(sizes[0])];
    char *ptr0[40];
    char *ptr1[40];
    char cmp[256];
    const int fill = 0xa5;

    memset(cmp, fill, 256);
    int i;
    for (i = 0; i < (int)(sizeof(ptr0) / sizeof(ptr0[0])); i++)
    {
        ptr0[i] = (char *)ls_palloc(97);
        memset(ptr0[i], fill, 97);
        CHECK(memcmp(ptr0[i], cmp, 97) == 0);
        ptr1[i] = (char *)ls_palloc(97);
        memset(ptr1[i], fill, 97);
        CHECK(memcmp(ptr1[i], cmp, 97) == 0);
    }

    --i;
    ptrs[0] = ptr0[i];
    ptrs[1] = ptr1[i];
    ptrs[2] = (char *)ls_prealloc(ptrs[0], 22);
    CHECK(memcmp(ptrs[2], cmp, 22) == 0);
    ptrs[0] = (char *)ls_prealloc(ptrs[2], 144);
    CHECK(memcmp(ptrs[0], cmp, 22) == 0);
    ls_pfree((void *)ptrs[0]);

    ptrs[3] = (char *)ls_prealloc(ptrs[1], 22);
    CHECK(ptrs[3] == ptrs[1]);
    ptrs[1] = (char *)ls_prealloc(ptrs[3], 144);
    CHECK(memcmp(ptrs[1], cmp, 22) == 0);
    ptrs[3] = (char *)ls_prealloc(ptrs[1], LSR_POOL_LGFREELIST_MAXBYTES);
    CHECK(memcmp(ptrs[3], cmp, 22) == 0);
    ls_pfree((void *)ptrs[3]);

    int *psizes = sizes;
    for (i = 0; i < (int)(sizeof(sizes) / sizeof(sizes[0])); i++)
    {
        ptrs[i] = (char *)ls_palloc(*psizes);
        memset(ptrs[i], fill, *psizes++);
    }

    while (--i >= 0)
        ls_pfree((void *)ptrs[i]);

    psizes = sizes;
    for (i = 0; i < (int)(sizeof(sizes) / sizeof(sizes[0])); i++)
    {
        ptrs[i] = (char *)ls_palloc(*psizes);
        memset(ptrs[i], fill, *psizes++);
    }

    while (--i >= 0)
        ls_pfree((void *)ptrs[i]);

    ptrs[0] = (char *)ls_palloc(LSR_POOL_SMFREELIST_MAXBYTES + 16);
    ls_pfree((void *)ptrs[0]);
    ptrs[0] = (char *)ls_palloc(LSR_POOL_SMFREELIST_MAXBYTES + 16);
    ls_pfree((void *)ptrs[0]);

    for (i = 0; i < (int)(sizeof(ptr0) / sizeof(ptr0[0]) - 1); i++)
    {
        ls_pfree((void *)ptr0[i]);
        ls_pfree((void *)ptr1[i]);
    }
}

#endif
