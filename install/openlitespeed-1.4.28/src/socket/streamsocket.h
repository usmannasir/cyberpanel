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
#ifndef STREAMSOCKET_H
#define STREAMSOCKET_H

#include <socket/coresocket.h>
#include <sys/types.h>
#include <sys/uio.h>


class StreamSocket : public CoreSocket
{
public:
    StreamSocket() {};
    StreamSocket(int iDomain)
        : CoreSocket(iDomain, SOCK_STREAM)
    {}
    ~StreamSocket() {};


    int     connect(const SockAddr *serv_addr, socklen_t addrlen)
    {   return ::connect(getfd(), serv_addr, addrlen); }

    int     shutdown(int how = SHUT_RDWR)
    {   return ::shutdown(getfd(), how);              }

    int     send(const void *msg, size_t len, int flags = 0)
    {   return ::send(getfd(), msg, len , flags);     }

    int     recv(void *buf, size_t len, int flags = 0)
    {   return ::recv(getfd(), buf, len, flags);      }

    ssize_t read(void *buf, size_t count)
    {   return ::read(getfd(), buf, count);           }

    ssize_t write(const void *buf, size_t count)
    {   return ::write(getfd(), buf, count);          }

    int     readv(const struct iovec *vector, int count)
    {   return ::readv(getfd(), vector, count);       }

    int     writev(const struct iovec *vector, int count)
    {   return ::writev(getfd(), vector, count);      }

};

#endif
