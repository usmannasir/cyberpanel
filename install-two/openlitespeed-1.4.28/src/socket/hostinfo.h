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
#ifndef HOSTINFO_H
#define HOSTINFO_H

#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>

class HostInfo : public hostent
{
private:
    char *m_pBuf;
    int init();
    static void copyMemArray(char **const pDestArray,
                             const char *const *const pArray, int length, char *&pBuf);
    static char *buf_memcpy(char *&pBuf, const char *pSrc, int n);
    static char *buf_strncpy(char *&pBuf, const char *pSrc, int n);

public:
    HostInfo();
    ~HostInfo();
    HostInfo(const hostent &rhs);
    HostInfo &operator=(const hostent &rhs);
    bool getHostByName(const char *name);
    bool getHostByAddr(const void *addr, int len = sizeof(in_addr),
                       int type = AF_INET);


};

#endif
