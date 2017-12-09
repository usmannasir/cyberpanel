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
#ifndef LOCALWORKERCONFIG_H
#define LOCALWORKERCONFIG_H

#include <extensions/extworkerconfig.h>
#include <util/rlimits.h>

#include <sys/types.h>

class ConfigCtx;
class LocalWorkerConfig : public ExtWorkerConfig
{
    char       *m_pCommand;
    int         m_iBackLog;
    int         m_iInstances;
    int         m_iPriority;
    int         m_iRunOnStartUp;
    RLimits     m_rlimits;
    int         m_umask;

    void operator=(const LocalWorkerConfig &rhs);
public:
    explicit LocalWorkerConfig(const char *pName);
    LocalWorkerConfig();

    ~LocalWorkerConfig();

    LocalWorkerConfig(const LocalWorkerConfig &rhs);

    void setAppPath(const char *pPath);
    void setBackLog(int backlog)
    {   if (backlog > 0) m_iBackLog = backlog;   }

    void setInstances(int instances)
    {   m_iInstances = instances;   }


    const char *getCommand() const
    {   return m_pCommand;  }

    int getBackLog() const
    {   return m_iBackLog;  }

    int getInstances() const
    {   return m_iInstances;    }

    void beginConfig();
    void endConfig();

    int getRunOnStartUp() const     {   return m_iRunOnStartUp;  }
    void setRunOnStartUp(int r)   {   m_iRunOnStartUp = r;     }

    void setRLimits(const RLimits *pRLimits);
    const RLimits *getRLimits() const    {   return &m_rlimits;   }
    RLimits *getRLimits()           {   return &m_rlimits;   }

    int getPriority() const         {   return m_iPriority; }
    void setPriority(int p)        {   m_iPriority = p;    }

    void setUmask(int mask)     {   m_umask = mask;       }
    int getUmask() const         {   return m_umask;      }

    int isProcPerConn() const       {   return m_iInstances >= getMaxConns();   }
    int checkExtAppSelfManagedAndFixEnv();
    int config(const XmlNode *pNode);
    void configExtAppUserGroup(const XmlNode *pNode, int iType);
};

#endif
