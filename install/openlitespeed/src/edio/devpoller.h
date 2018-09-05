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
#ifndef DEVPOLLER_H
#define DEVPOLLER_H

#if defined(sun) || defined(__sun)

#include <lsdef.h>
#include <edio/multiplexer.h>
#include <edio/reactorindex.h>
#include <poll.h>

#define MAX_CHANGES 40
#define MAX_EVENTS  20
class DevPoller : public Multiplexer
{
    int             m_fdDP;
    ReactorIndex    m_reactorIndex;

    int             m_curChanges;
    struct pollfd   m_events[MAX_EVENTS];
    struct pollfd   m_changes[MAX_CHANGES];

    int applyChanges();

    int appendChange(int fd, short mask)
    {
        if (m_curChanges >= MAX_CHANGES)
            if (applyChanges() == -1)
                return LS_FAIL;
        m_changes[m_curChanges].fd       = fd;
        m_changes[m_curChanges++].events = mask;
        return LS_OK;
    }
    void setEvent(EventReactor *pHandler, short mask)
    {
        if (mask != pHandler->getEvents())
        {
            appendChange(pHandler->getfd(), POLLREMOVE);
            appendChange(pHandler->getfd(), mask);
            pHandler->setMask2(mask);
        }
    }

    void addEvent(EventReactor *pHandler, short mask)
    {
        if ((mask & pHandler->getEvents()) != mask)
        {
            pHandler->orMask2(mask);
            appendChange(pHandler->getfd(), pHandler->getEvents());
        }
    }

    void removeEvent(EventReactor *pHandler, short mask)
    {
        if (mask & pHandler->getEvents())
        {
            appendChange(pHandler->getfd(), POLLREMOVE);
            pHandler->andMask2(~mask);
            appendChange(pHandler->getfd(), pHandler->getEvents());
        }
    }

public:
    DevPoller();
    ~DevPoller();

    virtual int getHandle() const   {   return m_fdDP;  }
    virtual int init(int capacity = DEFAULT_CAPACITY);
    virtual int add(EventReactor *pHandler, short mask);
    virtual int remove(EventReactor *pHandler);
    virtual int waitAndProcessEvents(int iTimeoutMilliSec);
    virtual void timerExecute();
    virtual void setPriHandler(EventReactor::pri_handler handler);
    virtual void modEvent(EventReactor *pHandler, short mask, int add_remove);
    virtual void setEventMask(EventReactor *pHandler, short mask)
    {   setEvent(pHandler, mask);       }

    virtual void continueRead(EventReactor *pHandler);
    virtual void suspendRead(EventReactor *pHandler);
    virtual void continueWrite(EventReactor *pHandler);
    virtual void suspendWrite(EventReactor *pHandler);

    virtual void switchWriteToRead(EventReactor *pHandler)
    {   setEvent(pHandler, POLLIN | POLLERR | POLLHUP);   }

    virtual void switchReadToWrite(EventReactor *pHandler)
    {   setEvent(pHandler, POLLOUT | POLLERR | POLLHUP);  }

    LS_NO_COPY_ASSIGN(DevPoller);
};

#endif //defined(sun) || defined(__sun)

#endif
