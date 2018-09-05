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
#include <util/gzipbuf.h>
#include <util/vmembuf.h>

#include <lsr/ls_fileio.h>

#include <log4cxx/logger.h>

#include <assert.h>
//#include <netinet/in.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

GzipBuf::GzipBuf()
{
    memset(&m_zstr, 0, sizeof(z_stream));
}


GzipBuf::~GzipBuf()
{
    release();
}


int GzipBuf::release()
{
    if (m_iType == COMPRESSOR_DECOMPRESS)
        return inflateEnd(&m_zstr);
    else
        return deflateEnd(&m_zstr);
}


int GzipBuf::init(int type, int level)
{
    int ret;
    if (type == COMPRESSOR_DECOMPRESS)
        m_iType = COMPRESSOR_DECOMPRESS;
    else
        m_iType = COMPRESSOR_COMPRESS;
    if (m_iType == COMPRESSOR_COMPRESS)
    {
        if (!m_zstr.state)
            ret = deflateInit2(&m_zstr, level, Z_DEFLATED, 15 + 16, 8,
                               Z_DEFAULT_STRATEGY);
        else
            ret = deflateReset(&m_zstr);
    }
    else
    {
        if (!m_zstr.state)
            ret = inflateInit2(&m_zstr, 15 + 16);
        else
            ret = inflateReset(&m_zstr);
    }
    return ret;
}

int GzipBuf::reinit()
{
    int ret = reset();
    m_iStreamStarted = 1;
    return ret;
}


int GzipBuf::beginStream()
{
    if (!m_pCompressCache)
        return LS_FAIL;
    size_t size;

    m_zstr.next_in = NULL;
    m_zstr.avail_in = 0;

    m_zstr.next_out = (unsigned char *)
                      m_pCompressCache->getWriteBuffer(size);
    m_zstr.avail_out = size;
    if (!m_zstr.next_out)
        return LS_FAIL;
    m_iStreamStarted = 1;
    return 0;
}

int GzipBuf::compress(const char *pBuf, int len)
{
    if (!m_iStreamStarted)
        return LS_FAIL;
    m_zstr.next_in = (unsigned char *)pBuf;
    m_zstr.avail_in = len;
    return process(0);
}

int GzipBuf::process(int finish)
{
//     LS_ERROR("GZIPBUF in process");
    do
    {
        int ret;
        size_t size;
        if (!m_zstr.avail_out)
        {
            m_zstr.next_out = (unsigned char *)m_pCompressCache->getWriteBuffer(size);
            m_zstr.avail_out = size;
            assert(m_zstr.avail_out);
        }
        if (m_iType == COMPRESSOR_COMPRESS)
            ret = ::deflate(&m_zstr, finish);
        else
            ret = ::inflate(&m_zstr, finish);
        if (ret == Z_STREAM_ERROR)
            return LS_FAIL;
        if (ret == Z_BUF_ERROR)
            ret = 0;
        m_pCompressCache->writeUsed(m_zstr.next_out -
                                    (unsigned char *)m_pCompressCache->getCurWPos());
        if ((m_zstr.avail_out) || (ret == Z_STREAM_END))
            return ret;
        m_zstr.next_out = (unsigned char *)m_pCompressCache->getWriteBuffer(size);
        m_zstr.avail_out = size;
        if (!m_zstr.next_out)
            return LS_FAIL;
    }
    while (true);
}


int GzipBuf::endStream()
{
    int ret = process(Z_FINISH);
    m_iStreamStarted = 0;
    if (ret != Z_STREAM_END)
        return LS_FAIL;
    return 0;
}

int GzipBuf::resetCompressCache()
{
    m_pCompressCache->rewindReadBuf();
    m_pCompressCache->rewindWriteBuf();
    size_t size;
    m_zstr.next_out = (unsigned char *)
                      m_pCompressCache->getWriteBuffer(size);
    m_zstr.avail_out = size;
    return 0;
}



