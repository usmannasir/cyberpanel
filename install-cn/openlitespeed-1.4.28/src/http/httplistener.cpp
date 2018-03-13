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
#include "httplistener.h"
#include <edio/multiplexer.h>
#include <edio/multiplexerfactory.h>
#include <http/clientcache.h>
#include <http/clientinfo.h>
#include <http/connlimitctrl.h>
#include <http/httpresourcemanager.h>
#include <http/httpvhost.h>
#include <http/ntwkiolink.h>
#include <http/smartsettings.h>
#include <http/vhostmap.h>
#include <log4cxx/logger.h>
#include <socket/coresocket.h>
#include <socket/gsockaddr.h>
#include <util/accessdef.h>

#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <netinet/in_systm.h>
#include <netinet/tcp.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <poll.h>
#include <sys/time.h>
#include <unistd.h>
#include <lsr/ls_strtool.h>

int32_t      HttpListener::m_iSockSendBufSize = -1;
int32_t      HttpListener::m_iSockRecvBufSize = -1;


HttpListener::HttpListener(const char *pName, const char *pAddr)
    : m_sName(pName)
    , m_pMapVHost(new VHostMap())
    , m_pSubIpMap(NULL)
    , m_iAdmin(0)
    , m_isSSL(0)
    , m_iBinding(0xffffffff)
{
    m_pMapVHost->setAddrStr(pAddr);
}


HttpListener::HttpListener()
    : m_pMapVHost(new VHostMap())
    , m_pSubIpMap(NULL)
    , m_iAdmin(0)
    , m_isSSL(0)
    , m_iBinding(0xffffffff)
{
}


HttpListener::~HttpListener()
{
    //stop();
    if (m_pMapVHost)
        delete m_pMapVHost;
    if (m_pSubIpMap)
        delete m_pSubIpMap;

}


void HttpListener::beginConfig()
{
}


void HttpListener::endConfig()
{
    m_pMapVHost->endConfig();
    if (m_pSubIpMap)
        m_pSubIpMap->endConfig();
    if (m_pMapVHost->getDedicated())
        setLogger(m_pMapVHost->getDedicated()->getLogger());
    if (m_pMapVHost->getSslContext()
        || (m_pSubIpMap && m_pSubIpMap->hasSSL()))
        m_isSSL = 1;
}


const char *HttpListener::buildLogId()
{
    AutoStr2 &id = getIdBuf();
    const AutoStr2 *pAddrStr;
    if (m_pMapVHost == NULL)
        return NULL;
    pAddrStr = m_pMapVHost->getAddrStr();
    if (pAddrStr == NULL || pAddrStr->len() == 0)
        return NULL;
    id = *pAddrStr;
    return id.c_str();
}


const char *HttpListener::getAddrStr() const
{
    return m_pMapVHost->getAddrStr()->c_str();
}


int  HttpListener::getPort() const
{
    return m_pMapVHost->getPort();
}


int HttpListener::assign(int fd, struct sockaddr *pAddr)
{
    GSockAddr addr(pAddr);
    char achAddr[128];
    if ((addr.family() == AF_INET)
        && (addr.getV4()->sin_addr.s_addr == INADDR_ANY))
        snprintf(achAddr, 128, "*:%hu", (short)addr.getPort());
    else if ((addr.family() == AF_INET6)
             && (IN6_IS_ADDR_UNSPECIFIED(&addr.getV6()->sin6_addr)))
        snprintf(achAddr, 128, "[::]:%hu", (short)addr.getPort());
    else
        addr.toString(achAddr, 128);
    LS_NOTICE("Recovering server socket: [%s]", achAddr);
    m_pMapVHost->setAddrStr(achAddr);
    if ((addr.family() == AF_INET6)
        && (IN6_IS_ADDR_UNSPECIFIED(&addr.getV6()->sin6_addr)))
        snprintf(achAddr, 128, "[ANY]:%hu", (short)addr.getPort());
    setName(achAddr);
    return setSockAttr(fd, addr);
}


