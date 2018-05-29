/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2016  LiteSpeed Technologies, Inc.                 *
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
#include "cachectrl.h"

#include <util/autostr.h>
#include <util/stringtool.h>

#include <ctype.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>

CacheCtrl::CacheCtrl()
    : m_flags(0)
    , m_iMaxAge(INT_MAX)
    , m_iMaxStale(0)
{
}


CacheCtrl::~CacheCtrl()
{
}
#define CACHE_DIRECTIVES 16
static const char *s_directives[CACHE_DIRECTIVES] =
{
    "no-cache",
    "no-store",
    "max-age",
    "max-stale",
    "min-fresh",
    "no-transform",
    "only-if-cached",
    "public",
    "private",
    "must-revalidate",
    "proxy-revalidate",
    "s-maxage",
    "esi",
    "no-vary",
    "set-blank",
    "shared"
};

static const int s_dirLen[CACHE_DIRECTIVES] =
{   8, 8, 7, 9, 9, 12, 14, 6, 7, 15, 16, 8, 3, 7, 9, 6    };


int CacheCtrl::parse(const char *pHeader, int len)
{
    StrParse parser(pHeader, pHeader + len, ",");
    const char *p;
    while (!parser.isEnd())
    {
        p = parser.trim_parse();
        if (!p)
            break;
        if (p != parser.getStrEnd())
        {
            AutoStr2 s(p, parser.getStrEnd() - p);
            int i;
            for (i = 0; i < CACHE_DIRECTIVES; ++i)
            {
                if (strncasecmp(s.c_str(), s_directives[i], s_dirLen[i]) == 0)
                    break;
            }
            if (i < CACHE_DIRECTIVES)
            {
                m_flags |= (1 << i);
                switch (i)
                {
                case 2:
                    if (m_flags & (s_maxage))
                        break;
                    //fall through
                case 3:
                case 11:
                    p += s_dirLen[i];
                    while ((*p == ' ') || (*p == '=') || (*p == '"'))
                        ++p;
                    if (isdigit(*p))
                    {
                        if (i == 3)
                            m_iMaxStale = atoi(p);
                        else
                        {
                            //If "max-age" set, enable public cache
                            m_iMaxAge = atoi(p);
                            m_flags |= cache_public;
                            m_flags &= (~no_cache & ~no_store);
                        }
                    }
                    break;
                case 12:
                    p += s_dirLen[i];
                    while ((*p == ' ') || (*p == '=') || (*p == '"'))
                        ++p;
                    if (strncasecmp(p, "on", 2) == 0)
                        m_flags |= esi_on;
                    else if (strncasecmp(p, "off", 3) == 0)
                        m_flags &= ~esi_on;
                    break;
                case 7:
                    // If php says public, cache publicly.
                    m_flags &= ~cache_private;
                    break;
                default:
                    break;
                }
            }
        }
    }
    return 0;
}

