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

#include "httprequestlinetest.h"
#include <http/httpmethod.h>
// #include <http/httpver.h>
// #include <http/httpstatuscode.h>
#include <stdio.h>
#include "unittest-cpp/UnitTest++.h"



TEST(HttpRequestLineTest_test)
{
    const char *s_psMethod[] =
    {
        "UNKNOWN",
        "OPTIONS ",
        "GET \t",
        "HEAD\t",
        "POST  ",
        "PUT\t\t",
        "DELETE \t ",
        "TRACE\t \t",
        "CONNECT ",
        "MOVE "
    };

    const char *s_psMethodBad[] =
    {
        "UNKNOWN",
        "OPTIONS23",
        "GETa",
        "HEADd",
        "POSb",
        "PUTw",
        "DELTE",
        " TRACE\n",
        "CONNECT2",
        " MOVE"
    };
    int i;
    for (i = 0; i < 10; i++)
    {
        //printf( "i=%d\n", i );
        CHECK(i == HttpMethod::parse(s_psMethod[i]));
    }
    //CHECK( 0 == reqline.setMethod( s_psMethod[0] ) );
    for (i = 1; i < 10; i++)
        CHECK(0 == HttpMethod::parse(s_psMethodBad[i]));
//    const char * pV1 = "HTTP/1.1";
//    const char * pV2 = "HTTP/1.0";
//    const char * pV3 = "HTTP/11.20";
//    CHECK( HTTP_1_1 == HttpVer::parse( pV1 ));
//    CHECK( HTTP_1_0 == HttpVer::parse( pV2 ));
//    CHECK( SC_505 == HttpVer::parse( pV3 ));
//
//    const char * pV1Bad = "HTTP / 1.1";
//    CHECK( SC_505 == HttpVer::parse( pV1Bad ));

}

#endif
