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
#ifndef LOCALWORKER_H
#define LOCALWORKER_H

#include <lsdef.h>
#include <extensions/extworker.h>


class PidList;
class LocalWorkerConfig;
class LocalWorker : public ExtWorker
{
    int                 m_fdApp;
    int                 m_sigGraceStop;
    PidList            *m_pidList;
    PidList            *m_pidListStop;

    void        moveToStopList();
public:
    explicit LocalWorker(int type);

    ~LocalWorker();

    LocalWorkerConfig &getConfig() const;

    PidList *getPidList() const    {   return m_pidList;   }
    void    addPid(pid_t pid);
    void    removePid(pid_t pid);
    int     startOnDemond(int force);

    void    cleanStopPids();
    void detectDiedPid();

    void setfd(int fd)            {   m_fdApp = fd;       }
    int getfd() const               {   return m_fdApp;     }

    int selfManaged() const;

    int runOnStartUp();

    void removeUnixSocket();
    int getCurInstances() const;
    int stop();
    void moveToStopList(int pid);
    int tryRestart();
    int restart();
    int addNewProcess();

    int startWorker();

    static int workerExec(LocalWorkerConfig &config, int fd);
    static void configRlimit(RLimits *pRLimits, const XmlNode *pNode);

    LS_NO_COPY_ASSIGN(LocalWorker);
};

#endif
