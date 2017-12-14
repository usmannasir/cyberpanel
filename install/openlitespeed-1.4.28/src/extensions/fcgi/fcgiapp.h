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
#ifndef FCGIAPP_H
#define FCGIAPP_H


#include <lsdef.h>
#include <extensions/localworker.h>
class FcgiAppConfig;

class FcgiApp : public LocalWorker
{
    int             m_iMaxConns;
    int             m_iMaxReqs;

    ExtConn        *newConn();

public:
    //explicit FcgiApp( FcgiAppConfig& fcgiAppConfig );
    explicit FcgiApp(const char *pName);
    ~FcgiApp();

    //bool isReady()
    //{   return (getCurInstances() > 0); }
    int startEx();

    FcgiAppConfig &getConfig() const
    {   return *(FcgiAppConfig *)getConfigPointer();    }

    void setFcgiMaxConns(int max)     {   m_iMaxConns = max;          }
    void setFcgiMaxReqs(int max)      {   m_iMaxReqs = max;           }

    virtual int setURL(const char *pURL);

    LS_NO_COPY_ASSIGN(FcgiApp);
};

#endif
