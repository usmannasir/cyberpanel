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
#ifndef TCPCONNECTION_H
#define TCPCONNECTION_H

#include <errno.h>
#include <socket/streamsocket.h>
#include <socket/gsockaddr.h>


class TcpServerSocket;
class TcpConnection : public StreamSocket
{
    friend class TcpServerSocket;
private:
    GSockAddr    m_peerAddr;
    TcpConnection(const TcpConnection &rhs);
    void operator=(const TcpConnection &rhs);
protected:
public:
    explicit TcpConnection(int fd)
        : StreamSocket()
    {   setfd(fd); }
    TcpConnection()
        : StreamSocket(PF_INET)
    {}
    ~TcpConnection() {};
    GSockAddr *getPeerAddr() {   return &m_peerAddr;  }

    int     getPeerName(SockAddr &name, socklen_t &namelen)
    {
        return ::getpeername(getfd(), &name, &namelen);
    }

    void    setPeerAddr(const GSockAddr *pAddr);

    int     connect(const GSockAddr *pDest)
    {   return StreamSocket::connect(pDest->get(), pDest->len()); }

    int     connect(const in_addr_t addr, int port)
    {
        m_peerAddr.set(addr, port);
        return connect(&m_peerAddr);
    }

    int     connect(const char *pAddr)
    {
        m_peerAddr.set(PF_INET, pAddr, NO_ANY);
        return connect(&m_peerAddr);
    }
    const char   *getPeerAddr(char *pAddr, int len) const
    {
        return m_peerAddr.toAddrString(pAddr, len);
    }
};

#endif
