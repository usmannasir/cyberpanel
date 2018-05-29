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
#ifndef SERVERPROCESSCONFIG_H
#define SERVERPROCESSCONFIG_H

#include <util/tsingleton.h>
#include <unistd.h>

class AutoStr2;

class ServerProcessConfig : public TSingleton< ServerProcessConfig >
{
    friend class TSingleton< ServerProcessConfig >;

    uid_t                  m_uid;
    gid_t                  m_gid;
    uid_t                  m_uidMin;
    gid_t                  m_gidMin;
    uid_t                  m_forceGid;
    int                    m_iPriority;
    int                    m_iUMask;
    AutoStr2              *m_pChroot;

    ServerProcessConfig(const ServerProcessConfig &rhs);
    void operator=(const ServerProcessConfig &rhs);
    ServerProcessConfig();
public:

    ~ServerProcessConfig();

    void setUid(uid_t uid)                {   m_uid = uid;                }
    uid_t getUid() const                    {   return m_uid;               }

    void setGid(gid_t gid)                {   m_gid = gid;                }
    gid_t getGid() const                    {   return m_gid;               }

    void setUidMin(uid_t uid)             {   m_uidMin = uid;             }
    uid_t getUidMin() const                 {   return m_uidMin;            }

    void setGidMin(gid_t gid)             {   m_gidMin = gid;             }
    gid_t getGidMin() const                 {   return m_gidMin;            }

    void setForceGid(uid_t forceGid)      {   m_forceGid = forceGid;      }
    uid_t getForceGid() const               {   return m_forceGid;          }

    void setPriority(int iPriority)       {   m_iPriority = iPriority;    }
    int getPriority() const                 {   return m_iPriority;         }

    void setUMask(int iUMask)             {   m_iUMask = iUMask;          }
    int getUMask() const                    {   return m_iUMask;            }

    void setChroot(AutoStr2 *pChroot)     {   m_pChroot = pChroot;        }
    AutoStr2 *getChroot() const             {   return m_pChroot;           }
};

#endif //SERVERPROCESSCONFIG_H

