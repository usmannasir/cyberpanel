/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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
#include "poller.h"

#include <edio/lookupfd.h>

#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <poll.h>


Poller::Poller()
    : m_pfdReactors()
{
}


Poller::~Poller()
{
}


int Poller::allocate(int capacity)
{
    return m_pfdReactors.allocate(capacity);
}


int Poller::init(int capacity)
{
    return allocate(capacity);
}


int Poller::add(EventReactor *pHandler, short mask)
{
    assert(pHandler);
    m_pfdReactors.add(pHandler, mask);
    return LS_OK;
}


int Poller::remove(EventReactor *pHandler)
{
    assert(pHandler);
    m_pfdReactors.remove(pHandler);
    return LS_OK;
}


int Poller::waitAndProcessEvents(int iTimeoutMilliSec)
{
    int events = ::poll(m_pfdReactors.getPollfd(),
                        m_pfdReactors.getSize(),
                        iTimeoutMilliSec);
    if (events > 0)
    {
        m_pfdReactors.setEvents(events);
        m_pfdReactors.processAllEvents();
        return LS_OK;
    }
    return events;
}


void Poller::timerExecute()
{
    m_pfdReactors.timerExecute();
}


