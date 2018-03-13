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
#include "stderrlogger.h"

#include <edio/multiplexer.h>
#include <http/httplog.h>
#include <log4cxx/appender.h>
#include <log4cxx/logger.h>

#include <assert.h>
#include <fcntl.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>


StdErrLogger::StdErrLogger()
    : m_iEnabled(0)
    , m_pAppender(NULL)
{
}


StdErrLogger::~StdErrLogger()
{
}


int StdErrLogger::handleEvents(short event)
{
    int ret = 0;
    if (event & POLLIN)
    {
        int len = 1;
        char achBuf[4096];
        while (len > 0)
        {
            len = ::read(EventReactor::getfd(), achBuf, 4096);
            if ((len > 0) && (m_pAppender))
                m_pAppender->append(achBuf, len);
        }
        //m_pAppender->flush();
    }
    else if (event & POLLHUP)
        LS_ERROR("POLLHUP");
    if ((ret != -1) && (event & POLLOUT))
        LS_ERROR("POLLOUT");
    if ((ret != -1) && (event & POLLERR))
        LS_ERROR("POLLERR");
    return 0;

}


int StdErrLogger::setLogFileName(const char *pName)
{
    if (!pName)
        m_pAppender = HttpLog::getErrorLogger()->getAppender();
    else
    {
        m_iEnabled = 1;
        if (m_pAppender)
        {
            if (strcmp(m_pAppender->getName(), pName) == 0)
                return 0;
            else
                m_pAppender->close();
        }
        m_pAppender = LOG4CXX_NS::Appender::getAppender(pName);
    }
    return 0;
}


const char *StdErrLogger::getLogFileName() const
{   return m_pAppender->getName();     }


int StdErrLogger::initLogger(Multiplexer *pMultiplexer)
{
    int fds[2];
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, fds) == -1)
    {
        LS_ERROR("Failed to setup StdErrLogger!");
        return LS_FAIL;
    }
    ::fcntl(fds[0], F_SETFD, FD_CLOEXEC);
    int fl = 0;
    ::fcntl(fds[0], F_GETFL, &fl);
    ::fcntl(fds[0], F_SETFL, fl | pMultiplexer->getFLTag());
    EventReactor::setfd(fds[0]);
    pMultiplexer->add(this, POLLIN | POLLHUP | POLLERR);
#ifndef RUN_TEST
    if (dup2(fds[1], STDERR_FILENO) == -1)
        m_fdStdErr = fds[1];
    else
    {
        close(fds[1]);
        m_fdStdErr = STDERR_FILENO;
    }
#else
    m_fdStdErr = fds[1];
#endif
    return 0;

}

