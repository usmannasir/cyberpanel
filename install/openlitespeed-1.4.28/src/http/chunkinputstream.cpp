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
#include "chunkinputstream.h"

#include <util/stringtool.h>

#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/uio.h>


ChunkInputStream::ChunkInputStream()
    : m_pIS(NULL)
    , m_iChunkLen(INIT_CHUNK_LEN)
    , m_iRemain(0)
{
}
ChunkInputStream::~ChunkInputStream()
{
}

void ChunkInputStream::open()
{
    m_iChunkLen = INIT_CHUNK_LEN;
    memset(&m_iRemain, 0, (char *)&m_achChunkLenBuf - (char *)&m_iRemain);
}

//void ChunkInputStream::updateLastBytes( char * pBuf, int len )
//{
//    if ( len > 8)
//        memmove( m_achLastBytes, pBuf + len - 8, 8 );
//    else if ( len > 0 )
//    {
//        memmove( &m_achLastBytes[ len ], m_achLastBytes, 8 - len );
//        memmove( &m_achLastBytes[ 8 - len ], pBuf, len );
//    }
//}

int ChunkInputStream::bufRead(char *pBuf, int len, int prefetch)
{
    int left = m_iBufLen - m_iBufUsed;
    int ret;
    if (left > 0)
    {
        if (left > len)
            left = len;
        memmove(pBuf, &m_achChunkLenBuf[m_iBufUsed], left);
        m_iBufUsed += left;
        if (m_iBufUsed == m_iBufLen)
            m_iBufUsed = m_iBufLen = 0;
        if (left == len)
            return left;
        pBuf += left;
        len -= left;
    }
    if (prefetch)
    {
        struct iovec vector[2];
        vector[0].iov_base = pBuf;
        vector[0].iov_len = len;
        vector[1].iov_base = m_achChunkLenBuf;
        vector[1].iov_len = 8;
        ret = m_pIS->readv(vector, 2);
        if (ret - len > 0)
        {
            m_iBufLen = ret - len;
            ret = len;
            updateLastBytes(pBuf, ret);
            updateLastBytes(m_achChunkLenBuf, m_iBufLen);
        }
        else
            updateLastBytes(pBuf, ret);

    }
    else
    {
        ret = m_pIS->read(pBuf, len);
        updateLastBytes(pBuf, ret);
    }
    if (ret > 0)
        return ret + left;
    if (left)
        return left;
    return ret;
}

int ChunkInputStream::nextChunk()
{
    if (m_iBufLen >= MAX_CHUNK_LEN_BUF_SIZE)
        return LS_FAIL;
    int len = (m_iBufLen) ? MAX_CHUNK_LEN_BUF_SIZE - m_iBufLen : 8;
    len = m_pIS->read(&m_achChunkLenBuf[ m_iBufLen ], len);
    if (len > 0)
    {
        updateLastBytes(&m_achChunkLenBuf[ m_iBufLen ], len);
        m_iBufLen += len;
        return parseChunkLen();
    }
    else if (len == 0)
        return len;
    //m_iChunkLen = INVALID_CHUNK;
    return LS_FAIL;
}

int ChunkInputStream::parseChunkLen()
{
    char *pLineEnd = (char *)memchr(m_achChunkLenBuf, '\n', m_iBufLen);
    if (pLineEnd)
    {
        m_iBufUsed = (pLineEnd - (char *)m_achChunkLenBuf) + 1;
        if (m_iBufUsed >= m_iBufLen)
            m_iBufUsed = m_iBufLen = 0;
        if (pLineEnd[-1] == '\r')
            --pLineEnd;
        char *p = m_achChunkLenBuf;
        StringTool::strTrim((const char *&)p, (const char *&)pLineEnd);
        *pLineEnd = 0;
        char *p1;
        long lLen = strtol(p, &p1, 16);
        if (((!*p1) || (*p1 == ' ') || (*p1 == ';')) && (p1 != p))
        {
            m_iChunkLen = lLen;
            if (m_iChunkLen)
                m_iRemain = lLen + 2;
            else
                m_iRemain = -2;

            return 1;
        }
    }
    else
    {
        if (m_iBufLen < MAX_CHUNK_LEN_BUF_SIZE)
            return 0;
    }
    //m_iChunkLen = INVALID_CHUNK;
    return LS_FAIL;
}

