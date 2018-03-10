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
#include "pthreadmutex.h"
#if (defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)) && !defined( NDEBUG )

#ifndef PTHREAD_ERRORCHECK_MUTEX_INITIALIZER_NP
# define PTHREAD_ERRORCHECK_MUTEX_INITIALIZER_NP \
    {0, 0, 0, PTHREAD_MUTEX_ERRORCHECK_NP, __LOCK_INITIALIZER}
#endif

pthread_mutex_t PThreadMutex::s_proto =
    PTHREAD_ERRORCHECK_MUTEX_INITIALIZER_NP;

#else

pthread_mutex_t PThreadMutex::s_proto = PTHREAD_MUTEX_INITIALIZER;

#endif

