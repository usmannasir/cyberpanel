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
#ifndef THREAD_H
#define THREAD_H

#include <lsdef.h>

#include <pthread.h>
#include <sys/time.h>

typedef void *(*entryFn)(void *arg);

/**
 * NOTICE: Any clean up routines need to be in the entry function.
 * The clean up should use the pthread cleanup routines.
 */

class Thread
{
    pthread_t       m_tid;
    pthread_attr_t  m_attr;

public:
    Thread()
        : m_tid(0)
    {
        pthread_attr_init(&m_attr);
    }

    ~Thread()
    {}

    pthread_t getId()
    {   return m_tid;  }

    const pthread_attr_t *getAttr()
    {   return &m_attr; }

    int run(entryFn entry, void *arg)
    {   return pthread_create(&m_tid, &m_attr, entry, arg);    }

    int cancel()
    {   return pthread_cancel(m_tid); }

    int setCancelState(int state, int *pOldState)
    {   return pthread_setcancelstate(state, pOldState);  }

    int setCancelType(int type, int *pOldType)
    {   return pthread_setcanceltype(type, pOldType);  }

    int isEqualTo(pthread_t rhs)
    {   return pthread_equal(m_tid, rhs); }

    int isJoinable()
    {
        int joinable;
        if (pthread_attr_getdetachstate(&m_attr, &joinable))
            return LS_FAIL;
        return (joinable == PTHREAD_CREATE_JOINABLE);
    }

    int detach()
    {   return pthread_detach(m_tid); }

    int join(void **pRetVal)
    {   return pthread_join(m_tid, pRetVal); }

#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
    int tryJoin(void **pRetVal)
    {   return pthread_tryjoin_np(m_tid, pRetVal); }

    int timedJoin(void **pRetVal, struct timespec *timeout)
    {   return pthread_timedjoin_np(m_tid, pRetVal, timeout);    }

    int attrSetAffinity(size_t cpusetsize, const cpu_set_t *cpuset)
    {   return pthread_attr_setaffinity_np(&m_attr, cpusetsize, cpuset);  }

    int attrGetAffinity(size_t cpusetsize, cpu_set_t *pCpuSet)
    {   return pthread_attr_getaffinity_np(&m_attr, cpusetsize, pCpuSet);  }
#endif

    int attrSetDetachState(int detachstate)
    {   return pthread_attr_setdetachstate(&m_attr, detachstate);    }

    int attrGetDetachState(int *pDetachState)
    {   return pthread_attr_getdetachstate(&m_attr, pDetachState);    }

    int attrSetGuardSize(size_t guardsize)
    {   return pthread_attr_setguardsize(&m_attr, guardsize); }

    int attrGetGuardSize(size_t *pGuardSize)
    {   return pthread_attr_getguardsize(&m_attr, pGuardSize); }

    int attrSetInheritSched(int inheritsched)
    {   return pthread_attr_setinheritsched(&m_attr, inheritsched); }

    int attrGetInheritSched(int *pInheritSched)
    {   return pthread_attr_getinheritsched(&m_attr, pInheritSched); }

    int attrSetSchedParam(const struct sched_param *param)
    {   return pthread_attr_setschedparam(&m_attr, param); }

    int attrGetSchedParam(struct sched_param *param)
    {   return pthread_attr_getschedparam(&m_attr, param); }

    int attrSetSchedPolicy(int policy)
    {   return pthread_attr_setschedpolicy(&m_attr, policy); }

    int attrGetSchedPolicy(int *pPolicy)
    {   return pthread_attr_getschedpolicy(&m_attr, pPolicy); }

    int attrSetScope(int scope)
    {   return pthread_attr_setscope(&m_attr, scope); }

    int attrGetScope(int *pScope)
    {   return pthread_attr_getscope(&m_attr, pScope); }

    int attrSetStack(void *stackaddr, size_t stacksize)
    {   return pthread_attr_setstack(&m_attr, stackaddr, stacksize); }

    int attrGetStack(void **pStackAddr, size_t *pStackSize)
    {   return pthread_attr_getstack(&m_attr, pStackAddr, pStackSize); }

    int attrSetStackSize(int stacksize)
    {
#ifdef _POSIX_THREAD_ATTR_STACKSIZE
        return pthread_attr_setstacksize(&m_attr, stacksize);
#else
        return LS_FAIL;
#endif
    }

    int attrGetStackSize(size_t *pStackSize)
    {
#ifdef _POSIX_THREAD_ATTR_STACKSIZE
        return pthread_attr_getstacksize(&m_attr, pStackSize);
#else
        *pStackSize = 0;
        return LS_FAIL;
#endif
    }






    LS_NO_COPY_ASSIGN(Thread);
};



#endif //THREAD_H


