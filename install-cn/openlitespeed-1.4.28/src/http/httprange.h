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
#ifndef HTTPRANGE_H
#define HTTPRANGE_H


#include <lsdef.h>
#include <util/objarray.h>
#include <sys/types.h>

#include <new>

#define MAX_PART_HEADER_LEN 256

class AutoStr2;
class ByteRange;
typedef struct ls_xpool_s ls_xpool_t;

class HttpRange
{
    TObjArray< ByteRange > m_array;
    off_t   m_lEntityLen;
    int     m_iCurRange;
    char    m_boundary[20];
    char    m_partHeaderBuf[MAX_PART_HEADER_LEN];
    char   *m_pPartHeaderEnd;
    char   *m_pCurHeaderPos;

    ByteRange *getSlot(ls_xpool_t *pool);
    int  checkAndInsert(ByteRange &range, ls_xpool_t *pool);
    void makeBoundaryString();

public:
    explicit HttpRange(off_t entityLen = -1);
    ~HttpRange() {}

    int  count() const;
    int  parse(const char *pRange, ls_xpool_t *pool);
    int  getContentRangeString(int n, char *pBuf, int len) const;
    int  getContentOffset(int n, off_t &begin, off_t &end) const;
    void setContentLen(off_t entityLen)    { m_lEntityLen = entityLen; }
    void beginMultipart();

    const char *getBoundary() const
    {   return m_boundary;  }

    off_t getPartLen(int n, int iMimeTypeLen) const;
    int  getPartHeader(int n, const char *pMimeType, char *buf,
                       int size) const;
    int  getPartHeader(const char *pMimeType, char *buf, int size) const
    {   return getPartHeader(m_iCurRange, pMimeType, buf, size);      }

    off_t getMultipartBodyLen(const AutoStr2 *pMimeType) const;

    bool more() const;
    void next() {   ++m_iCurRange;  }
    int  getContentOffset(off_t &begin, off_t &end) const;
    int  getPartHeaderLen() const   {   return m_pPartHeaderEnd - m_pCurHeaderPos;  }
    void partHeaderSent(int &len)
    {
        if (len > m_pPartHeaderEnd - m_pCurHeaderPos)
        {
            len -= m_pPartHeaderEnd - m_pCurHeaderPos;
            m_pCurHeaderPos = m_pPartHeaderEnd;
        }
        else
        {
            m_pCurHeaderPos += len;
            len = 0;
        }
    }
    int buildPartHeader(const char *pMimeType)
    {
        int len = getPartHeader(pMimeType, m_partHeaderBuf, MAX_PART_HEADER_LEN);
        m_pPartHeaderEnd = (char *)m_partHeaderBuf + len;
        m_pCurHeaderPos = m_partHeaderBuf;
        return len;
    }

    const char *getPartHeader() const {    return m_pCurHeaderPos; }
    LS_NO_COPY_ASSIGN(HttpRange);
};


#endif
