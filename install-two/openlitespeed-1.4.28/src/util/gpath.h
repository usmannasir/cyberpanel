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
#ifndef GPATH_H
#define GPATH_H



#include <stddef.h>

struct stat;
class GPath
{
    GPath() {};
    ~GPath() {};
public:
    static int getAbsolutePath(char *dest, size_t size,
                               const char *relativeRoot, const char *path);
    static int getAbsoluteFile(char *dest, size_t size,
                               const char *relativeRoot, const char *file);
    static int concat(char *dest, size_t size, const char *pRoot,
                      const char *pAppend);
    static int clean(char *path);
    static int clean(char *path, int len);
    static bool isValid(const char *path);
    static bool isWritable(const char *path);
    static bool hasSymLinks(char *path, char *pEnd, char *pStart);
    static int  checkSymLinks(char *path, char *pEnd, const char *pathBufEnd,
                              char *pStart, int getRealPath, int *hasLink = NULL);
    static bool isChanged(struct stat *stNew, struct stat *stOld);
    static int  readFile(char *pBuf, int bufLen, const char *pName,
                         const char *pBase = NULL);
    static int  writeFile(const char *pBuf, int bufLen, const char *pName,
                          int mode = 0644, const char *pBase = NULL);
    static int  createMissingPath(char *pBuf, int mode = 0755);

    static int  initReadLinkCache();
    static void clearReadLinkCache();

};

#endif
