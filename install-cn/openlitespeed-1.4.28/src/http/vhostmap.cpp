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
#include "vhostmap.h"

#include <lsdef.h>
#include <http/httpvhost.h>
#include <http/httpvhostlist.h>
#include <log4cxx/logger.h>
#include <lsr/ls_strtool.h>
#include <socket/gsockaddr.h>
#include <sslpp/sslcontext.h>
#include <util/stringlist.h>
#include <util/stringtool.h>

#include <ctype.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>


class WildMatch
{
    HttpVHost        *m_pVHost;
    StringList       *m_pParsed;
    const char       *m_pPattern;
public:
    WildMatch(HttpVHost *pVHost, const char *pPattern)
        : m_pVHost(pVHost)
        , m_pParsed(NULL)
        , m_pPattern(pPattern)
    {
        m_pParsed = StringTool::parseMatchPattern(pPattern);
    }

    ~WildMatch()
    {
        if (m_pParsed)
            delete m_pParsed;
    }
    void setVHost(HttpVHost *p)   {   m_pVHost = p;       }
    void setPattern(const char *p) {  m_pPattern = p;     }
    HttpVHost   *getVHost()   const {   return m_pVHost;    }
    const char *getPattern() const {   return m_pPattern;  }
    StringList *getParsed()  const {   return m_pParsed;   }
    int match(const char *pHostName, const char *pEnd) const
    {
        return StringTool::strMatch(pHostName, pEnd,
                                    m_pParsed->begin(), m_pParsed->end(), 0);
    }
    LS_NO_COPY_ASSIGN(WildMatch);
};


VHostMap::VHostMap()
    : m_pCatchAll(NULL)
    , m_pDedicated(NULL)
    , m_pWildMatches(NULL)
    , m_pSslContext(NULL)
    , m_iNamedVH(0)
    , m_iStripWWW(1)
{}


VHostMap::~VHostMap()
{

    if (m_pSslContext)
        delete m_pSslContext;
    clear();

}


HttpVHost *VHostMap::wildMatch(const char *pHost, const char *pEnd) const
{
    WildMatchList::iterator iter;
    for (iter = m_pWildMatches->begin(); iter != m_pWildMatches->end(); ++iter)
    {
        if ((*iter)->match(pHost, pEnd) == 0)
            return (*iter)->getVHost();
    }
    return m_pCatchAll;
}


static inline int isWildMatch(const char *pchKey)
{
    return (strpbrk(pchKey, "*?") != NULL);
}


int VHostMap::addWildMatch(const char *pchKey, HttpVHost *pHost)
{
    if (!m_pWildMatches)
    {
        m_pWildMatches = new WildMatchList();
        if (!m_pWildMatches)
            return LS_FAIL;
    }
    else
    {
        WildMatchList::iterator iter;
        for (iter = m_pWildMatches->begin(); iter != m_pWildMatches->end(); ++iter)
        {
            if (strcasecmp((*iter)->getPattern(), pchKey) == 0)
            {
                if ((*iter)->getVHost() == pHost)
                    return 0;
                HttpVHostMap::decRef((*iter)->getVHost());
                (*iter)->setVHost(pHost);
            }
        }
    }
    WildMatch *pMatch = new WildMatch(pHost, pchKey);
    if (!pMatch)
        return LS_FAIL;
    if ((!pMatch->getParsed()) ||
        (m_pWildMatches->push_back(pMatch) != 0))
    {
        delete pMatch;
        return LS_FAIL;
    }
    HttpVHostMap::incRef(pHost);
    return 0;
}


void VHostMap::removeWildMatch(WildMatchList::iterator iter)
{
    WildMatch *pMatch = *iter;
    HttpVHostMap::decRef(pMatch->getVHost());
    m_pWildMatches->erase(iter);
    delete pMatch;
}


int VHostMap::removeWildMatch(const char *pName)
{
    if (!m_pWildMatches)
        return 0;
    WildMatchList::iterator iter;
    for (iter = m_pWildMatches->begin(); iter != m_pWildMatches->end(); ++iter)
    {
        if (strcasecmp(pName, (*iter)->getPattern()) == 0)
        {
            removeWildMatch(iter);
            return 0;
        }
    }
    return 0;
}


int VHostMap::addMap(const char *pchKey, HttpVHost *pHost)
{
    if (!pHost)
        return LS_FAIL;
    if (strcmp(pchKey, "*") == 0)
    {
        if (m_pCatchAll)
            HttpVHostMap::decRef(m_pCatchAll);
        m_pCatchAll = pHost;
    }
    else
    {
        if (isWildMatch(pchKey))
            return addWildMatch(pchKey, pHost);
        iterator iter1 = find(pchKey);
        if (iter1 != end())
        {
            if (iter1.second() == pHost)
                return 0;
            HttpVHostMap::decRef(iter1.second());
            erase(iter1);
        }
        insert(pchKey, pHost);
    }
    HttpVHostMap::incRef(pHost);
    return 0;
}


