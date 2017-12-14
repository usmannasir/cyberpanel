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

#include <lsr/ls_xpool.h>
#include <lsr/ls_internal.h>
#include <lsr/ls_lock.h>
#include <lsr/ls_lfstack.h>
#include <lsr/ls_xpool_int.h>

#include <stdio.h>
#include <string.h>
#include "unittest-cpp/UnitTest++.h"

//#define LSR_XPOOL_DEBUG
#define LSR_XPOOL_SB_SIZE 4096

TEST(ls_XPoolTest_test)
{
#ifdef LSR_XPOOL_DEBUG
    printf("Starting XPool Test\n");
#endif
    static int sizes[] =
    {
        24, 3, 32, 40, 8, 24, 46,
        LSR_XPOOL_SB_SIZE - 8 - 16, LSR_XPOOL_SB_SIZE - 8 - 15, 1024, 1024, 2048, 800
    };

    ls_xpool_t *pool = ls_xpool_new();
    char *ptr, cmp[256];
    memset(cmp, 0, 256);

    ptr = (char *)ls_xpool_alloc(pool, LSR_XPOOL_SB_SIZE);
    CHECK(pool->psuperblk == NULL);
    CHECK(pool->pbigblk != NULL);
    CHECK(ls_xpool_isempty(pool) == 0);
    char *ptr2 = (char *)ls_xpool_alloc(pool, LSR_XPOOL_SB_SIZE);
    char *ptr3 = (char *)ls_xpool_alloc(pool, LSR_XPOOL_SB_SIZE);
    ls_xpool_free(pool, (void *)ptr2);
    ls_xpool_free(pool, (void *)ptr3);
    ls_xpool_free(pool, (void *)ptr);
    CHECK(pool->psuperblk == NULL);
    CHECK(pool->pbigblk == NULL);
    CHECK(ls_xpool_isempty(pool) == 1);

    ptr = (char *)ls_xpool_alloc(pool, 1032);
    ptr2 = (char *)ls_xpool_alloc(pool, 1032 + 16);
    ls_xpool_free(pool, (void *)ptr);
    ls_xpool_free(pool, (void *)ptr2);
    ls_xpool_alloc(pool, 4000);
    ls_xpool_alloc(pool, 4072);
    ptr3 = (char *)ls_xpool_alloc(pool, 1032);
    ls_xpool_free(pool, (void *)ptr3);
    ptr3 = (char *)ls_xpool_alloc(pool, 1032 + 32);
    ls_xpool_free(pool, (void *)ptr3);

    for (int i = 0; i < 50; i++)
    {
        ptr = (char *)ls_xpool_alloc(pool, 253);
        memset(ptr, 0, 253);
        CHECK(memcmp(ptr, cmp, 253) == 0);
    }

    ptr = (char *)ls_xpool_realloc(pool, ptr, 510);
    CHECK(memcmp(ptr, cmp, 253) == 0);

    ptr = (char *)ls_xpool_alloc(pool, 5000);
    memset(ptr, 0, 5000);
    for (int i = 0; i < 5000; ++i)
        CHECK(*(ptr + i) == 0);

    ptr = (char *)ls_xpool_realloc(pool, ptr, 5500);
    for (int i = 0; i < 5000; ++i)
        CHECK(*(ptr + i) == 0);

    int *psizes = sizes;
    for (int i = 0; i < (int)(sizeof(sizes) / sizeof(sizes[0])); i++)
    {
        ptr = (char *)ls_xpool_alloc(pool, *psizes);
        memset(ptr, 0x55, *psizes++);
        ls_xpool_free(pool, (void *)ptr);
    }

    ptr = (char *)ls_xpool_alloc(pool, 96 - sizeof(ls_xpool_header_t));
    ls_xpool_free(pool, (void *)ptr);     /* goes into min 96 bucket */
    ptr2 = (char *)ls_xpool_alloc(pool, 96 - sizeof(ls_xpool_header_t) - 15);
    CHECK(ptr == ptr2);                     /* takes from min 96 bucket */
    ls_xpool_free(pool, (void *)ptr2);    /* and keeps original size */
    ptr = (char *)ls_xpool_alloc(pool, 96 - sizeof(ls_xpool_header_t));
    CHECK(ptr == ptr2);
    ls_xpool_free(pool, (void *)ptr);

    ptr = (char *)ls_xpool_alloc(pool, 1024);
    for (int i = 0; i < 1024; ++i)
        *(ptr + i) = (i & 0xff);
    ls_xpool_free(pool, (void *)ptr);
    ptr2 = (char *)ls_xpool_alloc(pool, 1024);
    CHECK(ptr == ptr2);
    ls_xpool_free(pool, (void *)ptr2);
    ptr2 = (char *)ls_xpool_alloc(pool, 1024);
    CHECK(ptr == ptr2);
    ls_xpool_free(pool, (void *)ptr2);

    CHECK(ls_xpool_isempty(pool) == 0);
    (void)ls_xpool_alloc(pool, 8 * 1024);
    (void)ls_xpool_alloc(pool, 64 * 1024 + 1);
    (void)ls_xpool_alloc(pool, 8 * 1024);
    ls_xpool_delete(pool);
    // pool has been deleted by ls_pfree, can't
    // check if it's empty
    // CHECK(ls_xpool_isempty(pool) == 1);
}


