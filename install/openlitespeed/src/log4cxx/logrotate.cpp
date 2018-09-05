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

#include "logrotate.h"
#include <log4cxx/appender.h>

#include <util/ni_fio.h>
#include <util/gzipbuf.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>


#include <dirent.h>
int removeSimiliarFiles(const char *pPath, long tm)
{
    char achBuf[256];
    memccpy(achBuf, pPath, 0, 255);
    achBuf[255] = 0;
    char *p = strrchr(achBuf, '/');
    if (p == NULL)
        return LS_FAIL;
    *p = 0;
    const char *pOrgFileName = pPath + (p + 1 - achBuf);
    int len = strlen(pOrgFileName);
    DIR *pDir = opendir(achBuf);
    if (!pDir)
        return LS_FAIL;
    *p++ = '/';
    struct dirent *ent;
    while ((ent = readdir(pDir)) != NULL)
    {
        char *pFileName = ent->d_name;
        if ((strncmp(pFileName, pOrgFileName, len) == 0) &&
            (*(pFileName + len) == '.'))
        {
            memccpy(p, pFileName, 0, &(achBuf[255]) - p);
            if (tm != 0)
            {
                struct stat st;
                int ret = nio_stat(achBuf, &st);
                if (ret == 0)
                {
                    if (st.st_mtime >= tm)
                        continue;
                }
            }
            ::unlink(achBuf);
        }
    }
    closedir(pDir);
    return 0;
}


int archiveFile(const char *pFileName, const char *pSuffix,
                int compress, uid_t uid, gid_t gid)
{
    char *pMoreSuffix;
    int max = 1024;
    int n = 0;
    time_t lNow = time(NULL);
    struct tm tmTmp;
    int suffix = 1;
    int ret;
    char achBuf[1024];
    char achName[1024];
    ::localtime_r(&lNow, &tmTmp);
    n = snprintf(achBuf, max, "%s.%04d_%02d_%02d",
                 pFileName, tmTmp.tm_year + 1900,
                 tmTmp.tm_mon + 1, tmTmp.tm_mday);
    max -= n;
    pMoreSuffix = achBuf + n;
    struct stat st;
    int l = 0;
    while (1)
    {
        if (nio_stat(achBuf, &st) == -1)
        {
            strcat(pMoreSuffix, ".gz");
            if (nio_stat(achBuf, &st) == -1)
            {
                pMoreSuffix[l] = 0;
                break;
            }
        }
        l = snprintf(pMoreSuffix, max, ".%02d", suffix++);
    }
    if (pSuffix && *pSuffix)
    {
        snprintf(achName, 1024, "%s%s", pFileName, pSuffix);
        pFileName = achName;
    }
    ret = ::rename(pFileName, achBuf);
    if (ret == -1)
        return ret;
    if (compress)
    {
        int pid = fork();
        if (pid)
            return (pid == -1) ? pid : 0;
        setpriority(PRIO_PROCESS, 0, getpriority(PRIO_PROCESS, 0) + 4);
        snprintf(achName, 1024, "%s.gz", achBuf);
        GzipBuf gzBuf;
        if (gzBuf.compressFile(achBuf, achName) == 0)
            unlink(achBuf);
        else
            unlink(achName);
        chown(achName, uid, gid);
        chmod(achName, 0644);
        exit(0);
    }
    return 0;

}


BEGIN_LOG4CXX_NS


LogRotate::LogRotate()
{
}
LogRotate::~LogRotate()
{
}



int LogRotate::roll(Appender *pAppender, uid_t uid, gid_t gid,
                    off_t rollingSize)
{
    int ret = 0;
    if (testRolling(pAppender, rollingSize, uid, gid))
    {
        ret = archiveFile(pAppender->getName(), NULL,
                          pAppender->getCompress(), uid, gid);
        ret = postRotate(pAppender, uid, gid);
    }
    return ret;
}

int LogRotate::testRolling(Appender *pAppender, off_t rollingSize,
                           uid_t uid, gid_t gid)
{
    int ret = 0;
    const char *pName = pAppender->getName();
    struct stat st;
    if (nio_stat(pName, &st) == -1)
    {
        if (*pName == '/')
        {
            pAppender->close();
            pAppender->open();
            fchown(pAppender->getfd(), uid, gid);
        }
        return ret;
    }
    else if ((st.st_uid != uid) || (st.st_gid != gid))
        chown(pName, uid, gid);
    if (rollingSize <= 0)
        return ret;
    return (st.st_size > rollingSize);
}

int LogRotate::postRotate(Appender *pAppender, uid_t uid, gid_t gid)
{
    pAppender->close();
    pAppender->open();
    fchown(pAppender->getfd(), uid, gid);
    if (pAppender->getKeepDays() > 0)
    {
        time_t tm = time(NULL) - 3600L * 24 * pAppender->getKeepDays();
        return removeSimiliarFiles(pAppender->getName(), tm);
    }
    return 0;
}

int LogRotate::testAndRoll(Appender *pAppender, uid_t uid, gid_t gid)
{
    if (testRolling(pAppender, pAppender->getRollingSize(), uid, gid))
        return roll(pAppender, uid, gid, pAppender->getRollingSize());
    return 0;
}

int LogRotate::testRolling(Appender *pAppender, uid_t uid, gid_t gid)
{   return testRolling(pAppender, pAppender->getRollingSize(), uid, gid);   }




END_LOG4CXX_NS


