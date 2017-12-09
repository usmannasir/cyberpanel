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
#include "httpsignals.h"

#include <unistd.h>
#include <signal.h>
#include <stdio.h>

int HttpSignals::s_iEvents = 0;

static void sigquit(int sig)
{
    //printf( "sigquit()!\n" );
    //HttpServer::getInstance().shutdown();
    HttpSignals::orEvent(HS_STOP);
}

static void sigpipe(int sig)
{
    //printf( "sigpipe()!\n" );
}

static void sigalarm(int sig)
{
    HttpSignals::orEvent(HS_ALARM);
}

static void sighup(int sig)
{
    //fprintf( stderr, "sighup()!\n" );
    HttpSignals::orEvent(HS_HUP);
}

static void sigusr1(int sig)
{
    HttpSignals::orEvent(HS_USR1);
}

static void sigusr2(int sig)
{
    HttpSignals::orEvent(HS_USR2);
}

void HttpSignals::orEvent(int event)
{   s_iEvents |= event;     }


void HttpSignals::init(sighandler_t sigchild)
{
    SignalUtil::signal(SIGTERM, sigquit);
#ifdef RUN_TEST
    SignalUtil::signal(SIGINT, sigquit);
#endif
    SignalUtil::signal(SIGHUP, sighup);
    SignalUtil::signal(SIGPIPE, sigpipe);
    SignalUtil::signal(SIGCHLD, sigchild);
    SignalUtil::signal(SIGALRM, sigalarm);
    SignalUtil::signal(SIGUSR1, sigusr1);
    SignalUtil::signal(SIGUSR2, sigusr2);
}





