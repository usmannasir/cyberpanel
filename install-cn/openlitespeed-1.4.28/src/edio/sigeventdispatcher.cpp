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

#include <edio/sigeventdispatcher.h>

#if defined(LS_AIO_USE_KQ)
#include <sys/param.h>
#include <sys/linker.h>

static short s_iAiokoLoaded = -1;

void SigEventDispatcher::setAiokoLoaded()
{
    s_iAiokoLoaded = (kldfind("aio.ko") != -1);
}

short SigEventDispatcher::aiokoIsLoaded()
{
    return s_iAiokoLoaded;
}

#elif defined(LS_AIO_USE_SIGFD) || defined(LS_AIO_USE_SIGNAL)

#include <edio/multiplexer.h>
#include <edio/multiplexerfactory.h>

#include <errno.h>
#include <fcntl.h>
#include <unistd.h>

#if defined(LS_AIO_USE_SIGFD)
#include <sys/signalfd.h>
#endif // defined(LS_AIO_USE_SIGFD)

int SigEventDispatcher::processSigEvent()
{
#ifdef LS_AIO_USE_SIGNAL
    struct timespec timeout;
    siginfo_t si;
    sigset_t ss;

    timeout.tv_sec = 0;
    timeout.tv_nsec = 0;

    sigemptyset(&ss);
    sigaddset(&ss, HS_AIO);

    while (sigtimedwait(&ss, &si, &timeout) > 0)
    {
        if (!sigismember(&ss, HS_AIO))
            continue;
        ((AioEventHandler *)si.si_value.sival_ptr)->onAioEvent();
    }
#endif
    return LS_OK;
}

int SigEventDispatcher::init()
{
    SigEventDispatcher *pReactor;
    sigset_t ss;
    sigemptyset(&ss);
    sigaddset(&ss, HS_AIO);
    sigprocmask(SIG_BLOCK, &ss, NULL);
#if defined(LS_AIO_USE_SIGFD)
    pReactor = new SigEventDispatcher(&ss);
    if (pReactor->getfd() == -1)
    {
        delete pReactor;
        return LS_FAIL;
    }
    MultiplexerFactory::getMultiplexer()->add(pReactor, POLLIN);
#endif // defined(LS_AIO_USE_SIGFD)
    return LS_OK;
}


SigEventDispatcher::SigEventDispatcher(sigset_t *ss)
{
#if defined(LS_AIO_USE_SIGFD)
    int fd = signalfd(-1, ss, 0);
    if (fd != -1)
    {
        fcntl(fd, F_SETFD, FD_CLOEXEC);
        fcntl(fd, F_SETFL, fcntl(fd, F_GETFL, 0) | O_NONBLOCK);
        setfd(fd);
    }
#endif // defined(LS_AIO_USE_SIGFD)
}

int SigEventDispatcher::handleEvents(short event)
{
#if defined(LS_AIO_USE_SIGFD)
    int i, readCount = 0;
    signalfd_siginfo si[5];
    if (!(event & POLLIN))
        return LS_OK;
    do
    {
        if ((readCount = read(getfd(), &si, sizeof(signalfd_siginfo) * 5)) < 0)
        {
            if (errno == EAGAIN)
                break;
            return LS_FAIL;
        }
        else if (readCount == 0)
            return LS_OK;
        readCount /= sizeof(signalfd_siginfo);
        for (i = 0; i < readCount; ++i)
            ((AioEventHandler *)si[i].ssi_ptr)->onAioEvent();
    }
    while (readCount == 5);
#endif // defined(LS_AIO_USE_SIGFD)
    return LS_OK;
}

#endif // defined(LS_AIO_USE_KQ)
