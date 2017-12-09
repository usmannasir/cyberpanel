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
#include "multiplexerfactory.h"

#include <edio/devpoller.h>
#include <edio/epoll.h>
#include <edio/kqueuer.h>
#include <edio/poller.h>
#include <edio/rtsigio.h>

#include <stdlib.h>
#include <string.h>

int MultiplexerFactory::s_iMaxFds = 4096;
static const char *s_sType[MultiplexerFactory::BEST + 1] =
{
    "poll",
    "select",
    "devpoll",
    "kqueue",
    "rtsig",
    "epoll",
    "best"
};

int          MultiplexerFactory::s_iMultiplexerType = 0;
Multiplexer *MultiplexerFactory::s_pMultiplexer = NULL;

int MultiplexerFactory::getType(const char *pType)
{
    int i;
    if (!pType)
        return POLL;
    for (i = 0; i < BEST + 1; ++i)
    {
        if (strcasecmp(pType, s_sType[i]) == 0)
            break;
    }
    if (i == BEST)
    {
#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
        i = EPOLL;
#endif

#if defined(sun) || defined(__sun)
        i = DEV_POLL;
#endif

#if defined(__FreeBSD__ ) || defined(__NetBSD__) || defined(__OpenBSD__) \
    || defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)
        i = KQUEUE;
#endif
    }
    return i;
}


Multiplexer *MultiplexerFactory::getNew(int type)
{
    switch (type)
    {
#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
#if 0
    case RT_SIG:
        return new RTsigio();
#endif

    case BEST:
    case EPOLL:
        return new epoll();
#endif

#if defined(sun) || defined(__sun)
    case BEST:
    case DEV_POLL:
        return new DevPoller();
#endif

#if defined(__FreeBSD__ ) || defined(__NetBSD__) || defined(__OpenBSD__) \
    || defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)
    case BEST:
    case KQUEUE:
        return new KQueuer();
#endif
    case POLL:
        return new Poller();
    default:
        return NULL;
    }
}

void MultiplexerFactory::recycle(Multiplexer *ptr)
{
    if (ptr)
        delete ptr;
}
