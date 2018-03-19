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
#ifndef EVENTNOTIFIER_H
#define EVENTNOTIFIER_H

#include <edio/eventreactor.h>
#include <lsr/ls_atomic.h>

#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
#include <linux/version.h>
#if LINUX_VERSION_CODE >= KERNEL_VERSION(2,6,30)
#include <limits.h>
#include <sys/eventfd.h>
#define LSEFD_AVAIL
#endif // LINUX_VERSION_CODE >= KERNEL_VERSION(2,6,30)
#endif // defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)

class Multiplexer;

class EventNotifier :  public EventReactor
{
#ifdef LSEFD_AVAIL
    uint64_t m_count;
#else
    int m_fdIn;
#endif
    ls_atom_32_t  m_pending;
public:
    EventNotifier()
#ifdef LSEFD_AVAIL
        : m_count(0)
#else
        : m_fdIn(-1)
#endif
        , m_pending(0)
    {};
    virtual ~EventNotifier();
    virtual int handleEvents(short int event);
    int initNotifier(Multiplexer *pMultiplexer);
    void notify();
#ifndef LSEFD_AVAIL
    int getFdIn()
    {
        return m_fdIn;
    }
#endif
    void uninitNotifier(Multiplexer *pMultiplexer);

    virtual int onNotified(int count) = 0;
private:
    EventNotifier(const EventNotifier &rhs);
    void operator=(const EventNotifier &rhs);
};

#endif // EVENTNOTIFIER_H

