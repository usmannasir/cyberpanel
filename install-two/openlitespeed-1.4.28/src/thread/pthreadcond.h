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
#ifndef PTHREADCOND_H
#define PTHREADCOND_H


#include <pthread.h>

class PThreadCond
{
private: //prevent from being copied
    PThreadCond(const PThreadCond &rhs);
    void operator=(const PThreadCond &rhs);
public:
    PThreadCond()   {   ::pthread_cond_init(&m_obj, NULL);  }
    ~PThreadCond()  { ::pthread_cond_destroy(&m_obj);  }
    int signal()    { return ::pthread_cond_signal(&m_obj);  }
    int broadcast() { return ::pthread_cond_broadcast(&m_obj); }
    int wait(pthread_mutex_t *pMutex)
    {   return ::pthread_cond_wait(&m_obj, pMutex); }
    int wait(pthread_mutex_t *pMutex, long lMilliSec);
    pthread_cond_t &get()  {   return m_obj;    }
private:
    pthread_cond_t  m_obj;
};

#endif
