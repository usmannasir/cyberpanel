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
#ifndef SIGEVENTDISPATCHER_H
#define SIGEVENTDISPATCHER_H

#include <edio/aioeventhandler.h>
#include <edio/eventreactor.h>

#include <signal.h>

class SigEventDispatcher : public EventReactor
{
#if defined(LS_AIO_USE_SIGFD) || defined(LS_AIO_USE_SIGNAL)
private:

    explicit SigEventDispatcher(sigset_t *ss);
    SigEventDispatcher(const SigEventDispatcher &other);
    ~SigEventDispatcher() {}
    SigEventDispatcher &operator=(const SigEventDispatcher *rhs);

public:
    static int processSigEvent();

    static int init();

    virtual int handleEvents(short event);

#elif defined(LS_AIO_USE_KQ)
public:
    static void setAiokoLoaded();
    static short aiokoIsLoaded();
#endif // defined(LS_AIO_USE_SIGFD) || defined(LS_AIO_USE_SIGNAL)
};


#endif //SIGEVENTDISPATCHER_H