int ChunkInputStream::readTrailingCRLF()
{
    int ret = 1;
    if (m_iBufLen == m_iBufUsed)
    {
        m_iBufUsed = 0;
        m_iBufLen = 0;
        ret = m_pIS->read(m_achChunkLenBuf, 8 + m_iRemain);
        if (ret <= 0)
            return ret;
        updateLastBytes(m_achChunkLenBuf, ret);
        m_iBufLen = ret;
    }
    while (m_iBufLen > m_iBufUsed)
    {
        char ch = m_achChunkLenBuf[ m_iBufUsed++ ];
        if (ch == '\n')
        {
            m_iRemain = 0;
            if (m_iBufUsed)
            {
                memmove(m_achChunkLenBuf, &m_achChunkLenBuf[m_iBufUsed],
                        m_iBufLen - m_iBufUsed);
                m_iBufLen -= m_iBufUsed;
                m_iBufUsed = 0;
                if (m_iBufLen)
                    return parseChunkLen();
            }
            return 1;
        }
        if ((ch == '\r') && (m_iRemain == 2))
        {
            --m_iRemain;
            continue;
        }
        return LS_FAIL;
    }
    return ret;
}

int ChunkInputStream::skipTrailer()
{
    char achBuf[128];
    int ret;
    while (true)
    {
        ret = bufRead(achBuf, sizeof(achBuf), 1);
        if (ret <= 0)
            return ret;
        char *pBegin = achBuf;
        char *pEnd = &achBuf[ret];
        while (pBegin < pEnd)
        {
            switch (m_iRemain)
            {
            case -3:
                pBegin = (char *)memchr(pBegin, '\n', pEnd - pBegin);
                if (pBegin)
                {
                    ++m_iRemain;
                    ++pBegin;
                }
                else
                    pBegin = pEnd;
                break;
            case -2:
                if (*pBegin == '\r')
                    ++m_iRemain;
                else if (*pBegin == '\n')
                {
                    m_iChunkLen = CHUNK_EOF;
                    m_iRemain = 0;
                    return 1;
                }
                else
                    m_iRemain = -3;
                ++pBegin;
                break;
            case -1:
                if (*pBegin == '\n')
                {
                    m_iChunkLen = CHUNK_EOF;
                    m_iRemain = 0;
                    return 1;
                }
                else
                    m_iRemain = -3;
                ++pBegin;
                break;
            }
        }
    }
}


int ChunkInputStream::readChunkContent(char *&pBuf, int &size, int &len)
{
    int readLen = m_iRemain - 2;
    int ret;
    if (readLen > size)
    {
        readLen = size;
        ret = bufRead(pBuf, readLen, 0);
    }
    else
        ret = bufRead(pBuf, readLen, 1);
    if (ret > 0)
    {
        pBuf += ret;
        size -= ret;
        len += ret;
        m_iRemain -= ret;
    }
    return ret;
}

int ChunkInputStream::read(char *pBuf, int size)
{
    int ret = -1, len = 0;
    assert(m_pIS);
    if (!m_pIS)
        return LS_FAIL;
    do
    {
        if (m_iChunkLen == CHUNK_EOF)
            return len;
        if (m_iChunkLen <= INVALID_CHUNK)      //error of chunked stream
        {
            ret = -1;
            break;
        }
        if (!m_iRemain)           //current chunk is finished
            ret = nextChunk();
        if (m_iRemain > 2)
            ret = readChunkContent(pBuf, size, len);
        if ((m_iRemain <= 2)           // reading trailing "\r\n" of a chunk
            && (m_iRemain > 0))
            ret = readTrailingCRLF();
        if (m_iRemain < 0)
            ret = skipTrailer();
    }
    while ((ret > 0) && (size > 0));
    if (ret <= 0)
    {
        if (ret)
            m_iChunkLen = INVALID_CHUNK;
        if (len == 0)        //data is not ready from underlying IS
            len = ret;
    }
    return len;
}

int ChunkInputStream::readv(struct iovec *vector, size_t count)
{
    assert("ChunkInputStream::readv() is not impelemented" == NULL);
    return LS_FAIL;
}


