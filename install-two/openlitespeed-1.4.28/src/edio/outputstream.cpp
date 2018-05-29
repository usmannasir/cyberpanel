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
#include "outputstream.h"

#include <util/iovec.h>

#include <sys/uio.h>
#include <stdio.h>
#include <errno.h>

int OutputStream::writevToWrite(const struct iovec *vector, int count)
{
    int ret = 0;
    int bufSize;
    int written = 0;
    for (; count > 0; --count, ++vector)
    {
        const char *pBuf = (const char *) vector->iov_base;
        bufSize = vector->iov_len;
        if ((pBuf != NULL) && (bufSize > 0))
            written = write(pBuf, bufSize);
        if (written > 0)
            ret += written;
        else if (written < 0)
            ret = written;
        if (written < bufSize)
            break;
    }
    return ret;
}

int OutputStream::writev(IOVec &vec)
{

    return writev(vec.get(), vec.len());
}

int OutputStream::writev(IOVec &vec, int total)
{
    return writev(vec.get(), vec.len());
}


