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
#include "timerprocessor.h"
#include <util/timer.h>
#include <util/timertask.h>

#include <set>

class TaskSet: public std::set<TimerTask *>
{

};

TimerProcessor::TimerProcessor()
{
    m_pSet = new TaskSet();
}
TimerProcessor::~TimerProcessor()
{
    reset();
    delete m_pSet;
}

void TimerProcessor::reset()
{
    TaskSet::iterator iter = m_pSet->begin();
    for (; iter != m_pSet->end(); ++iter)
    {
        (*iter)->setProcessor(NULL);
        remove(*iter);
    }
    m_pSet->clear();
}

void TimerProcessor::add(TimerTask *pTask)
{
    m_pSet->insert(pTask);
    pTask->setProcessor(this);
}

void TimerProcessor::remove(TimerTask *pTask)
{
    if (pTask->getProcessor())
    {
        m_pSet->erase(pTask);
        pTask->setProcessor(NULL);
    }
    Timer *timer = pTask->getTimer();
    if (timer)
        timer->cancel(pTask);


}



