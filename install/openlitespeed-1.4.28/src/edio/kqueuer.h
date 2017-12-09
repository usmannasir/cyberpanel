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
#ifndef KQUEUER_H
#define KQUEUER_H

#if defined(__FreeBSD__ ) || defined(__NetBSD__) || defined(__OpenBSD__) \
    || defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)

#include <lsdef.h>

#include <multiplexer.h>
#include <reactorindex.h>

#include <sys/types.h>
#include <sys/event.h>

struct kevent;
class KQueuer : public Multiplexer
{
    int m_fdKQ;
    ReactorIndex    m_reactorIndex;
    int m_changeCapacity;
    int m_curChange;
    struct kevent *m_pChanges;
    //struct kevent   m_trace;
    //int             m_traceCounter;

    int allocateChangeBuf(int capacity);
    int deallocateChangeBuf();
    int appendEvent(EventReactor *pHandler, short filter, unsigned short flag);
    int addEvent(EventReactor *pHandler, short mask);
    int appendEvent(EventReactor *pHandler, int fd, short filter,
                    unsigned short flags)
    {
        if (fd == -1)
            return LS_OK;
        if (m_curChange == m_changeCapacity)
        {
            if (allocateChangeBuf(m_changeCapacity + 64) == -1)
                return LS_FAIL;
        }
        struct kevent *pEvent = m_pChanges + m_curChange++;
        pEvent->ident  = fd;
        pEvent->filter = filter;
        pEvent->flags  = flags;
        pEvent->udata  = pHandler;
        return LS_OK;
    }
    void processAioEvent(struct kevent *pEvent);
    void processSocketEvent(struct kevent *pEvent);
public:
    KQueuer();
    ~KQueuer();
    virtual int getHandle() const   {   return m_fdKQ;  }
    virtual int init(int capacity = DEFAULT_CAPACITY);
    virtual int add(EventReactor *pHandler, short mask);
    virtual int remove(EventReactor *pHandler);
    virtual int waitAndProcessEvents(int iTimeoutMilliSec);
    virtual void timerExecute();
    virtual void setPriHandler(EventReactor::pri_handler handler);
    virtual void wantRead(EventReactor *pHandler, int want);
    virtual void wantWrite(EventReactor *pHandler, int want);
    virtual void modEvent(EventReactor *pHandler, short mask, int add_remove);

    virtual void continueRead(EventReactor *pHandler);
    virtual void suspendRead(EventReactor *pHandler);
    virtual void continueWrite(EventReactor *pHandler);
    virtual void suspendWrite(EventReactor *pHandler);
    virtual void switchWriteToRead(EventReactor *pHandler);
    virtual void switchReadToWrite(EventReactor *pHandler);
    static int getFdKQ();

    LS_NO_COPY_ASSIGN(KQueuer);

};

#endif //defined(__FreeBSD__ ) || defined(__NetBSD__) || defined(__OpenBSD__) 
//|| defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)


#endif
