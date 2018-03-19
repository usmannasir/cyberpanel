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
#ifndef SENDFILEINFO_H
#define SENDFILEINFO_H



#include <string.h>
#include <sys/types.h>

class StaticFileCacheData;
class FileCacheDataEx;

class SendFileInfo
{
    StaticFileCacheData *m_pFileData;
    FileCacheDataEx      *m_pECache;
    void                 *m_pParam;
    void                 *m_pAioBuf;

    off_t     m_lCurPos;
    off_t     m_lCurEnd;
    off_t     m_lAioLen;

    SendFileInfo(const SendFileInfo &rhs);
    void operator=(const SendFileInfo &rhs);

public:

    SendFileInfo();
    ~SendFileInfo();

    void reset()
    {
        //m_pCache = NULL;
        //memset( &m_pCache, 0, (char *)(&m_pECache + 1) - (char *)&m_pCache );
        memset(this, 0, sizeof(*this));
    }


    void *getParam() const     {   return m_pParam;    }
    void setParam(void *p)   {   m_pParam = p;       }

    void setFileData(StaticFileCacheData *pData);
    StaticFileCacheData *getFileData() const  {   return m_pFileData;    }

    void setECache(FileCacheDataEx *pCache);
    FileCacheDataEx *getECache() const   {   return m_pECache;    }

    void setCurPos(off_t pos)  {   m_lCurPos = pos;    }
    void incCurPos(off_t inc)  {   m_lCurPos += inc;   }
    off_t getCurPos() const      {   return m_lCurPos;   }
    void setCurEnd(off_t end)  {   m_lCurEnd = end;    }
    off_t getCurEnd() const      {   return m_lCurEnd;   }
    off_t getRemain() const  {   return m_lCurEnd - m_lCurPos;   }

    int getfd();

    void *getAioBuf()           {   return m_pAioBuf;   }
    void setAioBuf(void *p)   {   m_pAioBuf = p;      }
    off_t getAioLen()            {   return m_lAioLen;   }
    void setAioLen(off_t len)  {   m_lAioLen = len;    }
    void resetAioBuf()
    {
        m_pAioBuf = NULL;
        m_lAioLen = 0;
    }
    int readyCacheData(char compress, char mode = 1);
    
    void release();

};

#endif
