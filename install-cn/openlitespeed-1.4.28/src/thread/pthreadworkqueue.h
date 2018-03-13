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
#ifndef PTHREADWORKQUEUE_H
#define PTHREADWORKQUEUE_H

#include <util/linkedqueue.h>
#include <thread/pthreadmutex.h>
#include <thread/pthreadcond.h>
#include <assert.h>
#include <errno.h>
#include <limits.h>


class PThreadWorkQueue
{
private:
    PThreadMutex m_mutex;
    PThreadCond  m_ready;
    LinkedQueue    m_queue;
    bool         m_bShutdown;
    int          m_iWaiting;


    PThreadWorkQueue(const PThreadWorkQueue &rhs);
    void operator=(PThreadWorkQueue &rhs);

    int doAppend(ls_lfnodei_t **pWork, int size)
    {
        return m_queue.put(pWork, size);
    }

    void notify()
    {
        if (m_iWaiting > 0)
            m_ready.signal();
    }

    int doGet(ls_lfnodei_t **pWork, int &size)
    {
        size = m_queue.get(pWork, size);
        return (size) ? 0 : ETIMEDOUT;
    }

    void waitTillNoWaiting()
    {
        while (true)
        {
            {
                LockMutex lock(m_mutex);
                if (m_iWaiting == 0)
                    break;
            }
            m_ready.broadcast();
            ::sched_yield();
        }
    }

public:
    PThreadWorkQueue()
        : m_queue()
        , m_bShutdown(false)
        , m_iWaiting(0)
    {}

    ~PThreadWorkQueue()
    {
        assert(m_iWaiting == 0);
    }

    int append(ls_lfnodei_t **pWork, int size = 1)
    {
        if ((pWork == NULL) || (0 >= size))
            return EINVAL;
        {
            LockMutex lock(m_mutex);
            if (m_bShutdown)
                return EACCES;
            doAppend(pWork, size);
        }
        notify();
        return 0;
    }

    int tryAppend(ls_lfnodei_t **pWork, int size = 1)
    {
        if ((NULL == pWork) || (0 >= size))
            return EINVAL;
        int ret = EBUSY;
        if (0 == m_mutex.trylock())
        {
            if (m_bShutdown)
                ret = EACCES;
            else
            {
                doAppend(pWork, size);
                ret = 0;
            }
            m_mutex.unlock();
            notify();
        }
        return ret;
    }



    int get(ls_lfnodei_t **pWork, int &size, long lMilliSec = LONG_MAX)
    {
        if ((pWork == NULL) || (0 >= size))
            return EINVAL;
        if (lMilliSec <= 0)
            return tryget(pWork, size);
        int ret;
        bool bEmpty = true;
        {
            LockMutex lock(m_mutex);
            if (m_bShutdown)
                ret = EACCES;
            else
            {
                if (m_queue.empty())
                {
                    m_iWaiting++;
                    m_ready.wait(&m_mutex, lMilliSec);
                    m_iWaiting--;
                }
                ret = doGet(pWork, size);
                bEmpty = m_queue.empty();
            }
        }
        if ((m_iWaiting > 0) && (!bEmpty))
            m_ready.signal();
        return ret;
    }

    int tryget(ls_lfnodei_t **pWork, int &size)
    {
        if ((pWork == NULL) || (0 >= size))
            return EINVAL;
        int ret = EBUSY;
        if (0 == m_mutex.trylock())
        {
            bool bEmpty = true;
            if (m_bShutdown)
                ret = EACCES;
            else
            {
                ret = doGet(pWork, size);
                bEmpty = m_queue.empty();
            }
            m_mutex.unlock();
            if ((m_iWaiting > 0) && (!bEmpty))
                m_ready.signal();
        }
        return ret;
    }

    void shutdown()
    {
        {
            LockMutex lock(m_mutex);
            m_bShutdown = true;
        }
        waitTillNoWaiting();
    }

    void start()
    {
        LockMutex lock(m_mutex);
        m_bShutdown = false;
    }
};

#endif
