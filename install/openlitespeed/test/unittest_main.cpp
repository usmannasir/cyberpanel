/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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

#include "unittest-cpp/UnitTest++.h"

#include <util/vmembuf.h>
#include <http/httplog.h>
#include <lsiapi/lsiapihooks.h>

#include <unistd.h>

char *argv0 = NULL;
// char *pServerRoot = NULL;
// void set_server_root()
// {
//     char achServerRoot[1024];
//     if (*argv0 != '/')
//     {
//         getcwd(achServerRoot, sizeof(achServerRoot) - 1);
//         strcat(achServerRoot, "/" );
//     }
//     else
//         achServerRoot[0] = 0;
//     strncat(achServerRoot, argv0,
//             sizeof(achServerRoot) -1 - strlen(achServerRoot));
//     const char *pEnd = strrchr(achServerRoot, '/');
//     --pEnd;
//     while (pEnd > achServerRoot && *pEnd != '/')
//         --pEnd;
//     --pEnd;
//     while (pEnd > achServerRoot && *pEnd != '/')
//         --pEnd;
//     ++pEnd;
// 
//     strcpy(&achServerRoot[pEnd - achServerRoot], "test/serverroot");
//     pServerRoot = strdup(achServerRoot);
// }


int main(int argc, char *argv[])
{
    argv0 = argv[0];

    VMemBuf::initAnonPool();
    umask(022);
    HttpLog::init();
    LsiApiHooks::initGlobalHooks();

    UnitTest::RunAllTests();
    return 0;
}
