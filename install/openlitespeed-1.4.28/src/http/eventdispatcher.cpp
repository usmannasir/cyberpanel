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
#include "eventdispatcher.h"
#include <edio/multiplexer.h>
#include <edio/multiplexerfactory.h>
#include <edio/sigeventdispatcher.h>
#include <edio/evtcbque.h>
#include <util/datetime.h>
#include <http/httpdefs.h>
#include <http/httplog.h>
#include <http/httpsignals.h>
#include <http/ntwkiolink.h>
#include <http/connlimitctrl.h>
#include <log4cxx/logger.h>
#include <main/httpserver.h>
#include <errno.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>
#include <lsiapi/modulemanager.h>

int highPriorityTask();


EventDispatcher::EventDispatcher()
{
}


EventDispatcher::~EventDispatcher()
{
    release();
}


int EventDispatcher::init(const char *pType)
{
    if (MultiplexerFactory::getMultiplexer())
        return 0;
    MultiplexerFactory::s_iMultiplexerType = MultiplexerFactory::getType(
                pType);
    Multiplexer *pMultiplexer =
        MultiplexerFactory::getNew(MultiplexerFactory::s_iMultiplexerType);
    if (pMultiplexer != NULL)
    {
        if (!pMultiplexer->init(DEFAULT_INIT_POLL_SIZE))
        {
            MultiplexerFactory::setMultiplexer(pMultiplexer);
            pMultiplexer->setPriHandler(highPriorityTask);
            //CallbackQueue::getInstance().initNotifier(pMultiplexer);
            return 0;
        }
    }
    return LS_FAIL;
}


int EventDispatcher::reinit()
{
    if (!MultiplexerFactory::getMultiplexer())
        return LS_FAIL;
    MultiplexerFactory::recycle(MultiplexerFactory::getMultiplexer());
    Multiplexer *pMultiplexer =
        MultiplexerFactory::getNew(MultiplexerFactory::s_iMultiplexerType);
    if (pMultiplexer != NULL)
    {
        if (!pMultiplexer->init(DEFAULT_INIT_POLL_SIZE))
        {
            MultiplexerFactory::setMultiplexer(pMultiplexer);
            pMultiplexer->setPriHandler(highPriorityTask);
            //CallbackQueue::getInstance().initNotifier(pMultiplexer);
            return 0;
        }
    }
    return LS_FAIL;
}


void EventDispatcher::release()
{
    MultiplexerFactory::recycle(MultiplexerFactory::getMultiplexer());
}


int EventDispatcher::stop()
{
    HttpSignals::setSigStop();
    return 0;
}


static void processTimer()
{
    struct timeval tv;
    gettimeofday(&tv, NULL);

    //TEST: debug code
    //LS_DBG_L( "processTimer()" );

    DateTime::s_curTime = tv.tv_sec;
    DateTime::s_curTimeUs = tv.tv_usec;
    NtwkIOLink::setPrevToken(NtwkIOLink::getToken());
    NtwkIOLink::setToken(tv.tv_usec / (1000000 / TIMER_PRECISION));
    if (NtwkIOLink::getToken() < NtwkIOLink::getPrevToken())
        HttpServer::getInstance().onTimer();
    MultiplexerFactory::getMultiplexer()->timerExecute();
}


int highPriorityTask()
{
    if (HttpSignals::gotSigAlarm())
    {
        HttpSignals::resetSigAlarm();
        processTimer();
    }
    ConnLimitCtrl::getInstance().tryAcceptNewConn();
    return 0;
}


static void startTimer()
{
    struct itimerval tmv;
    memset(&tmv, 0, sizeof(struct itimerval));
    tmv.it_interval.tv_usec = 1000000 / TIMER_PRECISION;
    gettimeofday(&tmv.it_value, NULL);
    tmv.it_value.tv_sec = 0;
    NtwkIOLink::setToken(tmv.it_value.tv_usec / tmv.it_interval.tv_usec);
    NtwkIOLink::setPrevToken(NtwkIOLink::getToken());
    tmv.it_value.tv_usec = tmv.it_interval.tv_usec -
                           tmv.it_value.tv_usec % tmv.it_interval.tv_usec;
    setitimer(ITIMER_REAL, &tmv, NULL);
}


