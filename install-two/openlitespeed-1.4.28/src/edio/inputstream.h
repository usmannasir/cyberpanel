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
#ifndef INPUTSTREAM_H
#define INPUTSTREAM_H


#include <stddef.h>
struct iovec;
class InputStream
{
public:
    InputStream() {};
    virtual ~InputStream() {};
    virtual int read(char *pBuf, int size) = 0;
    virtual int readv(struct iovec *vector, size_t count) = 0;
};
class CacheableIS : public InputStream
{
public:
    virtual int cacheInput(int iPreferredLen = -1) = 0;
    virtual int readLine(char *pBuf, int size) = 0;
};

class UnreadableIS : public CacheableIS
{
public:
    virtual int unread(const char *pBuf, int size) = 0;
};
#endif
