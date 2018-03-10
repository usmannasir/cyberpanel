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
#ifndef CGIDCONFIG_H
#define CGIDCONFIG_H

#include <lsdef.h>
#include <extensions/extworkerconfig.h>
#include <util/autostr.h>
#include <util/rlimits.h>


class CgidConfig : public ExtWorkerConfig
{
    char        m_achSecret[24];
    AutoStr2    m_sSocket;
    RLimits     m_limits;
    int         m_priority;
public:
    CgidConfig(const char *pName);
    CgidConfig();
    ~CgidConfig();
    const char *getSecret() const  {   return m_achSecret;     }
    char *getSecretBuf()           {   return m_achSecret;     }
    RLimits *getRLimits()          {   return &m_limits;       }

    void setPriority(int pri)     {   m_priority = pri;       }
    int getPriority() const         {   return m_priority;      }

    const char *getSocket() const  {   return m_sSocket.c_str();   }
    void setSocket(const char *p) {   m_sSocket.setStr(p);      }
    int  getSocketLen() const       {   return m_sSocket.len(); }

    LS_NO_COPY_ASSIGN(CgidConfig);
};

#endif
