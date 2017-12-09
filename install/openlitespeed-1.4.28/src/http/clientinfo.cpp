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
#include "clientinfo.h"

#include <http/iptogeo.h>
#include <http/iptoloc.h>
#include <log4cxx/logger.h>
#include <util/accessdef.h>
#include <util/datetime.h>

#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <limits.h>

#define ShmClientMagic  0x20140601
#define ShmClientInfo   "ClientInfo"
#define ShmClientHash   "ClientHash"


int ClientInfo::s_iSoftLimitPC = INT_MAX;
int ClientInfo::s_iHardLimitPC = 100;
int ClientInfo::s_iOverLimitGracePeriod = 10;
int ClientInfo::s_iBanPeriod = 60;

#if 0
TShmClientPool *ClientInfo::s_base = NULL;

int ClientInfo::shmData_init(lsShm_hCacheData_t *p, void *pUParam)
{
    TShmClient *pObj = (TShmClient *)p;
    ClientInfo *pInfo = (ClientInfo *)pObj;

    // Sample code for init...
    pObj->x_ctlThrottle = pInfo->m_ctlThrottle;
    pObj->x_iConns = pInfo->m_iConns;
    pObj->x_tmOverLimit = pInfo->m_tmOverLimit;
    pObj->x_sslNewConn = pInfo->m_sslNewConn;
    pObj->x_iHits = pInfo->m_iHits;
    pObj->x_lastConnect = pInfo->m_lastConnect;
    pObj->x_iAccess = pInfo->m_iAccess;
    return 0;
}

int ClientInfo::shmData_remove(lsShm_hCacheData_t *p, void *pUParam)
{
    // TShmClient * pObj = (TShmClient*)p;
    // Need to do something here...
    // ClientInfo * pInfo = (ClientInfo *)pObj;

    // Sample code for remove...
    return 0;
}
#endif


ClientInfo::ClientInfo()
    : m_iFlags( 0 )
    , m_iConns( 0 )
    , m_pGeoInfo(NULL)
#ifdef USE_IP2LOCATION
    , m_pLocInfo(NULL)
#endif
{
#if 0
    m_pShmClient = NULL;
    m_clientOffset = 0;
    // Only need to do this once!
    if (!s_base)
    {
        // s_base = new TShmClientPool
        s_base = new TShmClientPool(ShmClientMagic
                                    , ShmClientInfo
                                    , ShmClientHash
                                    , 101
                                    , sizeof(TShmClient)
                                    , LsShmHash::hashBuf
                                    , memcmp
                                    , shmData_init
                                    , shmData_remove
                                   );
        if (s_base && (s_base->status() != LSSHM_READY))
        {
            delete s_base;
            s_base = NULL;
        }
    }
#endif
    ;
}


ClientInfo::~ClientInfo()
{
    if (m_pGeoInfo)
        delete m_pGeoInfo;
}


void ClientInfo::setAddr(const struct sockaddr *pAddr)
{
    int len, strLen;
    if (AF_INET == pAddr->sa_family)
    {
        len = 16;
        strLen = 17;
    }
    else
    {
        len = 24;
        strLen = 41;
    }

#if 0
    if (s_base)
    {
        // remove the old one
        if (m_clientOffset)
        {
            // uhmmm probably not to remove...
            s_base->removeObj((lsShm_hCacheData_t *) s_base->offset2ptr(
                                  m_clientOffset));
        }

        m_pShmClient = (TShmClient *)s_base->getObj(pAddr, len, NULL ,
                       sizeof(TShmClient));
        // initialize the data here...
        if (m_pShmClient)
        {
            // track it
            s_base->push((lsShm_hCacheData_t *)m_pShmClient);
            m_clientOffset = s_base->ptr2offset(m_pShmClient);
        }
        else
            m_clientOffset = 0;
    }
#endif
    memmove(m_achSockAddr, pAddr, len);
    m_sAddr.prealloc(strLen);
    if (m_sAddr.buf())
    {
        inet_ntop(pAddr->sa_family, ((char *)pAddr) + ((len >> 1) - 4),
                  m_sAddr.buf(), strLen);
        m_sAddr.setLen(strlen(m_sAddr.c_str()));
    }
    memset(&m_iConns, 0, (char *)(&m_lastConnect + 1) - (char *)&m_iConns);
    m_iAccess = 1;
}


