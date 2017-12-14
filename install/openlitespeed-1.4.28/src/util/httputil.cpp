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
#include "httputil.h"
#include <util/stringtool.h>

#include <ctype.h>
#include <string.h>
#include <lsdef.h>

int HttpUtil::escape(const char *pSrc, char *pDest, int iDestlen)
{
    char ch;
    char *p = pDest;
    while (--iDestlen && ((ch = *pSrc++) != 0))
    {
        switch (ch)
        {
        case '+':
        case '?':
        case '&':
        case '%':
        case ' ':
            if (iDestlen > 3)
            {
                *p++ = '%';
                *p++ = StringTool::s_aHex[(ch >> 4) & 15];
                *p++ = StringTool::s_aHex[ch & 15];
                iDestlen -= 2;
            }
            else
                iDestlen = 1;
            break;
        default:
            *p++ = ch;
            break;
        }
    }
    *p = 0;
    return p - pDest;
}


int HttpUtil::escape(const char *pSrc, int iSrcLen, char *pDest,
                     int iDestLen)
{
    char ch;
    char *p = pDest;
    const char *pEnd = pSrc + iSrcLen;
    while (--iDestLen && (pSrc < pEnd))
    {
        ch = *pSrc++;
        switch (ch)
        {
        case '+':
        case '?':
        case '&':
        case '%':
        case ' ':
            if (iDestLen > 3)
            {
                *p++ = '%';
                *p++ = StringTool::s_aHex[(ch >> 4) & 15];
                *p++ = StringTool::s_aHex[ch & 15];
                iDestLen -= 2;
            }
            else
                iDestLen = 1;
            break;
        default:
            *p++ = ch;
            break;
        }
    }
    *p = 0;
    return p - pDest;
}


int HttpUtil::escapeRFC3986(const char *pSrc, char *pDest, int iDestlen)
{
    char ch;
    char *p = pDest;
    while (--iDestlen && ((ch = *pSrc++) != 0))
    {
        switch (ch)
        {
        //gen-delims missing ':' and '@'
        case '/':
        case '?':
        case '#':
        case '[':
        case ']':
        //special
        case '%':
        case ' ':
            if (iDestlen > 3)
            {
                *p++ = '%';
                *p++ = StringTool::s_aHex[(ch >> 4) & 15];
                *p++ = StringTool::s_aHex[ch & 15];
                iDestlen -= 2;
            }
            else
                iDestlen = 1;
            break;
        default:
            *p++ = ch;
            break;
        }
    }
    *p = 0;
    return p - pDest;
}


int HttpUtil::escapeRFC3986(const char *pSrc, int iSrcLen, char *pDest,
                            int iDestLen)
{
    char ch;
    char *p = pDest;
    const char *pEnd = pSrc + iSrcLen;
    while (--iDestLen && (pSrc < pEnd))
    {
        ch = *pSrc++;
        switch (ch)
        {
        //gen-delims missing ':' and '@'
        case '/':
        case '?':
        case '#':
        case '[':
        case ']':
        //special
        case '%':
        case ' ':
            if (iDestLen > 3)
            {
                *p++ = '%';
                *p++ = StringTool::s_aHex[(ch >> 4) & 15];
                *p++ = StringTool::s_aHex[ch & 15];
                iDestLen -= 2;
            }
            else
                iDestLen = 1;
            break;
        default:
            *p++ = ch;
            break;
        }
    }
    *p = 0;
    return p - pDest;
}


int HttpUtil::escapeQs(const char *pSrc, char *pDest, int iDestLen)
{
    char ch;
    char *p = pDest;
    while (--iDestLen && ((ch = *pSrc++) != 0))
    {
        switch (ch)
        {
        case ' ':
            *p++ = '+';
            break;
        case ':':
        case '/':
        case '?':
        case '#':
        case '[':
        case ']':
        case '@':
        case '!':
        case '$':
        case '&':
        case '(':
        case ')':
        case '*':
        case '+':
        case ',':
        case ';':
        case '=':
        case '%':
        case '\'':
            if (iDestLen < 3)
            {
                *p++ = '%';
                *p++ = StringTool::s_aHex[(ch >> 4) & 15];
                *p++ = StringTool::s_aHex[ch & 15];
                iDestLen -= 2;
            }
            else
                iDestLen = 1;
            break;
        default:
            *p++ = ch;
            break;
        }
    }
    *p = 0;
    return p - pDest;
}


