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
#include <util/loopbuf.h>
#include <util/iovec.h>

#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <assert.h>


void LoopBuf::iovInsert(IOVec &vect) const
{
    int size = this->size();
    if (size > 0)
    {
        int len = pbufend - phead;
        if (size > len)
        {
            vect.push_front(pbuf, size - len);
            vect.push_front(phead, len);
        }
        else
            vect.push_front(phead, size);
    }
}

void LoopBuf::iovAppend(IOVec &vect) const
{
    int size = this->size();
    if (size > 0)
    {
        int len = pbufend - phead;
        if (size > len)
        {
            vect.append(phead, len);
            vect.append(pbuf, size - len);
        }
        else
            vect.append(phead, size);
    }
}

void XLoopBuf::iovInsert(IOVec &vect) const
{
    int size = this->size();
    if (size > 0)
    {
        int len = loopbuf.pbufend - loopbuf.phead;
        if (size > len)
        {
            vect.push_front(loopbuf.pbuf, size - len);
            vect.push_front(loopbuf.phead, len);
        }
        else
            vect.push_front(loopbuf.phead, size);
    }
}

void XLoopBuf::iovAppend(IOVec &vect) const
{
    int size = this->size();
    if (size > 0)
    {
        int len = loopbuf.pbufend - loopbuf.phead;
        if (size > len)
        {
            vect.append(loopbuf.phead, len);
            vect.append(loopbuf.pbuf, size - len);
        }
        else
            vect.append(loopbuf.phead, size);
    }
}





