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
#ifndef HTTPUTIL_H
#define HTTPUTIL_H


#include <limits.h>

class HttpUtil
{
    HttpUtil() {};
    ~HttpUtil() {};
public:


    static int escape(const char *pSrc, char *pDest, int iDestlen);
    static int escape(const char *pSrc, int iSrcLen, char *pDest,
                      int iDestLen);
    static int escapeRFC3986(const char *pSrc, char *pDest, int iDestlen);
    static int escapeRFC3986(const char *pSrc, int iSrcLen, char *pDest,
                             int iDestLen);
    static int escapeQs(const char *pSrc, char *pDest, int iDestLen);
    static int escapeQs(const char *pSrc, int iSrcLen, char *pDest,
                        int iDestLen);
    static int escapeHtml(const char *pSrc, const char *pSrcEnd, char *pDest,
                          int iDestLen);


    static int unescape(char *pDest, int &iUriLen, const char *&pOrgSrc);
    static int unescape(const char *pSrc, char *pDest, int iDestLen);
    static int unescape(const char *pSrc, int iSrcLen, char *pDest,
                        int iDestLen);
    static int unescapeQs(char *pDest, int &iUriLen, const char *&pOrgSrc);
    static int unescapeQs(const char *pSrc, char *pDest, int iDestLen);
    static int unescapeQs(const char *pSrc, int iSrcLen,
                          char *pDest, int iDestLen);
    static int unescapeInPlace(char *pDest, int &iUriLen,
                               const char *&pOrgSrc);
    static int unescapeInPlaceQs(char *pDest, int &iUriLen,
                                 const char *&pOrgSrc);
};

#endif