int VHostMap::removeVHost(HttpVHost *pHost)
{
    if (!pHost)
        return LS_FAIL;
    iterator iter, iter1;
    for (iter = begin(); iter != end();)
    {
        if (iter.second() == pHost)
        {
            HttpVHostMap::decRef(pHost);
            iter1 = iter;
            iter = next(iter);
            erase(iter1);
        }
        else
            iter = next(iter);
    }
    if (m_pWildMatches)
    {
        WildMatchList::iterator iter;
        for (iter = m_pWildMatches->begin(); iter != m_pWildMatches->end();)
        {
            if ((*iter)->getVHost() == pHost)
                removeWildMatch(iter);
            else
                ++iter;
        }
    }

    if (m_pCatchAll == pHost)
    {
        HttpVHostMap::decRef(pHost);
        m_pCatchAll = NULL;
        m_pDedicated = NULL;
    }
    return 0;
}


void VHostMap::remove(const char *pName)
{
    iterator iter1 = find(pName);
    if (iter1 != end())
    {
        HttpVHostMap::decRef(iter1.second());
        erase(iter1);
    }
    else
        removeWildMatch(pName);
}


void VHostMap::removeMapping(const char *pName)
{
    if (strcmp(pName, "*") == 0)
    {
        if (m_pCatchAll)
            HttpVHostMap::decRef(m_pCatchAll);
        m_pCatchAll = NULL;
    }
    else
        remove(pName);
}


void VHostMap::findDedicated()
{
    if (m_pCatchAll)
    {
        const_iterator iter, iterEnd = end();
        for (iter = begin(); iter != iterEnd;
             iter = next(iter))
        {
            if ((iter.second() != m_pCatchAll))
            {
                m_pDedicated = NULL;
                return;
            }
        }
        if (m_pWildMatches)
        {
            WildMatchList::iterator iter;
            for (iter = m_pWildMatches->begin(); iter != m_pWildMatches->end(); ++iter)
            {
                if ((*iter)->getVHost() != m_pCatchAll)
                {
                    m_pDedicated = NULL;
                    return;
                }
            }
        }
    }
    m_pDedicated = m_pCatchAll;
}


void VHostMap::clear()
{
    if (m_pCatchAll)
        HttpVHostMap::decRef(m_pCatchAll);
    m_pDedicated = NULL;
    m_pCatchAll = NULL;
    iterator iter;
    for (iter = begin(); iter != end();)
    {
        HttpVHostMap::decRef(iter.second());
        iter = next(iter);
    }
    HashStringMap< HttpVHost * >::clear();
    if (m_pWildMatches)
    {
        WildMatchList::iterator iter;
        for (iter = m_pWildMatches->begin(); iter != m_pWildMatches->end(); ++iter)
            HttpVHostMap::decRef((*iter)->getVHost());
        m_pWildMatches->release_objects();
        delete m_pWildMatches;
        m_pWildMatches = NULL;
    }

}


void VHostMap::setPort(int p)
{
    char achBuf[20];
    m_port = p;
    p = ls_snprintf(achBuf, 20, "%d", m_port);
    m_sPort.setStr(achBuf, p);
}


void VHostMap::updateMapping(HttpVHostMap &vhosts)
{
    if (m_pCatchAll)
    {
        HttpVHost *pCur = vhosts.get(HttpVHostMap::getName(m_pCatchAll));
        HttpVHostMap::decRef(m_pCatchAll);
        m_pCatchAll = pCur;
        HttpVHostMap::incRef(pCur);
    }
    iterator iter, iter1;
    for (iter = begin(); iter != end();)
    {
        HttpVHost *pVHost = iter.second();
        HttpVHost *pCur = vhosts.get(HttpVHostMap::getName(pVHost));
        if (pVHost != pCur)
        {
            HttpVHostMap::decRef(pVHost);
            const char *pName = iter.first();
            iter1 = iter;
            iter = next(iter);
            erase(iter1);
            if (pCur)
                insert(
                    HttpVHostMap::addMatchName(pCur, pName),
                    pCur);
            HttpVHostMap::incRef(pCur);
        }
        else
            iter = next(iter);
    }
    if (m_pWildMatches)
    {
        WildMatchList::iterator iter;
        for (iter = m_pWildMatches->begin(); iter != m_pWildMatches->end();)
        {
            HttpVHost *pVHost = (*iter)->getVHost();
            HttpVHost *pCur = vhosts.get(HttpVHostMap::getName(pVHost));
            if (pVHost != pCur)
            {
                if (pCur)
                {
                    HttpVHostMap::decRef(pVHost);
                    HttpVHostMap::incRef(pCur);
                    (*iter)->setVHost(pCur);
                    (*iter)->setPattern(
                        HttpVHostMap::addMatchName(pCur, (*iter)->getPattern()));
                    ++iter;
                }
                else
                    removeWildMatch(iter);
            }
            else
                ++iter;
        }
    }
    findDedicated();
}


