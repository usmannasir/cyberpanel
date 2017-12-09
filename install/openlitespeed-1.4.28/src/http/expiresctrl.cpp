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
#include "expiresctrl.h"

#include <lsdef.h>
#include <http/httpcontext.h>
#include <util/stringtool.h>
#include <util/xmlnode.h>

#include <ctype.h>
#include <stdlib.h>
#include <string.h>

ExpiresCtrl::ExpiresCtrl()
    : m_iEnabled(0)
    , m_iBase(0)
    , m_iCompressible(0)
    , m_iBits(0)
    , m_iAge(0)
{}


ExpiresCtrl::ExpiresCtrl(const ExpiresCtrl &rhs)
    : m_iEnabled(rhs.m_iEnabled)
    , m_iBase(rhs.m_iBase)
    , m_iCompressible(rhs.m_iCompressible)
    , m_iBits(0)
    , m_iAge(rhs.m_iAge)
{
}


ExpiresCtrl::~ExpiresCtrl()
{}


int ExpiresCtrl::parse(const char *pConfig)
{
    short base;
    int time;
    const char *pEnd = NULL;

    while (*pConfig == ' ')
        ++pConfig;
    if ((*pConfig == '"') || (*pConfig == '\''))
        pEnd = StringTool::strNextArg(pConfig);
    if (!pEnd)
        pEnd = pConfig + strlen(pConfig);

    if (pConfig == pEnd)
        return LS_FAIL;

    StrParse parse(pConfig, pEnd, " \t");
    const char *p = parse.trim_parse();
    if (isdigit(*(p + 1)))
    {
        if ((*p == 'A') || (*p == 'a'))
            base = EXPIRES_ACCESS;
        else if ((*p == 'M') || (*p == 'm'))
            base = EXPIRES_MODIFY;
        else
            return LS_FAIL;
        ++p;
        char *pNumEnd;
        time = strtol(p, &pNumEnd, 10);
        if (pNumEnd == p)
            return LS_FAIL;

    }
    else
    {
        int factor;
        int len;
        int n;
        time = 0;
        len = parse.getStrEnd() - p;
        if ((strncasecmp("access", p, len) == 0) ||
            (strncasecmp("now", p, len) == 0))
            base = EXPIRES_ACCESS;
        else if (strncasecmp("modification", p, len) == 0)
            base = EXPIRES_MODIFY;
        else
            return LS_FAIL;
        p = parse.trim_parse();
        if (!p)
            return LS_FAIL;
        if (strncasecmp("plus", p, 4) == 0)
            p = parse.trim_parse();
        while (p && *p)
        {
            if (!isdigit(*p))
                return LS_FAIL;
            n = strtol(p, NULL, 10);
            p = parse.trim_parse();
            if (!p)
                return LS_FAIL;
            factor = 0;
            char ch1, ch = tolower(*p);
            switch (ch)
            {
            case 'y':
                factor = 3600 * 24 * 365;
                break;
            case 'w':
                factor = 3600 * 24 * 7;
                break;
            case 'd':
                factor = 3600 * 24;
                break;
            case 'm':
                ch1 = tolower(*(p + 1));
                if (ch1 == 'o')
                    factor = 3600 * 24 * 30;
                else if (ch1 == 'i')
                    factor = 60;
                else
                    return LS_FAIL;
                break;
            case 'h':
                factor = 3600;
                break;
            case 's':
                factor = 1;
                break;
            default:
                return LS_FAIL;
            }
            time += n * factor;
            p = parse.trim_parse();
        }

    }
    m_iBase = base;
    m_iAge = time;
    m_iBits |= CONFIG_EXPIRES;
    return 0;
}


void ExpiresCtrl::copyExpires(const ExpiresCtrl &rhs)
{
    m_iEnabled = rhs.m_iEnabled;
    m_iBase = rhs.m_iBase;
    m_iAge = rhs.m_iAge;
}


int ExpiresCtrl::config(const XmlNode *pExpires,
                        const ExpiresCtrl *pDefault,
                        HttpContext *pContext)
{
    const char *pValue;
    if (!pDefault)
        pDefault = this;
    pValue = pExpires->getChildValue("enableExpires");
    char enabled = pDefault->isEnabled();
    if (pValue)
    {
        enabled = pExpires->getLongValue("enableExpires" , 0, 1, enabled);
        if (pContext)
            pContext->setConfigBit(BIT_ENABLE_EXPIRES, 1);
    }
    enable(enabled);
    pValue = pExpires->getChildValue("expiresDefault");
    if (pValue)
    {
        parse(pValue);
        if (pContext)
            pContext->setConfigBit(BIT_EXPIRES_DEFAULT, 1);
    }
    else
    {
        setBase(pDefault->getBase());
        setAge(pDefault->getAge());
    }
    return 0;
}


int ExpiresCtrlConfig::operator()(ExpiresCtrl *pCtrl,
                                  const XmlNode *pExpires)
{
    const char *pValue;
    if (!m_pDefault)
        m_pDefault = pCtrl;
    pValue = pExpires->getChildValue("enableExpires");
    char enabled = m_pDefault->isEnabled();
    if (pValue)
    {
        enabled = pExpires->getLongValue("enableExpires" , 0, 1, enabled);
        if (m_pContext)
            m_pContext->setConfigBit(BIT_ENABLE_EXPIRES, 1);
    }
    pCtrl->enable(enabled);
    pValue = pExpires->getChildValue("expiresDefault");
    if (pValue)
    {
        pCtrl->parse(pValue);
        if (m_pContext)
            m_pContext->setConfigBit(BIT_EXPIRES_DEFAULT, 1);
    }
    else
    {
        pCtrl->setBase(m_pDefault->getBase());
        pCtrl->setAge(m_pDefault->getAge());
    }
    return 0;

}