/*
#define MLTPLX_TIMEOUT 1000
int EventDispatcher::run()
{
    int ret;
    int sigEvent;
    startTimer();
    while( true )
    {
        ret = MultiplexerFactory::getMultiplexer()->waitAndProcessEvents(
                    MLTPLX_TIMEOUT );
        if (( ret == -1 )&& errno )
        {
            if (!((errno == EINTR )||(errno == EAGAIN)))
            {
                LS_ERROR( "Unexpected error inside event loop: %s", strerror( errno ) ));
                return 1;
            }
        }
        if ( (sigEvent = HttpSignals::gotEvent()) )
        {
            HttpSignals::resetEvents();
            if ( sigEvent & HS_ALARM )
            {
                processTimer();
                ConnLimitCtrl::getInstance().checkWaterMark();

            }
            if ( sigEvent & HS_USR2 )
            {
                HttpLog::toggleDebugLog();
            }
            if ( sigEvent & HS_STOP )
                break;
        }
    }
    return 0;
}
*/

static int s_ppid = 1;
static inline void processTimerNew()
{
    struct timeval tv;
    gettimeofday(&tv, NULL);

    //TEST: debug code
    //int n = tv.tv_usec / ( 1000000 / TIMER_PRECISION );

    DateTime::s_curTime = tv.tv_sec;
    DateTime::s_curTimeUs = tv.tv_usec;
    NtwkIOLink::setPrevToken(NtwkIOLink::getToken());
    NtwkIOLink::setToken(tv.tv_usec / (1000000 / TIMER_PRECISION));
    if (NtwkIOLink::getToken() != NtwkIOLink::getPrevToken())
    {
        if (NtwkIOLink::getToken() < NtwkIOLink::getPrevToken())
        {
            if (getppid() != s_ppid)
                HttpSignals::setSigStop();
            HttpServer::getInstance().onTimer();
        }
        MultiplexerFactory::getMultiplexer()->timerExecute();
        ConnLimitCtrl::getInstance().checkWaterMark();
        //LS_DBG_L( "processTimer()" );
    }

    ModuleManager::getInstance().OnTimer100msec();
}


#define MLTPLX_TIMEOUT 100
int EventDispatcher::run()
{
    int ret;
    int sigEvent;
    s_ppid = getppid();
    while (true)
    {
        ret = MultiplexerFactory::getMultiplexer()->waitAndProcessEvents(
                  MLTPLX_TIMEOUT);
        if ((ret == -1) && errno)
        {
            if (!((errno == EINTR) || (errno == EAGAIN)))
            {
                LS_ERROR("Unexpected error inside event loop: %s", strerror(errno));
                return 1;
            }
        }
        processTimerNew();
#ifdef LS_AIO_USE_SIGNAL
        SigEventDispatcher::processSigEvent();
#endif

        EvtcbQue::getInstance().run();

        if ((sigEvent = HttpSignals::gotEvent()))
        {
            HttpSignals::resetEvents();
            if (sigEvent & HS_USR2)
            {
                HttpLog::toggleDebugLog();
            }
            if (sigEvent & HS_CHILD)
                HttpServer::cleanPid();
            if (sigEvent & HS_STOP)
                break;
        }
    }
    return 0;
}


int EventDispatcher::linger(int timeout)
{
    int ret;
    long endTime = time(NULL) + timeout;
    MultiplexerFactory::getMultiplexer()->setPriHandler(NULL);
    startTimer();
    while ((time(NULL) < endTime)
           && (ConnLimitCtrl::getInstance().getMaxConns()
               > ConnLimitCtrl::getInstance().availConn()))
    {
        ret = MultiplexerFactory::getMultiplexer()->waitAndProcessEvents(
                  MLTPLX_TIMEOUT);
        if (ret == -1)
        {
            if (!((errno == EINTR) || (errno == EAGAIN)))
            {
                LS_ERROR("Unexpected error inside event loop: %s", strerror(errno));
                return 1;
            }
        }
#ifdef LS_AIO_USE_SIGNAL
        SigEventDispatcher::processSigEvent();
#endif
        EvtcbQue::getInstance().run();

        if (HttpSignals::gotSigAlarm())
        {
            HttpSignals::resetEvents();
            processTimer();
        }
        if (HttpSignals::gotSigChild())
            HttpServer::cleanPid();

    }
    return 0;
}


