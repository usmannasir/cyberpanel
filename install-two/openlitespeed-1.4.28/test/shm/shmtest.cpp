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
#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#include <shm/lsshm.h>
#include <modules/lua/lsluaengine.h>
#include <edio/multiplexer.h>
#include <edio/multiplexerfactory.h>

#include <http/httplog.h>

#include <util/datetime.h>

#include <errno.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <ctype.h>

const char *progname;
char *argv0 = NULL;

void onIdleTime();

static int initMultiplexer(const char *pType)
{
    Multiplexer *pMplx;
    int iMultiplexerType = MultiplexerFactory::getType(pType);
    pMplx = MultiplexerFactory::getNew(iMultiplexerType);
    if (pMplx != NULL)
    {
        if (!pMplx->init(1024))
        {
            MultiplexerFactory::setMultiplexer(pMplx);
            return 0;
        }
    }
    return LS_FAIL;
}

static void processTimer()
{
    struct timeval tv;
    gettimeofday(&tv, NULL);

    //FIXME: debug code
    //LS_DBG_L( "processTimer()" );

    DateTime::s_curTime = tv.tv_sec;
    DateTime::s_curTimeUs = tv.tv_usec;

    MultiplexerFactory::getMultiplexer()->timerExecute();
}

int eventLoop()
{
    int ret;
    // register int sigEvent;
    while (true)
    {
        ret = MultiplexerFactory::getMultiplexer()->waitAndProcessEvents(1000);
        if ((ret == -1) && errno)
        {
            if (!((errno == EINTR) || (errno == EAGAIN)))
            {
                fprintf(stderr, "Unexpected error inside event loop: %s", strerror(errno));
                return 1;
            }
        }
        //printf( ".\n" );
        processTimer();
        /*
                if ( (sigEvent = HttpSignals::gotEvent()) )
                {
                    HttpSignals::resetEvents();
                    if ( sigEvent & HS_USR2 )
                    {
                        HttpLog::toggleDebugLog();
                    }
                    if ( sigEvent & HS_CHILD )
                    {
                        HttpServer::cleanPid();
                    }
                    if ( sigEvent & HS_STOP )
                        break;
                }
                */
        /*        onIdleTime(); */

        /* LsLuaEngine::testCmd(); */
        /*
                static int first = 1;
                if (first)
                {
                    LsLuaEngine::testCmd();
                    first = 0;
                }
        */
    }
    return 0;
}

extern int  testShm();

#include <modules/lua/lsluaengine.h>
int main(int argc, char *argv[])
{
    progname = argv[0];
    HttpLog::init();
    testShm();

#if 0
    // Test the fail message
    // if ( LsLuaEngine::init(LsLuaEngine::LSLUA_ENGINE_JIT, "/usr/lib/junk.so") == -1)
    // if ( LsLuaEngine::init(LsLuaEngine::LSLUA_ENGINE_REGULAR , "/usr/lib/liblua.so") == -1)
    // if ( LsLuaEngine::init(LsLuaEngine::LSLUA_ENGINE_JIT, "/usr/lib/libluajit.so") == -1)
    if (LsLuaEngine::init() == -1)
        return 1;
#endif

    return 0;
    // dont need this...
    initMultiplexer("epoll");
    eventLoop();

    exit(0);
}


