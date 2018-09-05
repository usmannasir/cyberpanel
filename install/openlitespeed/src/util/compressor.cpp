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
#include <util/compressor.h>
#include <util/vmembuf.h>

#include <lsr/ls_fileio.h>

#include <fcntl.h>
#include <string.h>
#include <unistd.h>


#define DEFAULT_FLUSH_WINDOW    2048

Compressor::Compressor()
    : m_iLastFlush(0)
    , m_iFlushWindowSize(DEFAULT_FLUSH_WINDOW)
    , m_iType(0)
    , m_iStreamStarted(0)
    , m_pCompressCache(0)
{
}


Compressor::~Compressor()
{
}


int Compressor::resetCompressCache()
{
    m_pCompressCache->rewindReadBuf();
    m_pCompressCache->rewindWriteBuf();
    return 0;
}


int Compressor::processFile(int type, const char *pFileName,
                         const char *pCompressFileName)
{
    int fd;
    int ret = 0;
    fd = open(pFileName, O_RDONLY);
    if (fd == -1)
        return LS_FAIL;
    VMemBuf gzFile;
    ret = gzFile.set(pCompressFileName, -1);
    if (!ret)
    {
        setCompressCache(&gzFile);
        if (((ret = init(type, 6)) == 0) && ((ret = beginStream()) == 0))
        {
            int len;
            char achBuf[16384];
            while (true)
            {
                len = ls_fio_read(fd, achBuf, sizeof(achBuf));
                if (len <= 0)
                    break;
                if (this->write(achBuf, len) != len)
                {
                    ret = -1;
                    break;
                }
            }
            if (!ret)
            {
                ret = endStream();
                off_t size;
                if (!ret)
                    ret = gzFile.exactSize(&size);
            }
            gzFile.close();
        }
    }
    ::close(fd);
    return ret;
}



