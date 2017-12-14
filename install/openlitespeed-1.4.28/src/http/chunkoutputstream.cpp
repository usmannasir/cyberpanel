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
#include "chunkoutputstream.h"

#include <edio/outputstream.h>

#include <assert.h>
#include <stdio.h>
#include <sys/uio.h>

static const char *s_CHUNK_END = "0\r\n\r\n";

ChunkOutputStream::ChunkOutputStream()
    : m_pOS(NULL)
    , m_iCurSize(0)
    , m_iBuffering(0)
    , m_iSendFileLeft(0)
    , m_iTotalPending(0)
{
    m_iov.clear();
}


ChunkOutputStream::~ChunkOutputStream()
{}


int ChunkOutputStream::buildChunkHeader(int size)
{
    int total = snprintf(m_headerBuf,
                         CHUNK_HEADER_SIZE, "%x\r\n", size);
    m_iov.append(m_headerBuf, total);
    return total;
}


int ChunkOutputStream::buildIovec(const char *pBuf, int size)
{
    int total = buildChunkHeader(size + m_iCurSize);
    if (m_iCurSize)
    {
        m_iov.append(m_bufChunk, m_iCurSize);
        total += m_iCurSize;
        m_iCurSize = 0;
    }
    if (pBuf)
    {
        m_iov.append((void *)pBuf, size);
        total += size;
    }
    if (pBuf || size == 0)
    {
        m_iov.append("\r\n", 2);
        total += 2;
    }
    return total;
}


void ChunkOutputStream::appendCRLF()
{
    m_iov.append("\r\n", 2);
    m_iTotalPending += 2;
}


int ChunkOutputStream::fillChunkBuf(const char *pBuf, int size)
{
    memmove(m_bufChunk + m_iCurSize, pBuf, size);
    m_iCurSize += size;
    return size;
}


int ChunkOutputStream::chunkedWrite(const char *pBuf, int size)
{
    //printf( "****ChunkOutputStream::chunkedWrite()\n" );

    m_iTotalPending = buildIovec(pBuf, size);
    int ret = flush2();
    switch (ret)
    {
    case 0:
        m_iLastBufLen = 0;
        return size;
    case 1:
        m_pLastBufBegin = pBuf;
        m_iLastBufLen = size;
        return 0;
    default:
        return ret;
    }
}


int ChunkOutputStream::write(const char *pBuf, int size)
{
    //printf( "****ChunkOutputStream::write()\n" );
    int chunkSize;
    int ret, left = size;
    if ((pBuf == NULL) || (size <= 0))
        return 0;
    assert(m_pOS != NULL);
    if (m_iTotalPending)
    {
        if (m_pLastBufBegin && pBuf != m_pLastBufBegin)
        {
            m_iov.adjust(m_pLastBufBegin, pBuf, m_iLastBufLen);
            m_pLastBufBegin = pBuf;
        }
        ret = flush2();
        switch (ret)
        {
        case 0:
            break;
        case 1:
            return 0;
        default:
            return ret;
        }
    }

    if (m_pLastBufBegin != NULL)
    {
        left -= m_iLastBufLen;
        pBuf += m_iLastBufLen;
        m_pLastBufBegin = NULL;
        m_iLastBufLen = 0;
        if (!left)
            return size;
    }

    do
    {
        if (left + m_iCurSize > MAX_CHUNK_SIZE)
            chunkSize = MAX_CHUNK_SIZE - m_iCurSize;
        else
            chunkSize = left;


        if ((m_iBuffering) && (chunkSize + m_iCurSize < CHUNK_BUFSIZE))
        {
            ret = fillChunkBuf(pBuf, chunkSize);
            return size;
        }
        ret = chunkedWrite(pBuf, chunkSize);

        if (ret > 0)
        {
            left -= ret;
            if (!left)
                return size;
            pBuf += ret;
            assert(left > 0);
        }
        else if (!ret)
            return size - left;
        else
            return ret;
    }
    while (1);
}


void ChunkOutputStream::reset()
{
    memset(&m_iCurSize, 0, (char *)m_headerBuf - (char *)&m_iCurSize);
    m_iov.clear();
}


int ChunkOutputStream::flush2()
{
    int ret = m_pOS->writev(m_iov, m_iTotalPending);
    if (ret >= m_iTotalPending)
    {
        m_iov.clear();
        m_iCurSize = 0;
        m_iTotalPending = 0;
        return 0;
    }
    else if (ret >= 0)
    {
        if (ret)
        {
            m_iTotalPending -= ret;
            m_iov.finish(ret);
        }
        return 1;
    }
    return LS_FAIL;
}


int ChunkOutputStream::close()
{
    if (m_iCurSize > 0)
        m_iTotalPending += buildIovec(NULL, 0);
    m_iTotalPending += 5;
    m_iov.append(s_CHUNK_END, 5);
    return flush2();
}


void ChunkOutputStream::buildSendFileChunk(int size)
{
    if (size > MAX_CHUNK_SIZE)
        size = MAX_CHUNK_SIZE;

    if (m_iCurSize > 0)
        m_iTotalPending += buildIovec(NULL, size);
    else
        m_iTotalPending += buildChunkHeader(size);
    m_iSendFileLeft = size;

}
