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

#include "expirestest.h"

#include <http/expiresctrl.h>
#include "unittest-cpp/UnitTest++.h"


TEST(ExpiresTest_test)
{
    ExpiresCtrl exp1;
    int ret;
    ret = exp1.parse("A3600");
    CHECK(ret != -1);
    CHECK(exp1.getBase() == EXPIRES_ACCESS);
    CHECK(exp1.getAge() == 3600);


    ret = exp1.parse("a3601");
    CHECK(ret != -1);
    CHECK(exp1.getBase() == EXPIRES_ACCESS);
    CHECK(exp1.getAge() == 3601);

    ret = exp1.parse("m3600");
    CHECK(ret != -1);
    CHECK(exp1.getAge() == 3600);
    CHECK(exp1.getBase() == EXPIRES_MODIFY);


    ret = exp1.parse("M3601");
    CHECK(ret != -1);
    CHECK(exp1.getAge() == 3601);
    CHECK(exp1.getBase() == EXPIRES_MODIFY);

    ret = exp1.parse("m 3600");
    CHECK(ret == -1);

    ret = exp1.parse("Access plus 1 year 1 month 1 week 1 day 1 hour 1 minutes 1 second");
    CHECK(ret != -1);
    CHECK(exp1.getBase() == EXPIRES_ACCESS);
    CHECK(exp1.getAge() == 3600 * ((365 + 30 + 7 + 1) * 24 + 1) + 60 + 1);

    ret = exp1.parse("'Now 1 year 1 month 1 week 1 day 1 hour 1 minutes 1 second'");
    CHECK(ret != -1);
    CHECK(exp1.getBase() == EXPIRES_ACCESS);
    CHECK(exp1.getAge() == 3600 * ((365 + 30 + 7 + 1) * 24 + 1) + 60 + 1);

    ret = exp1.parse("\"MODIFICATION 2 year 2 month 2 week 2 day 2 hour 2 minutes 2 second\"");
    CHECK(ret != -1);
    CHECK(exp1.getBase() == EXPIRES_MODIFY);
    CHECK(exp1.getAge() == (3600 * ((365 + 30 + 7 + 1) * 24 + 1) + 60 + 1) *
          2);

}


#endif



