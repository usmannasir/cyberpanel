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
#ifndef CORESOCKET_H
#define CORESOCKET_H

#include <sys/types.h>
#include <sys/socket.h>

#include <lsdef.h>
#include <socket/sockdef.h>



#define INVALID_FD  -1
class GSockAddr;
class CoreSocket
{
private:    //class members
    int m_ifd;      //file descriptor
protected:

    CoreSocket(int fd = INVALID_FD)
        : m_ifd(fd)
    {}
    CoreSocket(int domain, int type, int protocol = 0)
    {
        int fd = ::socket(domain, type, protocol);
        setfd(fd);
    }
    void    setfd(int ifd) { m_ifd = ifd;  }

public:
    enum
    {
        FAIL = -1,
        SUCCESS = 0
    };

    virtual ~CoreSocket()
    {
        if (getfd() != INVALID_FD)
            close();
    }
    int     getfd() const   { return m_ifd;     }

    int     close();

    int     getSockName(SockAddr *name, socklen_t *namelen)
    {   return ::getsockname(getfd(), name, namelen);   }

    int     getSockOpt(int level, int optname, void *optval, socklen_t *optlen)
    {   return ::getsockopt(getfd(), level, optname, optval, optlen);   }

    int     setSockOpt(int level, int optname, const void *optval,
                       socklen_t optlen)
    {   return ::setsockopt(getfd(), level, optname, optval, optlen);   }

    int     setSockOpt(int optname, const void *optval, socklen_t optlen)
    {   return setSockOpt(SOL_SOCKET, optname, optval, optlen);         }

    int     setSockOptInt(int optname, int val)
    {   return setSockOpt(optname, (void *)&val, sizeof(val));  }

    int     setTcpSockOptInt(int optname, int val)
    {   return ::setsockopt(getfd(), IPPROTO_TCP, optname, &val, sizeof(int)); }

    int     setReuseAddr(int reuse)
    {   return setSockOptInt(SO_REUSEADDR, reuse);  }

    int     setRcvBuf(int size)
    {   return setSockOptInt(SO_RCVBUF, size);   }

    int     setSndBuf(int size)
    {   return setSockOptInt(SO_SNDBUF, size);   }

    static int  connect(const char *pURL, int iFLTag, int *fd,
                        int dnslookup = 0, int nodelay = 1);
    static int  connect(const GSockAddr &server, int iFLTag, int *fd,
                        int nodelay = 1);
    static int  bind(const GSockAddr &server, int type, int *fd);
    static int  listen(const char *pURL, int backlog, int *fd,
                       int sndBuf = -1, int rcvBuf = -1);
    static int  listen(const GSockAddr &addr, int backlog, int *fd,
                       int sndBuf = -1, int rcvBuf = -1);


    LS_NO_COPY_ASSIGN(CoreSocket);
};

#endif
