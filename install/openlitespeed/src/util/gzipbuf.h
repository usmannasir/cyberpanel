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
#ifndef GZIPBUF_H
#define GZIPBUF_H

#include <lsdef.h>
#include <util/compressor.h>

#include <inttypes.h>
#include <zlib.h>

class VMemBuf;

class GzipBuf : public Compressor
{
    z_stream        m_zstr;
    //uint32_t        m_crc;

    int process(int finish);
    int compress(const char *pBuf, int len);
    int decompress(const char *pBuf, int len);
public:
    GzipBuf();
    ~GzipBuf();

    int init(int type, int level);
    int reinit();
    int beginStream();
    int write(const char *pBuf, int len)
    {   return (compress(pBuf, len) < 0) ? -1 : len;  }
    int shouldFlush()
    {   return m_zstr.total_in - m_iLastFlush > m_iFlushWindowSize;       }
    int flush()
    {   m_iLastFlush = m_zstr.total_in; return process(Z_SYNC_FLUSH);  }
    int endStream();
    int reset()
    {
        if (m_iType == COMPRESSOR_COMPRESS)
            return deflateReset(&m_zstr);
        else
            return inflateReset(&m_zstr);
    }

    int release();

    int resetCompressCache();
    const char *getLastError() const
    {   return m_zstr.msg;          }


    LS_NO_COPY_ASSIGN(GzipBuf);
};

#endif
