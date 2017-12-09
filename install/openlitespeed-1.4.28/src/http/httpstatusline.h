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
#ifndef HTTPSTATUSLINE_H
#define HTTPSTATUSLINE_H


#include <lsdef.h>
#include <http/httpstatuscode.h>
#include <util/tsingleton.h>

#define MAX_STATUS_LINE_LEN 64

class StatusLineString
{
    int     m_iLineLen;
    char   *m_pLine;
public:
    StatusLineString(int version, int code);
    int getLen() const          {   return m_iLineLen;  }
    const char *get() const    {   return m_pLine;     }
    LS_NO_COPY_ASSIGN(StatusLineString);
};

class HttpStatusLine : public TSingleton<HttpStatusLine>
{
    friend class TSingleton<HttpStatusLine>;

    StatusLineString *m_aCache[2][SC_END];
    HttpStatusLine();
    ~HttpStatusLine();

public:


    const StatusLineString &getStatusLine(int ver, int code)
    {   return *m_aCache[ver][code];  }



    LS_NO_COPY_ASSIGN(HttpStatusLine);
};

#endif
