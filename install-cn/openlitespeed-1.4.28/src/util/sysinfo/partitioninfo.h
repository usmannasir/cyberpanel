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
#ifndef PARTITIONINFO_H
#define PARTITIONINFO_H

#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>

#if defined(__linux) || defined(sun)
#include <sys/statvfs.h>
#elif defined(__FreeBSD__) || defined(__APPLE__)
#include <sys/param.h>
#include <sys/mount.h>
#endif

class PartitionInfo
{
public:
    PartitionInfo();
    ~PartitionInfo();
    static int getPartitionInfo(const char *path, uint64_t *outTotal,
                                uint64_t *outFree);

private:
    PartitionInfo(const PartitionInfo &other);
    PartitionInfo &operator= (const PartitionInfo &other);
    bool operator== (const PartitionInfo &other);

private:
};

#endif // PARTITIONINFO_H

