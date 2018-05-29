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
#include "urimatch.h"

URIMatch::URIMatch()
{
}
URIMatch::~URIMatch()
{
}

int URIMatch::set(const char *pExpr, const char *subst)
{
    if (!pExpr)
        return LS_FAIL;
    if (m_regex.compile(pExpr, 0) == 0)
    {
        if (subst)
            return m_subst.compile(subst);
        else
            return 0;
    }
    return LS_FAIL;
}

int URIMatch::match(const char *pURI, int uriLen, char *pResult, int &len)
{
    int vector[30];
    int size = 30;
    int n = m_regex.exec(pURI, uriLen, 0, 0, vector, size);
    if (n < 0)
        return LS_FAIL;
    if (n == 0)
        n = 10;
    return m_subst.exec(pURI, vector, n, pResult, len);
}

int URIMatch::match(const char *pStr, int strLen)
{
    int vector[30];
    int size = 30;
    int n = m_regex.exec(pStr, strLen, 0, 0, vector, size);
    if (n < 0)
        return LS_FAIL;
    if (n == 0)
        n = 10;
    return n;
}



