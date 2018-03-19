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
#ifndef PROFILETIME_H
#define PROFILETIME_H

#define __STDC_FORMAT_MACROS
#include <inttypes.h>
#include <stdio.h>
#if defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)
#include <mach/clock.h>
#include <mach/mach.h>
#else
#include <sys/time.h>
#include <time.h>
#endif

enum ProfilePrecision
{
    PROFILE_MICRO,
    PROFILE_NANO
};

class ProfileTime
{
private:
#if defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)
    clock_serv_t        m_clock;
    mach_timespec_t     m_begin;
    mach_timespec_t     m_end;
#else
    struct timespec     m_begin;
    struct timespec     m_end;
#endif
    int64_t             m_diffns;
    int                 m_iterCount;
    int                 m_used;
    ProfilePrecision    m_precision;
    const char         *m_pName;

private:
    void dx();
public:
    ProfileTime(const char *pName, int iLoopCount,
                ProfilePrecision p = PROFILE_MICRO);
    ~ProfileTime();

    int64_t timeUsed();

    void printTime();
};

#endif
