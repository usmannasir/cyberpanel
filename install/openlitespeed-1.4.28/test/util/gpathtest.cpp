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

#include "gpathtest.h"
#include <util/gpath.h>

#include <string.h>
#include <unistd.h>
#include "unittest-cpp/UnitTest++.h"



TEST(GPathTest_test)
{
    char buf[256];
    char *pBufEnd = &buf[256];
    strcpy(buf, "/b/./");
    CHECK(GPath::clean(buf) == 0);
    CHECK(strcmp(buf, "/b/") == 0);

    strcpy(buf, "//home/user//a/b/./");
    CHECK(GPath::clean(buf) == 0);
    CHECK(strcmp(buf, "/home/user/a/b/") == 0);

    strcpy(buf, "//home/user//a/b/./...");
    CHECK(GPath::clean(buf) == 0);
    CHECK(strcmp(buf, "/home/user/a/b/...") == 0);

//    strcpy( buf, "/examples/../examples/../../../../index.html" );
//    GPath::clean( buf );
//    //CHECK( GPath::clean( buf ) == 0 );
//    CHECK( strcmp( buf, "/../../../index.html" ) == 0 );

    strcpy(buf, "//home/user//a/b/./../c");
    CHECK(GPath::clean(buf) == 0);
    CHECK(strcmp(buf, "/home/user/a/c") == 0);

    strcpy(buf, "/home/user/a/b/./../../proj/httpd/httpd/wwwroot/../../");
    CHECK(GPath::clean(buf) == 0);
    CHECK(strcmp(buf, "/home/user/proj/httpd/") == 0);

    strcpy(buf, "///path//path1////path3 path4/../../../");
    CHECK(GPath::clean(buf) == 0);
    CHECK(strcmp(buf, "/") == 0);

    CHECK(GPath::getAbsolutePath(buf, 256, "/home/user/proj/httpd",
                                 "httpd/wwwroot/conf") == 0);
    CHECK(strcmp(buf, "/home/user/proj/httpd/httpd/wwwroot/conf/") == 0);

    CHECK(GPath::getAbsolutePath(buf, 256, "/home/user/proj/httpd/",
                                 "/httpd/wwwroot/conf") == 0);
    CHECK(strcmp(buf, "/httpd/wwwroot/conf/") == 0);

    CHECK(GPath::getAbsolutePath(buf, 256,
                                 "/home/user/proj/httpd/httpd/wwwroot/conf",
                                 "./../../vh/conf") == 0);
    CHECK(strcmp(buf, "/home/user/proj/httpd/httpd/vh/conf/") == 0);

    CHECK(GPath::getAbsoluteFile(buf, 256,
                                 "/home/user/proj/httpd/httpd/serverroot/",
                                 "conf/mime.properties") == 0);
    CHECK(strcmp(buf,
                 "/home/user/proj/httpd/httpd/serverroot/conf/mime.properties") == 0);

    char curPath[1024] = {0};
    getcwd(curPath, sizeof(curPath));

    strcpy(buf, curPath);
    strcat(buf, "/serverroot/wwwroot/index.html");
    GPath::checkSymLinks(buf, buf + strlen(buf), pBufEnd, buf, 0);
//    CHECK( n == -1 );

//     char * p = getcwd( buf, 256 );
//     strcat( buf, "/serverroot/" );
//     char * pEnd = p + strlen( p );
//     char buf2[256];
//     strcat( pEnd, "wwwroot/small_symlink.html" );
//     strcpy( buf2, "./small.html" );
//     symlink( buf2, buf );
//     strcpy( buf2, buf );
//     strcpy( &buf2[pEnd - buf], "wwwroot/small.html" );
//
//     bool ret = GPath::hasSymLinks( buf, buf + strlen( buf ), pEnd );
//     CHECK( ret == true );
//     n = GPath::checkSymLinks( buf, buf + strlen( buf ), pBufEnd, pEnd, 0);
//     CHECK( n == -1 );
//     CHECK( strcmp( pEnd, "wwwroot/small_symlink.html" ) == 0 );
//     n = GPath::checkSymLinks( buf, buf + strlen( buf ), pBufEnd, pEnd, 1 );
//     CHECK( n == (int)strlen( buf2 ) );
//     CHECK( strcmp( buf2, buf ) == 0 );
//
//     strcpy( pEnd, "wwwroot/small_symlink.html" );
//     n = GPath::checkSymLinks( buf, buf + strlen( buf ), pBufEnd, pEnd, 2 );
//     CHECK( n == (int)strlen( buf2 ) );
//     CHECK( strcmp( buf2, buf ) == 0 );
//
//
//     strcpy( pEnd, "root_sym" );
//     strcpy( buf2, "///" );
//     symlink( buf2, buf );
//     strcpy( buf2, buf );
//     n = GPath::checkSymLinks( buf, buf + strlen( buf ), pBufEnd, pEnd, 1 );
//     CHECK( n == 1 );
//     CHECK( strcmp( "/", buf ) == 0 );
//
//     strcpy( buf, buf2 );
//     strcpy( pEnd, "root_sym" );
//     n = GPath::checkSymLinks( buf, buf + strlen( buf ), pBufEnd, pEnd, 2 );
//     CHECK( n == -1 );
//     CHECK( strcmp( "/", buf ) == 0 );
//
//     strcpy( buf, buf2 );
//     strcpy( pEnd, "root_sym///" );
//     n = GPath::checkSymLinks( buf, buf + strlen( buf ), pBufEnd, pEnd, 1 );
//     CHECK( n == 1 );
//     CHECK( strcmp( "/", buf ) == 0 );
//
//     strcpy( buf, buf2 );
//     strcpy( pEnd, "root_sym///usr//" );
//     n = GPath::checkSymLinks( buf, buf + strlen( buf ), pBufEnd, pEnd, 1 );
//     CHECK( n == 5 );
//     CHECK( strcmp( "/usr/", buf ) == 0 );
//
//     strcpy( buf, buf2 );
//     strcpy( pEnd, "root_sym///usr//" );
//     n = GPath::checkSymLinks( buf, buf + strlen( buf ), pBufEnd, pEnd, 2 );
//     CHECK( n == -1 );
//     //CHECK( strcmp( "/", buf ) == 0 );
//
//     strcpy( buf, buf2 );
//     strcpy( pEnd, "parent_to_root_sym" );
//     strcpy( buf2, ".././../../../../../../../.." );
//     symlink( buf2, buf );
//     strcpy( buf2, buf );
//     n = GPath::checkSymLinks( buf, buf + strlen( buf ), pBufEnd, pEnd, 1 );
//     CHECK( n == 1 );
//     CHECK( strcmp( "/", buf ) == 0 );
//
//     strcpy( buf, buf2 );
//     strcpy( pEnd, "wwwroot/parent_sym" );
//     strcpy( buf2, "..//." );
//     symlink( buf2, buf );
//     strcpy( buf2, buf );
//     n = GPath::checkSymLinks( buf, buf + strlen( buf ), pBufEnd, pEnd, 1 );
//     CHECK( n == pEnd - buf );
//     CHECK( strncmp( buf2, buf, n ) == 0 );
//
//
//     strcpy( buf, buf2 );
//     strcpy( pEnd, "home_sym" );
//     strcpy( buf2, "/home" );
//     symlink( buf2, buf );
//     strcpy( buf2, buf );
//     strcpy( pEnd, "//home_sym////gwang" );


//     n = GPath::checkSymLinks( buf, buf + strlen( buf ), pBufEnd, pEnd, 1 );
//     CHECK( n == 11 );
//     CHECK( strcmp( "/home/gwang", buf ) == 0 );
//
//     strcpy( buf, buf2 );
//     strcpy( pEnd, "//home_sym////gwang" );
//
//     n = GPath::checkSymLinks( buf, buf + strlen( buf ), pBufEnd, pEnd, 2 );
//     CHECK( n == -1 );
//     CHECK( strcmp( "/home/gwang", buf ) == 0 );
//
//     strcpy( buf, buf2 );
//     strcpy( pEnd, "//home_sym////gwang///" );
//
//     n = GPath::checkSymLinks( buf, buf + strlen( buf ), pBufEnd, pEnd, 1 );
//     CHECK( n == 12 );
//     CHECK( strcmp( "/home/gwang/", buf ) == 0 );
//
//     strcpy( buf, buf2 );
//     strcpy( pEnd, "home_sym_sym" );
//     strcpy( buf2, "home_sym" );
//     symlink( buf2, buf );
//     strcpy( buf2, buf );
//     strcpy( pEnd, "/home_sym_sym////gwang/." );
//
//     n = GPath::checkSymLinks( buf, buf + strlen( buf ), pBufEnd, pEnd, 1 );
//     CHECK( n == 12 );
//     CHECK( strcmp( "/home/gwang/", buf ) == 0 );
//
//     strcpy( buf, buf2 );
//     strcpy( pEnd, "/home_sym_sym////gwang/.." );
//
//     n = GPath::checkSymLinks( buf, buf + strlen( buf ), pBufEnd, pEnd, 1 );
//     CHECK( n == 6 );
//     CHECK( strcmp( "/home/", buf ) == 0 );
//
//     strcpy( buf, buf2 );
//     strcpy( pEnd, "home_sym_sym" );
//     unlink( buf );
//     strcpy( pEnd, "home_sym" );
//     unlink( buf );
//     strcpy( pEnd, "wwwroot/parent_sym" );
//     unlink( buf );
//     strcpy( pEnd, "parent_to_root_sym" );
//     unlink( buf );
//     strcpy( pEnd, "root_sym" );
//     unlink( buf );
//     strcpy( pEnd, "wwwroot/small_symlink.html" );
//     unlink( buf );
//
//
//
//     strcpy( buf, buf2 );
//     *pEnd = 0;
//     strcpy( buf2, buf );
//     strcpy( pEnd, "wwwroot/test" );
//     strcat( buf2, "wwwroot/test_symlink" );
//     symlink( buf, buf2 );
//     strcat( pEnd, "/index.html" );
//     strcat( buf2, "/index.html" );
//     ret = GPath::hasSymLinks( buf, buf + strlen( buf ), pEnd);
//     CHECK( ret == false );
//     ret = GPath::hasSymLinks( buf2, buf2 + strlen( buf2 ), buf2 + (pEnd - buf) );
//     CHECK( ret == true );
//     strcpy( pEnd, "wwwroot/test_symlink" );
//     unlink( buf );


}

#endif