int HttpListener::start()
{
    GSockAddr addr;
    if (addr.set(getAddrStr(), 0))
        return errno;
    int fd;
    int ret = CoreSocket::listen(addr, SmartSettings::getSockBacklog(), &fd,
                                 m_iSockSendBufSize, m_iSockRecvBufSize);
    if (ret != 0)
        return ret;
    return setSockAttr(fd, addr);
}


int HttpListener::setSockAttr(int fd, GSockAddr &addr)
{
    setfd(fd);
    ::fcntl(fd, F_SETFD, FD_CLOEXEC);
    ::fcntl(fd, F_SETFL, MultiplexerFactory::getMultiplexer()->getFLTag());
    int nodelay = 1;
    //::setsockopt( fd, IPPROTO_TCP, TCP_NODELAY, &nodelay, sizeof( int ) );
#ifdef TCP_DEFER_ACCEPT
    nodelay = 30;
    ::setsockopt(fd, IPPROTO_TCP, TCP_DEFER_ACCEPT, &nodelay, sizeof(int));
#endif

    //int tos = IPTOS_THROUGHPUT;
    //setsockopt( fd, IPPROTO_IP, IP_TOS, &tos, sizeof( tos ));
    m_pMapVHost->setPort(addr.getPort());

#ifdef SO_ACCEPTFILTER
    /*
     * FreeBSD accf_http filter
     */
    struct accept_filter_arg arg;
    memset(&arg, 0, sizeof(arg));
    strcpy(arg.af_name, "httpready");
    if (setsockopt(fd, SOL_SOCKET, SO_ACCEPTFILTER, &arg, sizeof(arg)) < 0)
    {
        if (errno != ENOENT)
            LS_NOTICE("Failed to set accept-filter 'httpready': %s",
                      strerror(errno));
    }
#endif

    return MultiplexerFactory::getMultiplexer()->add(this,
            POLLIN | POLLHUP | POLLERR);
}


int HttpListener::suspend()
{
    if (getfd() != -1)
    {
        MultiplexerFactory::getMultiplexer()->suspendRead(this);
        return 0;
    }
    return EBADF;
}


int HttpListener::resume()
{
    if (getfd() != -1)
    {
        MultiplexerFactory::getMultiplexer()->continueRead(this);
        return 0;
    }
    return EBADF;
}


int HttpListener::stop()
{
    if (getfd() != -1)
    {
        LS_INFO("Stop listener %s.", getAddrStr());
        MultiplexerFactory::getMultiplexer()->remove(this);
        close(getfd());
        setfd(-1);
        return 0;
    }
    return EBADF;
}


static void no_timewait(int fd)
{
    struct linger l = { 1, 0 };
    setsockopt(fd, SOL_SOCKET, SO_LINGER, &l, sizeof(l));
}


struct conn_data
{
    int             fd;
    char            achPeerAddr[24];
    ClientInfo     *pInfo;
};


