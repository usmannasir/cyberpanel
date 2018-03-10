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


#include "coresockettest.h"
#include <socket/gsockaddr.h>
#include "unittest-cpp/UnitTest++.h"


class Tester : public CoreSocket
{
public:
    Tester(int domain, int type, int protocol)
        : CoreSocket(domain, type, protocol)
    {}
    Tester(int fd)
        : CoreSocket(fd)
    {}
    ~Tester() {}
};

TEST(CoreSocketTest_testConstructors)
{
    Tester sock1(PF_INET, SOCK_STREAM, 0);
    Tester sock2(sock1.getfd());
    CHECK(-1 != sock1.getfd());
    CHECK(sock1.getfd() == sock2.getfd());
    GSockAddr name1(PF_INET);
    socklen_t namelen1 = name1.len();
    GSockAddr name2(PF_INET);
    socklen_t namelen2 = name2.len();
    CHECK(0 == sock1.getSockName(name1.get(), &namelen1));
    CHECK(0 == sock2.getSockName(name2.get(), &namelen2));
    //CHECK( 0 == memcmp( &name1, &name2, sizeof( IPv4SockAddr ) ));
    CHECK(sock1.close() == 0);
    CHECK(sock2.close() == -1);
    CHECK(errno == EBADF);
}
// void CoreSocketTest::testBind()
// {
//     Tester sock1( PF_INET, SOCK_STREAM, 0 );
//     unsigned short port = 3452;
//     in_addr_t addr = 0;
//     sock1.setReuseAddr(1);
//     CHECK( sock1.bind( addr, port ) == 0 );
//     Tester sock2( PF_INET, SOCK_STREAM, 0 );
//     //sock2.setReuseAddr(1);
//     CHECK( sock2.bind( addr, port ) == -1 );
//     CHECK( errno == EADDRINUSE );
// }

#endif

