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
#include "extworkerconfig.h"

#include <http/httpdefs.h>
#include <lsr/ls_strtool.h>
#include <main/configctx.h>
#include <socket/gsockaddr.h>
#include <util/xmlnode.h>

#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <unistd.h>

ExtWorkerConfig::ExtWorkerConfig(const char *pName)
    : m_sURL(NULL)
    , m_sName(pName)
    , m_pVHost(NULL)
    , m_iMaxConns(1)
    , m_iTimeout(10)
    , m_iRetryTimeout(3)
    , m_iBuffering(0)
    , m_iKeepAlive(1)
    , m_iMaxIdleTime(INT_MAX)
    , m_iKeepAliveTimeout(INT_MAX)
    , m_iSelfManaged(1)
    , m_iStartByServer(0)
    , m_iRefAddr(0)
    , m_iDaemonSuEXEC(0)
    , m_uid(-1)
    , m_gid(-1)
    , m_pServerAddr(new GSockAddr())
    , m_pOrgEnv(NULL)
{
}


ExtWorkerConfig::ExtWorkerConfig()
    : m_pVHost(NULL)
    , m_iMaxConns(1)
    , m_iBuffering(0)
    , m_iRefAddr(0)
    , m_iDaemonSuEXEC(0)
    , m_uid(-1)
    , m_gid(-1)
    , m_pServerAddr(new GSockAddr())
{}


ExtWorkerConfig::~ExtWorkerConfig()
{
    if (!m_iRefAddr && m_pServerAddr)
        delete m_pServerAddr;
}


ExtWorkerConfig::ExtWorkerConfig(const ExtWorkerConfig &rhs)
{
    m_sURL = rhs.m_sURL;
    m_sName = rhs.m_sName;
    m_pVHost = rhs.m_pVHost;
    m_iMaxConns = rhs.m_iMaxConns;
    m_iBuffering = rhs.m_iBuffering;
    m_iRefAddr = rhs.m_iRefAddr;
    m_iDaemonSuEXEC = rhs.m_iDaemonSuEXEC;
    m_uid = rhs.m_uid;
    m_gid = rhs.m_gid;
    if (m_iRefAddr)
        m_pServerAddr = rhs.m_pServerAddr;
    else
        m_pServerAddr = new GSockAddr(*rhs.m_pServerAddr);
}


int ExtWorkerConfig::setURL(const char *pURL)
{
    if (pURL != NULL)
    {
        if ((m_sURL.c_str() == NULL) || (strcmp(m_sURL.c_str(), pURL) != 0))
        {
            m_sURL = pURL;
            return 0;
        }
    }
    return LS_FAIL;
}


void ExtWorkerConfig::setServerAddr(const GSockAddr *pAddr)
{
    if ((m_iRefAddr == 0) && (m_pServerAddr))
        delete m_pServerAddr;
    m_iRefAddr = 1;
    m_pServerAddr = (GSockAddr *)pAddr;
}


int ExtWorkerConfig::updateServerAddr(const char *pURL)
{
    if (m_iRefAddr)
        return LS_FAIL;
    return m_pServerAddr->set(pURL, NO_ANY | DO_NSLOOKUP);
}


void ExtWorkerConfig::setName(const char *pName)
{
    if (pName != NULL)
        m_sName = pName;
}


const char *ExtWorkerConfig::getServerAddrUnixSock() const
{
    if (m_pServerAddr && (m_pServerAddr->family() == AF_UNIX))
        return (const char *)m_pServerAddr->getUnix();
    return NULL;
}


void ExtWorkerConfig::altServerAddr()
{
    if (!m_pServerAddr || m_iRefAddr)
        return;
    switch (m_pServerAddr->family())
    {
    case AF_UNIX:
        {
            char *p1 = (char *)m_pServerAddr->getUnix();
            char *p = p1 + strlen(m_sURL.c_str()) - 5;
            int seq = rand() % 1000;
            ls_snprintf(p, p1 + 102 - p, ".%03d", seq);
        }
        break;
    case AF_INET:
    case AF_INET6:
        {
            short port = m_pServerAddr->getPort();
            m_pServerAddr->setPort(port + 1);
        }
        break;
    }
}


extern int removeSimiliarFiles(const char *pPath, long tm);


void ExtWorkerConfig::removeUnusedSocket()
{
    removeSimiliarFiles(m_sURL.c_str() + 5, 0);
    unlink(m_sURL.c_str() + 5);
}


void ExtWorkerConfig::config(const XmlNode *pNode)
{
    const char *pValue;
    int iMaxConns = ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                    "maxConns", 1, 2000, 1);
    int iRetryTimeout = ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                        "retryTimeout", 0, LONG_MAX, 10);
    int iInitTimeout = ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                       "initTimeout", 1, LONG_MAX, 3);
    int iBuffer = ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                  "respBuffer", 0, 2, 1);
    int iKeepAlive = ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                     "persistConn", 0, 1, 1);
    int iKeepAliveTimeout = ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                            "pcKeepAliveTimeout", -1, INT_MAX, INT_MAX);

    if (iKeepAliveTimeout == -1)
        iKeepAliveTimeout = INT_MAX;

    if (iBuffer == 1)
        iBuffer = 0;
    else if (iBuffer == 0)
        iBuffer = HEC_RESP_NOBUFFER;
    else if (iBuffer == 2)
        iBuffer = HEC_RESP_NPH;

    setPersistConn(iKeepAlive);
    setKeepAliveTimeout(iKeepAliveTimeout);
    setMaxConns(iMaxConns);
    setTimeout(iInitTimeout);
    setRetryTimeout(iRetryTimeout);
    setBuffering(iBuffer);
    clearEnv();
    const XmlNodeList *pList = pNode->getChildren("env");

    if (pList)
    {
        XmlNodeList::const_iterator iter;

        for (iter = pList->begin(); iter != pList->end(); ++iter)
        {
            pValue = (*iter)->getValue();

            if (pValue)
                addEnv((*iter)->getValue());
        }
    }

}