#define CONN_BATCH_SIZE 10
int HttpListener::handleEvents(short event)
{
    static struct conn_data conns[CONN_BATCH_SIZE];
    static struct conn_data *pEnd = &conns[CONN_BATCH_SIZE];
    struct conn_data *pCur = conns;
    int allowed;
    int iCount = 0;
    ConnLimitCtrl &ctrl = ConnLimitCtrl::getInstance();
    int limitType = 1;
    allowed = ctrl.availConn();
    if (isSSL())
    {
        if (allowed > ctrl.availSSLConn())
        {
            allowed = ctrl.availSSLConn();
            limitType = 2;
        }
    }

    while (iCount < allowed)
    {
        socklen_t len = 24;
#ifdef SOCK_CLOEXEC
        static int isUseAccept4 = 1;
        if (isUseAccept4)
        {
            pCur->fd = accept4(getfd(), (struct sockaddr *)(pCur->achPeerAddr),
                               &len, SOCK_NONBLOCK | SOCK_CLOEXEC);
            if (pCur->fd == -1 && errno == ENOSYS)
            {
                isUseAccept4 = 0;
                continue;
            }
        }
        else
#endif
        {
            pCur->fd = accept(getfd(), (struct sockaddr *)(pCur->achPeerAddr), &len);
            if (pCur->fd != -1)
            {
                fcntl(pCur->fd, F_SETFD, FD_CLOEXEC);
                fcntl(pCur->fd, F_SETFL, MultiplexerFactory::getMultiplexer()->getFLTag());
            }
        }
        if (pCur->fd == -1)
        {
            resetRevent(POLLIN);
            if ((errno != EAGAIN) && (errno != ECONNABORTED)
                && (errno != EINTR))
            {
                LS_ERROR(this,
                         "HttpListener::acceptConnection(): Accept failed:%s!",
                         strerror(errno));
            }
            break;
        }
        //++iCount;
        //addConnection( conns, &iCount );

        ++pCur;
        if (pCur == pEnd)
        {
            iCount += CONN_BATCH_SIZE;
            batchAddConn(conns, pCur, &iCount);
            pCur = conns;
        }

    }
    if (pCur > conns)
    {
        int n = pCur - conns;
        iCount += n;
        if (n > 1)
            batchAddConn(conns, pCur, &iCount);
        else
            addConnection(conns, &iCount);
    }
    if (iCount > 0)
    {
        m_pMapVHost->incRef(iCount);
        ctrl.incConn(iCount);
    }
    if (iCount >= allowed)
    {
        if (limitType == 1)
        {
            if (ctrl.availConn() <= 0)
            {
                LS_DBG_H(this, "Max connections reached, suspend accepting!");
                ctrl.suspendAll();
            }
        }
        else
        {
            if (ctrl.availSSLConn() <= 0)
            {
                LS_DBG_M(this, "Max SSL connections reached, suspend accepting!");
                ctrl.suspendSSL();
            }
        }
    }
    LS_DBG_H(this, "%d connections accepted!", iCount);
    return 0;
}


int HttpListener::checkAccess(struct conn_data *pData)
{
    struct sockaddr *pPeer = (struct sockaddr *) pData->achPeerAddr;
    if ((AF_INET6 == pPeer->sa_family) &&
        (IN6_IS_ADDR_V4MAPPED(&((struct sockaddr_in6 *)pPeer)->sin6_addr)))
    {
        pPeer->sa_family = AF_INET;
        memmove(&((struct sockaddr_in *)pPeer)->sin_addr.s_addr,
                &pData->achPeerAddr[20], 4);
    }
    ClientInfo *pInfo = ClientCache::getClientCache()->getClientInfo(pPeer);
    pData->pInfo = pInfo;

    LS_DBG_H(this, "New connection from %s:%d.", pInfo->getAddrString(),
             ntohs(((struct sockaddr_in *)pPeer)->sin_port));

    return pInfo->checkAccess();
}


int HttpListener::batchAddConn(struct conn_data *pBegin,
                               struct conn_data *pEnd, int *iCount)
{
    struct conn_data *pCur = pBegin;
    int n = pEnd - pBegin;
    while (pCur < pEnd)
    {
        if (checkAccess(pCur))
        {
            no_timewait(pCur->fd);
            close(pCur->fd);
            pCur->fd = -1;
            --(*iCount);
            --n;
        }
        ++pCur;
    }
    if (n <= 0)
        return 0;
    NtwkIOLink *pConns[CONN_BATCH_SIZE];
    int ret = HttpResourceManager::getInstance().getNtwkIOLinks(pConns, n);
    pCur = pBegin;
    if (ret <= 0)
    {
        LS_ERR_NO_MEM("HttpSessionPool::getConnections()");
        LS_ERROR("Need %d connections, allocated %d connections!", n, ret);
        while (pCur < pEnd)
        {
            if (pCur->fd != -1)
            {
                close(pCur->fd);
                --(*iCount);
            }
            ++pCur;
        }
        return LS_FAIL;
    }
    NtwkIOLink **pConnEnd = &pConns[ret];
    NtwkIOLink **pConnCur = pConns;
    VHostMap *pMap;
    sockaddr_in *pAddrIn;
    //int flag = MultiplexerFactory::getMultiplexer()->getFLTag();
    while (pCur < pEnd)
    {
        int fd = pCur->fd;
        if (fd != -1)
        {
            assert(pConnCur < pConnEnd);
            NtwkIOLink *pConn = *pConnCur;

            if (m_pSubIpMap)
                pMap = getSubMap(fd);
            else
                pMap = getVHostMap();
            pAddrIn = (sockaddr_in *)pCur->achPeerAddr;
            pConn->setVHostMap(pMap);
            pConn->setLogger(getLogger());
            pConn->setRemotePort(ntohs(pAddrIn->sin_port));

            //    if ( getDedicated() )
            //    {
            //        //pConn->accessGranted();
            //    }
            if (!pConn->setLink(this, fd, pCur->pInfo, pMap->getSslContext()))
            {
                ++pConnCur;
                pConn->tryRead();
            }
            else
            {
                close(fd);
                --(*iCount);
            }
        }
        ++pCur;
    }
    if (pConnCur < pConnEnd)
        HttpResourceManager::getInstance().recycle(pConnCur,
                pConnEnd - pConnCur);