// TEST(ls_XPoolTest_test2)
// {
//     ls_xpool_t *pool = ls_xpool_new();
//     char *ptr = (char *)ls_xpool_alloc(pool, 320);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 321);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 322);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 323);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 324);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 325);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 326);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 329);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 330);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 340);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 350);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 360);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 370);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 380);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 390);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 400);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 320);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 320);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 320);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 320);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 320);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 320);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 320);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 320);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 320);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 320);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 320);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 320);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 320);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 320);
//     ls_xpool_free(pool, (void *)ptr);
//     ptr = (char *)ls_xpool_alloc(pool, 320);
//
//
//     char *ptr1 = (char *)ls_xpool_alloc(pool, 320);
//     memset(ptr1, 255, 160);
//     ls_xpool_free(pool, (void *)ptr);
//
//
//     char *ptr2 = (char *)ls_xpool_realloc(pool, ptr1, 640);
//     CHECK(ptr2 > ptr1 || (long)ptr2 + 160 <= (long)ptr1);
//
//
//     char *ptr3 = (char *)ls_xpool_realloc(pool, ptr2, 648);
//     CHECK(ptr3 > ptr2 || (long)ptr3 + 320 <= (long)ptr2);
//
//
//     char *ptr4 = (char *)ls_xpool_realloc(pool, ptr3, 1280);
//     CHECK(ptr4 > ptr3 || ptr4 + 640 <= ptr3);
//
//     ls_xpool_free(pool, (void *)ptr4);
// }



TEST(ls_XPoolTest_testData)
{
    ls_xpool_t *pool = ls_xpool_new();

    int sz = 1024 - 8 - 1; //to make a exact same size as the superbuf
    char *ptr = (char *)ls_xpool_alloc(pool, sz);
    strcpy(ptr, "\x77\x77\x77\x77\x77\x77\x77\x77\x77");
    char *ptr1 = (char *)ls_xpool_alloc(pool, sz);
    strcpy(ptr1, "\x77\x77\x77\x77\x77\x77\x77\x77\x77");
    char *ptr2 = (char *)ls_xpool_alloc(pool, sz);
    strcpy(ptr2, "\x77\x77\x77\x77\x77\x77\x77\x77\x77");

    sz -= 256;  //even -256, still will alloc 1024, because when the last remain < 262
    //the blk will be removed and the remain will be append to the last alloc buffer
    char *ptr3 = (char *)ls_xpool_alloc(pool, sz);
    strcpy(ptr3, "\x77\x77\x77\x77\x77\x77\x77\x77\x77");


    //try to test the last buffer of the
    char *ptr4 = (char *)ls_xpool_alloc(pool, 0);



    ls_xpool_free(pool, (void *)ptr);
    ls_xpool_free(pool, (void *)ptr1);
    ls_xpool_free(pool, (void *)ptr2);
    ls_xpool_free(pool, (void *)ptr3);
    ls_xpool_free(pool, (void *)ptr4);

    sz = 4 * 1024 - 8 ; //to make a exact same size as the superbuf
    ptr = (char *)ls_xpool_alloc(pool, sz);
    strcpy(ptr, "\x77\x77\x77\x77\x77\x77\x77\x77\x77");
    ls_xpool_free(pool, (void *)ptr);

    sz = 4 * 1024 - 8 + 1; //to make a exact same size as the superbuf
    ptr = (char *)ls_xpool_alloc(pool, sz);
    strcpy(ptr, "\x77\x77\x77\x77\x77\x77\x77\x77\x77");
    ls_xpool_free(pool, (void *)ptr);


    sz = 4 * 1024 - 8 - 1; //to make a exact same size as the superbuf
    ptr = (char *)ls_xpool_alloc(pool, sz);
    strcpy(ptr, "\x77\x77\x77\x77\x77\x77\x77\x77\x77");
    ls_xpool_free(pool, (void *)ptr);


}




#endif
