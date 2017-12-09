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
#include "serverinfo.h"

#include <log4cxx/logger.h>

#include <lsr/ls_time.h>
#include <lsr/ls_fileio.h>

#include <sys/stat.h>
#include <sys/types.h>
#include <signal.h>
#include <unistd.h>

#include <new>

ServerInfo *ServerInfo::s_pServerInfo = NULL;

ServerInfo::ServerInfo(char *pBegin, char *pEnd)
    : m_pidList(pBegin, pEnd)
    , m_pidLinger(-1)
    , m_pChroot(NULL)
    , m_pBufEnd(pEnd)
    , m_restart(0)
    , m_flags(0)
{
}

ServerInfo::~ServerInfo()
{
}

void ServerInfo::addUnixSocket(const char *pSock, struct stat *pStat)
{
    int len = strlen(pSock);
    char *pBuf = allocate(len + sizeof(UnixSocketInfo));
    if (!pBuf)
        return;
    UnixSocketInfo *pInfo = new(pBuf) UnixSocketInfo();
    pInfo->m_pFileName = pBuf + sizeof(UnixSocketInfo);
    memmove(pInfo->m_pFileName, pSock, len + 1);
    pInfo->m_node = pStat->st_ino;
    pInfo->m_mtime = pStat->st_mtime;
    m_unixSocketList.addNext(pInfo);
}

void ServerInfo::updateUnixSocket(const char *pSock, struct stat *pStat)
{
    DLinkedObj *pNext = m_unixSocketList.next();
    while (pNext)
    {
        UnixSocketInfo *pInfo = (UnixSocketInfo *)pNext;
        if (strcmp(pInfo->m_pFileName, pSock) == 0)
        {
            pInfo->m_node = pStat->st_ino;
            pInfo->m_mtime = pStat->st_mtime;
            break;
        }
        pNext = pNext->next();
    }
}

int ServerInfo::cleanUnixSocketList()
{
    DLinkedObj *pNext = m_unixSocketList.next();
    char achBuf[2048];
    int chrootLen = 0;
    char *pSock;
    struct stat st;
    if (m_pChroot)
    {
        chrootLen = strlen(m_pChroot);
        memmove(achBuf, m_pChroot, chrootLen);
        pSock = achBuf;
    }
    while (pNext)
    {
        UnixSocketInfo *pInfo = (UnixSocketInfo *)pNext;
        if (m_pChroot)
            strcpy(&achBuf[chrootLen], pInfo->m_pFileName);
        else
            pSock = pInfo->m_pFileName;
        if (ls_fio_stat(pSock, &st) != -1)
        {
            if ((st.st_ino == pInfo->m_node) &&
                (st.st_mtime == pInfo->m_mtime))
                unlink(pSock);
        }
        pNext = pNext->next();
    }
    return 0;
}

char *ServerInfo::allocate(int len)
{
    int allocLen = (len + 8) & 0xfffffff8;
    if (m_pidList.m_pEnd - (char *)m_pidList.m_pCur < allocLen)
        return NULL;
    m_pidList.m_pEnd -= allocLen;
    return m_pidList.m_pEnd;
}

char *ServerInfo::dupStr(const char *pStr, int len)
{
    char *p = allocate(len);
    if (p)
        memmove(p, pStr, len + 1);
    return p;
}

int ServerInfo::cleanPidList(int toStopOnly)
{
    PidInfo *pInfo;
    pid_t pids[4096];
    pid_t *p = pids;
    pid_t *pEnd = p + 4096;
    for (pInfo = m_pidList.m_pBegin;
         (pInfo < m_pidList.m_pCur) && (p < pEnd); ++pInfo)
    {
        if ((!toStopOnly) || (pInfo->m_parent == KILL_TYPE_TERM))
            if (pInfo->m_pid > 0)
                *p++ = pInfo->m_pid;
    }
    pid_t *p1 = pids;
    for (; p1 != p; p1++)
    {
        kill(*p1, SIGTERM);
        kill(*p1, SIGUSR1);
        LS_DBG_L("[AutoRestater] Clean up child process with pid: %d", *p1);
    }
    ls_sleep(100);
    p1 = pids;
    for (; p1 != p; p1++)
        kill(*p1, SIGKILL);
    if (!toStopOnly)
        m_pidList.m_pCur = m_pidList.m_pBegin;
    return 0;
}



void ServerInfo::cleanUp()
{
    cleanPidList();
    cleanUnixSocketList();
    m_pidList.m_pEnd = m_pBufEnd;
    m_unixSocketList.setNext(NULL);
    m_pChroot = NULL;
}


