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
#ifndef TIMERTASK_H
#define TIMERTASK_H


class TimerProcessor;
class Timer;
class TimerTask
{
    long               m_iScheduled;
    int                m_iEvent;
    Timer             *m_pTimer;
    TimerProcessor    *m_pProcessor;


    TimerTask(const TimerTask &rhs);
    void operator=(const TimerTask &rhs);
public:
    TimerTask();
    TimerTask(TimerProcessor *pProcessor)
        : m_iScheduled(0)
        , m_iEvent(0)
        , m_pTimer(0)
        , m_pProcessor(pProcessor)
    {}
    ~TimerTask();
    void reset();
    int  getEvent() const
    {   return m_iEvent;     }
    void setEvent(int event)
    {   m_iEvent = event;    }
    long getScheduledTime() const
    {   return m_iScheduled; }
    void setScheduledTime(long scheduled)
    {   m_iScheduled = scheduled;    }
    TimerProcessor *getProcessor() const
    {   return m_pProcessor;    }
    void setProcessor(TimerProcessor *pProcessor)
    {   m_pProcessor = pProcessor;  }
    Timer *getTimer() const
    {   return m_pTimer;    }
    void setTimer(Timer *pTimer)
    {   m_pTimer = pTimer;   }
};

#endif
