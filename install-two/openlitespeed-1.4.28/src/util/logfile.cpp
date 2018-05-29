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
#include "logfile.h"
#include <lsr/ls_fileio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <time.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdarg.h>


#define DEFAULT_FILEMODE 0666
LogFile::LogFile(int fd)
    : m_pFileName(NULL)
    , m_iFd(fd)
    , m_iAppend(1)
    , m_iBackupMode(NONE)
    , m_iMaxSize(-1)
    , m_iLastDay(0)
    , m_iKeepDays(0)
{
}

LogFile::LogFile(const char *pFileName, int iAppend)
    : m_pFileName(NULL)
    , m_iFd(-1)
    , m_iAppend(iAppend)
    , m_iBackupMode(SIZE)
    , m_iMaxSize(1024 * 1024)
    , m_iLastDay(0)
    , m_iKeepDays(0)
{
    if (pFileName)
        m_pFileName = strdup(pFileName);
}

LogFile::~LogFile()
{
    if (m_pFileName)
        free(m_pFileName);
    if (m_iFd)
        close();
}

int LogFile::open()
{
    if (m_iFd != -1)
        return EBUSY;
    if (!m_pFileName)
        return EINVAL;
    int flag = O_WRONLY | O_CREAT;
    if (!m_iAppend)
        flag |= O_TRUNC;
    else
        flag |= O_APPEND;
    m_iFd = ::open(m_pFileName, flag, DEFAULT_FILEMODE);
    fcntl(m_iFd, F_SETFD, FD_CLOEXEC);
    return (m_iFd == -1) ? errno : 0;
}

int LogFile::close()
{
    if (m_iFd != -1)
    {
        ::close(m_iFd);
        m_iFd = -1;
    }
    return 0;
}

int LogFile::fprintf(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    int ret = vprintf(fmt, ap);
    va_end(ap);
    return ret;
}
int LogFile::vprintf(const char *fmt, va_list ap)
{
    char achLine[4096];
    int max = 4096;
    int n;
    n = vsnprintf(achLine, max, fmt, ap);
    if (n > max)
        n = max;
    return write(achLine, n);
}

int LogFile::setFileName(const char *pName)
{

    if (pName && m_pFileName && (strcmp(pName , m_pFileName) == 0))
        return 0;
    if (m_iFd != -1)
        close();
    if (m_pFileName)
        free(m_pFileName);
    if (pName)
    {
        m_pFileName = strdup(pName);
        if (!m_pFileName)
            return ENOMEM;
    }
    else
        m_pFileName = NULL;
    return 0;
}

int LogFile::backup()
{
    bool shouldBackup = false;
    if (m_pFileName  == NULL)
        return 0;
    long curSize = 0;
    struct stat st;
    if (ls_fio_stat(m_pFileName, &st) == 0)
    {
        curSize = st.st_size;
        struct stat st1;
        if (fstat(m_iFd, &st1) == 0)
        {
            if (st1.st_ino != st.st_ino)
            {
                close();
                open();
            }
        }
    }
    else
    {
        close();
        open();
    }
    if (m_iBackupMode & SIZE)
    {
        if ((m_iMaxSize > 0) && (curSize > m_iMaxSize))
            shouldBackup = true;
    }
    if (m_iBackupMode & DAILY)
    {
        time_t lNow = time(NULL);
        struct tm tmTmp;
        ::localtime_r(&lNow, &tmTmp);
        if (m_iLastDay != tmTmp.tm_yday)
        {
            shouldBackup = true;
            m_iLastDay = tmTmp.tm_yday;
        }
    }
    if (shouldBackup)
    {
        close();
        int ret = renameOldFile();
        if (ret != 0)
        {
            //TODO: renameOldFile() failed;
        }
        open();
        if (m_iKeepDays > 0)
            removeOldFiles();
    }
    return 0;
}

int LogFile::renameOldFile()
{
    char achBuf[256];
    char *pMoreSuffix;
    int max = 256;
    int n = 0;
    time_t lNow = time(NULL);
    struct tm tmTmp;
    ::localtime_r(&lNow, &tmTmp);
    n = ls_snprintf(achBuf, max, "%s.%04d_%02d_%02d",
                    m_pFileName, tmTmp.tm_year + 1900,
                    tmTmp.tm_mon + 1, tmTmp.tm_mday);
    max -= n;
    pMoreSuffix = achBuf + n;
    int suffix = 1;
    int ret;
    struct stat st;
    while (((ret = ls_fio_stat(achBuf, &st)) != -1))
        ls_snprintf(pMoreSuffix, max, ".%d", suffix++);
    ret = ::rename(m_pFileName, achBuf);
    return (ret) ? errno : 0;

}

int LogFile::removeOldFiles()
{
    time_t tm = time(NULL) - 3600L * 24 * m_iKeepDays;
    return removeSimiliarFiles(m_pFileName, tm);
}



