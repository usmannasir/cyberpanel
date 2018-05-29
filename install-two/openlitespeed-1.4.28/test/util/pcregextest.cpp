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

#include "pcregextest.h"

#include <util/pcregex.h>
#include "unittest-cpp/UnitTest++.h"

#include <string.h>

SUITE(PcregexTest)
{
    TEST(test)
    {
        Pcregex reg;
        char achSub1[] = "/some/dir/abc.gif";
        char achSub2[] = "/some/dir/abc.jpg";
        int vector[30];
        int find;
        CHECK(reg.compile("/(.*)\\.gif", 0) == 0);
        find = reg.exec(achSub1 , sizeof(achSub1) - 1 , 0, 0, vector, 30);
        CHECK(find == 2);
        CHECK(vector[0] == 0);
        CHECK(vector[1] == sizeof(achSub1) - 1);
        CHECK(vector[2] == 1);
        CHECK(vector[3] == sizeof(achSub1) - 5);
        find = reg.exec(achSub2, sizeof(achSub2) - 1, 0, 0, vector, 30);
        CHECK(find == PCRE_ERROR_NOMATCH);
    }

    TEST(testRegSub)
    {
        Pcregex reg;
        int vector[30];
        int find;
        char achSub1[] = "/abcdefghijklmnopqrst";
        CHECK(reg.compile("/(a)(b)(c)(d)(e)(f)(g)(h)(i)(j)(k).*", 0) == 0);
        find = reg.exec(achSub1, sizeof(achSub1) - 1, 0, 0, vector, 30);
        CHECK(find == 0);
        find = 10;


        RegSub regsub1, regsub2, regsub3;
        CHECK(regsub1.compile("/$9_$8_$7_$6_$5$4$3$2$1$0") == 0);
        CHECK(regsub2.compile("/\\$$9\\&$8_$7_$11_&") == 0);

        char expect1[] = "/i_h_g_f_edcba/abcdefghijklmnopqrst";
        char expect2[] = "/$i&h_g_a1_/abcdefghijklmnopqrst";
        char result[200];
        int len = sizeof(expect1);
        int ret = regsub1.exec(achSub1, vector, find, result, len);
        CHECK(ret == 0);
        CHECK(strcmp(result, expect1) == 0);
        CHECK(len == sizeof(expect1) - 1);

        len = sizeof(expect1) - 1;
        ret = regsub1.exec(achSub1, vector, find, result, len);
        CHECK(ret == -1);
        CHECK(len == sizeof(expect1) - 1);


        len = 200;
        ret = regsub2.exec(achSub1, vector, find, result, len);
        CHECK(ret == 0);
        CHECK(strcmp(result, expect2) == 0);
        CHECK(len == sizeof(expect2) - 1);


    }
}

#endif
