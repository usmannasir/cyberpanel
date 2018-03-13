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
#include "eventnotifier.h"
#include <edio/multiplexer.h>

#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>

EventNotifier::~EventNotifier()
{
#ifndef LSEFD_AVAIL
    if (m_fdIn != -1)
        close(m_fdIn);
#endif
    if (getfd() != -1)
        close(getfd());
}


int EventNotifier::handleEvents(short int event)
{
    int count = 0;
    ls_atomic_setint( &m_pending, 0);
    if (event & POLLIN)
    {
#ifdef LSEFD_AVAIL
        uint64_t ret;
        if (eventfd_read(getfd(), &ret) < 0)
            return LS_FAIL;

        if (ret > INT_MAX)
            count = INT_MAX;
        else
            count = (int)ret;
#else
        char achBuf[50];
        int len = 0;
        while ((len = read(getfd(), achBuf, sizeof(achBuf) / sizeof(char))) > 0)
            count += len;
#endif
        onNotified(count);
    }

    return LS_OK;
}


int EventNotifier::initNotifier(Multiplexer *pMultiplexer)
{
#ifdef LSEFD_AVAIL
    setfd(eventfd(0, EFD_CLOEXEC | EFD_NONBLOCK));
#else
    int fds[2];

    if (socketpair(AF_UNIX, SOCK_STREAM, 0, fds) == -1)
        return LS_FAIL;

    ::fcntl(fds[0], F_SETFD, FD_CLOEXEC);
    ::fcntl(fds[1], F_SETFD, FD_CLOEXEC);
    int fl = 0;
    ::fcntl(fds[1], F_GETFL, &fl);
    ::fcntl(fds[1], F_SETFL, fl | pMultiplexer->getFLTag());
    EventReactor::setfd(fds[1]);
    m_fdIn = fds[0];
#endif
    if (getfd() == -1)
        return LS_FAIL;
    pMultiplexer->add(this, POLLIN | POLLHUP | POLLERR);

    return LS_OK;
}


void EventNotifier::notify()
{
    char succ = ls_atomic_casint(&m_pending, 0, 1);       
    if (succ)
    {
#ifdef LSEFD_AVAIL
        eventfd_write(getfd(), 1);
#else
        write(m_fdIn, "a", 1);
#endif
    }
}


