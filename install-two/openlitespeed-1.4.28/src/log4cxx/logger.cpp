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
#include "logger.h"

#include <util/gfactory.h>
#include <log4cxx/fileappender.h>
#include "patternlayout.h"
#include "loggingevent.h"
#include "ilog.h"
#include "tmplogid.h"
#include "logsession.h"

#include <stdio.h>

BEGIN_LOG4CXX_NS

static int s_inited = 0;
::GFactory *s_pFactory = NULL;
Logger *Logger::s_pDefault = NULL;


Logger::Logger(const char *pName)
    : Duplicable(pName)
    , m_iLevel(Level::DEBUG)
    , m_iAdditive(1)
    , m_pAppender(NULL)
    , m_pLayout(NULL)
    , m_pParent(NULL)
{
}


void Logger::init()
{
    if (!s_inited)
    {
        s_inited = 1;
        s_pFactory = new GFactory();
        if (s_pFactory)
        {
            FileAppender::init();
            Layout::init();
            PatternLayout::init();
            s_pFactory->registerType(new Logger("Logger"));
            s_inited = 1;
        }
    }
}


Logger *Logger::getLogger(const char *pName)
{
    init();
    if (!pName || !*pName)
        pName = ROOT_LOGGER_NAME;
    return (Logger *)s_pFactory->getObj(pName, "Logger");
}


Duplicable *Logger::dup(const char *pName)
{
    return new Logger(pName);
}


static int logSanitize(char *pBuf, int len)
{
    char *pEnd = pBuf + len - 2;
    while (pBuf < pEnd)
    {
        if (*pBuf < 0x20)
        {
            switch (*pBuf)
            {
            case '\t':
            case '\n':
            case '\r':
                break;
            default:
                *pBuf = '.';
                break;
            }
        }
        ++pBuf;
    }
    return len;
}


void Logger::vlog(int level, const char *pId, const char *format,
                  va_list args,
                  int no_linefeed)
{
    char achBuf[8192];
    int messageLen = 0;
    if (pId != NULL)
        messageLen = snprintf(achBuf, sizeof(achBuf) - 1, "[%s] ", pId);
    messageLen += vsnprintf(&achBuf[messageLen],
                            sizeof(achBuf) - 1 - messageLen,  format, args);
    if (messageLen > (int)sizeof(achBuf) - 1)
    {
        messageLen = sizeof(achBuf) - 1;
        achBuf[messageLen] = 0;
    }
    messageLen = logSanitize(achBuf, messageLen);

    if ((level > Level::DEBUG) && (level < Level::TRACE))
        level = Level::DEBUG;

    LoggingEvent event(level, getName(), achBuf, messageLen);

    if (no_linefeed)
        event.m_flag |= LOGEVENT_NO_LINEFEED;

    gettimeofday(&event.m_timestamp, NULL);
    Logger *pLogger = this;
    while (1)
    {
        if (!event.m_pLayout)
            event.m_pLayout = pLogger->m_pLayout;
        if (pLogger->m_pAppender && pLogger->isEnabled(level))
        {
            //if (pLogger->m_pAppender->append(&event) == -1)
            //    break;
            pLogger->m_pAppender->append(&event);
        }
        if (!pLogger->m_pParent || !pLogger->m_iAdditive)
            break;
        pLogger = m_pParent;
    }
}


void Logger::lograw(const char *pBuf, int len)
{
    if (m_pAppender)
    {
        if (m_pAppender->append(pBuf, len) == -1)
            return;
        m_pAppender->flush();
    }
    if (m_pParent && m_iAdditive)
        m_pParent->lograw(pBuf, len);
}


void Logger::lograw(const struct iovec *pIov, int len)
{
    const struct iovec *end = pIov + len;
    for (; pIov < end; ++pIov)
    {
        lograw((const char *) pIov->iov_base, pIov->iov_len);
    }
    
}

void Logger::s_vlog(int level, LogSession *pLogSession,
                    const char *format, va_list args, int no_linefeed)
{
    log4cxx::Logger *l = (pLogSession && pLogSession->getLogger())
                         ? pLogSession->getLogger()
                         : log4cxx::Logger::getDefault();
    l->vlog(level, pLogSession ? pLogSession->getLogId() : NULL,
            format, args, no_linefeed);
}


void Logger::s_log(int level, LogSession *pLogSession,
                   const char *format, ...)
{
    log4cxx::Logger *l = (pLogSession && pLogSession->getLogger())
                         ? pLogSession->getLogger()
                         : log4cxx::Logger::getDefault();

    va_list  va;
    va_start(va, format);
    l->vlog(level, pLogSession ? pLogSession->getLogId() : NULL, format, va,
            0);
    va_end(va);
}


void Logger::s_log(int level, TmpLogId *pId,
                   const char *format, ...)
{
    log4cxx::Logger *l = log4cxx::Logger::getDefault();
    va_list  va;
    va_start(va, format);
    l->vlog(level, pId ? pId->getLogId() : NULL, format, va, 0);
    va_end(va);

}


void Logger::s_log(int level, log4cxx::Logger *l,
                   const char *format, ...)
{
    if (l == NULL)
        l = log4cxx::Logger::getDefault();
    va_list  va;
    va_start(va, format);
    l->vlog(level, format, va);
    va_end(va);
}


void Logger::s_log(int level, log4cxx::ILog *pILog,
                   const char *format, ...)
{
    log4cxx::Logger *l = (pILog && pILog->getLogger())
                         ? pILog->getLogger()
                         : log4cxx::Logger::getDefault();
    va_list  va;
    va_start(va, format);
    l->vlog(level, pILog ? pILog->getLogId() : NULL, format, va, 0);
    va_end(va);

}


void Logger::s_log(int level, const char *format, ...)
{
    log4cxx::Logger *l = log4cxx::Logger::getDefault();
    va_list  va;
    va_start(va, format);
    l->vlog(level, format, va);
    va_end(va);
}


void Logger::s_vlograw(log4cxx::Logger *l, const char *format, va_list va)
{
    char achBuf[8192];
    int messageLen ;
    messageLen = vsnprintf(achBuf,
                            sizeof(achBuf) - 1,  format, va);
    if (messageLen > (int)sizeof(achBuf) - 1)
    {
        messageLen = sizeof(achBuf) - 1;
        achBuf[messageLen] = 0;
    }
    messageLen = logSanitize(achBuf, messageLen);
    if (!l)
        l = log4cxx::Logger::getDefault();
    l->lograw(achBuf, messageLen);
}



void Logger::s_lograw(const char *format, ...)
{
    va_list  va;
    va_start(va, format);
    s_vlograw(NULL, format, va);
    va_end(va);
}

END_LOG4CXX_NS

