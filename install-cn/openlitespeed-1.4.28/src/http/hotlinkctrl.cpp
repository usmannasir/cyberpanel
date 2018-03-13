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
#include "hotlinkctrl.h"

#include <main/configctx.h>
#include <log4cxx/logger.h>
#include <util/pcregex.h>
#include <util/xmlnode.h>
#include <pcreposix.h>
#include <string.h>


HotlinkCtrl::HotlinkCtrl()
    : m_iAllowDirectAcc(false)
    , m_iOnlySelf(true)
    , m_pRegex(NULL)
{
}


HotlinkCtrl::~HotlinkCtrl()
{
    if (m_pRegex)
        delete m_pRegex;
}


int HotlinkCtrl::allowed(const char *pRef, int len) const
{
    StringList::const_iterator iter;
    for (iter = m_listHosts.begin(); iter != m_listHosts.end(); ++iter)
    {
        if (strncasecmp(pRef, (*iter)->c_str(), (*iter)->len()) == 0)
            return 1;
    }
    if (m_pRegex)
    {
        int ovector[30];
        return m_pRegex->exec(pRef, len, 0, 0, ovector, 30) > 0;
    }
    return 0;
}


int HotlinkCtrl::setSuffixes(const char *suffix)
{
    if (!suffix)
        return LS_FAIL;
    return m_listSuffix.split(suffix, suffix + strlen(suffix), " ,|");
}


int  HotlinkCtrl::setHosts(const char *pHosts)
{
    if (!pHosts)
        return LS_FAIL;
    return m_listHosts.split(pHosts, pHosts + strlen(pHosts), " ,|");
}


int  HotlinkCtrl::setRegex(const char *pRegex)
{
    if (!pRegex)
        return LS_FAIL;
    if (!m_pRegex)
    {
        m_pRegex = new Pcregex();
        if (!m_pRegex)
            return LS_FAIL;
    }
    int ret = m_pRegex->compile(pRegex, REG_EXTENDED | REG_ICASE);
    if (ret == -1)
    {
        delete m_pRegex;
        m_pRegex = NULL;
    }
    return ret;

}


int HotlinkCtrl::config(const XmlNode *pNode)
{
    if (setSuffixes(pNode->getChildValue("suffixes")) <= 0)
    {
        LS_ERROR(ConfigCtx::getCurConfigCtx(),
                 "no suffix is configured, disable hotlink protection.");
        return LS_FAIL;
    }

    setDirectAccess(ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                    "allowDirectAccess", 0, 1, 0));
    const char *pRedirect = pNode->getChildValue("redirectUri");

    if (pRedirect)
        setRedirect(pRedirect);

    int self = ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "onlySelf", 0,
               1, 0);

    if (!self)
    {
        char achBuf[4096];
        const char *pValue = pNode->getChildValue("allowedHosts");

        if (pValue)
        {
            ConfigCtx::getCurConfigCtx()->expandDomainNames(pValue, achBuf, 4096, ',');
            pValue = achBuf;
        }

        int ret = setHosts(pValue);
        int ret2 = setRegex(pNode->getChildValue("matchedHosts"));

        if ((ret <= 0) &&
            (ret2 < 0))
        {
            LS_WARN(ConfigCtx::getCurConfigCtx(),
                    "no valid host is configured, only self"
                    " reference is allowed.");
            self = 1;
        }
    }
    setOnlySelf(self);
    return 0;
}

