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
#ifndef HTTPVER_H
#define HTTPVER_H

#include <lsdef.h>

#include <assert.h>
#include <inttypes.h>
#include <sys/types.h>

#define HTTP_1_1 0
#define HTTP_1_0 1
#define HTTP_MAX_VER    1

typedef int http_ver_t;

class HttpVer
{
    static const char *const s_sHttpVer[2];
    HttpVer();
    ~HttpVer();
public:
    static const char *getVersionString(http_ver_t ver)
    {
        //assert(( ver >= HTTP_1_1 )&&( ver <= HTTP_0_9 ));
        return s_sHttpVer[ver];
    }
    static inline int getVersionStringLen(http_ver_t ver)
    {   return 8;   }
    LS_NO_COPY_ASSIGN(HttpVer);
};

#endif
