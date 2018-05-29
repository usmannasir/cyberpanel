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
#ifndef URIMATCH_H
#define URIMATCH_H


#include <lsdef.h>
#include <util/pcregex.h>

class URIMatch
{
    Pcregex     m_regex;
    RegSub      m_subst;
public:
    URIMatch();
    ~URIMatch();

    int set(const char *pExp, const char *subst);
    int match(const char *pURI, int uriLen,  char *pResult, int &len);
    int match(const char *pStr, int strLen);
    LS_NO_COPY_ASSIGN(URIMatch);
};

#endif
