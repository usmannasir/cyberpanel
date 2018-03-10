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

#include "denieddirtest.h"
#include <http/denieddir.h>
#include "unittest-cpp/UnitTest++.h"


TEST(DeniedDirTest_runTest)
{
    DeniedDir instance;
    instance.addDir("/etc/*");
    instance.addDir("/home/gwang/projects/httpd/dist/conf/*");
    CHECK(instance.addDir("/") == 0);
    instance.isDenied("/home/gwang/projects/httpd/dist/vhosts/example/html/");

    CHECK(instance.addDir("/usr/*") == 0);
    CHECK(instance.addDir("/home/lsong") == 0);
    CHECK(instance.addDir("/sbin/*") == 0);
    CHECK(instance.addDir("/home/lsong/*") == 0);
    CHECK(instance.addDir("/home/lsong/*") == 0);
    CHECK(instance.addDir("/opt/jdk/bin") == 0);
    CHECK(instance.addDir("/opt/jdk/lib/*") == 0);
    CHECK(instance.addDir("/bin/*") == 0);
    CHECK(instance.isDenied("/bin/ls") == true);
    CHECK(instance.isDenied("/bin/local/") == true);
    CHECK(instance.isDenied("/opt/jdk/bin/") == true);
    CHECK(instance.isDenied("/opt/") == false);
    CHECK(instance.isDenied("/opt/jdk") == false);
    CHECK(instance.isDenied("/opt/jdk/") == false);
    CHECK(instance.isDenied("/opt/jdk/bin") == false);
    CHECK(instance.isDenied("/opt/jdk/lib/") == true);
    CHECK(instance.isDenied("/opt/jdk/lib/m") == true);
    CHECK(instance.isDenied("/opt/jdk/lib/m/") == true);
    CHECK(instance.isDenied("/home/") == false);
    CHECK(instance.isDenied("/home/lsong/") == true);
    CHECK(instance.isDenied("/home/lsong/ab/c/") == true);
}

#endif

