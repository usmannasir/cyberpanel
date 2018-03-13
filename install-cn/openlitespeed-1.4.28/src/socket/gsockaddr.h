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
#ifndef GSOCKADDR_H
#define GSOCKADDR_H


#include <inttypes.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>

#define DO_NSLOOKUP     1
#define NO_ANY          2
#define ADDR_ONLY       4
#define DO_NSLOOKUP_DIRECT  8

class AdnsReq;
class GSockAddr
{
private:
    union
    {
        struct sockaddr      *m_pSockAddr;
        struct sockaddr_in   *m_v4;
        struct sockaddr_in6 *m_v6;
        struct sockaddr_un   *m_un;
    };

    int m_len;
    int allocate(int family);
    void release();
    int set2(int family, const char *pURL, int tag, char *pDest);
    int doLookup(int family, const char *p, int tag);

public:
    GSockAddr()
    {
        ::memset(this, 0, sizeof(GSockAddr));
    }
    explicit GSockAddr(int family)
    {
        ::memset(this, 0, sizeof(GSockAddr));
        allocate(family);
    }
    GSockAddr(const in_addr_t addr, const in_port_t port)
    {
        ::memset(this, 0, sizeof(GSockAddr));
        set(addr, port);
    }
    explicit GSockAddr(const struct sockaddr *pAddr)
    {
        ::memset(this, 0, sizeof(GSockAddr));
        allocate(pAddr->sa_family);
        memmove(m_pSockAddr, pAddr, m_len);
    }
    GSockAddr(const GSockAddr &rhs);
    GSockAddr &operator=(const GSockAddr &rhs)
    {   return operator=(*(rhs.m_pSockAddr));    }

    GSockAddr &operator=(const struct sockaddr &rhs);
    GSockAddr &operator=(const in_addr_t addr);
    operator const struct sockaddr *() const   {   return m_pSockAddr;  }
    explicit GSockAddr(const struct sockaddr_in &rhs)
    {
        ::memset(this, 0, sizeof(GSockAddr));
        allocate(AF_INET);
        memmove(m_pSockAddr, &rhs, sizeof(rhs));
    }

    ~GSockAddr()                {   release();          }
    struct sockaddr *get()     {   return m_pSockAddr; }

    int family() const
    {   return m_pSockAddr->sa_family;  }

    int len() const
    {   return m_len;   }

    const struct sockaddr *get() const
    {   return m_pSockAddr; }
    const struct sockaddr_in *getV4() const
    {   return (const struct sockaddr_in *)m_pSockAddr;  }
    const struct sockaddr_in6 *getV6() const
    {   return (const struct sockaddr_in6 *)m_pSockAddr; }
    const char *getUnix() const
    {   return ((sockaddr_un *)m_pSockAddr)->sun_path;  }
    void set(const in_addr_t addr, const in_port_t port);

    void set(const in6_addr *addr, const in_port_t port,
             uint32_t flowinfo = 0);
    int set(const char *pURL, int tag);
    int set(int family, const char *pURL, int tag = 0);

    int asyncSet(int family, const char *pURL, int tag
                 , int (*lookup_pf)(void *arg, const long lParam, void *pParam)
                 , void *ctx, AdnsReq **pReq);

    int setHttpUrl(const char *pHttpUrl, const int len);
    int parseAddr(const char *pString);
    /** return the address in string format. */
    static const char *ntop(const struct sockaddr *pAddr, char *pBuf, int len);
    static uint16_t getPort(const struct sockaddr *pAddr);

    const char *toAddrString(char *pBuf, int len) const
    {   return ntop(m_pSockAddr, pBuf, len);      }
    /** return the address and port in string format. */
    const char *toString(char *pBuf, int len) const;
    const char *toString() const;
    uint16_t getPort() const;
    void setPort(uint16_t port);

    static int compareAddr(const struct sockaddr *pAddr1,
                           const struct sockaddr *pAddr2);
};

#endif
