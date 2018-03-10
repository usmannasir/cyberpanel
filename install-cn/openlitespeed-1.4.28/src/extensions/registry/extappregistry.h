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
#ifndef EXTAPPREGISTRY_H
#define EXTAPPREGISTRY_H


#include <lsdef.h>
#include <sys/types.h>
#include <util/gpointerlist.h>

class ExtWorker;
class ExtAppMap;
class XmlNode;
class ConfigCtx;
class RLimits;
class HttpVHost;

class ExtAppSubRegistry
{
    ExtAppMap *m_pRegistry;
    ExtAppMap *m_pOldWorkers;
    TPointerList<ExtWorker> s_toBeStoped;
public:
    ExtAppSubRegistry();
    ~ExtAppSubRegistry();

    ExtWorker *addWorker(int type, const char *pName);
    ExtWorker *getWorker(const char *pName);
    int stopWorker(ExtWorker *pApp);
    int stopAllWorkers();
    void beginConfig();
    void endConfig();
    void clear();
    void onTimer();
    void runOnStartUp();
    int generateRTReport(int fd, int type);

    LS_NO_COPY_ASSIGN(ExtAppSubRegistry);
};
#define EA_CGID     0
#define EA_FCGI     1
#define EA_PROXY    2
#define EA_JENGINE  3
#define EA_LSAPI    4
#define EA_LOGGER   5
#define EA_LOADBALANCER 6
#define EA_NUM_APP  7

class ExtAppRegistry
{
private:
    static RLimits        *s_pRLimits;
public:
    static ExtWorker *newWorker(int type, const char *pName);
    static ExtWorker *addApp(int type, const char *pName);
    static ExtWorker *getApp(int type, const char *pName);
    static int stopApp(ExtWorker *pApp);
    static int stopAll();
    static void beginConfig();
    static void endConfig();
    static void clear();
    static void onTimer();
    static void runOnStartUp();
    static void init();
    static void shutdown();
    static int generateRTReport(int fd);
    static ExtWorker *configExtApp(const XmlNode *pNode);
    static int configLoadBalacner(const XmlNode *pNode,
                                  const HttpVHost *pVHost);
    static int configExtApps(const XmlNode *pRoot, const HttpVHost *pVHost);
    static RLimits *getRLimits()    {   return s_pRLimits;  }
    static void setRLimits(RLimits *pRLimits)   {   s_pRLimits = pRLimits;  }
    LS_NO_COPY_ASSIGN(ExtAppRegistry);
};

class PidSimpleList;
class PidRegistry
{
public:
    PidRegistry();
    ~PidRegistry();
    static void setSimpleList(PidSimpleList *pList);

    static void add(pid_t pid, ExtWorker *pApp, long tm);
    static ExtWorker *remove(pid_t pid);
    static void markToStop(pid_t pid, int kill_type);

    LS_NO_COPY_ASSIGN(PidRegistry);
};


#endif

