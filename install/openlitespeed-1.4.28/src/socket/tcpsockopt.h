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
#ifndef TCPSOCKOPT_H
#define TCPSOCKOPT_H

#include <sys/types.h>
#include <netinet/tcp.h>
#include <socket/coresocket.h>


class TcpSockOpt
{
private:
    TcpSockOpt() {};
    ~TcpSockOpt() {};
public:
    static int     setReuseAddr(CoreSocket &sock, int reuse)
    {   return sock.setSockOptInt(SO_REUSEADDR, reuse);  }
    static int     setRcvBuf(CoreSocket &sock, int size)
    {   return sock.setSockOptInt(SO_RCVBUF, size);   }
    static int     setSndBuf(CoreSocket &sock, int size)
    {   return sock.setSockOptInt(SO_SNDBUF, size);   }
    static int     setTcpKeepAlive(CoreSocket &sock, int timeout);
    static int     setTcpNoDelay(CoreSocket &sock, int nodelay)
    {   return sock.setTcpSockOptInt(TCP_NODELAY, nodelay); }
    static int     setTcpCork(CoreSocket &sock, int cork)
    {
#ifdef TCP_CORK
        return sock.setTcpSockOptInt(TCP_CORK, cork);
#else
        return CoreSocket::SUCCESS;
#endif //TCP_CORK
    }
    static int     setKeepAlive(CoreSocket &sock, int keepalive)
    {   return sock.setSockOptInt(SO_KEEPALIVE, keepalive);    }
    static int     setLinger(CoreSocket &sock, int onoff, int lingertime)
    {
        struct linger l;
        l.l_onoff = onoff;
        l.l_linger = lingertime;
        return sock.setSockOpt(SO_LINGER, &l, sizeof(l));
    }
};

#endif
