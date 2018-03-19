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
#include "httprange.h"

#include <http/httpstatuscode.h>
#include <lsr/ls_strtool.h>
#include <lsr/ls_xpool.h>
#include <util/autostr.h>
#include <util/stringtool.h>

#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>

class ByteRange
{
    off_t m_lBegin;
    off_t m_lEnd;
public:
    ByteRange()
        : m_lBegin(0), m_lEnd(0)
    {}

    ByteRange(off_t b, off_t e)
        : m_lBegin(b), m_lEnd(e)
    {}
    off_t getBegin() const   { return m_lBegin;  }
    off_t getEnd() const     { return m_lEnd;    }
    void setBegin(off_t b) { m_lBegin = b;     }
    void setEnd(off_t e)    { m_lEnd = e;       }
    int check(int entityLen);
    off_t getLen() const     { return m_lEnd - m_lBegin + 1;   }
    LS_NO_COPY_ASSIGN(ByteRange);
};



int ByteRange::check(int entityLen)
{
    if (entityLen > 0)
    {
        if (m_lBegin == -1)
        {
            off_t b = entityLen - m_lEnd;
            if (b < 0)
                b = 0;
            m_lBegin = b;
            m_lEnd = entityLen - 1;
        }
        if ((m_lEnd == -1) || (m_lEnd >= entityLen))
            m_lEnd = entityLen - 1 ;
        if (m_lEnd < m_lBegin)
            return LS_FAIL;
    }
    return 0;
}

HttpRange::HttpRange(off_t entityLen)
    : m_lEntityLen(entityLen)
{
    ::memset(m_boundary, 0, sizeof(m_boundary));
}


int HttpRange::count() const
{
    return m_array.getSize();
}

ByteRange *HttpRange::getSlot(ls_xpool_t *pool)
{
    if (m_array.getCapacity() == 0)
        m_array.guarantee(pool, 3);
    else if (m_array.getCapacity() <= m_array.getSize() + 1)
        m_array.guarantee(pool, m_array.getCapacity() * 2);
    return m_array.getNew();
}

int HttpRange::checkAndInsert(ByteRange &range, ls_xpool_t *pool)
{
    if ((range.getBegin() == -1) && (range.getEnd() == -1))
        return LS_FAIL;
    if (m_lEntityLen > 0)
    {
        if (range.getBegin() >= m_lEntityLen)
            return 0;
        if (range.check(m_lEntityLen))
            return LS_FAIL;
    }
    new(getSlot(pool)) ByteRange(range.getBegin(), range.getEnd());
    return 0;
}

/*
  Range: bytes=10-30,40-50,-60,61-
  A state machine is used to parse the range request string.
  states are:
    0: start parsing a range unit,
    1: first number in the range unit,
    2: '-' between the two number of the range unit
    3: second number in the range unit,
    4: space after first number
    5: space after second number
  states transitions:

    0 -> 0 : receive white space
    0 -> 1 : receive a digit
    0 -> 2 : receive a '-'
    0 -> end: receive '\0'
    0 -> err: receive char other than the above

    1 -> 1 : receive a digit
    1 -> 2 : receive a '-'
    1 -> 4 : receive a white space
    1 -> err: receive char other than the above

    2 -> 2 : receive white space
    2 -> 3 : receive a digit
    2 -> 0 : receive a ','
    2 -> end: receive '\0'
    2 -> err: receive char other than the above

    3 -> 3 : receive a digit
    3 -> 5 : receive a white space
    3 -> 0 : receive a ','
    3 -> end: receive '\0'
    3 -> err: receive char other than the above

    4 -> 4 : receive white space
    4 -> 2 : receive a '-'
    4 -> err: receive char other than the above

    5 -> 5 : receive white space
    5 -> 0 : receive ','
    5 -> end: receive '\0'
    5 -> err: receive char other than the above
*/

int HttpRange::parse(const char *pRange, ls_xpool_t *pool)
{
    m_array.clear();
    if (strncasecmp(pRange, "bytes=", 6) != 0)
        return SC_400;
    char ch;
    pRange += 6;
    while (isspace((ch = *pRange++)))
        ;
    if (!ch)
        return SC_400;
    int state = 0;
    ByteRange range(-1, -1);
    off_t lValue = 0;
    while (state != 6)
    {
        switch (ch)
        {
        case ' ':
        case '\t':
            switch (state)
            {
            case 0:
            case 2:
            case 4:
            case 5:
                break;
            case 1:
                state = 4;
                range.setBegin(lValue);
                lValue = 0;
                break;
            case 3:
                state = 5;
                range.setEnd(lValue);
                lValue = 0;
                break;
            }
            break;
        case '0':
        case '1':
        case '2':
        case '3':
        case '4':
        case '5':
        case '6':
        case '7':
        case '8':
        case '9':
            switch (state)
            {
            case 0:
            case 2:
                lValue = ch - '0';
                ++state;
                break;
            case 1:
            case 3:
                lValue = (lValue << 3) + (lValue << 1) + (ch - '0');
                break;
            case 4:
            case 5:
                state = 6; //error,
                break;
            }
            break;
        case '-':
            switch (state)
            {
            case 1:
                range.setBegin(lValue);
                lValue = 0;
            //don't break, fall through
            case 0:
            case 4:
                state = 2;
                break;
            case 2:
            case 3:
            case 5:
                state = 6;
                break;
            }
            break;
        case '\r':
        case '\n':
            ch = 0;
        //fall through
        case ',':
        case '\0':
            switch (state)
            {
            case 3:
                range.setEnd(lValue);
                lValue = 0;
            //don't break, fall through
            case 2:
            case 5:
                if (checkAndInsert(range, pool) == -1)
                {
                    state = 6;
                    break;
                }
                range.setBegin(-1);
                range.setEnd(-1);
                state = 0;
                break;
            case 1:
            case 4:
                state = 6;
                break;
            case 0:
                if (ch)
                    state = 6;
                break;
            }
            break;
        default:
            state = 6;
            break;
        }
        if (!ch)
            break;
        ch = *pRange++;
    }
    if (state == 6)
    {
        m_array.clear();
        return SC_400;
    }
    if (m_array.getSize() == 0)
        return SC_416; //range not satisfiable
    return 0;
}

