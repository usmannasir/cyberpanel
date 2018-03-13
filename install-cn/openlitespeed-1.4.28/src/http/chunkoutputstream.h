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
#ifndef CHUNKOUTPUTSTREAM_H
#define CHUNKOUTPUTSTREAM_H


#include <lsdef.h>
#include <util/iovec.h>


#define CHUNK_HEADER_SIZE   20
#define CHUNK_TAIL_SIZE     2   //"\r\n"
#define CHUNK_BUFSIZE       (1450 - CHUNK_HEADER_SIZE - CHUNK_TAIL_SIZE)
#define MAX_CHUNK_SIZE      8192

class OutputStream;

class ChunkOutputStream
{
    OutputStream   *m_pOS;
    IOVec           m_iov;
    int             m_iCurSize;
    char            m_iBuffering;
    short           m_iSendFileLeft;
    int             m_iTotalPending;
    int             m_iLastBufLen;
    const char     *m_pLastBufBegin;

    char            m_headerBuf[ CHUNK_HEADER_SIZE ];
    char            m_bufChunk[ CHUNK_BUFSIZE ];
    int writeChunk();
    int buildIovec(const char *pBuf, int size);
    int chunkedWrite(const char *pBuf, int size);
    int fillChunkBuf(const char *pBuf, int size);
    int buildChunkHeader(int size);
public:
    ChunkOutputStream();
    ~ChunkOutputStream();
    void setStream(OutputStream *pOS)
    {   m_pOS = pOS;  }
    void open()     {   reset();        }
    int write(const char *pBuf, int size);
    int close();
    int flush2();
    int flush()
    {
        if (m_iCurSize > 0)
        {
            m_iTotalPending += buildIovec(NULL, 0);
            m_iCurSize = 0;
        }
        if (m_iTotalPending)
            return flush2();
        return 0;
    }
    void reset();
    void setBuffering(int n)
    {   m_iBuffering = n;    }
    short &getSendFileLeft()  { return m_iSendFileLeft; }
    void buildSendFileChunk(int size);
    void appendCRLF();
    LS_NO_COPY_ASSIGN(ChunkOutputStream);
};

#endif
