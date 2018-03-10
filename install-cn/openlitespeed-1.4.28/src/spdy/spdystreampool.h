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
#ifndef SPDYSTREAMPOOL_H
#define SPDYSTREAMPOOL_H
#include <util/objpool.h>
#include <util/dlinkqueue.h>
#include <lsdef.h>

class SpdyStream;
typedef ObjPool<SpdyStream>       Pool;
class SpdyStreamPool : public ObjPool<SpdyStream>
{
    static Pool s_pool;
    SpdyStreamPool();
    ~SpdyStreamPool();

public:
    static void recycle(SpdyStream *pStream);
    static SpdyStream *getSpdyStream();
    static void recycle(SpdyStream **pStream, int n);
    static int getSpdyStreams(SpdyStream **pStream, int n);

    LS_NO_COPY_ASSIGN(SpdyStreamPool);
};

#endif // SPDYSTREAMPOOL_H
