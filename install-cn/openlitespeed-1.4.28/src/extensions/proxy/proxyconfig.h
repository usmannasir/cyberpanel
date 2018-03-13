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
#ifndef PROXYCONFIG_H
#define PROXYCONFIG_H




#include <lsdef.h>
#include <extensions/extworkerconfig.h>

class ProxyConfig : public ExtWorkerConfig
{
    int     m_iSsl;
public:
    ProxyConfig(const char *pName);
    ProxyConfig();
    ~ProxyConfig();

    int getSsl() const      {   return m_iSsl;  }
    void setSsl(int s)    {   m_iSsl = s;     }
    LS_NO_COPY_ASSIGN(ProxyConfig);
};

#endif
