/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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

/***************************************************************************
    $Id: ni_fio.h,v 1.1.1.1.2.3 2015/06/30 18:54:12 gwang Exp $
                         -------------------
    begin                : Fri Nov 5 2004
    author               : George Wang
    email                : gwang@litespeedtech.com
 ***************************************************************************/
#ifndef NI_FIO_H
#define NI_FIO_H

#include <stddef.h>
#include <sys/types.h>
#include <sys/stat.h>

#ifdef __cplusplus
extern "C" {
#endif
struct iovec;

extern int nio_creat(const char *pathname, mode_t mode);
extern int nio_open(const char *pathname, int flags, mode_t mode);

extern int nio_close(int fd);
extern int nio_read(int fd, void *pBuf, int len);
extern int nio_pread(int fd, void *pBuf, int len, off_t offset);
extern int nio_write(int fd, const void *pBuf, int len);
extern int nio_writev(int fd, const struct iovec *pIov, int count);
extern int nio_pwrite(int fd, const void *pBuf, int len, off_t offset);
extern off_t nio_lseek(int fildes, off_t offset, int whence);
extern int nio_stat(const char *pathname, struct stat *st);

#ifdef __cplusplus
}
#endif

#endif

