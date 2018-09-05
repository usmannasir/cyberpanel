/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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
#ifndef COMPRESSOR_H
#define COMPRESSOR_H

#include <lsdef.h>
#include <inttypes.h>

class VMemBuf;

class Compressor
{
protected:
    uint32_t        m_iLastFlush;
    uint32_t        m_iFlushWindowSize;
    short           m_iType;
    short           m_iStreamStarted;
    VMemBuf        *m_pCompressCache;

public:
    enum
    {
        COMPRESSOR_UNKNOWN,
        COMPRESSOR_COMPRESS,
        COMPRESSOR_DECOMPRESS
    };
    Compressor();
    virtual ~Compressor();

    int getType() const {   return m_iType;   }
    void setFlushWindowSize(unsigned long size)
    {   m_iFlushWindowSize = size;       }
    void setCompressCache(VMemBuf *pCache)
    {   m_pCompressCache = pCache;  }
    VMemBuf *getCompressCache() const
    {   return m_pCompressCache;    }

    virtual int init(int type, int level) = 0;
    virtual int reinit() = 0;
    virtual int beginStream() = 0;
    virtual int shouldFlush() = 0;
    virtual int flush() = 0;
    virtual int endStream() = 0;
    virtual int reset() = 0;
    virtual const char *getLastError() const = 0;

    virtual int resetCompressCache();
    virtual int write(const char *pBuf, int len) = 0;
    virtual int processFile(int type, const char *pFileName,
                    const char *pCompressFileName);

    int compressFile(const char *pFileName, const char *pCompressFileName)
    {   return processFile(COMPRESSOR_COMPRESS, pFileName, pCompressFileName);       }
    int decompressFile(const char *pFileName, const char *pDecompressFileName)
    {   return processFile(COMPRESSOR_DECOMPRESS, pFileName, pDecompressFileName);       }
    int isStreamStarted() const {   return m_iStreamStarted;     }


    LS_NO_COPY_ASSIGN(Compressor);
};

#endif
