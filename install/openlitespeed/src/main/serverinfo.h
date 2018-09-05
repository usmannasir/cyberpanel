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
#ifndef SERVERINFO_H
#define SERVERINFO_H



#include <extensions/pidlist.h>
#include <util/linkedobj.h>

class UnixSocketInfo : public DLinkedObj
{
public:
    char       *m_pFileName;
    ino_t       m_node;
    time_t      m_mtime;
};

#define SINFO_FLAG_ADNS_OP      4

class ServerInfo
{
    static ServerInfo *s_pServerInfo;
    int cleanUnixSocketList();
    char *allocate(int len);

public:
    PidSimpleList   m_pidList;
    pid_t           m_pidLinger;
    char           *m_pChroot;
    DLinkedObj      m_unixSocketList;
    char           *m_pBufEnd;
    volatile int    m_restart;
    volatile int64_t m_flags;

    ServerInfo(char *pBegin, char *pEnd);
    ~ServerInfo();
    ServerInfo(const ServerInfo &rhs);
    void operator=(const ServerInfo &rhs);
    void addUnixSocket(const char *pSock, struct stat *pStat);
    void updateUnixSocket(const char *pSock, struct stat *pStat);
    void cleanUp();
    char *dupStr(const char *pStr, int len);
    void setRestart(int val)      {   m_restart = val;    }
    int  getRestart() const         {   return m_restart;   }
    int  cleanPidList(int ToStopOnly = 0);

    static void setServerInfo(ServerInfo *pServerInfo)
    {   s_pServerInfo = pServerInfo;    }
    static ServerInfo *getServerInfo()
    {   return s_pServerInfo;   }

    void setAdnsOp(int adnsOp)
    {   m_flags = adnsOp ? (m_flags | SINFO_FLAG_ADNS_OP)
                         : (m_flags & ~SINFO_FLAG_ADNS_OP); }
    int isAdnsOp() const    {   return m_flags & SINFO_FLAG_ADNS_OP;    }
};

#endif
