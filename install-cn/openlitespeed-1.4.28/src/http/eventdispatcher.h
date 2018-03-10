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
#ifndef EVENTDISPATCHER_H
#define EVENTDISPATCHER_H



class EventDispatcher
{
    void release();
    EventDispatcher(const EventDispatcher &rhs);
    void operator=(const EventDispatcher &rhs);

public:

    EventDispatcher();
    ~EventDispatcher();
//    Multiplexer * getMultiplexer() const
//    {   return m_pMultiplexer;  }

    //void ready() {  m_iStatus = READY;   }

    //bool isStopped() const   { return ( m_iStatus == STOPPED );  }
    //bool isRunning() const   { return ( m_iStatus == RUNNING );  }
    int init(const char *pType);
    int reinit();
    int run();
    int stop();
    int linger(int timeout);
    void updateDebugLevel();
    //HttpResourceManager * getResManager()
    //{   return &m_ResManager;   }

};

#endif
