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
#include "extappregistry.h"

#include <http/handlerfactory.h>
#include <http/handlertype.h>
#include <http/serverprocessconfig.h>
#include <log4cxx/logger.h>
#include <main/configctx.h>
#include <socket/gsockaddr.h>
#include <util/hashstringmap.h>
#include <util/rlimits.h>
#include <util/staticobj.h>
#include <util/stringlist.h>
#include <util/stringtool.h>
#include <util/xmlnode.h>

#include <extensions/extworker.h>
#include <extensions/loadbalancer.h>
#include <extensions/localworkerconfig.h>
#include <extensions/pidlist.h>
#include <extensions/cgi/cgidworker.h>
#include <extensions/fcgi/fcgiapp.h>
#include <extensions/jk/jworker.h>
#include <extensions/lsapi/lsapiworker.h>
#include <extensions/proxy/proxyconfig.h>
#include <extensions/proxy/proxyworker.h>
#include <unistd.h>


static ExtWorker *newWorker(int type, const char *pName);
static StaticObj< ExtAppSubRegistry > s_registry[EA_NUM_APP];
static StaticObj< PidList > s_pidList;
static PidSimpleList *s_pSimpleList = NULL;

RLimits *ExtAppRegistry::s_pRLimits = NULL;

class ExtAppMap : public HashStringMap< ExtWorker * >
{
public:
    ExtAppMap()
    {}
    ~ExtAppMap()
    {   removeAll();    }
    void removeAll();
    LS_NO_COPY_ASSIGN(ExtAppMap);
};


void ExtAppMap::removeAll()
{
    release_objects();
}


ExtAppSubRegistry::ExtAppSubRegistry()
    : m_pRegistry(new ExtAppMap())
    , m_pOldWorkers(new ExtAppMap())
{
}


ExtAppSubRegistry::~ExtAppSubRegistry()
{
    if (m_pRegistry)
        delete m_pRegistry;
    if (m_pOldWorkers)
        delete m_pOldWorkers;
    s_toBeStoped.release_objects();
}


ExtWorker *ExtAppSubRegistry::addWorker(int type, const char *pName)
{
    if (pName == NULL)
        return NULL;
    ExtAppMap::iterator iter = m_pRegistry->find(pName);
    if (iter != m_pRegistry->end())
        return iter.second();
    else
    {
        ExtWorker *pApp = NULL;
        iter = m_pOldWorkers->find(pName);
        if (iter != m_pOldWorkers->end())
        {
            pApp = iter.second();
            m_pOldWorkers->remove(pApp->getName());
        }
        else
            pApp = newWorker(type, pName);
        if (pApp)
            m_pRegistry->insert(pApp->getName(), pApp);
        return pApp;
    }
}


ExtWorker *ExtAppSubRegistry::getWorker(const char *pName)
{
    if ((pName == NULL) || (strlen(pName) == 0))
        return NULL;
    ExtAppMap::iterator iter = m_pRegistry->find(pName);
    if (iter == m_pRegistry->end())
        return NULL;
//    if ( iter.second()->notStarted() )
//    {
//        if ( iter.second()->start() == -1 )
//            return NULL;
//    }
    return iter.second();

}


int ExtAppSubRegistry::stopWorker(ExtWorker *pApp)
{
    if (pApp)
        return pApp->stop();
    return 0;
}


int ExtAppSubRegistry::stopAllWorkers()
{
    ExtAppMap::iterator iter;
    for (iter = m_pRegistry->begin();
         iter != m_pRegistry->end();
         iter = m_pRegistry->next(iter))
        iter.second()->stop();
    return 0;
}


void ExtAppSubRegistry::runOnStartUp()
{
    ExtAppMap::iterator iter;
    for (iter = m_pRegistry->begin();
         iter != m_pRegistry->end();
         iter = m_pRegistry->next(iter))
        iter.second()->runOnStartUp();
}


void ExtAppSubRegistry::beginConfig()
{
    assert(m_pOldWorkers->size() == 0);
    m_pRegistry->swap(*m_pOldWorkers);

}


void ExtAppSubRegistry::endConfig()
{
    ExtAppMap::iterator iter;
    for (iter = m_pOldWorkers->begin();
         iter != m_pOldWorkers->end();
         iter = m_pRegistry->next(iter))
    {
        if (iter.second()->canStop())
            delete iter.second();
        else
            s_toBeStoped.push_back(iter.second());
    }
    m_pOldWorkers->clear();
}


