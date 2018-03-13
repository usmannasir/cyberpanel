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
#ifndef HTTPCONFIGLOADER_H
#define HTTPCONFIGLOADER_H

#include <lsdef.h>
#include <util/autostr.h>

#include <limits.h>
class XmlNode;


class HttpConfigLoader
{
private:
    XmlNode        *m_pRoot;

    AutoStr         m_sConfigFilePath;


public:
    HttpConfigLoader()
        : m_pRoot(NULL)
    {};

    ~HttpConfigLoader();
    void releaseConfigXmlTree();
    int loadConfigFile();
    void setConfigFilePath(const char *pConfig)
    {   m_sConfigFilePath = pConfig;      }
    XmlNode *getRoot()                  {   return m_pRoot;         }


    LS_NO_COPY_ASSIGN(HttpConfigLoader);
};

#endif
