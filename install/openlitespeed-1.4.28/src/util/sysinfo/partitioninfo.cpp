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
#include "partitioninfo.h"
#include <lsdef.h>

PartitionInfo::PartitionInfo()
{

}



PartitionInfo::~PartitionInfo()
{

}

int PartitionInfo::getPartitionInfo(const char *path, uint64_t *outTotal,
                                    uint64_t *outFree)
{
#if defined(__linux) || defined(sun)
    struct statvfs st;
    if (statvfs(path, &st) != 0)
    {
        *outFree = 0;
        *outTotal = 0;
        return LS_FAIL;
    }
#elif defined(__FreeBSD__) || defined(__APPLE__)
    struct statfs st;
    if (statfs(path, &st) != 0)
    {
        *outFree = 0;
        *outTotal = 0;
        return LS_FAIL;
    }
#else
    *outFree = 0;
    *outTotal = 0;
    return LS_FAIL;
#endif
    *outFree = st.f_bsize * st.f_bavail >> 10;
    *outTotal = st.f_bsize * st.f_blocks >> 10;
    return 0;
}

