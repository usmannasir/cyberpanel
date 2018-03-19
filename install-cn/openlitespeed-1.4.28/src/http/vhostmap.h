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
#ifndef VHOSTMAP_H
#define VHOSTMAP_H


#include <util/autostr.h>
#include <util/gpointerlist.h>
#include <util/hashstringmap.h>
#include <util/refcounter.h>

#include <inttypes.h>

class HttpVHost;
class HttpVHostMap;
class WildMatch;
class SslContext;

class VHostMap : private HashStringMap< HttpVHost * >, public RefCounter
{
    typedef TPointerList<WildMatch> WildMatchList;
    HttpVHost        *m_pCatchAll;
    HttpVHost        *m_pDedicated;
    WildMatchList    *m_pWildMatches;
    SslContext       *m_pSslContext;
    AutoStr2          m_sAddr;
    int               m_port;
    AutoStr2          m_sPort;
    int               m_iNamedVH;
    short             m_iStripWWW;

    VHostMap(const VHostMap &rhs);
    void operator=(const VHostMap &rhs);
    void remove(const char *pName);
    int addWildMatch(const char *pchKey, HttpVHost *pHost);
    int removeWildMatch(const char *pName);
    HttpVHost *wildMatch(const char *pHost, const char *pEnd) const;
    void removeWildMatch(WildMatchList::iterator iter);


public:
    VHostMap();
    ~VHostMap();
    int addMap(const char *pchKey, HttpVHost *pHost);
    int addMaping(HttpVHost *pVHost,
                  const char *pDomain, int optional = 0);
    int mapDomainList(HttpVHost    *pVHost,
                      const char *pDomains);

    void setAddrStr(const char *p)    {   m_sAddr.setStr(p);    }
    const AutoStr2 *getAddrStr() const {   return &m_sAddr;        }

    void removeMapping(const char *pchKey);
    int removeVHost(HttpVHost *pHost);
    void updateMapping(HttpVHost *pHost);
    HttpVHost *matchVHost(const char *pHost, const char *pHostEnd) const
    {
        const_iterator iter1 = find(pHost);
        if (iter1 != end())
            return iter1.second();
        if (m_pWildMatches)
            return wildMatch(pHost, pHostEnd);
        return m_pCatchAll;
    }

    HttpVHost *exactMatchVHost(const char *pHost) const;
    HttpVHost *getCatchAll() const
    {   return m_pCatchAll; }
    void clear();

    void findDedicated();
    void endConfig()    { findDedicated();  }

    HttpVHost *getDedicated() const
    {   return m_pDedicated;    }

    int getPort() const     {   return m_port;  }
    void setPort(int p);
    const AutoStr2 &getPortStr() const   {   return m_sPort; }
    void updateMapping(HttpVHostMap &vhosts);
    int writeStatusReport(int fd);

    SslContext *getSslContext() const      {   return m_pSslContext;   }
    void setSslContext(SslContext *p);

    int  isNamedVH() const              {   return m_iNamedVH;    }
    void setNamedVH(int admin)        {   m_iNamedVH = admin;   }
    short isStripWWW() const            {   return m_iStripWWW;   }
    void setStripWWW(short s)         {   m_iStripWWW = s;      }
};



class SubIpMap
{
private:
    typedef THash<VHostMap *>      IpMap;
    IpMap       m_map;
    SubIpMap(const SubIpMap &rhs);
    void operator=(const SubIpMap &rhs);
public:
    SubIpMap();
    ~SubIpMap();

    VHostMap *getMap(uint32_t ipv4) const;
    VHostMap *getMap(struct sockaddr *pAddr) const;
    VHostMap *addIP(const char *pIP);

    int addDefaultVHost(HttpVHost *pVHost);

    int writeStatusReport(int fd);
    void endConfig();
    int hasSSL();

};
extern SslContext *VHostMapFindSslContext(void *arg, const char *pName);

#endif
