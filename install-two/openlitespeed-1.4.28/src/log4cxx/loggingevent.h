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
#ifndef LOGGINGEVENT_H
#define LOGGINGEVENT_H


#include <lsdef.h>
#include <log4cxx/nsdefs.h>
#include <stdarg.h>
#include <stddef.h>
#include <sys/time.h>

BEGIN_LOG4CXX_NS

#define LOGEVENT_NO_LINEFEED 1
class Layout;
class LoggingEvent
{
public:
    int             m_level;
    int             m_flag;
    const char     *m_pLoggerName;
    const char     *m_pMessageBuf;
    int             m_iMessageLen;
    Layout         *m_pLayout;
    struct timeval  m_timestamp;


    LoggingEvent(int level, const char *pLoggerName,
                 const char *pMessage,  int iMessageLen)
        : m_level(level)
        , m_flag(0)
        , m_pLoggerName(pLoggerName)
        , m_pMessageBuf(pMessage)
        , m_iMessageLen(iMessageLen)
        , m_pLayout(NULL)
    {
    }
    ~LoggingEvent() {}



    LS_NO_COPY_ASSIGN(LoggingEvent);
};

END_LOG4CXX_NS

#endif
