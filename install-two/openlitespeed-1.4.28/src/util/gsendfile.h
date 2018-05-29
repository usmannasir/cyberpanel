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
#ifndef GSENDFILE_H
#define GSENDFILE_H

#ifdef __cplusplus
extern "C" {
#endif

#if defined(__FreeBSD__ ) || defined(__NetBSD__) || defined(__OpenBSD__)
#include <sys/types.h>
#include <sys/socket.h>
static inline ssize_t gsendfile(int fdOut, int fdIn, off_t *off,
                                off_t size)
{
    ssize_t ret;
    off_t written;
    ret = ::sendfile(fdIn, fdOut, *off, size, NULL, &written, 0);
    if (written > 0)
    {
        ret = written;
        *off += ret;
    }
    return ret;
}
#endif

#if defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)
#include <sys/types.h>
#include <sys/socket.h>
static inline ssize_t gsendfile(int fdOut, int fdIn, off_t *off,
                                off_t size)
{
    ssize_t ret;
    off_t len = size;
    ret = ::sendfile(fdIn, fdOut, *off, &len, NULL, 0);
    if (len > 0)
    {
        ret = len;
        *off += len;
    }
    return ret;
}
#endif

#if defined(sun) || defined(__sun)
#include <sys/sendfile.h>
static inline ssize_t gsendfile(int fdOut, int fdIn, off_t *off,
                                off_t size)
{
    int n = 0;
    sendfilevec_t vec[1];

    vec[n].sfv_fd   = fdIn;
    vec[n].sfv_flag = 0;
    vec[n].sfv_off  = *off;
    vec[n].sfv_len  = size;
    ++n;

    size_t written;
    ssize_t ret = ::sendfilev(fdOut, vec, n, &written);
    if ((!ret) || (errno == EAGAIN))
        ret = written;
    if (ret > 0)
        *off += ret;
    return ret;
}
#endif

#if defined(linux) || defined(__linux) || defined(__linux__) || \
    defined(__gnu_linux__)
#include <sys/sendfile.h>
#define gsendfile ::sendfile
#endif
#if defined(HPUX)
static inline ssize_t gsendfile(int fdOut, int fdIn, off_t *off,
                                off_t size)
{
    return ::sendfile(fdOut, fdIn, off, size, NULL, 0);
}
#endif



#ifdef __cplusplus
}
#endif


#endif

