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
#include <util/stringtool.h>
#include <util/stringlist.h>
#include <ctype.h>
#include <string.h>

const char StringTool::s_aHex[17] = "0123456789abcdef";

StringList *StringTool::parseMatchPattern(const char *pPattern)
{
    char *pBegin;
    char ch;
    StringList *pList = new StringList();
    if (!pList)
        return NULL;
    char achBuf[2048];
    pBegin = achBuf;
    *pBegin++ = 0;
    while ((ch = *pPattern++))
    {
        switch (ch)
        {
        case '*':
        case '?':
            if (pBegin - 1 != achBuf)
                pList->add(achBuf, pBegin - achBuf);
            pBegin = achBuf;
            while (1)
            {
                *pBegin++ = ch;
                if (*pPattern != ch)
                    break;
                ++pPattern;

            }
            if (ch == '*')
                pList->add(achBuf, 1);
            else
                pList->add(achBuf, pBegin - achBuf);
            pBegin = achBuf;
            *pBegin++ = 0;
            break;

        case '\\':
            ch = *pPattern++;
        //fall through
        default:
            if (ch)
                *pBegin++ = ch;
            break;

        }
    }
    if (pBegin - 1 != achBuf)
        pList->add(achBuf, pBegin - achBuf);
    return pList;
}

void *StringTool::memmem(const char *haystack, size_t haystacklen,
                         const char *needle, size_t needleLength)
{
    const char *p = haystack + haystacklen;

    if (haystacklen < needleLength)
        return NULL;

    if (needleLength == 0)
        return (void *)haystack;

    while (haystack < p
           && ((haystack = (const char *)memchr(haystack, *needle,
                           p - haystack)) != NULL))
    {
        if (memcmp(haystack, needle, needleLength) == 0)
            return (void *)haystack;
        ++haystack;
    }
    return NULL;
}

