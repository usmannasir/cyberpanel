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

#include "httpbuftest.h"
#include <util/autobuf.h>
#include "unittest-cpp/UnitTest++.h"


TEST(HttpBufTest_test)
{
    AutoBuf buf;
    CHECK(0 == buf.size());
    CHECK(0 < buf.capacity());
    CHECK(0 == buf.reserve(0));
    CHECK(0 == buf.capacity());

    // this is not true on Solaris 8, sparc platform.
    //CHECK( NULL == buf.begin() );
    //CHECK( NULL == buf.end() );

    CHECK(0 == buf.reserve(1024));
    CHECK(1024 == buf.capacity());
    CHECK(0 == buf.grow(1));
    CHECK(1024 < buf.capacity());
    CHECK(0 == buf.size());
    buf.used(10);
    CHECK(10 == buf.size());
    buf.used(10);
    CHECK(20 == buf.size());
    buf.resize(15);
    CHECK(15 == buf.size());

    CHECK(buf.size() == buf.end() - buf.begin());
    CHECK(10 == buf.getp(10) - buf.begin());
    CHECK(buf.available() == buf.capacity() - buf.size());
    buf.clear();
    CHECK(0 == buf.size());
    const char *pStr = "Test String";

    CHECK((int)strlen(pStr) == buf.append(pStr, strlen(pStr)));
    CHECK(buf.size() == (int)strlen(pStr));
    CHECK(0 == strncmp(pStr, buf.begin(), strlen(pStr)));

}

#endif
