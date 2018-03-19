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
#ifdef RUN_TEST

#include <iostream>
#include <util/sysinfo/partitioninfo.h>
#include "unittest-cpp/UnitTest++.h"

static const char *pRoot = "/";

TEST(PartitionInfoTest)
{
    uint64_t iTotal = 0, iFree = 0;
    CHECK((PartitionInfo::getPartitionInfo(pRoot, &iTotal, &iFree) == 0)
          && iTotal != 0
          && iFree != 0);
    std::cout << "Total: " << iTotal << ", Free: " << iFree << std::endl;
}

#endif

