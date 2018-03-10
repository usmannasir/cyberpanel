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
#ifndef AWSTATS_H
#define AWSTATS_H

#include <lsdef.h>
#include <util/autostr.h>

#define AWS_STATIC  1
#define AWS_DYNAMIC 2

class HttpVHost;
class ConfigCtx;
class XmlNode;

class Awstats
{
    AutoStr         m_sWorkingDir;
    AutoStr         m_sAwstatsURI;
    AutoStr         m_sSiteDomain;
    AutoStr         m_sSiteAliases;
    int             m_iUpdateInterval;
    int             m_iUpdateTimeOffset;
    int             m_iLastUpdate;
    int             m_iMode;

    int processLine(const HttpVHost *pVHost, int fdConf,
                    char *pCur, char *pLineEnd, char *&pLastWrite);

    int shouldBuildStatic(const char *pName);
    int executeUpdate(const char *pName);
    int createConfigFile(char *pModel, const HttpVHost *pVHost);
    int prepareAwstatsEnv(const HttpVHost *pVHost);
public:
    Awstats();
    ~Awstats();
    int updateIfNeed(long curTime, const HttpVHost *pVHost);
    int update(const HttpVHost *pVHost);
    void setWorkingDir(const char *pDir) {   m_sWorkingDir.setStr(pDir);   }
    void setURI(const char *pURI)        {   m_sAwstatsURI.setStr(pURI);   }
    void setSiteDomain(const char *pDmn) {   m_sSiteDomain.setStr(pDmn);   }
    void setAliases(const char *pAls)    {   m_sSiteAliases.setStr(pAls);  }
    void setMode(int mode)                {   m_iMode = mode;                 }
    void setInterval(int i)               {   m_iUpdateInterval = i;          }
    void setOffset(int off)               {   m_iUpdateTimeOffset = off;      }
    const char *getWorkingDir() const      {   return m_sWorkingDir.c_str();   }
    const char *getSiteDomain() const      {   return m_sSiteDomain.c_str();   }
    int  getInterval() const                {   return m_iUpdateInterval;       }
    void config(HttpVHost *pVHost, int val, char *achBuf,
                const XmlNode *pAwNode,
                char *iconURI, const char *vhDomain, int vhAliasesLen);

    LS_NO_COPY_ASSIGN(Awstats);
};

#endif
