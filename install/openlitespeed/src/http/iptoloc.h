/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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
#ifndef IPTOLOC_H
#define IPTOLOC_H

#include <config.h>

#ifdef USE_IP2LOCATION

#include <inttypes.h>

#include <lsdef.h>
#include "IP2Location.h"

//class HttpReq;
class IEnv;
class IpToLoc;
class XmlNode;
class ConfigCtx;

class LocInfo
{
    friend class IpToLoc;
public:
    LocInfo();
    ~LocInfo();
    const char *getLocEnv(const char *pEnvName);
    int addLocEnv(IEnv *pEnv);
    //void addLocEnv( HttpReq * pReq );
    void reset();
    void release();

private:

    IP2LocationRecord *m_pRecord;
    LS_NO_COPY_ASSIGN(LocInfo);
};

class IpToLoc
{

public:
    IpToLoc();
    ~IpToLoc();

    int setIpToLocDbFile(char *pFile, const char *cacheMode);

    int lookUp(const char *pIp, int ipLen, LocInfo *pInfo);
    int config(const XmlNode *pNode);

    static void setIpToLoc(IpToLoc *pItl)
    {   s_pIpToLoc = pItl;  }
    static IpToLoc *getIpToLoc()
    {   return s_pIpToLoc;  }

private:
    int loadIpToLocDbFile(char *pFile, int flag);
    int testIpToLocDbFile(char *pFile, int flag);

    IP2Location    *m_pDb;
    static IpToLoc *s_pIpToLoc;
    LS_NO_COPY_ASSIGN(IpToLoc);
};

#endif // USE_IP2LOCATION
#endif
