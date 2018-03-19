/*
 * Copyright 2002 Lite Speed Technologies Inc, All Rights Reserved.
 * LITE SPEED PROPRIETARY/CONFIDENTIAL.
 */

/***************************************************************************
    $Id: ni_fio.c,v 1.1.1.1.2.4 2015/06/30 18:54:12 gwang Exp $
                         -------------------
    begin                : Fri Nov 5 2004
    author               : George Wang
    email                : gwang@litespeedtech.com
 ***************************************************************************/

#include <util/ni_fio.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/uio.h>
#include <unistd.h>


int nio_creat(const char *pathname, mode_t mode)
{
    int ret;
    while (1)
    {
        ret = creat(pathname, mode);
        if ((ret == -1) && (errno == EINTR))
            continue;
        return ret;
    }
}

int nio_open(const char *pathname, int flags, mode_t mode)
{
    int ret;
    while (1)
    {
        ret = open(pathname, flags, mode);
        if ((ret == -1) && (errno == EINTR))
            continue;
        return ret;
    }
}

int nio_close(int fd)
{
    int ret;
    while (1)
    {
        ret = close(fd);
        if ((ret == -1) && (errno == EINTR))
            continue;
        return ret;
    }
}

int nio_read(int fd, void *pBuf, int len)
{
    int ret;
    while (1)
    {
        ret = read(fd, pBuf, len);
        if ((ret == -1) && (errno == EINTR))
            continue;
        return ret;
    }
}

int nio_pread(int fd, void *pBuf, int len, off_t off)
{
    int ret;
    while (1)
    {
        ret = pread(fd, pBuf, len, off);
        if ((ret == -1) && (errno == EINTR))
            continue;
        return ret;
    }
}


int nio_write(int fd, const void *pBuf, int len)
{
    int ret;
    while (1)
    {
        ret = write(fd, pBuf, len);
        if ((ret == -1) && (errno == EINTR))
            continue;
        return ret;
    }
}

int nio_writev(int fd, const struct iovec *pIov, int count)
{
    int ret;
    while (1)
    {
        ret = writev(fd, pIov, count);
        if ((ret == -1) && (errno == EINTR))
            continue;
        return ret;
    }
}

int nio_pwrite(int fd, const void *pBuf, int len, off_t off)
{
    int ret;
    while (1)
    {
        ret = pwrite(fd, pBuf, len, off);
        if ((ret == -1) && (errno == EINTR))
            continue;
        return ret;
    }
}

off_t nio_lseek(int fd, off_t offset, int whence)
{
    off_t ret;
    while (1)
    {
        ret = lseek(fd, offset, whence);
        if ((ret == -1) && (errno == EINTR))
            continue;
        return ret;
    }
}

int nio_stat(const char *pathname, struct stat *st)
{
    int ret;
    while (1)
    {
        ret = stat(pathname, st);
        if ((ret == -1) && ((errno == EINTR) || (errno == EAGAIN)))
            continue;
        return ret;
    }
}


