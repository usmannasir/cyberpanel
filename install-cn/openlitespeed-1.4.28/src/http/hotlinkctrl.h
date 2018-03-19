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
#ifndef HOTLINKCTRL_H
#define HOTLINKCTRL_H


#include <lsdef.h>
#include <util/stringlist.h>
#include <util/autostr.h>

class Pcregex;
class XmlNode;
class ConfigCtx;

class HotlinkCtrl
{
    char            m_iAllowDirectAcc;
    char            m_iOnlySelf;
    short           m_iDummy;
    StringList      m_listSuffix;
    StringList      m_listHosts;
    Pcregex        *m_pRegex;
    AutoStr2        m_sRedirect;

public:
    HotlinkCtrl();
    ~HotlinkCtrl();
    char allowDirectAccess() const          {   return m_iAllowDirectAcc;   }
    char onlySelf() const                   {   return m_iOnlySelf;         }
    const StringList *getSuffixList() const {   return &m_listSuffix;       }
    const char *getRedirect() const        {   return m_sRedirect.c_str(); }
    int  getRedirectLen() const             {   return m_sRedirect.len();   }

    void setDirectAccess(int dir)         {   m_iAllowDirectAcc = dir;    }
    void setOnlySelf(int self)            {   m_iOnlySelf = self;         }
    void setRedirect(const char *uri)    {   m_sRedirect.setStr(uri);  }
    int  setHosts(const char *pHosts);
    int  setRegex(const char *pRegex);
    int  setSuffixes(const char *suffix);
    int  allowed(const char *pRef, int len)  const;
    int config(const XmlNode *pNode);
    LS_NO_COPY_ASSIGN(HotlinkCtrl);
};

#endif

