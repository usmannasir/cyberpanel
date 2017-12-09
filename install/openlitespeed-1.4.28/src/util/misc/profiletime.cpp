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
#include "profiletime.h"


ProfileTime::ProfileTime(const char *pName, int iLoopCount,
                         ProfilePrecision p)
    : m_pName(pName)
{
    m_used = 0;
    m_precision = p;
    if (iLoopCount < 1)
        m_iterCount = 1;
    else
        m_iterCount = iLoopCount;
#if defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)
    host_get_clock_service(mach_host_self(), SYSTEM_CLOCK, &m_clock);
    clock_get_time(m_clock, &m_begin);
#else
    clock_gettime(CLOCK_MONOTONIC, &m_begin);
#endif
}

ProfileTime::~ProfileTime()
{
#if defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)
    mach_port_deallocate(mach_task_self(), m_clock);
#endif
    if (m_used)
        return;
    printTime();
}

int64_t ProfileTime::timeUsed()
{
    dx();
    m_used = 1;
    return m_diffns;
}

void ProfileTime::dx()
{
#if defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)
    clock_get_time(m_clock, &m_end);
#else
    clock_gettime(CLOCK_MONOTONIC, &m_end);
#endif
    int64_t ns;
    int iDiv, iMult;

    if (m_precision == PROFILE_MICRO)
    {
        iDiv = 1e3;
        iMult = 1e6;
    }
    else
    {
        iDiv = 1;
        iMult = 1e9;
    }
    ns = (m_end.tv_nsec - m_begin.tv_nsec) / iDiv;
    if (ns >= 0)
        m_diffns = (m_end.tv_sec - m_begin.tv_sec) * iMult + ns;
    else
        m_diffns = (m_end.tv_sec - m_begin.tv_sec - 1) * iMult + (ns + iMult);
}

void ProfileTime::printTime()
{
    dx();
    const char *pType = (m_precision == PROFILE_MICRO ? "ms" : "ns");
    printf("%s Total: %" PRId64 " %s, Average Per Loop: %" PRId64 " %s\n",
           m_pName, m_diffns, pType, m_diffns / m_iterCount, pType);
}


