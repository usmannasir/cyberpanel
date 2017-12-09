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
#include "coresocket.h"

#include "gsockaddr.h"

#include <errno.h>
#include <fcntl.h>
#include <netinet/tcp.h>
#include <string.h>
#include <unistd.h>

#ifndef TCP_FASTOPEN

#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)

#define TCP_FASTOPEN 23

#elif defined(__FreeBSD__)

#define TCP_FASTOPEN 1025

#elif defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)

#define TCP_FASTOPEN 0x105

#endif

#endif // !defined(TCP_FASTOPEN)

/**
  * @return 0, succeed
  *         -1,  invalid URL.
  *         EINPROGRESS, non blocking socket connecting are in progress
  *         Other error code occured when call socket(), connect().
*/

int  CoreSocket::connect(const char *pURL, int iFLTag, int *fd,
                         int dnslookup,
                         int nodelay)
{
    int ret;
    GSockAddr server;
    *fd = -1;
    int tag = NO_ANY;
    if (dnslookup)
        tag |= DO_NSLOOKUP;
    ret = server.set(pURL, tag);
    if (ret != 0)
        return LS_FAIL;
    return connect(server, iFLTag, fd, nodelay);
}


int  CoreSocket::connect(const GSockAddr &server, int iFLTag, int *fd,
                         int nodelay)
{
    int type = SOCK_STREAM;
    int ret;
    *fd = ::socket(server.family(), type, 0);
    if (*fd == -1)
        return LS_FAIL;
    if (iFLTag)
        ::fcntl(*fd, F_SETFL, iFLTag);
    if ((nodelay) && ((server.family() == AF_INET) ||
                      (server.family() == AF_INET6)))
        ::setsockopt(*fd, IPPROTO_TCP, TCP_NODELAY, &nodelay, sizeof(int));

    ret = ::connect(*fd, server.get(), server.len());
    if (ret != 0)
    {
        if (!((iFLTag & O_NONBLOCK) && (errno == EINPROGRESS)))
        {
            ::close(*fd);
            *fd = -1;
        }
        return LS_FAIL;
    }
    return ret;
}


int CoreSocket::listen(const char *pURL, int backlog, int *fd, int sndBuf,
                       int rcvBuf)
{
    int ret;
    GSockAddr server;
    ret = server.set(pURL, 0);
    if (ret != 0)
        return LS_FAIL;
    return listen(server, backlog, fd, sndBuf, rcvBuf);
}


int CoreSocket::listen(const GSockAddr &server, int backLog, int *fd,
                       int sndBuf, int rcvBuf)
{
    int ret;
    ret = bind(server, SOCK_STREAM, fd);
    if (ret)
        return ret;

    if (sndBuf > 4096)
        ::setsockopt(*fd, SOL_SOCKET, SO_SNDBUF, &sndBuf, sizeof(int));
    if (rcvBuf > 4096)
        ::setsockopt(*fd, SOL_SOCKET, SO_RCVBUF, &rcvBuf, sizeof(int));

    if (((server.family() == AF_INET) ||
         (server.family() == AF_INET6)))
    {
        int nodelay = 1;
        ::setsockopt(*fd, IPPROTO_TCP, TCP_NODELAY, &nodelay, sizeof(int));

#ifdef TCP_FASTOPEN
        nodelay = backLog / 2;
        if (nodelay > 256)
            nodelay = 256;
        ::setsockopt(*fd, IPPROTO_TCP, TCP_FASTOPEN, &nodelay, sizeof(int));
#endif
    }

    ret = ::listen(*fd, backLog);

    if (ret == 0)
        return 0;
    ret = errno;
    ::close(*fd);
    *fd = -1;
    return ret;
}


int CoreSocket::bind(const GSockAddr &server, int type, int *fd)
{
    int ret;
    if (!server.get())
        return EINVAL;
    *fd = ::socket(server.family(), type, 0);
    if (*fd == -1)
        return errno;
    int flag = 1;
    if (setsockopt(*fd, SOL_SOCKET, SO_REUSEADDR,
                   (char *)(&flag), sizeof(flag)) == 0)
    {
        ret = ::bind(*fd, server.get(), server.len());
        if (!ret)
            return ret;
    }
    ret = errno;
    ::close(*fd);
    *fd = -1;
    return ret;
}


int CoreSocket::close()
{
    int iRet;
    for (int i = 0; i < 3; i++)
    {
        iRet = ::close(getfd());
        if (iRet != EINTR)   // not interupted
        {
            setfd(INVALID_FD);
            return iRet;
        }
    }
    return iRet;
}


