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
#ifndef MODUSERDIR_H
#define MODUSERDIR_H



#include <lsdef.h>
#include <util/autostr.h>
#include <util/stringlist.h>

class ModUserdir
{
    char        m_disabled;
    char        m_mode;
    short       m_wildcard;

    AutoStr2    m_userdir;
    StringList  m_disabledUsers;
    StringList  m_enabledUsers;

    enum
    {
        MUD_UNIX,
        MUD_PATH,
        MUD_REDIRECT
    };
    int buildPath(char *pURL, int urlLen, char *p, char *pPath, int &len);

public:
    ModUserdir();
    ~ModUserdir();

    int parse(char *pBegin, char *pEnd);
    int buildPath(char *pURL, int userLen, char *pPath, int &len);
    LS_NO_COPY_ASSIGN(ModUserdir);
};

#endif
