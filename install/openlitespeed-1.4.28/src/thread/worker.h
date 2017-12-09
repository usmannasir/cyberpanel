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
#ifndef WORKER_H
#define WORKER_H

#include <lsdef.h>
#include <thread/thread.h>

#include <assert.h>

typedef void *(*workFn)(void *arg);

class Worker : public Thread
{
    int     m_iRunning;
    workFn  m_pWork;
    void   *m_pArg;

    // given to Thread::run so signature must conform
    static void *setWorker(void *pWorker)
    {
        // Thread::run is given 'this' as arg, which it will
        // pass to setWorker, so expecting a Worker *:
        return ((Worker *)pWorker)->doWork();
    }

    void *doWork()
    {
        void *ret = NULL;
        while (running())
        {
            if ((ret = m_pWork(m_pArg)))
                break;
        }
        m_iRunning = 0;
        return ret;
    }

    public:
    Worker(workFn work = NULL)
        : m_iRunning(0)
          , m_pWork(work)
          , m_pArg(NULL)
    {}

    ~Worker()
    {   assert(!m_iRunning);  }

    void setWorkFn(workFn work)
    {   m_pWork = work; }

    int running()
    {   return m_iRunning; }

    void setRunning()
    {   m_iRunning = 1; }

    void setStop()
    {   m_iRunning = 0; }

    int run(void *arg)
    {
        if (!m_pWork)
            return LS_FAIL;
        m_pArg = arg;
        setRunning();
        return Thread::run(setWorker, this);
    }



    LS_NO_COPY_ASSIGN(Worker);
};

#endif //WORKER_H

