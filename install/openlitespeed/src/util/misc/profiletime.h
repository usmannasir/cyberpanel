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

class ProfileTime
{
private:
#if defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)
    mach_timespec_t     m_begin;
#else
    struct timespec     m_begin;
#endif
    int64_t             m_diffns;

public:
    ProfileTime();
    ~ProfileTime();

    void start();
    void stop();

    int64_t getTimeUsedNanoSec();

    void printTime(const char *desc, int loop_count);
    void printTimeMs(const char *desc, int loop_count);
};

#endif
