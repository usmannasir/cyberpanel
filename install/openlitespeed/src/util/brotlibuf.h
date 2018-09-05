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
#ifndef BROTLIBUF_H
#define BROTLIBUF_H

#include <config.h>

#ifdef USE_BROTLI
#include <lsdef.h>
#include <util/compressor.h>

#include <brotli/encode.h>
#include <brotli/decode.h>


class VMemBuf;

class BrotliBuf : public Compressor
{
    union {
        BrotliEncoderState *m_pEncoder;
        BrotliDecoderState *m_pDecoder;
    };
    size_t          m_iAvailIn;
    size_t          m_iAvailOut;
    const uint8_t  *m_pNextIn;
    uint8_t        *m_pNextOut;
    //uint32_t        m_crc;

    int process(BrotliEncoderOperation op);
    int compress(const char *pBuf, int len);
    int decompress(const char *pBuf, int len);

    int isStreamFinished();
public:
    BrotliBuf();
    ~BrotliBuf();

    explicit BrotliBuf(int type, int level);

    int getType() const {   return m_iType;   }

    int init(int type, int level);
    int reinit();
    int beginStream();
    int write(const char *pBuf, int len)
    {   return (compress(pBuf, len) < 0) ? -1 : len;  }
    int shouldFlush();
    int flush()
    {   return process(BROTLI_OPERATION_FLUSH); }
    int endStream();
    int reset();

    int release();

    int resetCompressCache();
    const char *getLastError() const;

    LS_NO_COPY_ASSIGN(BrotliBuf);
};

#endif // USE_BROTLI

#endif