void ExtAppSubRegistry::onTimer()
{
    ExtAppMap::iterator iter;
    for (iter = m_pRegistry->begin();
         iter != m_pRegistry->end();
         iter = m_pRegistry->next(iter))
        iter.second()->onTimer();
}


void ExtAppSubRegistry::clear()
{
    m_pRegistry->release_objects();
    m_pOldWorkers->release_objects();
}


int ExtAppSubRegistry::generateRTReport(int fd, int type)
{
    static const char *s_pTypeName[] =
    {
        "CGI",
        "FastCGI",
        "Proxy",
        "Servlet",
        "LSAPI",
        "Logger"
    };

    ExtAppMap::iterator iter;
    for (iter = m_pRegistry->begin();
         iter != m_pRegistry->end();
         iter = m_pRegistry->next(iter))
        iter.second()->generateRTReport(fd, s_pTypeName[ type ]);
    return 0;
}


static ExtWorker *newWorker(int type, const char *pName)
{
    ExtWorker *pWorker;
    switch (type)
    {
    case EA_CGID:
        pWorker = new CgidWorker(pName);
        break;
    case EA_FCGI:
        pWorker = new FcgiApp(pName);
        break;
    case EA_PROXY:
        pWorker = new ProxyWorker(pName);
        break;
    case EA_JENGINE:
        pWorker = new JWorker(pName);
        break;
    case EA_LSAPI:
        pWorker = new LsapiWorker(pName);
        break;
    case EA_LOGGER:
        pWorker = new FcgiApp(pName);
        break;
    case EA_LOADBALANCER:
        pWorker = new LoadBalancer(pName);
        break;
    default:
        return NULL;
    }
    return pWorker;
}


ExtWorker *ExtAppRegistry::addApp(int type, const char *pName)
{
    assert(type >= 0 && type < EA_NUM_APP);
    return s_registry[type]()->addWorker(type, pName);
}


ExtWorker *ExtAppRegistry::getApp(int type, const char *pName)
{
    assert(type >= 0 && type < EA_NUM_APP);
    return s_registry[type]()->getWorker(pName);
}


int ExtAppRegistry::stopApp(ExtWorker *pApp)
{
    if (pApp)
        return pApp->stop();
    return 0;
}


int ExtAppRegistry::stopAll()
{
    for (int i = 0; i < EA_NUM_APP; ++i)
        s_registry[i]()->stopAllWorkers();
    return 0;
}


void ExtAppRegistry::beginConfig()
{
    for (int i = 0; i < EA_NUM_APP; ++i)
        s_registry[i]()->beginConfig();
}


void ExtAppRegistry::endConfig()
{
    for (int i = 0; i < EA_NUM_APP; ++i)
        s_registry[i]()->endConfig();
}


void ExtAppRegistry::clear()
{
    for (int i = 0; i < EA_NUM_APP; ++i)
        s_registry[i]()->clear();
}


void ExtAppRegistry::onTimer()
{
    for (int i = 0; i < EA_NUM_APP; ++i)
        s_registry[i]()->onTimer();
}


void ExtAppRegistry::init()
{
    for (int i = 0; i < EA_NUM_APP; ++i)
        s_registry[i].construct();
    s_pidList.construct();
}


void ExtAppRegistry::shutdown()
{
    s_pidList.destruct();
    s_pSimpleList = NULL;
    for (int i = 0; i < EA_NUM_APP; ++i)
    {
        s_registry[i]()->clear();
        s_registry[i].destruct();
    }
}


void ExtAppRegistry::runOnStartUp()
{
    for (int i = 0; i < EA_NUM_APP; ++i)
    {
        if (i != EA_LOGGER)
            s_registry[i]()->runOnStartUp();
    }

}


int ExtAppRegistry::generateRTReport(int fd)
{
    for (int i = 0; i < EA_NUM_APP; ++i)
    {
        if (i != EA_LOGGER)
            s_registry[i]()->generateRTReport(fd, i);
    }
    return 0;
}


