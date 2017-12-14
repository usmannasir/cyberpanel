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
#ifndef POLLER_H
#define POLLER_H

#include <lsdef.h>
#include <edio/multiplexer.h>
#include <edio/pollfdreactor.h>


class Poller : public Multiplexer
{
    PollfdReactor  m_pfdReactors;

    int allocate(int iInitCapacity);
    int deallocate();
protected:
    PollfdReactor &getPfdReactor() {    return m_pfdReactors;   }

public:
    Poller();
    virtual ~Poller();
    virtual int init(int capacity);
    virtual int add(EventReactor *pHandler, short mask);
    virtual int remove(EventReactor *pHandler);
    virtual int waitAndProcessEvents(int iTimeoutMilliSec);
    virtual void timerExecute();
    virtual void setPriHandler(EventReactor::pri_handler handler)
    {   m_pfdReactors.setPriHandler(handler);     }

    LS_NO_COPY_ASSIGN(Poller);
};

#endif