int ClientInfo::checkAccess()
{
    int iSoftLimit = ClientInfo::getPerClientSoftLimit();
    switch (m_iAccess)
    {
    case AC_BLOCK:
    case AC_DENY:
        LS_DBG_L("[%s] Access is denied!", getAddrString());
        return 1;
    case AC_ALLOW:
        if (getOverLimitTime())
        {
            if (DateTime::s_curTime - getOverLimitTime()
                >= ClientInfo::getOverLimitGracePeriod())
            {
                LS_NOTICE("[%s] is over per client soft connection limit: %d for %d seconds,"
                          " close connection!",
                          getAddrString(), iSoftLimit,
                          (int)(DateTime::s_curTime - getOverLimitTime()));
                setOverLimitTime(DateTime::s_curTime);
                setAccess(AC_BLOCK);
                return 1;
            }
            else
            {
                LS_DBG_L("[%s] %zd connections established, limit: %d.",
                         getAddrString(), getConns(), iSoftLimit);
            }
        }
        else if ((int)getConns() >= iSoftLimit)
            setOverLimitTime(DateTime::s_curTime);
        if ((int)getConns() >= ClientInfo::getPerClientHardLimit())
        {
            LS_NOTICE("[%s] Reached per client connection hard limit: %d, close connection!",
                      getAddrString(), ClientInfo::getPerClientHardLimit());
            setOverLimitTime(DateTime::s_curTime);
            setAccess(AC_BLOCK);
            return 1;
        }
    //fall through
    case AC_TRUST:
    default:
        break;
    }
    return 0;
}


GeoInfo *ClientInfo::allocateGeoInfo()
{
    if (!m_pGeoInfo)
        m_pGeoInfo = new GeoInfo();
    return m_pGeoInfo;
}


#ifdef USE_IP2LOCATION
LocInfo *ClientInfo::allocateLocInfo()
{
    if (!m_pLocInfo)
        m_pLocInfo = new LocInfo();
    return m_pLocInfo;
}
#endif


static inline int isGoog(const char *pHost, int iHostLen)
{
    if (!strncmp("googlebot.com", pHost + iHostLen - 13, 13))
        return 1;
    return (strncmp("google.com", pHost + iHostLen - 10, 10) == 0);
}


int ClientInfo::checkHost()
{
    struct sockaddr *pAddr = (struct sockaddr *)m_achSockAddr;
    clearFlag(CLIENTINFO_GOOG_TEST);
    if ((m_sHostName.len() == 0)
        || (isGoog(m_sHostName.c_str(), m_sHostName.len()) == 0))
    {
        setFlag(CLIENTINFO_GOOG_FAKE);
        LS_NOTICE("Client attempted to fake being google. Ip: %s, Host: %s",
                  m_sAddr.c_str(), m_sHostName.c_str());
        return 0;
    }
    return pAddr->sa_family;
}


void ClientInfo::verifyIp(void *ip, const long length)
{
    struct sockaddr *pAddr = (struct sockaddr *)m_achSockAddr;
    void *pOrigAddr;
    int size;
    if (pAddr->sa_family == AF_INET)
    {
        size = sizeof(in_addr);
        pOrigAddr = &((struct sockaddr_in *)pAddr)->sin_addr;
    }
    else
    {
        size = sizeof(in6_addr);
        pOrigAddr = &((struct sockaddr_in6 *)pAddr)->sin6_addr;
    }
    if ((size == length) && (memcmp(pOrigAddr, ip, size) == 0))
    {
        m_iFlags |= CLIENTINFO_GOOG_REAL;
        return;
    }

    m_iFlags |= CLIENTINFO_GOOG_FAKE;
    if (LS_LOG_ENABLED(log4cxx::Level::NOTICE))
    {
        char ipAddr[INET6_ADDRSTRLEN];
        inet_ntop(pAddr->sa_family, ip, ipAddr, INET6_ADDRSTRLEN);
        LS_NOTICE("Client attempted to fake being google. Host: %s, REAL Ip %*s",
                  m_sHostName.c_str(), (int)length, ipAddr);
    }
}
