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
#ifndef CACHEOS_H
#define CACHEOS_H



class IOVec;

class CacheOS
{
public:
    CacheOS() {}
    virtual ~CacheOS() {}
    //        pRet return total bytes written to output stream
    // return -1 if error occure
    //        other total bytes cached and written to output stream

    virtual int cacheWrite(const char *pBuf, int size,
                           int *pRet = 0) = 0;
    virtual int cacheWritev(IOVec &vector, int total,
                            int *pRet = 0) = 0;
    virtual bool canHold(int size) = 0;

};
#endif