int HttpUtil::escapeQs(const char *pSrc, int iSrcLen, char *pDest,
                       int iDestLen)
{
    char ch;
    char *p = pDest;
    const char *pEnd = pSrc + iSrcLen;
    while (--iDestLen && (pSrc < pEnd))
    {
        ch = *pSrc++;
        switch (ch)
        {
        case ' ':
            *p++ = '+';
            break;
        case ':':
        case '/':
        case '?':
        case '#':
        case '[':
        case ']':
        case '@':
        case '!':
        case '$':
        case '&':
        case '(':
        case ')':
        case '*':
        case '+':
        case ',':
        case ';':
        case '=':
        case '%':
        case '\'':
            if (iDestLen > 3)
            {
                *p++ = '%';
                *p++ = StringTool::s_aHex[(ch >> 4) & 15];
                *p++ = StringTool::s_aHex[ch & 15];
                iDestLen -= 2;
            }
            else
                iDestLen = 1;
            break;
        default:
            *p++ = ch;
            break;
        }
    }
    *p = 0;
    return p - pDest;
}


int HttpUtil::escapeHtml(const char *pSrc, const char *pSrcEnd,
                         char *pDest,
                         int iDestLen)
{
    char *pBegin = pDest;
    char *pEnd = pDest + iDestLen - 6;
    char ch;
    while ((pSrc < pSrcEnd) && (ch = *pSrc) && (pDest < pEnd))
    {
        switch (ch)
        {
        case '<':
            memmove(pDest, "&lt;", 4);
            pDest += 4;
            break;
        case '>':
            memmove(pDest, "&gt;", 4);
            pDest += 4;
            break;
        case '&':
            memmove(pDest, "&amp;", 5);
            pDest += 5;
            break;
        case '"':
            memmove(pDest, "&quot;", 6);
            pDest += 6;
            break;
        default:
            *pDest++ = ch;
            break;
        }
        ++pSrc;
    }
    *pDest = 0;
    return pDest - pBegin;
}


int HttpUtil::unescape(char *pDest, int &iUriLen,
                       const char *&pOrgSrc)
{
    const char *pSrc = pOrgSrc;
    const char *pEnd = pOrgSrc + iUriLen;
    char *p = pDest;
    char c, x1, x2;

    while (pSrc < pEnd)
    {
        c = *pSrc++;
        switch (c)
        {
        case '%':
            {
                x1 = *pSrc++;
                if (!isxdigit(x1))
                {
                    *p++ = '%';
                    c = x1;
                    break;
                }
                x2 = *pSrc++;
                if (!isxdigit(x2))
                {
                    *p++ = '%';
                    *p++ = x1;
                    c = x2;
                    break;
                }
                c = (hexdigit(x1) << 4) + hexdigit(x2);
                break;
            }
        case '?':
            iUriLen = p - pDest;
            *p++ = 0;
            if (pOrgSrc != pDest)
            {
                pOrgSrc = p;
                memmove(p, pSrc, pEnd - pSrc);
                p += pEnd - pSrc;
                *p++ = 0;
            }
            else
            {
                pOrgSrc = pSrc;
                p = (char *)pEnd + 1;
            }
            return p - pDest;
        }
        *p++ = c;
    }
    pOrgSrc = p;
    iUriLen = p - pDest;
    *p++ = 0;
    return p - pDest;
}


int HttpUtil::unescape(const char *pSrc, char *pDest, int iDestLen)
{
    char c;
    char *p = pDest;

    while (iDestLen-- && ((c = *pSrc++) != 0))
    {
        switch (c)
        {
        case '%':
            {
                char x1, x2;
                x1 = *pSrc++;
                if (!isxdigit(x1))
                    return LS_FAIL;
                x2 = *pSrc++;
                if (!isxdigit(x2))
                    return LS_FAIL;
                *p++ = (hexdigit(x1) << 4) + hexdigit(x2);
                iDestLen -= 2;
                break;
            }
        case '/':
            //get rid of duplicate '/'s.
            if (*pSrc == '/')
                break;
        default:
            *p++ = c;
        }
    }
    *p = 0;
    return p - pDest;
}



int HttpUtil::unescape(const char *pSrc, int iSrcLen, char *pDest,
                       int iDestLen)
{
    char c;
    char *p = pDest;
    const char *pSrcEnd = pSrc + iSrcLen;

    while (iDestLen-- && (pSrc < pSrcEnd))
    {
        c = *pSrc++;
        if (c == '%' && pSrc + 2 < pSrcEnd)
        {
            char x1, x2;
            x1 = *pSrc++;
            if (!isxdigit(x1))
                return LS_FAIL;
            x2 = *pSrc++;
            if (!isxdigit(x2))
                return LS_FAIL;
            *p++ = (hexdigit(x1) << 4) + hexdigit(x2);
            iDestLen -= 2;
        }
        else if (c == '/' && pSrc < pSrcEnd && *pSrc == '/')
        {
            //handle "://" case, keep them
            if (iDestLen + 2 <= iSrcLen && pSrc[-2] == ':')
                *p++ = c;
            //else
            //; //Do nothing so that get rid of duplicate '/'s.
        }
        else
            *p++ = c;
    }

    return p - pDest;
}