int VHostMap::writeStatusReport(int fd)
{
    char achBuf[1024];
    if (m_pCatchAll)
    {
        int len = ls_snprintf(achBuf, 1024, "LVMAP [%s] *\n",
                              HttpVHostMap::getName(m_pCatchAll));
        if (::write(fd, achBuf, len) != len)
            return LS_FAIL;
    }
    const_iterator iter;
    const_iterator iterEnd = end();
    for (iter = begin(); iter != iterEnd; iter = next(iter))
    {
        int len = ls_snprintf(achBuf, 1024, "LVMAP [%s] %s\n",
                              HttpVHostMap::getName(iter.second()),
                              iter.first());
        if (::write(fd, achBuf, len) != len)
            return LS_FAIL;
    }
    if (m_pWildMatches)
    {
        WildMatchList::iterator iter;
        for (iter = m_pWildMatches->begin(); iter != m_pWildMatches->end(); ++iter)
        {
            int len = ls_snprintf(achBuf, 1024, "LVMAP [%s] %s\n",
                                  HttpVHostMap::getName((*iter)->getVHost()),
                                  (*iter)->getPattern());
            if (::write(fd, achBuf, len) != len)
                return LS_FAIL;
        }
    }
    return 0;
}


HttpVHost *VHostMap::exactMatchVHost(const char *pHost) const
{
    if (strcmp(pHost, "*") == 0)
        return m_pCatchAll;
    const_iterator iter1 = find(pHost);
    if (iter1 != end())
        return iter1.second();
    if (m_pWildMatches)
    {
        WildMatchList::iterator iter;
        for (iter = m_pWildMatches->begin(); iter != m_pWildMatches->end(); ++iter)
        {
            if (strcasecmp(pHost, (*iter)->getPattern()) == 0)
                return (*iter)->getVHost();
        }
    }
    return NULL;
}


void VHostMap::setSslContext(SslContext *pContext)
{
    if (pContext == m_pSslContext)
        return;
    if (m_pSslContext)
        delete m_pSslContext;
    m_pSslContext = pContext;
}


int VHostMap::addMaping(HttpVHost *pVHost,
                        const char *pDomain, int optional)
{
    HttpVHost *pOld = exactMatchVHost(pDomain);
    if (pOld)
    {
        if (pOld == pVHost)
            return 0;
        if (strcmp(pOld->getName(), pVHost->getName()) == 0)
            removeMapping(pDomain);
        else
        {
            if (!optional)
            {
                LS_ERROR("Hostname [%s] on listener [%s] is mapped to virtual host [%s], "
                         "can't map to virtual host [%s]!",
                         pDomain, m_sAddr.c_str(), pOld->getName(), pVHost->getName());
                return LS_FAIL;
            }
            return 0;
        }
    }
    const AutoStr2 *psDomain = pVHost->addMatchName(pDomain);
    if ((!psDomain) ||
        (addMap(psDomain->c_str(), pVHost)))
    {
        LS_ERROR("Associates [%s] with [%s] on hostname/IP [%s] %s!",
                 pVHost->getName(), m_sAddr.c_str(), pDomain, "failed");
        return LS_FAIL;
    }
    else
    {
        LS_DBG_L("Associates [%s] with [%s] on hostname/IP [%s] %s!",
                 pVHost->getName(), m_sAddr.c_str(), pDomain, "succeed");
        return 0;
    }
}


int VHostMap::mapDomainList(HttpVHost    *pVHost,
                            const char *pDomains)
{
    if (pVHost == NULL || !pDomains)
        return LS_FAIL;
    //www.vh1.com,vh1.com,localhost,127.0.0.1
    char temp[256];
    const char *p0, *p1;
    const char *pEnd = pDomains + strlen(pDomains);
    p0 = pDomains;
    while (p0 < pEnd)
    {
        while (isspace(*p0))
            ++p0;
        p1 = strchr(p0, ',');
        if (!p1)
            p1 = pEnd;
        while ((p1 > p0) && isspace(p1[-1]))
            --p1;
        int len = p1 - p0;
        if (len > 0)
        {
            char *p;
            if (len >= 256)
                len = 255;
            StringTool::strLower(p0, temp, len);
            temp[len] = 0;
            // check IPv6 IP address, inside "[..]"
            if (temp[0] == '[')
            {
                if (temp[len - 1] != ']')
                {
                    p = strrchr(temp, ']');
                    if (p)
                        *(p + 1) = 0;
                    else
                    {
                        LS_ERROR("Missing ']' for literal IPv6 address: %s", temp);
                        len = 0;
                    }
                }
            }
            else
            {
                //check if a port number is specified.
                p = strchr(temp, ':');
                if (p)
                    *p = 0;
            }
            p0 = temp;

            if (m_iStripWWW)
            {
                if (strncmp(p0, "www.", 4) == 0)
                    p0 += 4;
            }
            if (len)
                addMaping(pVHost, p0);
        }
        p0 = p1 + 1;
    }
    return 0;
}


