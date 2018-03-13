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
#ifndef EXTWORKERCONFIG_H
#define EXTWORKERCONFIG_H

#include <util/autostr.h>
#include <util/env.h>

#include <sys/types.h>

class HttpVHost;
class GSockAddr;
class XmlNode;
class ConfigCtx;
class ExtWorkerConfig
{
    AutoStr     m_sURL;
    AutoStr     m_sName;
    const HttpVHost *m_pVHost;
    int         m_iMaxConns;
    int         m_iTimeout;
    int         m_iRetryTimeout;
    int         m_iBuffering;

    short       m_iKeepAlive;
    int         m_iMaxIdleTime;
    int         m_iKeepAliveTimeout;

    char        m_iSelfManaged;
    char        m_iStartByServer;
    char        m_iRefAddr;
    char        m_iDaemonSuEXEC;

    uid_t       m_uid;
    gid_t       m_gid;

    GSockAddr *m_pServerAddr;
    Env         m_env;
    const void *m_pOrgEnv;
    AutoStr2    m_sPhprc;
public:
    explicit ExtWorkerConfig(const char *pName);
    ExtWorkerConfig();
    virtual ~ExtWorkerConfig();
    ExtWorkerConfig(const ExtWorkerConfig &rhs);

    int setURL(const char *pURL);
    const char *getURL() const     {   return m_sURL.c_str();  }
    int updateServerAddr(const char *pURL);

    void setMaxConns(int max)         {   m_iMaxConns = max;  }
    int getMaxConns() const             {   return m_iMaxConns; }

    void setName(const char *pName);
    const char *getName() const        {   return m_sName.c_str();  }

    void setVHost(const HttpVHost *p) {   m_pVHost = p;       }
    const HttpVHost *getVHost() const  {   return m_pVHost;    }

    int addEnv(const char *pEnv)
    {   return m_env.add(pEnv);   }

    int updateEnv(const char *name, const char *value)
    {   return m_env.update(name, value);     }

    const Env *getEnv() const           {   return &m_env;      }
    Env *getEnv()                       {   return &m_env;      }
    void clearEnv()                     {   m_env.clear();      }
    void setOrgEnv(const void *p)     {   m_pOrgEnv = p;      }
    const void *getOrgEnv() const      {   return m_pOrgEnv;   }

    const GSockAddr &getServerAddr() const
    {   return *m_pServerAddr;        }

    void setServerAddr(const GSockAddr *pAddr);

    const char *getServerAddrUnixSock() const;

    void altServerAddr();
    void removeUnusedSocket();

    int getRetryTimeout() const     {   return m_iRetryTimeout;     }
    void setRetryTimeout(int timeout) {   m_iRetryTimeout = timeout;  }

    int getTimeout() const          {   return m_iTimeout;      }
    void setTimeout(int timeout)  {   m_iTimeout = timeout;   }

    int getBuffering() const        {   return m_iBuffering;    }
    void setBuffering(int b)      {   m_iBuffering = b;       }

    void setPersistConn(int keepAlive) {  m_iKeepAlive = keepAlive;   }
    short isPersistConn() const          {   return m_iKeepAlive;       }

    void setKeepAliveTimeout(int to)  {   m_iKeepAliveTimeout = to;   }
    int  getKeepAliveTimeout() const    {   return m_iKeepAliveTimeout; }

    void setMaxIdleTime(int s)         {   m_iMaxIdleTime = s;         }
    int  getMaxIdleTime() const         {   return m_iMaxIdleTime;      }

    short getSelfManaged() const        {   return m_iSelfManaged;  }
    void setSelfManaged(int s)        {   m_iSelfManaged = s;     }

    char getStartByServer() const       {   return m_iStartByServer;  }
    void setStartByServer(int s)      {   m_iStartByServer = s;     }

    char getDaemonSuEXEC() const        {   return m_iDaemonSuEXEC;     }
    void setDaemonSuEXEC(int s)       {   m_iDaemonSuEXEC = s;        }

    uid_t getUid() const            {   return m_uid;   }
    gid_t getGid() const            {   return m_gid;   }

    void setUGid(uid_t uid, gid_t gid)
    {   m_uid = uid;    m_gid = gid;    }

    void setPhprc(const char *pRC, int len)
    {   m_sPhprc.setStr(pRC, len);        }
    const AutoStr2 &getPhprc() const
    {   return m_sPhprc;    }
    void config(const XmlNode *pNode);

};

#endif
