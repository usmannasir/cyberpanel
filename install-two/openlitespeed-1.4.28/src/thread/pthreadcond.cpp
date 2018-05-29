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
#include "pthreadcond.h"
#include <limits.h>
#include <sys/time.h>


int PThreadCond::wait(pthread_mutex_t *pMutex, long lMilliSec)
{
    if (LONG_MAX == lMilliSec)
        return wait(pMutex);
    struct timeval  curtime;
    gettimeofday(&curtime, NULL);
    struct timespec timeout;
    timeout.tv_sec = curtime.tv_sec + lMilliSec / 1000;
    timeout.tv_nsec = curtime.tv_usec * 1000 + lMilliSec % 1000 * 1000000;
    if (timeout.tv_nsec > 1000000000)
    {
        timeout.tv_sec ++;
        timeout.tv_nsec -= 1000000000;
    }
    return ::pthread_cond_timedwait(&m_obj, pMutex, &timeout);
}

