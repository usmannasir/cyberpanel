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
#include "spdystreampool.h"
#include "spdystream.h"

Pool SpdyStreamPool::s_pool;
void SpdyStreamPool::recycle(SpdyStream *pStream)
{
    s_pool.recycle(pStream);
}


SpdyStream *SpdyStreamPool::getSpdyStream()
{
    SpdyStream *p = s_pool.get();
    return p;
}


void SpdyStreamPool::recycle(SpdyStream **pStream, int n)
{
    s_pool.recycle((void **)pStream, n);
}


int SpdyStreamPool::getSpdyStreams(SpdyStream **pStream, int n)
{
    int ret = s_pool.get(pStream, n);
    return ret;
}


