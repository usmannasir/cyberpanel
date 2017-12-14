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
#ifndef IPV4ADDR_H
#define IPV4ADDR_H

#include <sys/types.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>


class IPv4Addr : public in_addr
{
public:
    IPv4Addr() {};
    IPv4Addr(const char *pAddr)
    { inet_aton(pAddr);               }
    IPv4Addr(const in_addr addr): in_addr(addr) {};
    IPv4Addr(in_addr_t addr) {   s_addr = addr;  }
    int     inet_aton(const char *cp)
    {   return ::inet_pton(AF_INET, cp, this); }
    static  int inet_aton(const char *cp, in_addr *addr)
    {   return ::inet_pton(AF_INET, cp, addr); }
    static  in_addr_t inet_addr(const char *cp)
    {   return ::inet_addr(cp);       }
    char   *inet_ntoa()
    {   return ::inet_ntoa(*this);    }
    // Note: when copy constructor is declared, do not need to override operator=
    // IPv4Addr& operator=( const in_addr& rhs )
    //     {   this->s_addr = rhs.s_addr; return *this;  }
    //void test( IPv4Addr& lhs, in_addr& rhs )
    //    {   lhs = rhs; rhs = lhs; }
    bool operator==(const in_addr_t &rhs)
    {   return (this->s_addr == rhs);  }
};

class IPv4SockAddr : public sockaddr_in
{
    void init()
    {   ::memset((sockaddr_in *)this, 0, sizeof(sockaddr_in));   }
public:
    IPv4SockAddr()
    {   init();     }
    IPv4SockAddr(const sockaddr_in &rhs)
        : sockaddr_in(rhs)
    {}
    IPv4SockAddr(const int family, const in_addr_t addr, const in_port_t port)
    {
        init();
        sin_family      = family;
        sin_addr.s_addr = addr;
        sin_port        = htons(port);
    }
    void set(const int family, const in_addr_t addr, const in_port_t port)
    {
        sin_family      = family;
        sin_addr.s_addr = addr;
        sin_port        = htons(port);
    }
    const char *toAddrString(char *pBuf, int len) const
    {
        return inet_ntop(sin_family, &sin_addr, pBuf, len);
    }
};

#endif
