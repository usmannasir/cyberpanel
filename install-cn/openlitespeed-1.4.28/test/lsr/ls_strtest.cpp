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

//#define LSR_STR_DEBUG

#include <stdio.h>

#include <lsr/ls_str.h>

#include <lsr/ls_hash.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_xpool.h>
#include "unittest-cpp/UnitTest++.h"

TEST(ls_strtest_test)
{
#ifdef LSR_STR_DEBUG
    printf("Start LSR Str Test\n");
#endif

    ls_str_t *pFive = ls_str_new(NULL, 0);
    CHECK(ls_str_len(pFive) == 0);
    CHECK(ls_str_dup(pFive, "apple", 5) == 5);
    CHECK(memcmp(ls_str_cstr(pFive), "apple", 5) == 0);
    ls_str_append(pFive, "grape", 5);
    CHECK(memcmp(ls_str_cstr(pFive), "applegrape", 10) == 0);
    ls_str_setlen(pFive, 7);
    CHECK(ls_str_len(pFive) == 7);
    CHECK(memcmp(ls_str_cstr(pFive), "applegr", 7) == 0);

    ls_str_t *pSix = ls_str_new("applegr", 7);
    ls_str_t pSeven;
    ls_str(&pSeven, "applegr", 7);
    ls_str_t pEight;
    CHECK(ls_str_copy(&pEight, &pSeven) != NULL);
    CHECK(memcmp(ls_str_cstr(pFive), ls_str_cstr(pSix), 7) == 0);
    CHECK(memcmp(ls_str_cstr(pSix), ls_str_cstr(&pSeven), 7) == 0);
    CHECK(memcmp(ls_str_cstr(pSix), ls_str_cstr(&pEight), 7) == 0);


    ls_str_delete(pFive);
    ls_str_delete(pSix);
    ls_str_d(&pSeven);
    ls_str_d(&pEight);
}

TEST(ls_strtest_pooltest)
{
#ifdef LSR_STR_DEBUG
    printf("Start LSR Str XPool Test\n");
#endif
    ls_xpool_t *pool = ls_xpool_new();
    ls_str_t *pFive = ls_str_xnew(NULL, 0, pool);
    CHECK(ls_str_len(pFive) == 0);
    CHECK(ls_str_xsetstr(pFive, "apple", 5, pool) == 5);
    CHECK(memcmp(ls_str_cstr(pFive), "apple", 5) == 0);
    ls_str_xappend(pFive, "grape", 5, pool);
    CHECK(memcmp(ls_str_cstr(pFive), "applegrape", 10) == 0);
    ls_str_setlen(pFive, 7);
    CHECK(ls_str_len(pFive) == 7);
    CHECK(memcmp(ls_str_cstr(pFive), "applegr", 7) == 0);

    ls_str_t *pSix = ls_str_xnew("applegr", 7, pool);
    ls_str_t pSeven;
    ls_str_x(&pSeven, "applegr", 7, pool);
    ls_str_t pEight;
    CHECK(ls_str_xcopy(&pEight, &pSeven, pool) != NULL);
    CHECK(memcmp(ls_str_cstr(pFive), ls_str_cstr(pSix), 7) == 0);
    CHECK(memcmp(ls_str_cstr(pSix), ls_str_cstr(&pSeven), 7) == 0);
    CHECK(memcmp(ls_str_cstr(pSix), ls_str_cstr(&pEight), 7) == 0);


    ls_str_xdelete(pFive, pool);
    ls_str_xdelete(pSix, pool);
    ls_str_xd(&pSeven, pool);
    ls_str_xd(&pEight, pool);
    ls_xpool_delete(pool);
}
/*
TEST( test_ls_strhashtest )
{
    const char  *test1 = "I Want A Hash Function\0For This String.",
                *test2 = "Perhaps\\There?Is/Something*Missing{That}This$Will%Test.";
    int test1_len = 22,
        test2_len = 55;
    int reg_res, ls_res;
    ls_str_t str;
    printf( "Start LSR Str Hash Test\n" );

    ls_str( &str, test1, test1_len );

    reg_res = ls_hash_hash_string( ls_str_buf( &str ) );
    ls_res = ls_str_hf( &str );
    printf( "Reg res: %d, Lsr res: %d\n", reg_res, ls_res );
    CHECK( reg_res - ls_res == 0 );

    reg_res = ls_hash_cistring( ls_str_buf( &str ) );
    ls_res = ls_str_hfci( &str );
    printf( "Reg res: %d, Lsr res: %d\n", reg_res, ls_res );
    CHECK( reg_res - ls_res == 0 );

    ls_str( &str, test2, test2_len );

    reg_res = ls_hash_hash_string( ls_str_buf( &str ) );
    ls_res = ls_str_hf( &str );
    printf( "Reg res: %d, Lsr res: %d\n", reg_res, ls_res );
    CHECK( reg_res - ls_res == 0 );

    reg_res = ls_hash_cistring( ls_str_buf( &str ) );
    ls_res = ls_str_hfci( &str );
    printf( "Reg res: %d, Lsr res: %d\n", reg_res, ls_res );
    CHECK( reg_res - ls_res == 0 );
}
*/




#endif
