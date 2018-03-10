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
#ifndef LOGIDTRACKER_H
#define LOGIDTRACKER_H

#include <lsdef.h>
#include <util/autostr.h>

class TmpLogId
{
    static char  s_aLogId[128];
    static int   s_iIdLen;

    AutoStr m_oldId;
public:
    TmpLogId(const char *pNewId)
    {
        m_oldId = getLogId();
        setLogId(pNewId);
    }
    TmpLogId()
    {
        m_oldId = getLogId();
    }
    ~TmpLogId()
    {
        setLogId(m_oldId.c_str());
    }
    static const char *getLogId()
    {   return s_aLogId;    }

    static void setLogId(const char *pId)
    {
        strncpy(s_aLogId, pId, sizeof(s_aLogId) - 1);
        s_aLogId[ sizeof(s_aLogId) - 1 ] = 0;
        s_iIdLen = strlen(s_aLogId);
    }

    static void appendLogId(const char *pId)
    {
        strncpy(s_aLogId + s_iIdLen, pId, sizeof(s_aLogId) - 1 - s_iIdLen);
        s_aLogId[ sizeof(s_aLogId) - 1 ] = 0;
        s_iIdLen += strlen(s_aLogId + s_iIdLen);
    }


    LS_NO_COPY_ASSIGN(TmpLogId);
};


#endif // LOGIDTRACKER_H
