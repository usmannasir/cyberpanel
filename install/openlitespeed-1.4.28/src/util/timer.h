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
#ifndef TIMER_H
#define TIMER_H



class TimerTask;
class TimerImpl;

class Timer
{
    TimerImpl *m_pImpl;

    Timer(const Timer &rhs);
    void operator=(const Timer &rhs);
public:
    Timer();
    ~Timer();
    /** Schedules the specified task for execution after the specified delay.
     *  @param task task to be scheduled.
     *  @param delay delay in seconds before task is to be executed.
     */
    int  schedule(TimerTask *task, long delay);
    void cancel(TimerTask *task);
    void execute();
    static int currentTime();
};

#endif