typedef union
    {
        in6_addr    m_addr6;
        in_addr_t   m_addrs[4];
    } Addr6;


SubIpMap::SubIpMap()
    : m_map(11, NULL, NULL)
{
}


SubIpMap::~SubIpMap()
{
    m_map.release_objects();
}


VHostMap *SubIpMap::getMap(uint32_t ipv4) const
{
    IpMap::iterator iter = m_map.find((void *)(unsigned long)ipv4);
    if (iter == m_map.end())
        return NULL;
    return iter.second();
}


uint32_t addrConvert(struct sockaddr *pAddr)
{
    uint32_t ipv4;
    if (AF_INET6 == pAddr->sa_family)
    {
        if (IN6_IS_ADDR_V4MAPPED(&((struct sockaddr_in6 *)pAddr)->sin6_addr))
            ipv4 = ((Addr6 *) & ((struct sockaddr_in6 *)pAddr)->sin6_addr)->m_addrs[3];
        else
        {
            Addr6 *a6 = (Addr6 *) & ((struct sockaddr_in6 *)pAddr)->sin6_addr;
            ipv4 = a6->m_addrs[0] ^ a6->m_addrs[1] ^ a6->m_addrs[2] ^ a6->m_addrs[3];
        }
    }
    else
        ipv4 = ((struct sockaddr_in *)pAddr)->sin_addr.s_addr;
    return ipv4;
}


VHostMap *SubIpMap::getMap(struct sockaddr *pAddr) const
{
    uint32_t ipv4 = addrConvert(pAddr);
    return getMap(ipv4);

}


VHostMap *SubIpMap::addIP(const char *pIP)
{
    GSockAddr addr;
    VHostMap *pMap;
    uint32_t ipv4;
    if (addr.parseAddr(pIP) == -1)
        return NULL;
    struct sockaddr *pAddr = addr.get();
    pMap = getMap(pAddr);
    if (pMap)
        return pMap;

    pMap = new VHostMap();
    if (pMap)
    {
        pMap->setAddrStr(pIP);
        ipv4 = addrConvert(pAddr);
        m_map.insert((void *)(unsigned long)ipv4, pMap);
    }
    return pMap;
}


int SubIpMap::addDefaultVHost(HttpVHost *pVHost)
{
    int count = 0;
    IpMap::iterator iter = m_map.begin();
    for (; iter != m_map.end(); iter = m_map.next(iter))
    {
        if (iter.second()->isNamedVH())
        {
            iter.second()->addMaping(pVHost, "*");
            ++count;
        }
    }
    return count;
}


int SubIpMap::writeStatusReport(int fd)
{
    IpMap::iterator iter = m_map.begin();
    for (; iter != m_map.end(); iter = m_map.next(iter))
    {
        if (iter.second()->writeStatusReport(fd) == -1)
            return LS_FAIL;
    }
    return 0;
}


void SubIpMap::endConfig()
{
    IpMap::iterator iter = m_map.begin();
    for (; iter != m_map.end(); iter = m_map.next(iter))
        iter.second()->endConfig();
}


int SubIpMap::hasSSL()
{
    IpMap::iterator iter = m_map.begin();
    for (; iter != m_map.end(); iter = m_map.next(iter))
    {
        if (iter.second()->getSslContext())
            return 1;
    }
    return 0;
}


SslContext *VHostMapFindSslContext(void *arg, const char *pName)
{
    VHostMap *pMap = (VHostMap *)arg;
    HttpVHost *pVHost = pMap->getDedicated();
    if (!pVHost)
    {
        char *pHost;
        char *pHostEnd;
        char achBuf[1024];
        int len = 1024;
        pHost = StringTool::strLower(pName, achBuf, len);
        pHostEnd = pHost + len;
        pVHost = pMap->matchVHost(pHost, pHostEnd);
        if ((!pVHost || pVHost == pMap->getCatchAll()) && (memcmp(pHost, "www.", 4) == 0))
        {
            pHost += 4;
            pVHost = pMap->matchVHost(pHost, pHostEnd);
        }
    }
    if (pVHost && pVHost->getSslContext())
        return pVHost->getSslContext();
    return pMap->getSslContext();

}

