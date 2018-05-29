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
#include "httpconfigloader.h"

#include <main/mainserverconfig.h>
#include <main/plainconf.h>
#include <util/xmlnode.h>

HttpConfigLoader::~HttpConfigLoader()
{
}


int HttpConfigLoader::loadConfigFile()
{
    plainconf::initKeywords();
    plainconf::setRootPath(MainServerConfig::getInstance().getServerRoot());

    if (!m_pRoot)
        m_pRoot = plainconf::parseFile(m_sConfigFilePath.c_str(),
                                       "httpServerConfig");

    return (m_pRoot == NULL) ? -1 : 0;
}


void HttpConfigLoader::releaseConfigXmlTree()
{
    if (m_pRoot)
    {
        delete m_pRoot;
        m_pRoot = NULL;
    }
}