int HttpUtil::unescapeQs(char *pDest, int &uriLen,
                         const char *&pOrgSrc)
{
    const char *pSrc = pOrgSrc;
    const char *pEnd = pOrgSrc + uriLen;
    char *p = pDest;

    while (pSrc < pEnd)
    {
        char c = *pSrc++;
        switch (c)
        {
        case '%':
            {
                char x1, x2;
                x1 = *pSrc++;
                if (!isxdigit(x1))
                {
                    *p++ = '%';
                    c = x1;
                    break;
                }
                x2 = *pSrc++;
                if (!isxdigit(x2))
                {
                    *p++ = '%';
                    *p++ = x1;
                    c = x2;
                    break;
                }
                c = (hexdigit(x1) << 4) + hexdigit(x2);
                break;
            }
        case '+':
            c = ' ';
            break;
        }
        *p++ = c;
    }
    pOrgSrc = p;
    uriLen = p - pDest;
    *p++ = 0;
    return p - pDest;
}


int HttpUtil::unescapeQs(const char *pSrc, char *pDest, int iDestLen)
{
    char c;
    char *p = pDest;

    while (iDestLen-- && ((c = *pSrc++) != 0))
    {
        switch (c)
        {
        case '%':
            {
                char x1, x2;
                x1 = *pSrc++;
                if (!isxdigit(x1))
                    return LS_FAIL;
                x2 = *pSrc++;
                if (!isxdigit(x2))
                    return LS_FAIL;
                *p++ = (hexdigit(x1) << 4) + hexdigit(x2);
                iDestLen -= 2;
                break;
            }
        case '+':
            *p++ = ' ';
            break;
        default:
            *p++ = c;
        }
    }
    *p = 0;
    return p - pDest;
}


int HttpUtil::unescapeQs(const char *pSrc, int iSrcLen, char *pDest,
                         int iDestLen)
{
    char c;
    char *p = pDest;
    const char *pSrcEnd = pSrc + iSrcLen;

    while (iDestLen-- && (pSrc < pSrcEnd))
    {
        c = *pSrc++;
        if (c == '%' && pSrc + 2 < pSrcEnd)
        {
            char x1, x2;
            x1 = *pSrc++;
            if (!isxdigit(x1))
                return LS_FAIL;
            x2 = *pSrc++;
            if (!isxdigit(x2))
                return LS_FAIL;
            *p++ = (hexdigit(x1) << 4) + hexdigit(x2);
            iDestLen -= 2;
        }
        else if (c == '+')
            *p++ = ' ';
        else
            *p++ = c;
    }
    *p = 0;
    return p - pDest;
}


int HttpUtil::unescapeInPlace(char *pDest, int &iUriLen,
                              const char *&pOrgSrc)
{
    const char *pSrc = pOrgSrc;
    const char *pEnd = pOrgSrc + iUriLen;
    char *p = pDest;

    while (pSrc < pEnd)
    {
        char c = *pSrc++;
        switch (c)
        {
        case '%':
            {
                char x1, x2;
                x1 = *pSrc++;
                if (!isxdigit(x1))
                    return LS_FAIL;
                x2 = *pSrc++;
                if (!isxdigit(x2))
                    return LS_FAIL;
                c = (hexdigit(x1) << 4) + hexdigit(x2);
                break;
            }
        case '?':
            iUriLen = p - pDest;
            *p++ = 0;
            if (pOrgSrc != pDest)
            {
                pOrgSrc = p;
                memmove(p, pSrc, pEnd - pSrc);
                p += pEnd - pSrc;
                *p++ = 0;
            }
            else
            {
                pOrgSrc = pSrc;
                p = (char *)pEnd + 1;
            }
            return p - pDest;
        }
        switch (c)
        {
        case '.':
            if (*(p - 1) == '/')
                return LS_FAIL;
            *p++ = c;
            break;
        case '/':
            //get rid of duplicate '/'s.
            if (*pSrc == '/')
                break;
        //fall through
        default:
            *p++ = c;
        }
    }
    pOrgSrc = p;
    iUriLen = p - pDest;
    *p++ = 0;
    return p - pDest;
}


int HttpUtil::unescapeInPlaceQs(char *pDest, int &uriLen,
                                const char *&pOrgSrc)
{
    const char *pSrc = pOrgSrc;
    const char *pEnd = pOrgSrc + uriLen;
    char *p = pDest;

    while (pSrc < pEnd)
    {
        char c = *pSrc++;
        switch (c)
        {
        case '%':
            {
                char x1, x2;
                x1 = *pSrc++;
                if (!isxdigit(x1))
                    return LS_FAIL;
                x2 = *pSrc++;
                if (!isxdigit(x2))
                    return LS_FAIL;
                c = (hexdigit(x1) << 4) + hexdigit(x2);
                break;
            }
        case '+':
            c = ' ';
            break;
        }
        *p++ = c;
    }
    pOrgSrc = p;
    uriLen = p - pDest;
    *p++ = 0;
    return p - pDest;
}





