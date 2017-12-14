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
#include "railsappconfig.h"
#include "extappregistry.h"

#include <http/serverprocessconfig.h>
#include <log4cxx/logger.h>
#include <main/configctx.h>
#include <main/mainserverconfig.h>
#include <util/xmlnode.h>

#include <extensions/localworker.h>
#include <extensions/localworkerconfig.h>
#include <unistd.h>
#include <limits.h>
#include <config.h>

AutoStr     RailsAppConfig::s_railsRunner;
int         RailsAppConfig::s_iRailsEnv = 1;
LocalWorkerConfig *RailsAppConfig::s_pRailsDefault = NULL;
int         RailsAppConfig::s_iRubyProcLimit = 10;
int         RailsAppConfig::s_iRailsAppLimit = 1;


LocalWorker *RailsAppConfig::newRailsApp(HttpVHost *pvhost,
        const char *pAppName, const char *pName,
        const char *appPath, int maxConns, const char *pRailsEnv, int maxIdle,
        const Env *pEnv,
        int runOnStart, const char *pRubyPath)
{
    int iChrootlen = 0;
    if (ServerProcessConfig::getInstance().getChroot() != NULL)
        iChrootlen = ServerProcessConfig::getInstance().getChroot()->len();
    char achFileName[MAX_PATH_LEN];
    const char *pRailsRunner = s_railsRunner.c_str();

    if (!s_pRailsDefault)
        return NULL;

    int pathLen = snprintf(achFileName, MAX_PATH_LEN, "%s", appPath);

    if (pathLen > MAX_PATH_LEN - 20)
    {
        LS_ERROR(ConfigCtx::getCurConfigCtx(),
                 "path to Rack application is too long!");
        return NULL;
    }

    if (access(achFileName, F_OK) != 0)
    {
        ConfigCtx::getCurConfigCtx()->logErrorPath("Rack application",
                achFileName);
        return NULL;
    }
    if (!pRailsRunner)
    {
        LS_ERROR(ConfigCtx::getCurConfigCtx(),
                 "'Ruby path' is not set properly, Rack context is disabled!");
        return NULL;
    }

    LocalWorker *pWorker;
    char achAppName[1024];
    char achName[MAX_PATH_LEN];
    snprintf(achAppName, 1024, "Rack:%s:%s", pName, pAppName);

    pWorker = (LocalWorker *) ExtAppRegistry::addApp(EA_LSAPI, achAppName);

    strcpy(&achFileName[pathLen], "tmp/sockets");
    //if ( access( achFileName, W_OK ) == -1 )
    {
        snprintf(achName, MAX_PATH_LEN, "uds:/%s/%s:%s.sock",
                 DEFAULT_TMP_DIR,
                 pName, pAppName);

        for (char *p = &achName[18]; *p; ++p)
        {
            if (*p == '/')
                *p = '_';
        }
    }
    pWorker->setURL(achName);


    LocalWorkerConfig &config = pWorker->getConfig();
    config.setVHost(pvhost);
    config.setAppPath(pRailsRunner);
    config.setBackLog(s_pRailsDefault->getBackLog());
    config.setSelfManaged(1);
    config.setStartByServer(2);
    config.setMaxConns(maxConns);
    config.setKeepAliveTimeout(s_pRailsDefault->getKeepAliveTimeout());
    config.setPersistConn(1);
    config.setTimeout(s_pRailsDefault->getTimeout());
    config.setRetryTimeout(s_pRailsDefault->getRetryTimeout());
    config.setBuffering(s_pRailsDefault->getBuffering());
    config.setPriority(s_pRailsDefault->getPriority());
    config.setMaxIdleTime(maxIdle);
    config.setRLimits(s_pRailsDefault->getRLimits());

    config.setInstances(1);
    config.clearEnv();

    if (pEnv)
        config.getEnv()->add(pEnv);

    achFileName[pathLen] = 0;
    snprintf(achName, MAX_PATH_LEN, "RAILS_ROOT=%s", &achFileName[iChrootlen]);
    config.addEnv(achName);

    if (pRailsEnv)
    {
        snprintf(achName, MAX_PATH_LEN, "RAILS_ENV=%s", pRailsEnv);
        config.addEnv(achName);
    }

    if (maxConns > 1)
    {
        snprintf(achName, MAX_PATH_LEN, "LSAPI_CHILDREN=%d", maxConns);
        config.addEnv(achName);
    }
    else
        config.setSelfManaged(0);

    if (maxIdle != INT_MAX)
    {
        snprintf(achName, MAX_PATH_LEN, "LSAPI_MAX_IDLE=%d", maxIdle);
        config.addEnv(achName);
        snprintf(achName, MAX_PATH_LEN, "LSAPI_PGRP_MAX_IDLE=%d", maxIdle);
        config.addEnv(achName);
    }

    config.getEnv()->add(s_pRailsDefault->getEnv());
    config.addEnv(NULL);

    config.setRunOnStartUp(runOnStart);
    return pWorker;
}


