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
#include <util/pidfile.h>

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>
#include <lsr/ls_fileio.h>
#include <lsr/ls_strtool.h>

PidFile::PidFile()
    : m_iFd(-1)
{
}
PidFile::~PidFile()
{
}

static int lockFile(int fd, short lockType = F_WRLCK)
{
    int ret;
    struct flock lock;
    lock.l_type = lockType;
    lock.l_start = 0;
    lock.l_whence = SEEK_SET;
    lock.l_len = 0;
    while (1)
    {
        ret = fcntl(fd, F_SETLK, &lock);
        if ((ret == -1) && (errno == EINTR))
            continue;
        return ret;
    }
}

static int writePid(int fd, pid_t pid)
{
    char achBuf[20];
    int len = ls_snprintf(achBuf, 20, "%d\n", (int)pid);
    if (ftruncate(fd, 0) || (ls_fio_write(fd, achBuf, len) != len))
    {
        ls_fio_close(fd);
        return LS_FAIL;
    }
    return fd;
}


int PidFile::openPidFile(const char *pPidFile)
{
    //closePidFile();
    if (m_iFd == -1)
    {
        m_iFd  = ls_fio_open(pPidFile, O_WRONLY | O_CREAT, 0644);
        if (m_iFd != -1)
            fcntl(m_iFd, F_SETFD,  FD_CLOEXEC);
    }
    return m_iFd;
}

int PidFile::lockPidFile(const char *pPidFile)
{
    if (openPidFile(pPidFile) < 0)
        return LS_FAIL;
    if (lockFile(m_iFd))
    {
        ls_fio_close(m_iFd);
        m_iFd = -1;
        return -2;
    }
    return 0;
}
int PidFile::writePidFile(const char *pPidFile, int pid)
{
    if (openPidFile(pPidFile) < 0)
        return LS_FAIL;
    ::writePid(m_iFd, pid);
    ls_fio_close(m_iFd);
    m_iFd = -1;
    return 0;
}

int PidFile::writePid(int pid)
{
    int ret = ::writePid(m_iFd, pid);
    if (ret < 0)
        return ret;
    while (1)
    {
        ret = fstat(m_iFd, &m_st);
        if ((ret == -1) && (errno = EINTR))
            continue;
        return ret;
    }
}

void PidFile::closePidFile()
{
    if (m_iFd >= 0)
    {
        lockFile(m_iFd, F_UNLCK);
        close(m_iFd);
        m_iFd = -1;
    }
}


int PidFile::testAndRemovePidFile(const char *pPidFile)
{
    struct stat st;
    if ((ls_fio_stat(pPidFile, &st) == 0) &&
        (st.st_mtime == m_st.st_mtime) &&
        (st.st_size == m_st.st_size) &&
        (st.st_ino == m_st.st_ino))
        unlink(pPidFile);
    return 0;
}

int PidFile::testAndRelockPidFile(const char *pPidFile, int pid)
{
    struct stat st;
    if ((ls_fio_stat(pPidFile, &st) == -1) ||
        (st.st_mtime != m_st.st_mtime) ||
        (st.st_size != m_st.st_size) ||
        (st.st_ino != m_st.st_ino))
    {
        closePidFile();
        int ret = lockPidFile(pPidFile);
        if (!ret)
            ret = writePid(pid);
        return ret;
    }
    return 0;
}



