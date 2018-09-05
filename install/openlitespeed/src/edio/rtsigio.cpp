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
#if 0
#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)

#include "rtsigio.h"

#include <assert.h>
#include <errno.h>
#ifndef __USE_GNU
#define __USE_GNU
#include <fcntl.h>
#undef __USE_GNU
#else
#include <fcntl.h>
#endif

#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <poll.h>
#include <unistd.h>

#define RTSIGNUM    SIGRTMIN+1

//#if 0

RTsigio::RTsigio()
{
    setFLTag(O_NONBLOCK | O_RDWR | O_ASYNC);
}

RTsigio::~RTsigio()
{
    signal(RTSIGNUM, SIG_IGN);
}



int RTsigio::init(int capacity)
{
    if ((m_fdindex.allocate(capacity) == 0) &&
        (Poller::init(capacity) == 0))
        return enableSigio();
    return LS_FAIL;
}

int RTsigio::enableSigio()
{
    if ((!sigemptyset(&m_sigset)) &&
        (!sigaddset(&m_sigset, SIGIO)) &&
        (!sigaddset(&m_sigset, RTSIGNUM)) &&
        (!sigprocmask(SIG_BLOCK, &m_sigset, NULL)))
        return LS_OK;
    return LS_FAIL;
}

int RTsigio::add(EventReactor *pHandler, short mask)
{
    int index = getPfdReactor().add(pHandler, mask);
    if (index == -1)
        return index;
    int fd = pHandler->getfd();
    if (m_fdindex.set(fd, index) == -1)
    {
        getPfdReactor().remove(pHandler);
        return LS_FAIL;
    }

    /* Set signal number >= SIGRTMIN to send a RealTime signal */
    fcntl(fd, F_SETSIG, RTSIGNUM);

    /* Set process id to send signal to */
    fcntl(fd, F_SETOWN, getpid());

#if defined( F_SETAUXFL )
    /* Allow only one signal per socket fd */
    fcntl(fd, F_SETAUXFL, O_ONESIGFD);
#endif
//    struct pollfd pfd;
//    pfd.fd = fd;
//    pfd.events = POLLIN | POLLOUT | POLLHUP | POLLERR | POLLPRI;
//    if ( ::poll( &pfd, 1, 0 ) == 1 )
//    {
//        getPfdReactor().processEvent( fd, index, pfd.revents );
//
//    }

    return LS_OK;
}


int RTsigio::remove(EventReactor *pHandler)
{
    if (!pHandler)
    {
        errno = EINVAL;
        return LS_FAIL;
    }
    int fd = pHandler->getfd();
    if (fd >= m_fdindex.getCapacity())
        return LS_OK;
    if (getPfdReactor().remove(pHandler))
        return LS_FAIL;
    //remove O_ASYNC flag, stop generate signal
    //::fcntl( fd, F_SETFL, O_NONBLOCK );
    m_fdindex.set(fd, 65535);
    return LS_OK;

}



int RTsigio::waitAndProcessEvents(int iTimeoutMilliSec)
{
    struct timespec timeout;
    timeout.tv_sec  = iTimeoutMilliSec / 1000;
    timeout.tv_nsec = (iTimeoutMilliSec % 1000) * 1000000;

    siginfo_t info;
    while (1)
    {
        int ret = sigtimedwait(&m_sigset, &info, &timeout);
        if (ret == RTSIGNUM)
        {
            int fd = info.si_fd;
            //printf( "Receive RTSIG for fd: %d, Event: %d\n", fd, (int)(info.si_band & 0x3f) );
            if (fd < m_fdindex.getCapacity())
            {
//                int index = m_pIndexes[fd];
//                printf( "fd: %d, index:%d, pollfd.fd: %d, pollfd.event: %d\n", fd, index,
//                          getPfdReactor().getPollfd( index )->fd,
//                          getPfdReactor().getPollfd( index )->revents    );
                getPfdReactor().processEvent(fd,
                                             m_fdindex.get(fd), info.si_band & 0x3f);
//                    printf( "Ignore RTSIG for fd: %d, Event: %d\n", fd, (int)(info.si_band & 0x3f) );
            }
        }
        else if (ret == -1)
            return ret;
        else if (ret == SIGIO)
        {
            printf("Real time signal queue over flow!\n");
            ret = Poller::waitAndProcessEvents(0);
            signal(RTSIGNUM, SIG_IGN);
            signal(RTSIGNUM, SIG_DFL);
            return ret;
        }
    }
//    while ( m_pQueueEnd != m_pQueueBegin )
//        processNextEvent( retcode );
}


//#endif

#endif
#endif
