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
#ifndef RAILSAPPCONFIG_H
#define RAILSAPPCONFIG_H

#include <lsdef.h>
#include <sys/types.h>
#include <stddef.h>
class AutoStr;
class ConfigCtx;
class LocalWorkerConfig;
class LocalWorker;
class Env;
class HttpVHost;
class RLimits;
class XmlNode;

class RailsAppConfig
{
private:
    static AutoStr      s_railsRunner;
    static int          s_iRailsEnv;
    static LocalWorkerConfig *s_pRailsDefault;
    static int s_iRubyProcLimit;
    static int s_iRailsAppLimit;
    RailsAppConfig() {}
    ~RailsAppConfig() {}
public:
    static int getRailsEnv()  { return s_iRailsEnv;}
    static const LocalWorkerConfig *getpRailsDefault()  { return s_pRailsDefault; }
    static LocalWorker *newRailsApp(HttpVHost *pvhost, const char *pAppName,
                                    const char *pName,
                                    const char *appPath, int maxConns, const char *pRailsEnv, int maxIdle,
                                    const Env *pEnv,
                                    int runOnStart, const char *pRubyPath = NULL);
    static int configRailsRunner(char *pRunnerCmd, int cmdLen,
                                 const char *pRubyBin);
    static int loadRailsDefault(const XmlNode *pNode);

    static void setRubyProcLimit(int val)   {   s_iRubyProcLimit = val;     }
    static int getRubyProcLimit()           {   return s_iRubyProcLimit;    }

    static void setRailsAppLimit(int val)   {   s_iRailsAppLimit = val;     }
    static int getRailsAppLimit()           {   return s_iRailsAppLimit;    }
    LS_NO_COPY_ASSIGN(RailsAppConfig);
};

#endif // RAILSAPPCONFIG_H
