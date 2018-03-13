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
#ifndef LS_FILEIO_H
#define LS_FILEIO_H

#include <stddef.h>
#include <sys/types.h>
#include <sys/stat.h>

#ifdef __cplusplus
extern "C" {
#endif

int ls_fio_creat(const char *pathname, mode_t mode);
int ls_fio_open(const char *pathname, int flags, mode_t mode);

int ls_fio_close(int fd);
int ls_fio_read(int fd, void *pBuf, int len);
int ls_fio_write(int fd, const void *pBuf, int len);
off_t ls_fio_lseek(int fildes, off_t offset, int whence);
int ls_fio_stat(const char *pathname, struct stat *st);

#ifdef __cplusplus
}
#endif

#endif // LS_FILEIO_H

