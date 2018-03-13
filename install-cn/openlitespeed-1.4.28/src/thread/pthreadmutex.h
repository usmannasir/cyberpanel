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
#ifndef PTHREADMUTEX_H
#define PTHREADMUTEX_H



#include <pthread.h>

#ifndef NDEBUG
#include <stdio.h>
#endif

class PThreadMutex
{
private:
    static pthread_mutex_t s_proto;
    pthread_mutex_t        m_obj;
private: //prevent from being copied
    PThreadMutex(const PThreadMutex &rhs);
    void operator=(const PThreadMutex &rhs);
public:
    PThreadMutex() : m_obj(s_proto) {}
    //PThreadMutex()
    //{   ::pthread_mutex_init( &m_obj, NULL ); }
    pthread_mutex_t *operator&()   {   return &m_obj;  }
#ifndef NDEBUG
    ~PThreadMutex()
    {
        int ret = ::pthread_mutex_destroy(&m_obj);
        if (0 != ret)
            fprintf(stderr, "Failed to destroy, the mutex is currently locked!\n");
    }
    int lock()
    {
        int ret = ::pthread_mutex_lock(&m_obj);
        if (0 != ret)
            fprintf(stderr, "The mutex is already locked by calling thread!\n");
        return ret;
    }
    int trylock()
    {   return ::pthread_mutex_trylock(&m_obj); }

    int unlock()
    {
        int ret = ::pthread_mutex_unlock(&m_obj);
        if (0 != ret)
            fprintf(stderr, "The mutex is not owned by calling thread!\n");
        return ret;
    }
#else
    ~PThreadMutex() {   ::pthread_mutex_destroy(&m_obj); }
    int lock()      {   return ::pthread_mutex_lock(&m_obj);    }
    int trylock()   {   return ::pthread_mutex_trylock(&m_obj); }
    int unlock()    {   return ::pthread_mutex_unlock(&m_obj);  }
#endif
};

class LockMutex
{
private:
    PThreadMutex &m_mutex;
public:
    LockMutex(PThreadMutex &obj)
        : m_mutex(obj)
    {   m_mutex.lock();      }

    ~LockMutex()
    {   m_mutex.unlock();    }
};


#endif
