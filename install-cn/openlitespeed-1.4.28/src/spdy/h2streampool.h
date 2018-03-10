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
#ifndef H2STREAMPOOL_H
#define H2STREAMPOOL_H

#include <util/dlinkqueue.h>
#include <util/objpool.h>

class H2Stream;
typedef ObjPool<H2Stream>       Pool;
class H2StreamPool : public ObjPool<H2Stream>
{
    static Pool s_pool;
    H2StreamPool();
    ~H2StreamPool();
public:
    static void recycle(H2Stream *pStream);
    static H2Stream *getH2Stream();
    static void recycle(H2Stream **pStream, int n);
    static int getH2Streams(H2Stream **pStream, int n);

    LS_NO_COPY_ASSIGN(H2StreamPool);
};

#endif // H2STREAMPOOL_H
