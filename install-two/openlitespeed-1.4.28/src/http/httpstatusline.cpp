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
#include "httpstatusline.h"

#include <http/httpver.h>

#include <string.h>

#define STATUS_LINE_BUF_SIZE 64 * SC_END * 2

static  char s_achBuf[STATUS_LINE_BUF_SIZE];
static  char *s_pEnd = s_achBuf;

StatusLineString::StatusLineString(int version, int code)
{
    if (code > 0)
    {
        int verLen = HttpVer::getVersionStringLen(version);
        int codeLen = HttpStatusCode::getInstance().getCodeStringLen(code);
        m_iLineLen = verLen + codeLen ;
        m_pLine = s_pEnd;
        memcpy(s_pEnd, HttpVer::getVersionString(version), verLen);
        memcpy(s_pEnd + verLen, HttpStatusCode::getInstance().getCodeString(code),
               codeLen);
        s_pEnd += m_iLineLen;
    }
    else
    {
        m_pLine = NULL;
        m_iLineLen = 0;
    }
}


HttpStatusLine::HttpStatusLine()
{
    int code, version = HTTP_1_1;
    for (code = 0; code < SC_END; ++code)
        m_aCache[version][code] = new StatusLineString(version, code);

    version = HTTP_1_0;
    for (code = 0; code < SC_END; ++code)
        m_aCache[version][code] = new StatusLineString(version, code);
}


HttpStatusLine::~HttpStatusLine()
{
    int code, version = HTTP_1_1;
    for (code = 0; code < SC_END; ++code)
        delete m_aCache[version][code];

    version = HTTP_1_0;
    for (code = 0; code < SC_END; ++code)
        delete m_aCache[version][code];
}


