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
#include "proxyworker.h"
#include "proxyconfig.h"
#include "proxyconn.h"
#include <http/handlertype.h>
ProxyWorker::ProxyWorker(const char *pName)
    : ExtWorker(HandlerType::HT_PROXY)
{
    setConfigPointer(new ProxyConfig(pName));
}


ProxyWorker::~ProxyWorker()
{}


ExtConn *ProxyWorker::newConn()
{
    ProxyConn *pConn = new ProxyConn();
    //if (( pConn )&&( getConfig().getSsl() ))
    //    pConn->setUseSsl( 1 );

    return pConn;
}

