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
#include "cacheos.h"

#include <util/iovec.h>

#include <errno.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/uio.h>

int CacheOS::cacheWritev(IOVec &vec, int total, int *pRet)
{
    int ret = 0;
    int bufSize;
    int written = 0;
    const struct iovec *vector = vec.begin();
    for (; vector < vec.end(); ++vector)
    {
        const char *pBuf = (const char *) vector->iov_base;
        bufSize = vector->iov_len;
        if ((pBuf != NULL) && (bufSize > 0))
            written = cacheWrite(pBuf, bufSize, pRet);
        if (written > 0)
            ret += written;
        if (ret < 0)
            break;
        if (written < bufSize)
            break;
    }
    return ret;

}


