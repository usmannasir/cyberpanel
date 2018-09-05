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
#include <util/brotlibuf.h>

#ifdef USE_BROTLI

#include <util/vmembuf.h>

#include <lsr/ls_fileio.h>

#include <assert.h>
//#include <netinet/in.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>



BrotliBuf::BrotliBuf()
    : m_pEncoder(NULL)
    , m_iAvailIn(0)
    , m_iAvailOut(0)
    , m_pNextIn(NULL)
    , m_pNextOut(NULL)
{
}

BrotliBuf::BrotliBuf(int type, int level)
    : m_pEncoder(NULL)
    , m_iAvailIn(0)
    , m_iAvailOut(0)
    , m_pNextIn(NULL)
    , m_pNextOut(NULL)
{
    init(type, level);
}

BrotliBuf::~BrotliBuf()
{
    release();
}

int BrotliBuf::release()
{
    if (m_iType == COMPRESSOR_DECOMPRESS)
        BrotliDecoderDestroyInstance(m_pDecoder);
    else
        BrotliEncoderDestroyInstance(m_pEncoder);
    return 0;
}


int BrotliBuf::init(int type, int level)
{
    if (type == COMPRESSOR_DECOMPRESS)
        m_iType = COMPRESSOR_DECOMPRESS;
    else
        m_iType = COMPRESSOR_COMPRESS;
    if (m_iType == COMPRESSOR_COMPRESS)
    {
        m_pEncoder = BrotliEncoderCreateInstance(NULL, NULL, NULL);
        if (m_pEncoder != NULL)
            BrotliEncoderSetParameter(m_pEncoder, BROTLI_PARAM_QUALITY, level);
        return (m_pEncoder ? LS_OK : LS_FAIL);
    }
    else
    {
        m_pDecoder = BrotliDecoderCreateInstance(NULL, NULL, NULL);
        return (m_pDecoder ? LS_OK : LS_FAIL);
    }
}

int BrotliBuf::reinit()
{
    m_iStreamStarted = 1;
    return reset();
}


int BrotliBuf::beginStream()
{
    if (!m_pCompressCache)
        return LS_FAIL;
    size_t size;

    m_pNextIn = NULL;
    m_iAvailIn = 0;

    m_pNextOut = (uint8_t *) m_pCompressCache->getWriteBuffer(size);
    m_iAvailOut = size;
    if (!m_pNextOut)
        return LS_FAIL;
    m_iStreamStarted = 1;
    return 0;
}

int BrotliBuf::shouldFlush()
{
    BROTLI_BOOL ret;
    if (m_iType == COMPRESSOR_COMPRESS)
        ret = BrotliEncoderHasMoreOutput(m_pEncoder);
    else
        ret = BrotliDecoderHasMoreOutput(m_pDecoder);
    return (ret == BROTLI_TRUE);
}

int BrotliBuf::compress(const char *pBuf, int len)
{
    if (!m_iStreamStarted)
        return LS_FAIL;
    m_pNextIn = (uint8_t *)pBuf;
    m_iAvailIn = len;
    return process(BROTLI_OPERATION_PROCESS);
}

int BrotliBuf::process(BrotliEncoderOperation op)
{
    do
    {
        int ret;
        size_t size;
        if (!m_iAvailOut)
        {
            m_pNextOut = (unsigned char *)m_pCompressCache->getWriteBuffer(size);
            m_iAvailOut = size;
            assert(m_iAvailOut);
        }
        if (m_iType == COMPRESSOR_COMPRESS)
            ret = BrotliEncoderCompressStream(m_pEncoder, op, &m_iAvailIn,
                &m_pNextIn, &m_iAvailOut, &m_pNextOut, NULL);
        else
            ret = BrotliDecoderDecompressStream(m_pDecoder, &m_iAvailIn,
                &m_pNextIn, &m_iAvailOut, &m_pNextOut, NULL);
        if (((m_iType == COMPRESSOR_COMPRESS) && (ret == BROTLI_FALSE))
            || ((m_iType == COMPRESSOR_DECOMPRESS) && (ret == BROTLI_DECODER_RESULT_ERROR)))
            return LS_FAIL;
//         if (ret == Z_BUF_ERROR)
//             ret = 0;
        m_pCompressCache->writeUsed(m_pNextOut -
                                    (uint8_t *)m_pCompressCache->getCurWPos());
        if ((m_iAvailOut) || (isStreamFinished() == LS_OK))
            return ret;
        m_pNextOut = (uint8_t *)m_pCompressCache->getWriteBuffer(size);
        m_iAvailOut = size;
        if (!m_pNextOut)
            return LS_FAIL;
    }
    while (true);
}


int BrotliBuf::isStreamFinished()
{
    BROTLI_BOOL ret;
    if (m_iType == COMPRESSOR_COMPRESS)
        ret = BrotliEncoderIsFinished(m_pEncoder);
    else
        ret = BrotliDecoderIsFinished(m_pDecoder);
    return ((ret == BROTLI_TRUE) ? LS_OK : LS_FAIL);
}


int BrotliBuf::endStream()
{
    process(BROTLI_OPERATION_FINISH);
    m_iStreamStarted = 0;
    if (isStreamFinished() != LS_OK)
        return LS_FAIL;
    return 0;
}

int BrotliBuf::reset()
{
    if (m_iType == COMPRESSOR_COMPRESS)
    {
        if (m_pEncoder != NULL)
            BrotliEncoderDestroyInstance(m_pEncoder);
        m_pEncoder = BrotliEncoderCreateInstance(NULL, NULL, NULL);
        return (m_pEncoder ? LS_OK : LS_FAIL);
    }
    else
    {
        if (m_pDecoder != NULL)
            BrotliDecoderDestroyInstance(m_pDecoder);
        m_pDecoder = BrotliDecoderCreateInstance(NULL, NULL, NULL);
        return (m_pDecoder ? LS_OK : LS_FAIL);
    }
}

int BrotliBuf::resetCompressCache()
{
    m_pCompressCache->rewindReadBuf();
    m_pCompressCache->rewindWriteBuf();
    size_t size;
    m_pNextOut = (uint8_t *)m_pCompressCache->getWriteBuffer(size);
    m_iAvailOut = size;
    return 0;
}


const char *BrotliBuf::getLastError() const
{
    if (m_iType == COMPRESSOR_COMPRESS)
        return NULL;
    return BrotliDecoderErrorString(BrotliDecoderGetErrorCode(m_pDecoder));
}


#endif // USE_BROTLI

