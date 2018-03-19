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
#include "moduserdir.h"

#include <http/httpstatuscode.h>
#include <lsr/ls_strtool.h>

#include <pwd.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>

ModUserdir::ModUserdir()
    : m_disabled(0)
{
}


ModUserdir::~ModUserdir()
{
}


int ModUserdir::parse(char *pBegin, char *pEnd)
{
    StringList *pList;
    if (strncasecmp(pBegin, "disabled", 8) == 0)
    {
        if (pEnd - pBegin == 8)
        {
            m_disabled = 1;
            return 0;
        }
        pBegin += 9;
        pList = &m_disabledUsers;

    }
    else if (strncasecmp(pBegin, "enabled", 7) == 0)
    {
        if (pEnd - pBegin == 7)
            return 0;
        pBegin += 8;
        pList = &m_enabledUsers;
    }
    else
    {
        m_userdir.setStr(pBegin, pEnd - pBegin);
        if (strchr(pBegin, ':'))
            m_mode = MUD_REDIRECT;
        else if (*pBegin != '/')
            m_mode = MUD_UNIX;
        else
            m_mode = MUD_PATH;
        char *p = strchr(pBegin, '*');
        if (p)
            m_wildcard = p - pBegin;
        else
            m_wildcard = -1;
        return 0;
    }
    pList->split(pBegin, pEnd, " \t");
    pList->sort();
    return 0;
}


int ModUserdir::buildPath(char *pURL, int urlLen, char *pPath, int &len)
{
    char *p = strchr(pURL + 2, '/');
    if (p)
        *p = 0;
    int ret = buildPath(pURL, urlLen, (p) ? (p + 1) : (pURL + urlLen), pPath,
                        len);
    if (p)
        *p = '/';
    if (ret == SC_403)
        return ret;

    return ret;
}


int ModUserdir::buildPath(char *pURL, int urlLen, char *p, char *pPath,
                          int &len)
{
    pURL += 2;
    if (m_disabledUsers.bfind(pURL) != NULL)
        return SC_403;
    if ((m_disabled) && (m_enabledUsers.bfind(pURL) == NULL))
        return SC_403;
    if (m_mode == MUD_UNIX)
    {
        struct passwd *pw;
        if (strcmp("root", pURL) == 0)
            return SC_403;
        pw = getpwnam(pURL);
        if (pw)
            len = ls_snprintf(pPath, len, "%s/%s/%s", pw->pw_dir, m_userdir.c_str(),
                              p);
    }
    else
    {
        char *pos = pPath;
        if (m_wildcard >= 0)
        {
            memmove(pos, m_userdir.c_str(), m_wildcard);
            pos += m_wildcard;
            len = ls_snprintf(pos, (pPath + len) - pos, "%s%s/%s",
                              pURL, m_userdir.c_str() + 1 + m_wildcard, p);
            len += m_wildcard;
        }
        if (m_mode == MUD_REDIRECT)
            return SC_302;
    }
    return 0;
}



