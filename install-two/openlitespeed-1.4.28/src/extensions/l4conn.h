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
#ifndef L4CONN_H
#define L4CONN_H

#include <lsdef.h>
#include <edio/ediostream.h>
#include <log4cxx/nsdefs.h>

#define MAX_OUTGOING_BUF_ZISE    8192

class GSockAddr;
class L4Handler;
class LogSession;
class LoopBuf;
BEGIN_LOG4CXX_NS
class Logger;
END_LOG4CXX_NS

class L4conn : public EdStream
{
public:
    L4conn(L4Handler  *pL4Handler);
    virtual ~L4conn();

    int onEventDone();
    int onError();
    int onWrite();
    int onRead();
    int close();
    int readv(iovec *vector, size_t count)  {    return 0;  }

    int onInitConnected();

    int doRead();
    int doWrite();


    //Return 0 is OK
    int init(const GSockAddr *pGSockAddr);
    int connectEx(const GSockAddr *pGSockAddr);

    LoopBuf  *getBuf()             {   return m_buf;  }

private:
    char            m_iState;
    L4Handler      *m_pL4Handler;
    LoopBuf        *m_buf;

    enum
    {
        DISCONNECTED,
        CONNECTING,
        PROCESSING,
        CLOSING,
    };

    LOG4CXX_NS::Logger *getLogger() const;
    const char *getLogId();
    LogSession *getLogSession() const;

    LS_NO_COPY_ASSIGN(L4conn);
};

#endif // L4CONN_H
