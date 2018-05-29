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
#ifndef PROXYWORKER_H
#define PROXYWORKER_H


#include <lsdef.h>
#include <extensions/extworker.h>
class ProxyConfig;
class ProxyWorker : public ExtWorker
{
protected:

    virtual ExtConn *newConn();

public:
    explicit ProxyWorker(const char *pName);
    ~ProxyWorker();
    ProxyConfig &getConfig()
    {   return *((ProxyConfig *)getConfigPointer());  }

    LS_NO_COPY_ASSIGN(ProxyWorker);
};

#endif
