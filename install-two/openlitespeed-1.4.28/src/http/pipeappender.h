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
#ifndef PIPEAPPENDER_H
#define PIPEAPPENDER_H


#include <lsdef.h>
#include <log4cxx/appender.h>
#include <edio/eventreactor.h>
#include <edio/outputbuf.h>


class PipeAppender : public LOG4CXX_NS::Appender, public EventReactor
{
    OutputBuf       m_buf;
    int             m_pid;
    int             m_fd;
    int             m_error;

    int     flush();

public:
    explicit PipeAppender(const char *pName)
        : Appender(pName)
        , m_pid(-1)
        , m_fd(-1)
        , m_error(0)
    {}
    Duplicable *dup(const char *pName);

    ~PipeAppender() {};
    static int init();

    void setfd(int fd)            {   m_fd = fd;      }
    virtual int getfd() const       {   return m_fd;    }

    virtual int open();
    virtual int close();
    virtual int reopenExist();
    virtual int append(const char *pBuf, int len);
    virtual int handleEvents(short event);
    virtual int isFull();
    virtual int isFail();
    LS_NO_COPY_ASSIGN(PipeAppender);
};


#endif