int RailsAppConfig::configRailsRunner(char *pRunnerCmd, int cmdLen,
                                      const char *pRubyBin)
{
    const char *rubyBin[2] = { "/usr/local/bin/ruby", "/usr/bin/ruby" };

    if ((pRubyBin) && (access(pRubyBin, X_OK) != 0))
    {
        LS_ERROR(ConfigCtx::getCurConfigCtx(), "Ruby path is not vaild: %s",
                 pRubyBin);
        pRubyBin = NULL;
    }

    if (!pRubyBin)
    {
        for (int i = 0; i < 2; ++i)
        {
            if (access(rubyBin[         i], X_OK) == 0)
            {
                pRubyBin = rubyBin[i];
                break;
            }
        }
    }

    if (!pRubyBin)
    {
        LS_NOTICE(ConfigCtx::getCurConfigCtx(),
                  "Cannot find ruby interpreter, Rails easy configuration is turned off");
        return LS_FAIL;
    }

    snprintf(pRunnerCmd, cmdLen, "%s %sfcgi-bin/RackRunner.rb", pRubyBin,
             MainServerConfig::getInstance().getServerRoot());
    return 0;
}


int RailsAppConfig::loadRailsDefault(const XmlNode *pNode)
{
    const char *pRubyBin = NULL;
    s_iRailsEnv = 1;

    s_pRailsDefault = new LocalWorkerConfig();

    s_pRailsDefault->setPersistConn(1);
    s_pRailsDefault->setKeepAliveTimeout(30);
    s_pRailsDefault->setMaxConns(1);
    s_pRailsDefault->setTimeout(120);
    s_pRailsDefault->setRetryTimeout(0);
    s_pRailsDefault->setBuffering(0);
    s_pRailsDefault->setPriority(
        ServerProcessConfig::getInstance().getPriority() + 1);
    s_pRailsDefault->setBackLog(10);
    s_pRailsDefault->setMaxIdleTime(300);
    s_pRailsDefault->setRLimits(ExtAppRegistry::getRLimits());
    s_pRailsDefault->getRLimits()->setCPULimit(RLIM_INFINITY, RLIM_INFINITY);

    if (!pNode)
        return LS_FAIL;

    if (ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "enableRailsHosting",
            0, 1, 0) == 1)
    {
        setRailsAppLimit(ConfigCtx::getCurConfigCtx()->getLongValue(
                             pNode, "railsAppLimit", 0, 20, 1));
        setRubyProcLimit(ConfigCtx::getCurConfigCtx()->getLongValue(
                             pNode, "rubyProcLimit", 0, 100, 10));
    }
    else
        setRailsAppLimit(-1);

    s_iRailsEnv = ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "railsEnv",
                  0, 2, 1);
    pRubyBin = pNode->getChildValue("rubyBin");
    char achBuf[4096];

    if (configRailsRunner(achBuf, 4096, pRubyBin) == -1)
        return LS_FAIL;

    s_railsRunner.setStr(achBuf);

    ((ExtWorkerConfig *)s_pRailsDefault)->config(pNode);
    s_pRailsDefault->config(pNode);

    return 0;
}
