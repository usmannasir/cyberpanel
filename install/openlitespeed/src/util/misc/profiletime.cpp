/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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
#include "profiletime.h"


#if defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)
static clock_serv_t s_clock;
#endif


ProfileTime::ProfileTime()
{
#if defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)
    static int clock_inited = 0;
    if (!clock_inited)
    {
        host_get_clock_service(mach_host_self(), SYSTEM_CLOCK, &s_clock);
        clock_inited = 1;
    }
#endif
    start();
}


ProfileTime::~ProfileTime()
{
// #if defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)
//     mach_port_deallocate(mach_task_self(), s_clock);
// #endif
}


void ProfileTime::start()
{
#if defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)
    clock_get_time(s_clock, &m_begin);
#else
    clock_gettime(CLOCK_MONOTONIC, &m_begin);
#endif
    m_diffns = 0;
}


int64_t ProfileTime::getTimeUsedNanoSec()
{
    if (!m_diffns)
        stop();
    return m_diffns;
}


void ProfileTime::stop()
{
#if defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)
    mach_timespec_t     end;
    clock_get_time(s_clock, &end);
#else
    struct timespec     end;
    clock_gettime(CLOCK_MONOTONIC, &end);
#endif
    m_diffns = (end.tv_sec - m_begin.tv_sec) * 1e9 
                + (end.tv_nsec - m_begin.tv_nsec);
}


void ProfileTime::printTime(const char *desc, int loop_count)
{
    int64_t time_diff = getTimeUsedNanoSec();
    printf("%s Total: %" PRId64 " ns, Average Per Loop: %" PRId64 " ns\n",
           desc, time_diff, time_diff / loop_count);
}


void ProfileTime::printTimeMs(const char *desc, int loop_count)
{
    int64_t time_diff = getTimeUsedNanoSec() / 1e3;
    printf("%s Total: %" PRId64 " ms, Average Per Loop: %" PRId64 " ms\n",
           desc, time_diff, time_diff / loop_count);
}


