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

#include "httpvhostlisttest.h"

#include <http/httpvhostlist.h>
#include <http/httpvhost.h>
#include "unittest-cpp/UnitTest++.h"


TEST(HttpVHostListTest_test)
{
    HttpVHostMap list;
    HttpVHost *pHost1 = new HttpVHost("host1");
    HttpVHost *pHost2 = new HttpVHost("host2");
    CHECK(list.add(pHost1) == 0);
    CHECK(list.add(pHost2) == 0);
    HttpVHost *p1 = list.get("host1");
    CHECK(p1 != NULL);
    CHECK(p1 == pHost1);
    CHECK(list.get("host2") == pHost2);
    CHECK(list.get("host3") == NULL);
    // add again will fail
    CHECK(list.add(pHost1) != 0);

    CHECK(list.remove(p1) == 0);
    CHECK(list.get("host1") == NULL);
    //CHECK( list.remove( p1 ) == 0 );
}

#endif

