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
#ifndef LOGFILE_H
#define LOGFILE_H

#include <lsdef.h>

#include <stdarg.h>
#include <sys/types.h>
#include <sys/uio.h>
#include <unistd.h>


class LogFile
{
    char       *m_pFileName;
    int         m_iFd;
    int         m_iAppend;
    int         m_iBackupMode;
    long        m_iMaxSize;
    int         m_iLastDay;
    int         m_iKeepDays;
    enum
    {
        NONE,
        SIZE = 1,
        DAILY = 2
    };
    int renameOldFile();
    int removeOldFiles();
public:
    LogFile(const char *pFileName, int iAppend = 0);
    LogFile(int fd);
    ~LogFile();
    int open();
    int close();
    int getFd() const   {   return m_iFd;    }

    int write(const char *pBuf, int len)
    {
        int ret = ::write(m_iFd, pBuf, len);
        if (ret == -1)
        {
            close();
            open();
            ret = ::write(m_iFd, pBuf, len);
        }
        return ret;
    }
    int writev(const struct iovec *vector, int count)
    {
        int ret = ::writev(m_iFd, vector, count);
        if (ret == -1)
        {
            close();
            open();
            ret = ::writev(m_iFd, vector, count);
        }
        return ret;
    }
    int fprintf(const char *fmt, ...);
    int vprintf(const char *fmt, va_list ap);
    int setFileName(const char *pName);
    const char *getFileName() const
    {   return m_pFileName; }
    int backup();
    void setAppend(int iAppend)
    {   m_iAppend = iAppend;    }
    void setDailyBackup()
    {   m_iBackupMode |= DAILY;  }
    void setSizeBackup(long maxSize)
    {   m_iBackupMode |= SIZE; m_iMaxSize = maxSize; }
    void setNoBackup()
    {   m_iBackupMode = NONE;   }
    void setKeepDays(int days)    {   m_iKeepDays = days;     }
    int getKeepDays() const         {   return m_iKeepDays;     }


    LS_NO_COPY_ASSIGN(LogFile);
};

extern int removeSimiliarFiles(const char *pPath, long tm);

#endif
