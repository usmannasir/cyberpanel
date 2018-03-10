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
#ifndef DATAGRAMSOCKET_H
#define DATAGRAMSOCKET_H

#include <socket/coresocket.h>


class DatagramSocket : public CoreSocket
{
protected:
    DatagramSocket(int iDomain)
        : CoreSocket(iDomain, SOCK_DGRAM)
    {}
public:
    ~DatagramSocket() {}

    int     sendTo(const void *msg, size_t len, int flags,
                   const SockAddr *to, socklen_t tolen)
    {   return ::sendto(getfd(), msg, len, flags, to, tolen);    }

    int     recvFrom(void  *buf,  size_t len, int flags,
                     SockAddr *from, socklen_t *fromlen)
    {   return ::recvfrom(getfd(), buf, len, flags, from, fromlen);  }

};

#endif