ExtWorker *ExtAppRegistry::configExtApp(const XmlNode *pNode)
{
    int iType;
    int role;
    char achAddress[128];
    GSockAddr addr;
    char achName[256];
    const char *pName;
    const char *pType;
    const char *pUri;
    char buf[MAX_PATH_LEN];
    int iAutoStart = 0;
    const char *pPath = NULL;
    ExtWorker *pWorker = NULL;
    ExtWorkerConfig *pConfig = NULL;
    int isHttps = 0;
    int len = 0;
    if (ServerProcessConfig::getInstance().getChroot() != NULL)
        len = ServerProcessConfig::getInstance().getChroot()->len();
    if (strncasecmp(pNode->getName(), "extProcessor", 12) != 0)
        return NULL;

    pName = ConfigCtx::getCurConfigCtx()->getExpandedTag(pNode, "name",
            achName, 256, 1);
    if (pName == NULL)
        return NULL;

    ConfigCtx currentCtx(pName);

    pType = ConfigCtx::getCurConfigCtx()->getTag(pNode, "type");
    if (!pType)
        return NULL;

    iType = HandlerType::getHandlerType(pType, role);
    if ((iType < HandlerType::HT_FASTCGI) ||
        (iType >= HandlerType::HT_END))
    {
        LS_ERROR(&currentCtx, "unknown external processor <type>: %s", pType);
        return NULL;
    }

    if (HandlerType::HT_LOADBALANCER == iType)
        return NULL;

    iType -= HandlerType::HT_CGI;

    pUri = ConfigCtx::getCurConfigCtx()->getExpandedTag(pNode, "address",
            achAddress, 128);
    if ((pUri == NULL) && (iType != HandlerType::HT_LOGGER))
        return NULL;

    //Check http or https for proxy type
    if (iType == EA_PROXY)
    {
        if (strncasecmp(pUri, "https://", 8) == 0)
            isHttps = 1;

        //Remove the protocol prefix
        if (strstr(pUri, "//"))
            pUri = strstr(pUri, "//") + 2;

        //Remove last '/' if exists
        int l = strlen(achAddress);
        if (achAddress[l - 1] == '/')
            achAddress[l - 1] = 0x00;

        if (strchr(pUri, ':') == NULL)
            strcat(achAddress, (isHttps ? ":443" : ":80"));

        LS_DBG_L(&currentCtx, "ExtApp Proxy isHttps %d, Uri %s.",  isHttps, pUri);
    }

    if (addr.set(pUri, NO_ANY | DO_NSLOOKUP))
    {
        LS_ERROR(&currentCtx, "failed to set socket address %s!", pUri);
        return NULL;
    }

    if ((iType == EA_FCGI) || (iType == EA_LOGGER) || (iType == EA_LSAPI))
    {
        if (iType == EA_LOGGER)
            iAutoStart = 1;
        else
            iAutoStart = ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "autoStart",
                         0, 2, 0);

        pPath = pNode->getChildValue("path");

        if ((iAutoStart) && ((!pPath || !*pPath)))
        {
            currentCtx.logErrorMissingTag("path");
            return NULL;
        }

        if (iAutoStart)
        {
            if (ConfigCtx::getCurConfigCtx()->getAbsoluteFile(buf, pPath) != 0)
                return NULL;

            char *pCmd = buf;
            char *p = (char *) StringTool::strNextArg(pCmd);

            if (p)
                *p = 0;

            if (access(pCmd, X_OK) == -1)
            {
                LS_ERROR(&currentCtx, "invalid path - %s, "
                         "it cannot be started by Web server!", buf);
                return NULL;
            }

            if (p)
                *p = ' ';

            if (pCmd != buf)
                buf[len] = *buf;

            pPath = &buf[len];
        }
    }
    pWorker = addApp(iType, pName);

    if (!pWorker)
    {
        LS_ERROR(&currentCtx, "failed to add external processor!");
        return NULL;
    }
    pConfig = pWorker->getConfigPointer();
    assert(pConfig);

    if (pUri)
    {
        if (iType == EA_PROXY)
            ((ProxyWorker *)pWorker)->getConfig().setSsl(isHttps);

        if (pWorker->setURL(pUri))
        {
            LS_ERROR(&currentCtx, "failed to set socket address to %s!", pName);
            return NULL;
        }
    }

    pWorker->setRole(role);

    pConfig->config(pNode);

    if (!iAutoStart)
    {
        pConfig->getEnv()->add(0, 0, 0, 0);
        return pWorker;
    }

    LocalWorker *pApp = static_cast<LocalWorker *>(pWorker);

    if (pApp)
    {
        LocalWorkerConfig &config = pApp->getConfig();
        config.setAppPath(pPath);
        config.setStartByServer(iAutoStart);

        config.config(pNode);
        config.configExtAppUserGroup(pNode, iType);
    }

    return pWorker;

}


