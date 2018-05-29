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
#include "timer.h"
#include <util/timerprocessor.h>
#include <util/timertask.h>

#include <errno.h>
#include <stdio.h>
#include <time.h>

#include <map>
#include <set>

static long s_iTime = 0;

class TimerTaskList : public std::set<TimerTask *>
{
public:
    void execute();
};


void TimerTaskList::execute()
{
    iterator iterEnd = end();
    iterator iter;
    for (iter = begin(); iter != iterEnd; ++iter)
    {
        TimerProcessor *pProcessor = (*iter)->getProcessor();
        assert(pProcessor);
        pProcessor->onTimer(*iter);
    }
}


class TimerImpl : private std::map<long, TimerTaskList>
{
public:
    void add(TimerTask *task, long time);
    void remove(TimerTask *task);
    void execute();
};

void TimerImpl::add(TimerTask *task, long time)
{
    static TimerTaskList empty;
    task->setScheduledTime(time);
    std::pair< iterator, bool > ret = insert(value_type(time, empty));
    ret.first->second.insert(task);
}

void TimerImpl::remove(TimerTask *task)
{
    iterator iter = find(task->getScheduledTime());
    if (iter != end())
        iter->second.erase(task);
}

void TimerImpl::execute()
{
    iterator iter;
    iterator iterEnd = end();
    for (iter = begin(); iter != iterEnd;)
    {
        if (iter->first <= s_iTime)
        {
            iter->second.execute();
            iterator iterTemp = iter++;
            erase(iterTemp);
        }
        else
            break;
    }
}


Timer::Timer()
{
    s_iTime = time(NULL);
    m_pImpl = new TimerImpl();
}

Timer::~Timer()
{
}


/** Schedules the specified task for execution after the specified delay.  */
int Timer::schedule(TimerTask *task, long delay)
{
    if (delay < 0)
        return EINVAL;
    if (delay == 0)
        task->getProcessor()->onTimer(task);
    else
    {
        m_pImpl->add(task, delay + s_iTime);
        task->setTimer(this);
    }
    return 0;
}

void Timer::cancel(TimerTask *task)
{
    m_pImpl->remove(task);
    task->setTimer(NULL);
}

void Timer::execute()
{
    //printf( "Timer::execute()\n" );
    long lCurTime = time(NULL);
    if (lCurTime != s_iTime)
    {
        s_iTime = lCurTime;
        m_pImpl->execute();
    }
}

int Timer::currentTime()
{
    return s_iTime;
}


