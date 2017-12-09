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

#include "datetimetest.h"

#include <util/datetime.h>
#include <stdio.h>
#include <time.h>
#include <string.h>
#include "unittest-cpp/UnitTest++.h"


TEST(DateTimeTest_testHttpTime)
{
    const char *date1 = "Fri, 03 May 2002 14:06:20 GMT";
    const char *date2 = "Friday, 03-May-02 14:06:20 GMT";
    const char *date3 = "Fri May  3 14:06:20 2002";
    //const char* logGMT   = "[03/May/2002:14:06:20 +0000] \"";
    time_t t1 = DateTime::parseHttpTime(date1);
    CHECK(t1 != 0);
    long t2 = DateTime::parseHttpTime(date2);
    CHECK(t2 != 0);
    long t3 = DateTime::parseHttpTime(date3);
    CHECK(t3 != 0);
    CHECK(t1 == t2);
    CHECK(t1 == t3);
    char achBuf[50];
    CHECK(NULL != DateTime::getRFCTime(t1, achBuf));
    CHECK(strcmp(achBuf, date1) == 0);
    //CHECK( NULL != DateTime::getLogTime( t1, achBuf, 1 ) );
    //printf( "%s\n", achBuf );
    //CHECK( strcmp( achBuf, logGMT ) == 0 );
    CHECK(NULL != DateTime::getLogTime(t1, achBuf, 0));
    char achLocal[50];
    achLocal[0] = '[';
    struct tm local;
    localtime_r(&t1, &local);
    strftime(achLocal + 1, 30, "%d/%b/%Y:%H:%M:%S", &local);
#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
    char *p = achLocal + strlen(achLocal);

    //NOTE: tm_gmtoff is not available on some system
    int timezone = local.tm_gmtoff / 60;
    char ch = (timezone < 0) ? '-' : '+';
    timezone = (timezone >= 0) ? timezone : -timezone;
    sprintf(p, " %c%04d] \"", ch, timezone / 60 * 100 + timezone % 60);
    //printf( "%s\n", achLocal );
    CHECK(strcmp(achBuf, achLocal) == 0);

#endif //defined( linux )

    date1 = "Fri,   03 May 2002  23:59:59   GMT";
    date2 = "Friday,    03-May-02   23:59:59    GMT";
    date3 = "Fri May   3   23:59:59   2002  ";
    t1 = DateTime::parseHttpTime(date1);
    CHECK(t1 != 0);
    t2 = DateTime::parseHttpTime(date2);
    CHECK(t2 != 0);
    t3 = DateTime::parseHttpTime(date3);
    CHECK(t3 != 0);
    CHECK(t1 == t2);
    CHECK(t1 == t3);

    date1 = "Fri,   03 May 2002  00:00:00   GMT";
    date2 = "Friday,    03-May-02   00:00:00    GMT";
    date3 = "Fri May   3   00:00:00   2002\n";
    t1 = DateTime::parseHttpTime(date1);
    CHECK(t1 != 0);
    t2 = DateTime::parseHttpTime(date2);
    CHECK(t2 != 0);
    t3 = DateTime::parseHttpTime(date3);
    CHECK(t3 != 0);
    CHECK(t1 == t2);
    CHECK(t1 == t3);

    date1 = "Fri,   29 Feb 2002  14:06:20   GMT";
    date2 = "Friday,    03-May-02   24:00:00    GMT";
    date3 = "Fri May   3   14:60:20   2002  ";
    t1 = DateTime::parseHttpTime(date1);
    CHECK(t1 == 0);
    t2 = DateTime::parseHttpTime(date2);
    CHECK(t2 == 0);
    t3 = DateTime::parseHttpTime(date3);
    CHECK(t3 == 0);

    date1 = "Fri,   3 May 2002  14:06:60   GMT";
    date2 = "Friday,   -3-May-02   00:00:00    GMT";
    date3 = "Fri,   3-May 2002  14:58:20   GMT";

    t1 = DateTime::parseHttpTime(date1);
    CHECK(t1 == 0);
    t2 = DateTime::parseHttpTime(date2);
    CHECK(t2 == 0);
    t3 = DateTime::parseHttpTime(date3);
    CHECK(t3 == 0);

    t1 = time(NULL);
    date1 = asctime(gmtime(&t1));
    t2 = DateTime::parseHttpTime(date1);
    CHECK(t2 != 0);
    //printf( "t1 = %ld, t2 = %ld, t1 - t2 = %ld\n", t1, t2, t1 - t2 );
    CHECK(t1 == t2);

}

#endif


