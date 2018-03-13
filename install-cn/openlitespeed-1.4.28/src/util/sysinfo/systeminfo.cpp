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
#include "systeminfo.h"
#include <sys/time.h>
#include <sys/resource.h>
#include <unistd.h>


SystemInfo::SystemInfo()
{
}
SystemInfo::~SystemInfo()
{
}

int SystemInfo::s_iPageSize = 0;

int SystemInfo::getPageSize()
{
    if (s_iPageSize == 0)
        s_iPageSize = sysconf(_SC_PAGESIZE);
    return s_iPageSize;
}

unsigned long long SystemInfo::maxOpenFile(unsigned long long max)
{
    struct  rlimit rl;
    unsigned long long iMaxOpenFiles = 0;
    if (getrlimit(RLIMIT_NOFILE, &rl) == 0)
    {
        iMaxOpenFiles = rl.rlim_cur;
        if ((rl.rlim_cur != RLIM_INFINITY) && (max > rl.rlim_cur))
        {
            if (rl.rlim_cur < max && max <= rl.rlim_max)
                rl.rlim_cur = max;
            else
                rl.rlim_cur = rl.rlim_max = max;
            //if ( rl.rlim_cur == RLIM_INFINITY )
            //    rl.rlim_cur = 4096;
            if (setrlimit(RLIMIT_NOFILE, &rl) == 0)
                iMaxOpenFiles = rl.rlim_cur;
        }
    }
    return iMaxOpenFiles;
}



