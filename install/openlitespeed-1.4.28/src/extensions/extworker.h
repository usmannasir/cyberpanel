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
#ifndef EXTWORKER_H
#define EXTWORKER_H

#include "extworkerconfig.h"

#include <lsdef.h>
#include <http/httphandler.h>
#include <http/reqstats.h>
#include <util/connpool.h>
#include <util/dlinkqueue.h>

#include <sys/types.h>


#define EXTAPP_RESPONDER    1
#define EXTAPP_AUTHORIZER   2
#define EXTAPP_FILTER       3

class RLimits;

class ExtConn;
class ExtRequest;
class GSockAddr;
class Multiplexer;
class PidList;

class ExtWorker : public HttpHandler
{
    ExtWorkerConfig    *m_pConfig;
    DLinkQueue          m_reqQueue;
    ConnPool            m_connPool;
    unsigned short      m_iRole;
    unsigned char       m_iMultiplexConns;
    unsigned char       m_iWantManagementInfo;
    int                 m_iErrors;
    int                 m_iState;
    long                m_lErrorTime;
    long                m_lLastRestart;
    long                m_lIdleTime;
    int                 m_iLingerConns;
    ReqStats            m_reqStats;


    void processPending();
    void failOutstandingReqs();

protected:
    void setConfigPointer(ExtWorkerConfig *pConfig)
    {   m_pConfig = pConfig;    }
    virtual ExtConn *newConn() = 0;

public:
    enum
    {
        ST_NOTSTARTED,
        ST_BAD,
        ST_GOOD
    };

    explicit ExtWorker(int type);
    virtual ~ExtWorker();
    ConnPool &getConnPool()     {   return m_connPool;  }

    ExtWorkerConfig *getConfigPointer() const
    {   return m_pConfig;       }

    const char *getURL() const
    {   return m_pConfig->getURL();  }
    const char *getName() const
    {   return m_pConfig->getName();    }
    const GSockAddr &getServerAddr() const
    {   return m_pConfig->getServerAddr();  }

    bool wantManagementInfo() const
    {
        return (m_iWantManagementInfo == 1);
    }
    void gotManagementInfo()            {   m_iWantManagementInfo = 0;  }

    unsigned short getRole() const      {   return m_iRole;             }
    void setRole(unsigned short r)    {   m_iRole = r;                }

    void setMultiplexConns(int val)   {   m_iMultiplexConns = val;    }
    unsigned char isMultiplexConns() const       {   return m_iMultiplexConns;   }



    int getTimeout() const
    {   return m_pConfig->getTimeout();     }

    void setMaxConns(int max)
    {
        m_pConfig->setMaxConns(max);
        m_connPool.setMaxConns(max);
    }
    void clearCurConnPool();
    ExtConn *getConn();
    void recycleConn(ExtConn *conn);
    int  removeReq(ExtRequest *pReq);
    int  processRequest(ExtRequest *pReq, int retry = 0);
    void onTimer();

    void setState(int state)  {   m_iState = state;   }
    int getState() const        {   return m_iState;    }

    bool notStarted() const {   return m_iState == ST_NOTSTARTED;   }
    bool isReady() const    {   return m_iState > ST_BAD;       }

    int  getQueuedReqs() const  {   return m_reqQueue.size();   }
    int  getUtilRatio() const
    {   return m_connPool.getUsedConns() * 1000 / (m_connPool.getMaxConns() + 1); }

    int start();
    virtual int restart()       {   return start();     }
    virtual int tryRestart()    {   return 0;           }
    virtual int startEx()       {   return 1;           }
    virtual int stop()          {   m_iState = ST_NOTSTARTED; return 0;  }
    virtual int addNewProcess() {   return 0;           }
    virtual int startOnDemond(int force) {   return 0;           }
    virtual int runOnStartUp()  {   return 0;           }
    virtual void detectDiedPid() {}
    bool canStop()
    {
        return m_connPool.getTotalConns() == m_connPool.getFreeConns();
    }
    int connectionError(ExtConn *pConn, int errCode);
    int processConnError(ExtConn *pConn, ExtRequest *pReq, int errCode);

    static int startServerSock(ExtWorkerConfig *pConfig, int backlog);
    int generateRTReport(int fd, const char *pTypeName);

    ReqStats *getReqStats()    {   return &m_reqStats; }

    virtual void addPid(pid_t pid)    {}
    virtual void removePid(pid_t pid)  {}
    virtual void moveToStopList()       {}
    virtual void cleanStopPids()        {}

    virtual int setURL(const char *pURL);

    long getLastRestart() const         {   return m_lLastRestart;      }
    void setLastRestart(long l)       {   m_lLastRestart = l;         }

    int getLingerConns() const          {   return m_iLingerConns;      }
    LS_NO_COPY_ASSIGN(ExtWorker);
};

#endif
