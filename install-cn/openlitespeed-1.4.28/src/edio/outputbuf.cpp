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
#include "outputbuf.h"

#include <sys/types.h>
#include <sys/uio.h>

OutputBuf::OutputBuf()
{
}
OutputBuf::~OutputBuf()
{
}

int OutputBuf::cache(const char *pBuf, int total, int written)
{
    if (written >= total)
        return total;
    int cached = total - written;
    int ret = append(pBuf + written, cached);
    if (ret > 0)
        written += ret;
    return written;
}

int OutputBuf::cache(const struct iovec *vector, int count, int written)
{
    int w1 = written;
    const char *pCurBuf = NULL;
    int  iCurSize = 0;
    while (count > 0)
    {
        int blockSize = vector->iov_len;
        if (blockSize <= w1)
        {
            w1 -= blockSize;
            --count;
            ++vector;
        }
        else
        {
            pCurBuf = (const char *)vector->iov_base + w1;
            iCurSize = blockSize - w1;
            break;
        }
    }
    while (count > 0)
    {
        int cached = iCurSize;
        if (cached <= 0)
            break;
        int ret = append(pCurBuf, cached);
        if (ret > 0)
            written += ret;
        else
            break;
        if (cached < iCurSize)
            break;
        --count;
        if (count > 0)
        {
            ++vector;
            pCurBuf = (const char *)vector->iov_base;
            iCurSize = vector->iov_len;
        }
        else
            break;
    }
    return written;
}

