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
#ifndef CHUNKINPUTSTREAM_H
#define CHUNKINPUTSTREAM_H

#include <lsdef.h>
#include <edio/inputstream.h>


#define INIT_CHUNK_LEN  -2
#define INVALID_CHUNK   -3
#define CHUNK_EOF       -4
#define MAX_CHUNK_LEN_BUF_SIZE 80
class ChunkInputStream : public InputStream
{
    InputStream *m_pIS;
    int     m_iChunkLen;
    int     m_iRemain;
    int     m_iBufLen;
    int     m_iBufUsed;
    char    m_achChunkLenBuf[MAX_CHUNK_LEN_BUF_SIZE];
    //char    m_achLastBytes[8];

    int bufRead(char *pBuf, int len, int prefetch);
    int nextChunk();
    int readTrailingCRLF();
    int readChunkContent(char *&pBuf, int &size, int &len);
    int parseChunkLen();
    int skipTrailer();

    void updateLastBytes(char *pBuf, int len) {}

public:
    ChunkInputStream();
    ~ChunkInputStream();
    void open();
    void setStream(InputStream *pIS)   {   m_pIS = pIS;   }
    virtual int read(char *pBuf, int size);
    int readv(struct iovec *vector, size_t count);
    void close() {};
    bool eos()  const  {  return m_iChunkLen == CHUNK_EOF ;       }
    bool fail() const  {  return m_iChunkLen == INVALID_CHUNK;    }
    int getChunkLen()       const   {   return m_iChunkLen;     }
    int getBufSize()        const   {   return m_iBufLen;       }
    int getChunkRemain()    const   {   return m_iRemain;       }
    const char *getChunkLenBuf() const   {   return m_achChunkLenBuf;    }
    //const char* getLastBytes() const      {   return m_achLastBytes;  }
    LS_NO_COPY_ASSIGN(ChunkInputStream);
};

#endif