int ExtAppRegistry::configLoadBalacner(const XmlNode *pNode,
                                       const HttpVHost *pVHost)
{
    if (strncasecmp(pNode->getName(), "extProcessor", 12) != 0)
        return 1;

    char achName[256];
    const char *pName = ConfigCtx::getCurConfigCtx()->getExpandedTag(pNode,
                        "name", achName, 256, 1);

    if (pName == NULL)
        return 1;

    ConfigCtx currentCtx(pName);

    const char *pType = ConfigCtx::getCurConfigCtx()->getTag(pNode, "type");

    if (!pType)
        return 1;

    int iType;
    int role;
    iType = HandlerType::getHandlerType(pType, role);

    if (HandlerType::HT_LOADBALANCER != iType)
        return 1;

    iType -= HandlerType::HT_CGI;

    LoadBalancer *pLB;

    pLB = (LoadBalancer *) addApp(iType, pName);

    if (!pLB)
    {
        LS_ERROR(&currentCtx, "failed to add load balancer!");
        return 1;
    }
    else
    {
        pLB->clearWorkerList();

        if (pVHost)
            pLB->getConfigPointer()->setVHost(pVHost);

        const char *pWorkers = pNode->getChildValue("workers");

        if (pWorkers)
        {
            StringList workerList;
            workerList.split(pWorkers, pWorkers + strlen(pWorkers), ",");
            StringList::const_iterator iter;

            for (iter = workerList.begin(); iter != workerList.end(); ++iter)
            {
                const char *pType = (*iter)->c_str();
                char *pName = (char *) strstr(pType, "::");

                if (!pName)
                {
                    LS_ERROR(&currentCtx, "invalid worker syntax [%s].", pType);
                    continue;
                }

                *pName = 0;
                pName += 2;
                iType = HandlerType::getHandlerType(pType, role);

                if ((iType == HandlerType::HT_LOADBALANCER) ||
                    (iType == HandlerType::HT_LOGGER) ||
                    (iType < HandlerType::HT_CGI))
                {
                    LS_ERROR(&currentCtx,
                             "invalid handler type [%s] for load balancer worker.",
                             pType);
                    continue;
                }

                const ExtWorker *pWorker = static_cast<const ExtWorker *>
                                           (HandlerFactory::getHandler(pType, pName));

                if (pWorker)
                {
                    if (pWorker->getConfigPointer()->getVHost() != pVHost)
                    {
                        LS_ERROR(&currentCtx, "Access to handler [%s:%s] is denied!",
                                 pType, pName);
                        continue;
                    }
                }

                if (pWorker)
                    pLB->addWorker((ExtWorker *) pWorker);
            }
        }
    }

    return 0;

}


int ExtAppRegistry::configExtApps(const XmlNode *pRoot,
                                  const HttpVHost *pVHost)
{
    const XmlNode *pNode = pRoot->getChild("extProcessorList", 1);

    XmlNodeList list;
    int c = pNode->getAllChildren(list);
    int add = 0 ;
    XmlNode *pExtAppNode;

    for (int i = 0 ; i < c ; ++ i)
    {
        pExtAppNode = list[i];
        ExtWorker *pWorker = configExtApp(pExtAppNode);
        if (pWorker != NULL)
        {
            if (pVHost)
                pWorker->getConfigPointer()->setVHost(pVHost);
            ++add ;
        }
    }

    for (int i = 0 ; i < c ; ++ i)
    {
        pExtAppNode = list[i];

        if (configLoadBalacner(pExtAppNode, pVHost) == 0)
            ++add ;
    }

    return 0;

}


PidRegistry::PidRegistry()
{
}


PidRegistry::~PidRegistry()
{
}


void PidRegistry::add(pid_t pid, ExtWorker *pApp, long tm)
{
    s_pidList()->add(pid, tm);
    if (pApp)
        pApp->addPid(pid);

    if (s_pSimpleList)
        s_pSimpleList->add(pid, getpid(), pApp);
}


ExtWorker *PidRegistry::remove(pid_t pid)
{
    ExtWorker *pWorker = NULL;
    if (s_pSimpleList)
    {
        pWorker = s_pSimpleList->remove(pid);
        s_pidList()->remove(pid);
    }
    return pWorker;

}


void PidRegistry::setSimpleList(PidSimpleList *pList)
{
    s_pSimpleList = pList;
}


void PidRegistry::markToStop(pid_t pid, int kill_type)
{
    if (s_pSimpleList)
        s_pSimpleList->markToStop(pid, kill_type);
}


