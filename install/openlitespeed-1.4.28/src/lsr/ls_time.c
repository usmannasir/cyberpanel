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
#include <lsr/ls_time.h>

#include <errno.h>
#ifndef __USE_POSIX199309
#define __USE_POSIX199309
#endif
#include <time.h>

void ls_sleep(int millisec)
{
    struct timespec tm;
    if (!millisec)
        return;
    tm.tv_sec = millisec / 1000;
    tm.tv_nsec = millisec % 1000 * 1000000;
    while ((nanosleep(&tm, &tm) == -1) && (errno == EINTR)
           && (tm.tv_sec > 0) && (tm.tv_nsec > 0));
}


