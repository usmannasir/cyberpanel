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
#include <http/pipeappender.h>

#include <edio/multiplexer.h>
#include <edio/multiplexerfactory.h>
#include <log4cxx/logger.h>
#include <lsr/ls_fileio.h>
#include <util/iovec.h>

#include <extensions/fcgi/fcgiapp.h>
#include <extensions/fcgi/fcgiappconfig.h>
#include <extensions/localworker.h>
#include <extensions/registry/extappregistry.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>


using namespace LOG4CXX_NS;

Duplicable *PipeAppender::dup(const char *pName)
{
    Appender *pAppender = new PipeAppender(pName);
    return pAppender;
}


int PipeAppender::reopenExist()
{
//    const char * pName = getName();
//    struct stat st;
//    if ( ::stat( pName, &st) == -1 )
//    {
//        return 0;
//    }
//    if ( m_ino != st.st_ino )
//    {
//        close();
//        return open();
//    }
    return 0;
}


int PipeAppender::open()
{
    m_error = 0;
    if (Appender::getfd() != -1)
        return 0;
    const char *pName = getName();
    if (!pName)
    {
        m_error = errno = EINVAL;
        return LS_FAIL;
    }
    FcgiApp *pApp = (FcgiApp *)ExtAppRegistry::getApp(EA_LOGGER, pName);
    if (!pApp)
        return LS_FAIL;
    if (pApp->getCurInstances() >= pApp->getConfig().getInstances())
        return LS_FAIL;
    int fds[2];
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, fds) == -1)
    {
        m_error = errno;
        LS_ERROR("[PipeAppender] socketpair() failed!");
        return LS_FAIL;
    }
    fcntl(fds[0], F_SETFD, FD_CLOEXEC);
    m_pid = LocalWorker::workerExec(pApp->getConfig(), fds[1]);
    ::close(fds[1]);
    if (m_pid == -1)
    {
        m_error = errno;
        ::close(fds[0]);
        return LS_FAIL;
    }
    long fl;
    fl = ::fcntl(fds[0], F_GETFL);
    fl = fl | MultiplexerFactory::getMultiplexer()->getFLTag();
    ::fcntl(fds[0], F_SETFL, fl);
    setfd(fds[0]);
    EventReactor::setfd(fds[0]);
    MultiplexerFactory::getMultiplexer()->add(this, POLLERR | POLLHUP);
    m_buf.clear();
    return 0;
}

int PipeAppender::close()
{
    // stop previous external logger

    MultiplexerFactory::getMultiplexer()->remove(this);
    EventReactor::setfd(-1);
    ::close(getfd());
    setfd(-1);

    if (m_pid != -1)
        kill(m_pid, SIGTERM);
    m_pid = -1;
    return 0;
}


int PipeAppender::append(const char *pBuf, int len)
{
    if (Appender::getfd() == -1)
        if (open() == -1)
            return LS_FAIL;
    if (!m_buf.empty())
    {
        flush();
        if (!m_buf.empty())
            return m_buf.cache(pBuf, len, 0);
    }
    int ret = ::ls_fio_write(Appender::getfd(), pBuf, len);
    if (ret < len)
    {
        if ((ret > -1) || (errno == EAGAIN))
        {
            LS_NOTICE("[PipeAppender:%d] cache output: %d", Appender::getfd(),
                      len - ret);
            MultiplexerFactory::getMultiplexer()->continueWrite(this);
            return m_buf.cache(pBuf, len, (ret == -1) ? 0 : ret);
        }
        else
            close();
    }
    return ret;
}

int PipeAppender::flush()
{
    LS_NOTICE("[PipeAppender:%d] flush() cache size: %d", Appender::getfd(),
              m_buf.size());
    if (!m_buf.empty())
    {
        IOVec iov;
        m_buf.getIOvec(iov);
        int ret = ::writev(Appender::getfd(), iov.get(), iov.len());
        LS_NOTICE("[PipeAppender] flush() writev() return %d", ret);
        if (ret > 0)
        {
            if (m_buf.size() <= ret)
                m_buf.clear();
            else
                m_buf.pop_front(ret);
            if (!m_buf.empty())
                return 0;
        }
        else
        {
            if (errno != EAGAIN)
            {
                m_error = errno;
                close();
                return LS_FAIL;
            }
            return 0;
        }

    }
    MultiplexerFactory::getMultiplexer()->suspendWrite(this);
    return 0;
}

int PipeAppender::handleEvents(short event)
{
    if (event & POLLOUT)
        flush();
    if (event & (POLLHUP | POLLERR))
        close();
    return 0;
}

int PipeAppender::isFull()
{
    return !m_buf.empty();
}

int PipeAppender::isFail()
{
    return m_error;
}




