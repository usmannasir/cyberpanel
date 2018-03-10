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
#ifndef AIOOUTPUTSTREAM_H
#define AIOOUTPUTSTREAM_H

#include <lsdef.h>
#include <edio/aioeventhandler.h>

#include <aio.h>
#include <sys/types.h>

#ifdef LS_AIO_USE_KQ
#include <sys/event.h>
#endif

class AutoBuf;

class AioReq
{
    struct aiocb    m_aiocb;

private:
    void setcb(int fildes, void *buf, size_t nbytes, int off, void *handler);

public:
    AioReq();

    void *getBuf()
    {
        void *p = (void *)m_aiocb.aio_buf;
        m_aiocb.aio_buf = NULL;
        return p;
    }

    off_t getOffset()
    {   return m_aiocb.aio_offset;  }

    int getError()
    {   return aio_error(&m_aiocb);   }

    //NOTICE: If the error is EINPROGRESS, the result of this is undefined.
    int getReturn()
    {   return aio_return(&m_aiocb);  }

    int read(int fildes, void *buf, int nbytes, int offset,
             AioEventHandler *pHandler)
    {
        setcb(fildes, buf, nbytes, offset, pHandler);
        return aio_read(&m_aiocb);
    }

    int write(int fildes, void *buf, int nbytes, int offset,
              AioEventHandler *pHandler)
    {
        setcb(fildes, buf, nbytes, offset, pHandler);
        return aio_write(&m_aiocb);
    }
    LS_NO_COPY_ASSIGN(AioReq);
};

class AioOutputStream : public AioEventHandler, private AioReq
{
    int             m_fd;
    char            m_async;
    char            m_flushRequested;
    char            m_closeRequested;
    char            m_iFlock;
    AutoBuf        *m_pRecv;
    AutoBuf        *m_pSend;

private:
    int syncWrite(const char *pBuf, int len);

public:

    AioOutputStream()
        : AioReq()
        , m_fd(-1)
        , m_async(0)
        , m_flushRequested(0)
        , m_closeRequested(0)
        , m_iFlock(0)
        , m_pRecv(NULL)
        , m_pSend(NULL)
    {
    }
    virtual ~AioOutputStream() {};

    int getfd() const               {   return m_fd;            }
    void setfd(int fd)            {   m_fd = fd;              }
    int open(const char *pathname, int flags, mode_t mode);
    int close();
    bool isAsync() const            {   return m_async == 1;    }

    void setFlock(int l)           {   m_iFlock = l;           }

    void setAsync()
    {
#ifdef LS_AIO_USE_AIO
        m_async = 1;
#endif
    }

    int append(const char *pBuf, int len);
    virtual int onAioEvent();
    int flush();
    LS_NO_COPY_ASSIGN(AioOutputStream);
};



#endif //AIOOUTPUTSTREAM_H
