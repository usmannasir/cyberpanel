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
#include "fcgiapp.h"
#include "fcgiappconfig.h"
#include "fcgiconnection.h"
#include <http/handlertype.h>
#include <lsr/ls_time.h>

#include <signal.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>


FcgiApp::FcgiApp(const char *pName)
    : LocalWorker(HandlerType::HT_FASTCGI)
    , m_iMaxConns(10)
    , m_iMaxReqs(10)
{
    setConfigPointer(new FcgiAppConfig(pName));
}


FcgiApp::~FcgiApp()
{
    //stop();
}

int FcgiApp::startEx()
{
    int ret = 1;
    if ((getConfig().getURL()) && (getConfig().getCommand()))
        ret = startWorker();
    return ret;
}


ExtConn *FcgiApp::newConn()
{
    return new FcgiConnection();
}


int FcgiApp::setURL(const char *pURL)
{
//    return ExtWorker::setURL( pURL );
    getConfig().setURL(pURL);
    if (getfd() == -1)
        return getConfig().updateServerAddr(pURL);
    return 0;
}

