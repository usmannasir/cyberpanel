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
#ifndef OUTPUTBUF_H
#define OUTPUTBUF_H


#include <lsdef.h>

#include <util/loopbuf.h>
struct iovec;
class OutputBuf : public LoopBuf
{
public:
    OutputBuf();
    OutputBuf(int initSize)
        : LoopBuf(initSize)
    {}
    ~OutputBuf();

    int cache(const char *pBuf, int total, int written);
    int cache(const struct iovec *vector, int count, int written);
    LS_NO_COPY_ASSIGN(OutputBuf);

};

#endif