//Content-Range:
int HttpRange::getContentRangeString(int n, char *pBuf, int len) const
{
    char *pBegin = pBuf;
    int ret;
    ret = ls_snprintf(pBuf, len, "%s", "Content-Range: bytes ");
    pBuf += ret;
    len -= ret;
    ret = 0;
    if (len <= 0)
        return LS_FAIL;
    char achLen[30];
    StringTool::offsetToStr(achLen, 30, m_lEntityLen);
    if ((n < 0) || (n >= m_array.getSize()))
    {
        if (m_lEntityLen == -1)
            return LS_FAIL;
        else
            ret = ls_snprintf(pBuf, len, "*/%s\r\n", achLen);
    }
    else
    {
        int ret1;
        ret1 = StringTool::offsetToStr(pBuf, len, m_array.getObj(n)->getBegin());
        if (ret1 < 0)
            return LS_FAIL;
        pBuf += ret1;
        len -= ret1;
        *pBuf++ = '-';
        ret1 = StringTool::offsetToStr(pBuf, len, m_array.getObj(n)->getEnd());
        if (ret1 < 0)
            return LS_FAIL;
        pBuf += ret1;
        len -= ret1;
        *pBuf++ = '/';
        len -= 2;

        if (len <= 0)
            return LS_FAIL;
        if (m_lEntityLen >= 0)
            ret = ls_snprintf(pBuf, len, "%s\r\n", achLen);
        else
        {
            if (len > 4)
            {
                *pBuf++ = '*';
                *pBuf++ = '\r';
                *pBuf++ = '\n';
                *pBuf = 0;
            }
            else
                return LS_FAIL;
        }
    }
    len -= ret;
    pBuf += ret;
    return (len > 0) ? pBuf - pBegin : -1;
}

int HttpRange::getContentOffset(int n, off_t &begin, off_t &end) const
{
    if ((n < 0) || (n >= m_array.getSize()))
        return LS_FAIL;
    if (m_array.getObj(n)->check(m_lEntityLen) == 0)
    {
        begin = m_array.getObj(n)->getBegin();
        end = m_array.getObj(n)->getEnd() + 1;
        return 0;
    }
    else
        return LS_FAIL;
}

void HttpRange::makeBoundaryString()
{
    struct timeval now;
    gettimeofday(&now, NULL);
    ls_snprintf(m_boundary, sizeof(m_boundary) - 1, "%08x%08x",
                (int)now.tv_usec ^ getpid(), (int)(now.tv_usec ^ now.tv_sec));
    *(m_boundary + sizeof(m_boundary) - 1) = 0;
}

void HttpRange::beginMultipart()
{
    makeBoundaryString();
    m_iCurRange = -1;
}

int HttpRange::getPartHeader(int n, const char *pMimeType, char *buf,
                             int size) const
{
    assert((n >= 0) && (n <= m_array.getSize()));
    int ret;
    if (n < m_array.getSize())
    {
        ret = snprintf(buf, size,
                       "\r\n--%s\r\n"
                       "Content-type: %s\r\n",
                       m_boundary, pMimeType);
        if (ret >= size)
            return LS_FAIL;
        buf += ret;
        int ret1 = getContentRangeString(n, buf, size - ret);
        if (ret1 == -1)
            return LS_FAIL;
        buf += ret1 ;
        *buf++ = '\r';
        *buf++ = '\n';
        ret += ret1 + 2;
    }
    else
        ret = snprintf(buf, size, "\r\n--%s--\r\n", m_boundary);
    return (ret == size) ? -1 : ret;
}


static off_t getDigits(off_t n)
{
    if (n < 10)
        return 1;
    else
        return (off_t)log10((double)n) + 1;
}

off_t HttpRange::getPartLen(int n, int iMimeTypeLen) const
{
    off_t len = 4 + 16 + 2
                + 14 + iMimeTypeLen + 2
                + 21 + getDigits(m_array.getObj(n)->getBegin()) + 1
                + getDigits(m_array.getObj(n)->getEnd()) + 1
                + 2 + 2
                + m_array.getObj(n)->getLen();
    if (m_lEntityLen == -1)
        ++len;
    else
        len += getDigits(m_lEntityLen);
    return len;
}

off_t HttpRange::getMultipartBodyLen(const AutoStr2 *pMimeType) const
{
    assert(pMimeType);
    if (m_lEntityLen == -1)
        return LS_FAIL;
    int typeLen = pMimeType->len();
    int size = m_array.getSize();
    off_t total = 0;
    for (int i = 0; i < size; ++i)
        total += getPartLen(i, typeLen);
    return total + 24;
}

bool HttpRange::more() const
{
    return m_iCurRange < m_array.getSize();
}

int HttpRange::getContentOffset(off_t &begin, off_t &end) const
{
    return getContentOffset(m_iCurRange, begin, end);
}



