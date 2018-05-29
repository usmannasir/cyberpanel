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
#include <log4cxx/fileappender.h>
#include <util/gfactory.h>

#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>



BEGIN_LOG4CXX_NS

int FileAppender::init()
{
    return s_pFactory->registerType(new FileAppender("appender.ps"));
}

Duplicable *FileAppender::dup(const char *pName)
{
    FileAppender *pAppender = new FileAppender(pName);
    if (m_stream.isAsync())
        pAppender->setAsync();
    if (strcasecmp(pName, "stdout") == 0)
        pAppender->m_stream.setfd(::dup(1));
    else if (strcasecmp(pName, "stderr") == 0)
        pAppender->m_stream.setfd(::dup(2));
    else
        return pAppender;
    fcntl(pAppender->getfd(), F_SETFD, FD_CLOEXEC);
    return pAppender;
}


int FileAppender::reopenExist()
{
    const char *pName = getName();
    struct stat st;
    if (stat(pName, &st) == -1)
        return 0;
    if (m_ino != st.st_ino)
    {
        close();
        return open();
    }
    return 0;
}


int FileAppender::open()
{
    if (getfd() != -1)
        return 0;
    const char *pName = getName();
    if (!pName)
    {
        errno = EINVAL;
        return LS_FAIL;
    }
    int flag = O_WRONLY | O_CREAT;
    if (!getAppendMode())
        flag |= O_TRUNC ;
    else
        flag |= O_APPEND;
    m_stream.open(pName, flag, 0644);
    if (getfd() == -1)
        return LS_FAIL;
    m_stream.setFlock(getFlock());

    struct stat st;
    if (::fstat(getfd(), &st) != -1)
        m_ino = st.st_ino;
    fcntl(getfd(), F_SETFD, FD_CLOEXEC);
    return 0;
}

int FileAppender::close()
{
    if (getfd() != -1)
        return m_stream.close();
    return 0;
}

int FileAppender::append(const char *pBuf, int len)
{
    if (getfd() == -1)
        if (open() == -1)
            return LS_FAIL;
    return m_stream.append(pBuf, len);
}


END_LOG4CXX_NS


