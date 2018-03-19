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

#include "hostinfotest.h"
// #include <socket/gsockaddr.h>
#include <stdio.h>
#include <string.h>
#include "unittest-cpp/UnitTest++.h"



hostent *getHostByName(const char *hostname)
{
    return ::gethostbyname(hostname);
}


void testOne(const hostent *h0)
{
    printf("start HostInfoTest::TestOne\n");
    CHECK(h0 != NULL);
    HostInfo h1 = *h0 ;
    printf("h_name = %s (%s)\n", h0->h_name, h1.h_name);
    CHECK(0 == strcmp(h0->h_name, h1.h_name));
    char **a0 = h0->h_aliases;
    char **a1 = h1.h_aliases;
    int i = 0;
    while (*a0 != NULL)
    {
        CHECK(*a1 != NULL);
        CHECK(0 == strcmp(*a0, *a1));
        printf(" alias %d %s (%s)\n", i, *a0, *a1);
        a0 ++;
        a1 ++;
        i ++;
    }
    CHECK(*a1 == NULL);
    CHECK(h0->h_addrtype == h1.h_addrtype);
    CHECK(h0->h_length == h1.h_length);

    a0 = h0->h_addr_list;
    a1 = h1.h_addr_list;
    i = 0;
    while (*a0 != NULL)
    {
        CHECK(*a1 != NULL);
        CHECK(0 == memcmp(*a0, *a1, h0->h_length));
        printf(" addr_list %d %s (%s)\n", i, inet_ntoa(*((in_addr *)*a0)),
               inet_ntoa(*((in_addr *)*a1)));
        a0 ++;
        a1 ++;
        i ++;
    }
    CHECK(*a1 == NULL);

}


TEST(HostInfoTest_testAll)
{
    testOne(getHostByName("localhost"));
    HostInfo h;
    //bool b = h.getHostByName("w.a.com");
    //CHECK(b==false);
//    GSockAddr a0("127.0.0.1");
//    b = h.getHostByAddr(&a0);
//    CHECK(b == true);

}
#endif
