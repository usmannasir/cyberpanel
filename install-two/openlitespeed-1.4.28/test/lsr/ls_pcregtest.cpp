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

#include <lsr/ls_pcreg.h>
#include <string.h>
#include "unittest-cpp/UnitTest++.h"



TEST(ls_pcregextest_test)
{
    ls_pcre_t *reg = ls_pcre_new();
    char achSub1[] = "/some/dir/abc.gif";
    char achSub2[] = "/some/dir/abc.jpg";
    int vector[30];
    int find;
    CHECK(ls_pcre_compile(reg, "/(.*)\\.gif", 0, 0, 0) == 0);
    find = ls_pcre_exec(reg, achSub1 , sizeof(achSub1) - 1 , 0, 0, vector, 30);
    CHECK(find == 2);
    CHECK(vector[0] == 0);
    CHECK(vector[1] == sizeof(achSub1) - 1);
    CHECK(vector[2] == 1);
    CHECK(vector[3] == sizeof(achSub1) - 5);
    find = ls_pcre_exec(reg, achSub2, sizeof(achSub2) - 1, 0, 0, vector, 30);
    CHECK(find == PCRE_ERROR_NOMATCH);
    ls_pcre_delete(reg);
}

TEST(ls_pcregex_regsub_test)
{
    ls_pcre_t *reg = ls_pcre_new();
    int vector[30];
    int find;
    char achSub1[] = "/abcdefghijklmnopqrst";
    CHECK(ls_pcre_compile(reg, "/(a)(b)(c)(d)(e)(f)(g)(h)(i)(j)(k).*", 0, 0,
                          0) == 0);
    find = ls_pcre_exec(reg, achSub1, sizeof(achSub1) - 1, 0, 0, vector, 30);
    CHECK(find == 0);
    find = 10;


    ls_pcresub_t regsub1,
                 *regsub2 = ls_pcresub_new(),
                  *regsub3 = ls_pcresub_new();
    ls_pcre_sub(&regsub1);
    CHECK(ls_pcresub_compile(&regsub1, "/$9_$8_$7_$6_$5$4$3$2$1$0") == 0);
    CHECK(ls_pcresub_compile(regsub2, "/\\$$9\\&$8_$7_$11_&") == 0);

    char expect1[] = "/i_h_g_f_edcba/abcdefghijklmnopqrst";
    char expect2[] = "/$i&h_g_a1_/abcdefghijklmnopqrst";
    char result[200];
    int len = sizeof(expect1);
    int ret = ls_pcresub_exec(&regsub1, achSub1, vector, find, result, &len);
    CHECK(ret == 0);
    CHECK(strcmp(result, expect1) == 0);
    CHECK(len == sizeof(expect1) - 1);

    len = sizeof(expect1) - 1;
    ret = ls_pcresub_exec(&regsub1, achSub1, vector, find, result, &len);
    CHECK(ret == -1);
    CHECK(len == sizeof(expect1) - 1);


    len = 200;
    ret = ls_pcresub_exec(regsub2, achSub1, vector, find, result, &len);
    CHECK(ret == 0);
    CHECK(strcmp(result, expect2) == 0);
    CHECK(len == sizeof(expect2) - 1);

    ls_pcresub_d(&regsub1);
    ls_pcresub_delete(regsub2);
    ls_pcresub_delete(regsub3);
    ls_pcre_delete(reg);
}


#endif
