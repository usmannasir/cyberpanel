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
#ifndef STDERRLOGGER_H
#define STDERRLOGGER_H


#include <lsdef.h>
#include <edio/eventreactor.h>
#include <log4cxx/nsdefs.h>
#include <util/tsingleton.h>

BEGIN_LOG4CXX_NS
class Appender;
END_LOG4CXX_NS

class Multiplexer;
class StdErrLogger : public EventReactor, public TSingleton<StdErrLogger>
{
    friend class TSingleton<StdErrLogger>;
    int m_iEnabled;
    int m_fdStdErr;
    LOG4CXX_NS::Appender *m_pAppender;
    StdErrLogger();
public:
    ~StdErrLogger();
    int setLogFileName(const char *pName);
    const char *getLogFileName() const;
    virtual int handleEvents(short event);
    int getStdErr() const   {   return m_fdStdErr;    }
    int initLogger(Multiplexer *pMultiplexer);
    LOG4CXX_NS::Appender *getAppender() const {    return m_pAppender; }
    int isEnabled() const   {   return m_iEnabled;  }

    LS_NO_COPY_ASSIGN(StdErrLogger);
};

#endif