    return 0;
}


VHostMap *HttpListener::getSubMap(int fd)
{
    VHostMap *pMap;
    char achAddr[128];
    socklen_t addrlen = 128;
    if (getsockname(fd, (struct sockaddr *) achAddr, &addrlen) == -1)
        return 0;
    pMap = m_pSubIpMap->getMap((struct sockaddr *) achAddr);
    if (!pMap)
        pMap = m_pMapVHost;
    return pMap;
}


int HttpListener::addConnection(struct conn_data *pCur, int *iCount)
{
    int fd = pCur->fd;
    sockaddr_in *pAddrIn = (sockaddr_in *)pCur->achPeerAddr;
    if (checkAccess(pCur))
    {
        no_timewait(fd);
        close(fd);
        --(*iCount);
        return 0;
    }
    NtwkIOLink *pConn = HttpResourceManager::getInstance().getNtwkIOLink();
    if (!pConn)
    {
        LS_ERR_NO_MEM("HttpSessionPool::getConnection()");
        close(fd);
        --(*iCount);
        return LS_FAIL;
    }
    VHostMap *pMap;
    if (m_pSubIpMap)
        pMap = getSubMap(fd);
    else
        pMap = getVHostMap();
    pConn->setVHostMap(pMap);
    pConn->setLogger(getLogger());
    pConn->setRemotePort(ntohs(pAddrIn->sin_port));
    if (pConn->setLink(this, pCur->fd, pCur->pInfo, pMap->getSslContext()))
    {
        HttpResourceManager::getInstance().recycle(pConn);
        close(fd);
        --(*iCount);
        return LS_FAIL;
    }
    pConn->tryRead();
    return 0;
}


void HttpListener::onTimer()
{
}


VHostMap *HttpListener::addIpMap(const char *pIP)
{
    if (!m_pSubIpMap)
    {
        m_pSubIpMap = new SubIpMap();
        if (!m_pSubIpMap)
            return NULL;
    }
    VHostMap *pMap = m_pSubIpMap->addIP(pIP);
    if (pMap)
        pMap->setPort(m_pMapVHost->getPort());
    return pMap;
}


int HttpListener::addDefaultVHost(HttpVHost *pVHost)
{
    int count = 0;
    if (m_pMapVHost->addMaping(pVHost, "*", 1) == 0)
        ++count;
    if (m_pSubIpMap)
        count += m_pSubIpMap->addDefaultVHost(pVHost);
    return count;
}


int HttpListener::writeStatusReport(int fd)
{
    char achBuf[1024];

    int len = ls_snprintf(achBuf, 1024, "LISTENER%d [%s] %s\n",
                          isAdmin(), getName(), getAddrStr());
    if (::write(fd, achBuf, len) != len)
        return LS_FAIL;
    if (getVHostMap()->writeStatusReport(fd) == -1)
        return LS_FAIL;
    if (m_pSubIpMap && m_pSubIpMap->writeStatusReport(fd) == -1)
        return LS_FAIL;
    if (::write(fd, "ENDL\n", 5) != 5)
        return LS_FAIL;
    return 0;

}


int HttpListener::mapDomainList(HttpVHost *pVHost, const char *pDomains)
{
    return m_pMapVHost->mapDomainList(pVHost, pDomains);

}

