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
#include "h2connection.h"
#include <http/hiohandlerfactory.h>
#include <http/httprespheaders.h>
#include <http/httpstatuscode.h>
#include <http/httpserverconfig.h>
#include <log4cxx/logger.h>
#include <spdy/h2stream.h>
#include <spdy/h2streampool.h>
#include <util/iovec.h>
#include <util/datetime.h>
#include <lsdef.h>

#include <ctype.h>

static const char s_h2sUpgradeResponse[] =
    "HTTP/1.1 101 Switching Protocols\r\nConnection: Upgrade\r\nUpgrade: h2c\r\n\r\n";
static const char *s_clientPreface = "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n";
#define H2_CLIENT_PREFACE_LEN   24


static hash_key_t int_hash(const void *p)
{
    return (int)(long)p;
}


static int  int_comp(const void *pVal1, const void *pVal2)
{
    return (int)(long)pVal1 - (int)(long)pVal2;
}


static inline void appendNbo4Bytes(LoopBuf *pBuf, uint32_t val)
{
    pBuf->append(val >> 24);
    pBuf->append((val >> 16) & 0xff);
    pBuf->append((val >> 8) & 0xff);
    pBuf->append(val & 0xff);
}


// static inline void append4Bytes(LoopBuf *pBuf, const char *val)
// {
//     pBuf->append(*val++);
//     pBuf->append(*val++);
//     pBuf->append(*val++);
//     pBuf->append(*val);
// }


H2Connection::H2Connection()
    : m_bufInput(4096)
    , m_uiPushStreamId(2)
    , m_uiLastStreamId(0)
    , m_uiShutdownStreams(0)
    , m_uiGoAwayId(0)
    , m_iCurPushStreams(0)
    , m_iCurrentFrameRemain(-H2_FRAME_HEADER_SIZE)
    , m_tmLastFrameIn(0)
    , m_mapStream(50, int_hash, int_comp)
    , m_iFlag(0)
    , m_iCurDataOutWindow(H2_FCW_INIT_SIZE)
    , m_iCurInBytesToUpdate(0)
    , m_iDataInWindow(H2_FCW_INIT_SIZE)
    , m_iStreamInInitWindowSize(H2_FCW_INIT_SIZE)
    , m_iServerMaxStreams(100)
    , m_iStreamOutInitWindowSize(H2_FCW_INIT_SIZE)
    , m_iMaxPushStreams(100)
    , m_iPeerMaxFrameSize(H2_DEFAULT_DATAFRAME_SIZE)
    , m_tmIdleBegin(0)
{
    m_timevalPing.tv_sec = 0;
    m_pCurH2Header = (H2FrameHeader *)m_iaH2HeaderMem;

}


HioHandler *H2Connection::get()
{
    H2Connection *pConn = new H2Connection();
    //pConn->init();
    return pConn;
}


int H2Connection::init()
{
    m_iCurDataOutWindow = H2_FCW_INIT_SIZE;
    m_uiLastStreamId = 0;
    m_iStreamOutInitWindowSize = H2_FCW_INIT_SIZE;
    m_iServerMaxStreams = 100;
    m_iMaxPushStreams = 100;
    m_tmIdleBegin = 0;
    m_uiShutdownStreams = 0;
    m_iCurPushStreams = 0;
    m_iCurrentFrameRemain = -H2_FRAME_HEADER_SIZE;
    m_pCurH2Header = (H2FrameHeader *)m_iaH2HeaderMem;
    return 0;
}


int H2Connection::onInitConnected()
{
    m_iState = HIOS_CONNECTED;
    setOS(getStream());
    getStream()->continueRead();
    return 0;
}


H2Connection::~H2Connection()
{
}


int H2Connection::onReadEx()
{
    int ret;
    m_iFlag &= ~H2_CONN_FLAG_WAIT_PROCESS;
    ret = onReadEx2();
    if ((m_iFlag & H2_CONN_FLAG_WAIT_PROCESS) != 0)
        onWriteEx();
    if (getBuf()->size() > 1024)
        flush();
    return ret;
}


int H2Connection::verifyClientPreface()
{
    char sPreface[H2_CLIENT_PREFACE_LEN];
    m_bufInput.moveTo(sPreface, H2_CLIENT_PREFACE_LEN);
    if (memcmp(sPreface, s_clientPreface, H2_CLIENT_PREFACE_LEN) != 0)
    {
        LS_DBG_L(getLogSession(), "Missing client PREFACE string,"
                 " got [%.24s], close.", sPreface);
        return LS_FAIL;
    }
    m_iFlag |= H2_CONN_FLAG_PREFACE;
    return 0;
}


int H2Connection::parseFrame()
{
    int ret;
    while (!m_bufInput.empty())
    {
        if (m_iCurrentFrameRemain < 0)
        {
            if (m_bufInput.size() < H2_FRAME_HEADER_SIZE)
                break;
            m_bufInput.moveTo((char *)m_pCurH2Header, H2_FRAME_HEADER_SIZE);

            m_iCurrentFrameRemain = m_pCurH2Header->getLength();
            LS_DBG_L(getLogSession(), "Frame type %d, size: %d",
                     m_pCurH2Header->getType(), m_iCurrentFrameRemain);
            if (m_iCurrentFrameRemain > H2_DEFAULT_DATAFRAME_SIZE)
            {
                LS_DBG_L(getLogSession(), "Frame size is too large, "
                         "Max: %d, Current Frame Size: %d.",
                         H2_DEFAULT_DATAFRAME_SIZE, m_iCurrentFrameRemain);
                return H2_ERROR_FRAME_SIZE_ERROR;
            }
        }
        if (!(m_iFlag & H2_CONN_FLAG_SETTING_RCVD))
        {
            if (m_pCurH2Header->getType() != H2_FRAME_SETTINGS)
            {
                LS_DBG_L(getLogSession(), "Expected SETTINGS frame "
                         "as part of client PREFACE, got frame type %d",
                         m_pCurH2Header->getType());
                return LS_FAIL;
            }
        }

        if ((m_iFlag & H2_CONN_HEADERS_START) == H2_CONN_HEADERS_START
            && m_pCurH2Header->getType() != H2_FRAME_CONTINUATION)
            return LS_FAIL;

        if (m_pCurH2Header->getType() != H2_FRAME_DATA)
        {
            if (m_iCurrentFrameRemain > m_bufInput.size())
                return 0;
            if ((ret = processFrame(m_pCurH2Header)) != LS_OK)
                return ret;
            if (m_iCurrentFrameRemain > 0)
                m_bufInput.pop_front(m_iCurrentFrameRemain);
            m_iCurrentFrameRemain = -H2_FRAME_HEADER_SIZE;
        }
        else
        {
            if ((ret = processDataFrame(m_pCurH2Header)) != LS_OK)
                return ret;
            if (m_iCurrentFrameRemain == 0)
                m_iCurrentFrameRemain = -H2_FRAME_HEADER_SIZE;
        }
    }

    if (m_iDataInWindow / 2 < m_iCurInBytesToUpdate)
    {
        LS_DBG_L(getLogSession(), "Send WINDOW_UPDATE, window: %d, consumed: %d.",
                 m_iDataInWindow, m_iCurInBytesToUpdate);
        sendWindowUpdateFrame(0, m_iCurInBytesToUpdate);
        m_iCurInBytesToUpdate = 0;
    }

    return 0;
}


int H2Connection::onReadEx2()
{
    int n = 0, avaiLen = 0;
    int ret;
    while (true)
    {
        if (m_bufInput.available() < 500)
            m_bufInput.guarantee(1024);
        avaiLen = m_bufInput.contiguous();
        n = getStream()->read(m_bufInput.end(), avaiLen);
        LS_DBG_L(getLogSession(), "Read() returned %d", n);

        if (n == -1)
            break;
        else if (n == 0)
            return 0;
        m_bufInput.used(n);

        if (!(m_iFlag & H2_CONN_FLAG_PREFACE))
        {
            if (m_bufInput.size() < H2_CLIENT_PREFACE_LEN)
                return 0;
            if (verifyClientPreface() == LS_FAIL)
                break;
        }
        if ((ret = parseFrame()) != LS_OK)
        {
            H2ErrorCode err;
            if ((ret < 0) || (ret >= H2_ERROR_CODE_COUNT))
                err = H2_ERROR_PROTOCOL_ERROR;
            else
                err = (H2ErrorCode)ret;
            doGoAway(err);
            return LS_FAIL;
        }
    }
    // must start to close connection
    // must turn off READING event in the meantime
    getStream()->suspendRead();
    onCloseEx();
    return LS_FAIL;
}


int H2Connection::processFrame(H2FrameHeader *pHeader)
{
    static uint32_t requiredLength[11] =
    {  0, 0, 5, 4, 0, 0, 8, 0, 4, 0, 0 };

    m_tmLastFrameIn = DateTime::s_curTime;

    int type = pHeader->getType();
    //m_bufInput.moveTo((char *)pHeader + H2_FRAME_HEADER_SIZE, extraHeader);
    if (type < H2_FRAME_MAX_TYPE)
    {
        if ((requiredLength[type] != 0)
            && (requiredLength[type] != pHeader->getLength()))
            return H2_ERROR_FRAME_SIZE_ERROR;
    }
    memset((char *)pHeader + H2_FRAME_HEADER_SIZE, 0, 10);
    printLogMsg(pHeader);

    switch (type)
    {
    case H2_FRAME_HEADERS:
        return processHeadersFrame(pHeader);
    case H2_FRAME_PRIORITY:
        return processPriorityFrame(pHeader);
    case H2_FRAME_RST_STREAM:
        return processRstFrame(pHeader);
    case H2_FRAME_SETTINGS:
        return processSettingFrame(pHeader);
    case H2_FRAME_PUSH_PROMISE:
        return processPushPromiseFrame(pHeader);
    case H2_FRAME_GOAWAY:
        processGoAwayFrame(pHeader);
        break;
    case H2_FRAME_WINDOW_UPDATE:
        return processWindowUpdateFrame(pHeader);
    case H2_FRAME_CONTINUATION:
        return processContinuationFrame(pHeader);
    case H2_FRAME_PING:
        return processPingFrame(pHeader);
    default:
        sendPingFrame(0, (uint8_t *)"01234567");
        break;
    }
    return 0;
}


void H2Connection::printLogMsg(H2FrameHeader *pHeader)
{
    if (LS_LOG_ENABLED(LOG4CXX_NS::Level::DBG_LESS))
    {
        const char *message = "";
        int messageLen = 0;
        if (pHeader->getType() == H2_FRAME_GOAWAY)
        {
            message = (const char *)m_bufInput.begin() + 8;
            messageLen = pHeader->getLength() - 8;
        }
        LS_DBG_L(getLogger(),
                 "[%s-%d] Received %s, size: %d, flag: 0x%hhx, Message: '%.*s'",
                 getLogId(), pHeader->getStreamId(),
                 getH2FrameName(pHeader->getType()), pHeader->getLength(),
                 pHeader->getFlags(), messageLen, message);
    }
}


int H2Connection::processPriorityFrame(H2FrameHeader *pHeader)
{
    if (pHeader->getStreamId() == 0)
    {
        LS_DBG_L(getLogSession(), "Bad PRIORITY frame, stream ID is zero.");
        return LS_FAIL;
    }

    return 0;
}


int H2Connection::processPushPromiseFrame(H2FrameHeader *pHeader)
{
    doGoAway(H2_ERROR_PROTOCOL_ERROR);
    return 0;
}


int H2Connection::processSettingFrame(H2FrameHeader *pHeader)
{
    //process each setting ID/value pair
    static const char *cpEntryNames[] =
    {
        "",
        "SETTINGS_HEADER_TABLE_SIZE",
        "SETTINGS_ENABLE_PUSH",
        "SETTINGS_MAX_CONCURRENT_STREAMS",
        "SETTINGS_INITIAL_WINDOW_SIZE",
        "SETTINGS_MAX_FRAME_SIZE",
        "SETTINGS_MAX_HEADER_LIST_SIZE"
    };
    uint32_t iEntryID, iEntryValue;
    if (pHeader->getStreamId() != 0)
    {
        LS_DBG_L(getLogSession(),
                 "Bad SETTINGS frame, stream ID must be zero.");
        doGoAway(H2_ERROR_PROTOCOL_ERROR);
        return 0;

    }

    int iEntries = m_iCurrentFrameRemain / 6;
    if (m_iCurrentFrameRemain % 6 != 0)
    {
        LS_DBG_L(getLogSession(),
                 "Bad SETTINGS frame, frame size does not match.");
        doGoAway(H2_ERROR_FRAME_SIZE_ERROR);
        return 0;
    }

    if (pHeader->getFlags() & H2_FLAG_ACK)
    {
        if (iEntries != 0)
        {
            LS_DBG_L(getLogSession(),
                     "Bad SETTINGS frame with ACK flag, has %d entries.",
                     iEntries);
            return LS_FAIL;
        }
        if (m_iFlag & H2_CONN_FLAG_SETTING_SENT)
        {
            m_iFlag |= H2_CONN_FLAG_CONFIRMED;
            return 0;
        }
        else
        {
            LS_DBG_L(getLogSession(), "Received SETTINGS frame with ACK flag "
                     "before sending our SETTINGS frame.");
            return LS_FAIL;
        }
    }

    int32_t   windowsSizeDiff = 0;
    unsigned char p[6];
    for (int i = 0; i < iEntries; i++)
    {
        m_bufInput.moveTo((char *)p, 6);
        iEntryID = ((uint16_t)p[0] << 8) | p[1];
        iEntryValue = beReadUint32(&p[2]);
        LS_DBG_L(getLogSession(), "%s(%d) value: %d",
                 (iEntryID < 7) ? cpEntryNames[iEntryID] : "INVALID", iEntryID,
                 iEntryValue);
        switch (iEntryID)
        {
        case H2_SETTINGS_HEADER_TABLE_SIZE:
            if (iEntryValue > MAX_HEADER_TABLE_SIZE)
            {
                LS_DBG_L(getLogSession(), "HEADER_TABLE_SIZE value is invalid, %d.",
                         iEntryValue);
                return LS_FAIL;
            }
            m_hpack.getReqDynTbl().updateMaxCapacity(iEntryValue);
            break;
        case H2_SETTINGS_MAX_FRAME_SIZE:
            if ((iEntryValue < H2_DEFAULT_DATAFRAME_SIZE) ||
                (iEntryValue > H2_MAX_DATAFRAM_SIZE))
            {
                LS_DBG_L(getLogSession(), "MAX_FRAME_SIZE value is invalid, %d.",
                         iEntryValue);
                return LS_FAIL;
            }
            m_iPeerMaxFrameSize = iEntryValue;
            break;
        case H2_SETTINGS_INITIAL_WINDOW_SIZE:
            if (iEntryValue > H2_FCW_MAX_SIZE)
            {
                doGoAway(H2_ERROR_FLOW_CONTROL_ERROR);
                return 0;
            }
            windowsSizeDiff = (int32_t)iEntryValue - m_iStreamOutInitWindowSize;
            m_iStreamOutInitWindowSize = iEntryValue ;
            break;
        case H2_SETTINGS_MAX_CONCURRENT_STREAMS:
            m_iMaxPushStreams = iEntryValue ;
            if (m_iMaxPushStreams == 0)
                m_iFlag |= H2_CONN_FLAG_NO_PUSH;
            break;
        case H2_SETTINGS_MAX_HEADER_LIST_SIZE:
            break;
        case H2_SETTINGS_ENABLE_PUSH:
            if (iEntryValue > 1)
                return LS_FAIL;
            if (!iEntryValue)
                m_iFlag |= H2_CONN_FLAG_NO_PUSH;
            break;
        default:
            break;
        }
    }
    m_iCurrentFrameRemain = 0;
    m_iFlag |= H2_CONN_FLAG_SETTING_RCVD;

    sendSettingsFrame();
    sendFrame0Bytes(H2_FRAME_SETTINGS, H2_FLAG_ACK, 0);

    if (windowsSizeDiff != 0)
    {
        StreamMap::iterator itn, it = m_mapStream.begin();
        for (; it != m_mapStream.end();)
        {
            it.second()->adjWindowOut(windowsSizeDiff);
            itn = m_mapStream.next(it);
            it = itn;
        }
    }
    return 0;
}


int H2Connection::resetStream(uint32_t id, H2Stream *pStream,
                              H2ErrorCode code)
{
    if (pStream)
        id = pStream->getStreamID();
    else
        pStream = findStream(id);
    if (id > 0)
        sendRstFrame(id, code);
    if (pStream)
    {
        pStream->setState(HIOS_RESET);
        recycleStream(id);
    }
    return 0;
}



int H2Connection::processWindowUpdateFrame(H2FrameHeader *pHeader)
{
    char sTemp[4];
    m_bufInput.moveTo(sTemp, 4);
    m_iCurrentFrameRemain -= 4;
    uint32_t id = pHeader->getStreamId();
    int32_t delta = beReadUint32((const unsigned char *)sTemp);
    delta &= 0x7FFFFFFFu;
    if (delta == 0)
    {
        LS_DBG_L(getLogSession(), "Session WINDOW_UPDATE ERROR: %d", delta);
        if (id)
            resetStream(id, NULL, H2_ERROR_PROTOCOL_ERROR);
        else
            doGoAway(H2_ERROR_PROTOCOL_ERROR);
        return 0;
    }


    if (id == 0)
    {
        // || (id == 0 && ((delta % 4) != 0))
        uint32_t tmpVal = m_iCurDataOutWindow + delta;
        if (tmpVal > 2147483647)  //2^31 -1
        {
            //sendRstFrame(pHeader->getStreamId(), H2_ERROR_PROTOCOL_ERROR);
            LS_DBG_L(getLogSession(),
                     "Session WINDOW_UPDATE ERROR: %d, window size: %d, total %d (m_iDataInWindow: %d)",
                     delta, m_iCurDataOutWindow, tmpVal, m_iDataInWindow);
            doGoAway(H2_ERROR_FLOW_CONTROL_ERROR);
            return 0;
        }
        LS_DBG_L(getLogSession(),
                 "Session WINDOW_UPDATE: %d, current window size: %d, new: %d",
                 delta, m_iCurDataOutWindow, tmpVal);
        if (m_iCurDataOutWindow <= 0 && tmpVal > 0)
        {
            m_iCurDataOutWindow = tmpVal;
            onWriteEx();
        }
        else
            m_iCurDataOutWindow = tmpVal;
    }
    else
    {
        H2Stream *pStream = findStream(id);
        if (pStream != NULL)
        {
            int ret = pStream->adjWindowOut(delta);
            if (ret < 0)
                resetStream(id, pStream, H2_ERROR_FLOW_CONTROL_ERROR);
            else if (pStream->getWindowOut() <= delta)
                pStream->continueWrite();

        }
        else
        {
            if (id > m_uiLastStreamId)
                return LS_FAIL;
            //sendRstFrame(id, H2_ERROR_STREAM_CLOSED);
        }

        //flush();
    }
    m_iCurrentFrameRemain = 0;
    return 0;
}


int H2Connection::processRstFrame(H2FrameHeader *pHeader)
{
    uint32_t streamID = pHeader->getStreamId();

    if (streamID == 0)
        return LS_FAIL;
    if (streamID % 2 != 0)
    {
        if (streamID > m_uiLastStreamId)
            return LS_FAIL;
    }
    else
    {
        if (streamID >= m_uiPushStreamId)
            return LS_FAIL;
    }

    H2Stream *pH2Stream = findStream(streamID);
    if (pH2Stream == NULL)
        return 0;

    unsigned char p[4];
    m_bufInput.moveTo((char *)p, 4);
    uint32_t errorCode = beReadUint32(p);
    LS_DBG_L(getLogSession(), "StreamID:%d processRstFrame, error code: %d",
             streamID, errorCode);
    pH2Stream->setFlag(HIO_FLAG_PEER_RESET, 1);
    recycleStream(streamID);
    return 0;
}


void H2Connection::skipRemainData()
{
    int len = m_bufInput.size();
    if (len > m_iCurrentFrameRemain)
        len = m_iCurrentFrameRemain;
    m_bufInput.pop_front(len);
    m_iCurrentFrameRemain -= len;

    m_iCurInBytesToUpdate += len;
}


int H2Connection::processDataFrame(H2FrameHeader *pHeader)
{
    uint32_t streamID = pHeader->getStreamId();

    printLogMsg(pHeader);
    if (streamID == 0 || streamID > m_uiLastStreamId)
        return LS_FAIL;

    H2Stream *pH2Stream = findStream(streamID);
    if (pH2Stream == NULL || pH2Stream->isPeerShutdown())
    {
        LS_DBG_L(getLogSession(), "stream: %p, isPeerShutdown: %d ",
                 pH2Stream, pH2Stream ? pH2Stream->isPeerShutdown() : 0);
        skipRemainData();
        resetStream(streamID, pH2Stream, H2_ERROR_STREAM_CLOSED);
        return 0;
    }

    uint8_t padLen = 0;
    if (pHeader->getFlags() & H2_FLAG_PADDED)
    {
        padLen = (uint8_t)(*(m_bufInput.begin()));
        if (m_iCurrentFrameRemain <= 1 + padLen)
        {
            resetStream(streamID, pH2Stream, H2_ERROR_PROTOCOL_ERROR);
            return 0;
        }
        m_bufInput.pop_front(1);
        //Do not pop_back right now since buf may have more data then this frame
        m_iCurrentFrameRemain -= (1 + padLen);
    }

    while (m_iCurrentFrameRemain > 0)
    {
        int len = m_bufInput.blockSize();
        if (len == 0)
            break;
        if (len > m_iCurrentFrameRemain)
            len = m_iCurrentFrameRemain;
        m_iCurrentFrameRemain -= len;
        if (pH2Stream->appendReqData(m_bufInput.begin(), len,
                                     m_iCurrentFrameRemain ? 0
                                     : pHeader->getFlags()) == LS_FAIL)
        {
            resetStream(streamID, pH2Stream, H2_ERROR_PROTOCOL_ERROR);
            return 0;
        }
        m_bufInput.pop_front(len);
        m_iCurInBytesToUpdate += len;
    }

    m_bufInput.pop_front(padLen);

    if (!pH2Stream->isPeerShutdown())
    {
        LS_DBG_H(getLogSession(),
                 "processDataFrame() ID: %d, input window size: %d ",
                 streamID, pH2Stream->getWindowIn());

        if (pH2Stream->getWindowIn() < m_iStreamInInitWindowSize / 2)
        {
            sendWindowUpdateFrame(streamID, m_iStreamInInitWindowSize / 2);
            pH2Stream->adjWindowIn(m_iStreamInInitWindowSize / 2);
        }
    }
    return 0;
}


int H2Connection::processContinuationFrame(H2FrameHeader *pHeader)
{
    if (m_iFlag & H2_CONN_FLAG_GOAWAY)
        return 0;
    uint32_t id = pHeader->getStreamId();
    if ((id != m_uiLastStreamId)
        || (m_iFlag & H2_CONN_HEADERS_START) == 0)
    {
        LS_DBG_L(getLogSession(),
                 "Received unexpected CONTINUATION frame, expect id: %d,"
                 " connection flag: %d",  m_uiLastStreamId, m_iFlag);
        return LS_FAIL;
    }
    if (pHeader->getFlags() & H2_FLAG_END_HEADERS)
        m_iFlag &= ~H2_CONN_HEADERS_START;

    return processReqHeader(pHeader->getFlags());
}

int H2Connection::processReqHeader(unsigned char iHeaderFlag)
{
    int iDatalen = (m_bufInput.size() < m_iCurrentFrameRemain) ?
                   (m_bufInput.size()) : (m_iCurrentFrameRemain);
    if (iDatalen <= 0)
        return 0;

    //Check if we need to move the buffer to stream bufinflat
    bool needToMove = false;
    int bufPart1Len = m_bufInput.blockSize();
    if ((iHeaderFlag & H2_FLAG_END_HEADERS) == 0
        || iDatalen > bufPart1Len
        || m_bufInflate.size() > 0)
    {
        needToMove = true;
        if (iDatalen > bufPart1Len)
        {
            m_bufInflate.append(m_bufInput.begin(), bufPart1Len);
            m_bufInput.pop_front(bufPart1Len);
            m_bufInflate.append(m_bufInput.begin(), iDatalen - bufPart1Len);
            m_bufInput.pop_front(iDatalen - bufPart1Len);
        }
        else
        {
            m_bufInflate.append(m_bufInput.begin(), iDatalen);
            m_bufInput.pop_front(iDatalen);
        }
        m_iCurrentFrameRemain -= iDatalen;
    }

    if (iHeaderFlag & H2_FLAG_END_HEADERS)
    {
        unsigned char *pSrc = NULL;
        AutoBuf tmpBuf;
        if (needToMove)
        {
            tmpBuf.swap(m_bufInflate);
            pSrc = (unsigned char *)tmpBuf.begin();
            iDatalen = tmpBuf.size();
        }
        else
            pSrc = (unsigned char *)m_bufInput.begin();
        return decodeHeaders(pSrc, iDatalen, iHeaderFlag);
    }
    else
        return 0;
}


int H2Connection::decodeHeaders(unsigned char *pSrc, int length,
                                unsigned char iHeaderFlag)
{
    char method[10] = {0};
    int methodLen = 0;
    char *uri = NULL;
    int uriLen = 0;

    unsigned char *bufEnd = pSrc + length;
    int rc = decodeData(pSrc, bufEnd, method, &methodLen, &uri, &uriLen);
    if (rc < 0)
    {
        if (uri)
            free(uri);
        LS_DBG_L(getLogSession(), "decodeData() failure, return %d", rc);
        doGoAway(H2_ERROR_COMPRESSION_ERROR);
        return LS_FAIL;
    }

    H2Stream *pStream = NULL;
    pStream = getNewStream(iHeaderFlag);
    if (!pStream)
    {
        sendRstFrame(m_uiLastStreamId, H2_ERROR_PROTOCOL_ERROR);
        return 0;
    }

    appendReqHeaders(pStream, method, methodLen, uri, uriLen);
    pStream->appendInputData("\r\n", 2);
    free(uri);

    pStream->onInitConnected();

    if (pStream->getState() != HIOS_CONNECTED)
        recycleStream(pStream->getStreamID());

    return 0;
}

int H2Connection::processHeadersFrame(H2FrameHeader *pHeader)
{
    uint32_t id = pHeader->getStreamId();
    if (m_iFlag & H2_CONN_FLAG_GOAWAY)
        return 0;

    if (id == 0)
    {
        LS_INFO(getLogSession(), "Protocol error, HEADER frame STREAM ID is 0");
        return LS_FAIL;
    }

    if (id % 2 == 0)
    {
        LS_DBG_L(getLogSession(), "invalid HEADER frame id %d ",
                    id);
        return LS_FAIL;
    }
    
    if (id <= m_uiLastStreamId)
    {
        H2Stream *pStream = findStream(id);
        if (pStream)
        {
            H2ErrorCode ret = H2_ERROR_PROTOCOL_ERROR;
            if (pStream->isPeerShutdown())
                ret = H2_ERROR_STREAM_CLOSED;
            resetStream(id, pStream, ret);
        }
        LS_INFO(getLogSession(), "Protocol error, STREAM ID: %d is less the"
                " previously received stream ID: %d, go away!",
                id, m_uiLastStreamId);
        return LS_FAIL;
    }
    m_uiLastStreamId = id;

    unsigned char iHeaderFlag = pHeader->getFlags();

    unsigned char *pSrc = (unsigned char *)m_bufInput.begin();
    if (iHeaderFlag & H2_FLAG_PADDED)
    {
        uint8_t padLen = *pSrc;
        if (m_iCurrentFrameRemain <= 1 + padLen)
            return H2_ERROR_PROTOCOL_ERROR;
        m_bufInput.pop_front(1);
        m_bufInput.pop_back(padLen);
        m_iCurrentFrameRemain -= padLen + 1;
    }

    if (iHeaderFlag & H2_FLAG_PRIORITY)
    {
        pSrc = (unsigned char *)m_bufInput.begin();
        m_priority.m_exclusive = *pSrc >> 7;
        m_priority.m_dependStreamId = beReadUint32((const unsigned char *)pSrc) &
                                      0x7FFFFFFFu;
        if (m_priority.m_dependStreamId == id)
            return H2_ERROR_PROTOCOL_ERROR;

        //Add one to the value to obtain a weight between 1 and 256.
        m_priority.m_weight = *(pSrc + 4) + 1;
        m_bufInput.pop_front(5);
        m_iCurrentFrameRemain -= 5;
    }
    else
        memset(&m_priority, 0, sizeof(m_priority));

    if ((iHeaderFlag & H2_FLAG_END_HEADERS) == 0)
        m_iFlag |= H2_CONN_HEADERS_START;

    m_bufInflate.clear();
    return processReqHeader(iHeaderFlag);
}


int H2Connection::decodeData(unsigned char *pSrc, unsigned char *bufEnd,
                             char *method, int *methodLen, char **uri,
                             int *uriLen)
{
    int rc, n = 0;
    m_bufInflate.clear();

    char out[16 * 1024];
    uint16_t name_len = 0 ;
    uint16_t val_len = 0;
    AutoBuf cookieStr(0);
    int regular_header = 0;

    bool authority = false;
    bool scheme = false;
    bool error = false;
    while ((rc = m_hpack.decHeader(pSrc, bufEnd, out, out + sizeof(out),
                                   name_len, val_len)) > 0)
    {
        char *name = out;
        char *val = name + name_len;

        if (name[0] == ':')
        {
            if (regular_header)
                error = true;
            name_len = 0;
            if (memcmp(name, ":authority", 10) == 0)
            {
                if (authority)
                {
                    error = true;
                    break;
                }
                name = (char *)"host";
                name_len = 4;
                authority = true;
            }
            else if (memcmp(name, ":method", 7) == 0)
            {
                //If second time have the :method, ERROR
                if (*methodLen)
                {
                    error = true;
                    break;
                }

                if (val_len < 10 && val_len > 2)
                {
                    strncpy(method, val, val_len);
                    *methodLen = val_len;
                }
            }
            else if (memcmp(name, ":path", 5) == 0)
            {
                //If second time have the :path, ERROR
                if (*uri)
                {
                    error = true;
                    break;
                }
                *uri = strndup(val, val_len);
                *uriLen = val_len;
            }
            else if (memcmp(name, ":scheme", 7) == 0)
            {
                if (scheme)
                {
                    error = true;
                    break;
                }
                scheme = true;
                //Do nothing
                //We set to (char *)"HTTP/1.1"
            }
            else
                error = true;
        }
        else
        {
            regular_header = true;
            if (name_len == 6 && memcmp(name, "cookie", 6) == 0)
            {
                if (cookieStr.size() > 0)
                    cookieStr.append("; ", 2);

                cookieStr.append(val, val_len);
                name_len = 0;
            }
            else if (name_len == 2 && memcmp(name, "te", 2) == 0)
            {
                if (val_len != 8 || strncasecmp("trailers", val, 8) != 0)
                    return LS_FAIL;
            }
        }

        if (name_len > 0)
        {
            n += name_len + val_len + 4;
            if (n >= MAX_HTTP2_HEADERS_SIZE)
                return LS_FAIL;
            m_bufInflate.append(name, name_len);
            m_bufInflate.append(": ", 2);
            m_bufInflate.append(val, val_len);
            m_bufInflate.append("\r\n", 2);
        }
    }

    if (error || rc < 0 || methodLen == 0 || uriLen == 0 || *uri == NULL)
    {
        if (*uri)
        {
            free(*uri);
            *uri = NULL;
        }
        return LS_FAIL;
    }

    /*TODO: we suppose cookies are in one frame, if in another frame, it will
     * create multi-line cookie in req header.
     */
    if (cookieStr.size() > 0)
    {
        n += (6 + cookieStr.size() + 4);
        if (n >= MAX_HTTP2_HEADERS_SIZE)
            return LS_FAIL;
        m_bufInflate.append("cookie", 6);
        m_bufInflate.append(": ", 2);
        m_bufInflate.append(cookieStr.begin(), cookieStr.size());
        m_bufInflate.append("\r\n", 2);
    }

    return n;
}


int H2Connection::appendReqHeaders(H2Stream *pStream, char *method,
                                   int methodLen, char *uri, int uriLen)
{
    if (method && methodLen && uri && uriLen)
    {
        pStream->appendInputData(method, methodLen);
        pStream->appendInputData(" ", 1);
        pStream->appendInputData(uri, uriLen);
        pStream->appendInputData(" HTTP/1.1\r\n", 11);
    }

    pStream->appendInputData(m_bufInflate.begin(), m_bufInflate.size());

    return 0;
}


H2Stream *H2Connection::getNewStream(uint8_t ubH2_Flags)
{
    H2Stream *pStream;
    HioHandler *pSession = HioHandlerFactory::getHioHandler(HIOS_PROTO_HTTP);
    if (!pSession)
        return NULL;

    LS_DBG_H(getLogger(),
             "[%s-%d] getNewStream(), stream map size: %d, shutdown streams: %d, flag: %d ",
             getLogId(), m_uiLastStreamId, (int)m_mapStream.size(),
             m_uiShutdownStreams, (int)ubH2_Flags);

    if ((int)m_mapStream.size() - (int)m_uiShutdownStreams - m_iCurPushStreams 
            >= m_iServerMaxStreams)
        return NULL;

    pStream = new H2Stream();
    m_mapStream.insert((void *)(long)m_uiLastStreamId, pStream);
    if (m_tmIdleBegin)
        m_tmIdleBegin = 0;
    pStream->init(m_uiLastStreamId, this, pSession, &m_priority);
    pStream->setProtocol(HIOS_PROTO_HTTP2);
    int flag = (ubH2_Flags & H2_CTRL_FLAG_FIN) | HIO_FLAG_FLOWCTRL;
    if (!(m_iFlag & H2_CONN_FLAG_NO_PUSH))
        flag |= HIO_FLAG_PUSH_CAPABLE;
    pStream->setFlag(flag, 1);
    return pStream;
}


int H2Connection::h2cUpgrade(HioHandler *pSession)
{
    assert(pSession != NULL);
    H2Stream *pStream = new H2Stream();
    uint32_t uiStreamID = 1;  //Through upgrade h2c, it is 1.
    m_mapStream.insert((void *)(long)uiStreamID, pStream);
    pStream->init(uiStreamID, this, pSession);
    pStream->setProtocol(HIOS_PROTO_HTTP2);
    int flag = HIO_FLAG_FLOWCTRL;
    if (!(m_iFlag & H2_CONN_FLAG_NO_PUSH))
        flag |= HIO_FLAG_PUSH_CAPABLE;
    pStream->setFlag(flag, 1);
    onInitConnected();
    setPendingWrite();
    getBuf()->append(s_h2sUpgradeResponse, sizeof(s_h2sUpgradeResponse) - 1);
    sendSettingsFrame();
    return pStream->onInitConnected(true);
}


void H2Connection::recycleStream(uint32_t uiStreamID)
{
    StreamMap::iterator it = m_mapStream.find((void *)(long) uiStreamID);
    if (it == m_mapStream.end())
        return;
    recycleStream(it);
}


void H2Connection::recycleStream(StreamMap::iterator it)
{
    H2Stream *pH2Stream = it.second();
    
    if (pH2Stream->getStreamID() % 2 == 0)
        --m_iCurPushStreams;

    m_mapStream.erase(it);
    pH2Stream->close();
    m_priQue[pH2Stream->getPriority()].remove(pH2Stream);
    if (pH2Stream->getHandler())
        pH2Stream->getHandler()->recycle();

    LS_DBG_H(getLogger(), "[%s-%d] recycleStream(), stream map size: %zd ",
             getLogId(), pH2Stream->getStreamID(), m_mapStream.size());
    //H2StreamPool::recycle( pH2Stream );
    delete pH2Stream;
}



int H2Connection::sendDataFrame(uint32_t uiStreamId, int flag,
                                IOVec *pIov, int total)
{
    int ret = 0;
    H2FrameHeader header(total, H2_FRAME_DATA, flag, uiStreamId);

    if (m_buf.empty() && !getStream()->isWantWrite())
        getStream()->continueWrite();

    m_buf.append((char *)&header, 9);
    if (pIov)
        ret = cacheWritev(*pIov, total);
    if (ret != -1)
        m_iCurDataOutWindow -= total;
    return ret;
}


int H2Connection::sendDataFrame(uint32_t uiStreamId, int flag,
                                const char *pBuf, int len)
{
    int ret = 0;
    H2FrameHeader header(len, H2_FRAME_DATA, flag, uiStreamId);

    if (m_buf.empty() && !getStream()->isWantWrite())
        getStream()->continueWrite();

    m_buf.append((char *)&header, 9);
    if (pBuf)
        ret = cacheWrite(pBuf, len);
    if (ret != -1)
        m_iCurDataOutWindow -= ret;
    return ret;
}



int H2Connection::sendFrame8Bytes(H2FrameType type, uint32_t uiStreamId,
                                  uint32_t uiVal1, uint32_t uiVal2)
{
    getBuf()->guarantee(17);
    appendCtrlFrameHeader(type, 8, 0, uiStreamId);
    appendNbo4Bytes(getBuf(), uiVal1);
    appendNbo4Bytes(getBuf(), uiVal2);
    LS_DBG_H(getLogger(), "[%s-%d] send %s frame, stream: %d, value: %d",
             getLogId(), uiStreamId, getH2FrameName(type), uiVal1, uiVal2);
    return 0;
}


int H2Connection::sendFrame4Bytes(H2FrameType type, uint32_t uiStreamId,
                                  uint32_t uiVal1)
{
    getBuf()->guarantee(13);
    appendCtrlFrameHeader(type, 4, 0, uiStreamId);

    appendNbo4Bytes(getBuf(), uiVal1);
    LS_DBG_H(getLogger(), "[%s-%d] send %s frame, value: %d", getLogId(),
             uiStreamId, getH2FrameName(type), uiVal1);
    return 0;
}


int H2Connection::sendFrame0Bytes(H2FrameType type, unsigned char flags,
                                  uint32_t uiStreamId)
{
    getBuf()->guarantee(9);
    appendCtrlFrameHeader(type, 0, flags, uiStreamId);
    LS_DBG_H(getLogger(), "[%s-%d] send %s frame, with Flag: %d",
             getLogId(), uiStreamId, getH2FrameName(type), flags);
    return 0;
}


int H2Connection::sendPingFrame(uint8_t flags, uint8_t *pPayload)
{
    //Server initiate a Ping
    getBuf()->guarantee(17);
    appendCtrlFrameHeader(H2_FRAME_PING, 8, flags);
    getBuf()->append((char *)pPayload, H2_PING_FRAME_PAYLOAD_SIZE);
    return 0;
}


int H2Connection::sendSettingsFrame()
{
    if (m_iFlag & H2_CONN_FLAG_SETTING_SENT)
        return 0;

    static char s_settings[][6] =
    {
        //{0x00, 0x01, 0x00, 0x00, 0x10, 0x00 },
        {0x00, 0x03, 0x00, 0x00, 0x00, 0x64 },
        {0x00, 0x04, 0x00, 0x01, 0x00, 0x00 },
        {0x00, 0x05, 0x00, 0x00, 0x40, 0x00 },
        //{0x00, 0x06, 0x00, 0x00, 0x40, 0x00 },
    };

    getBuf()->guarantee(27);
    appendCtrlFrameHeader(H2_FRAME_SETTINGS, 18);
    getBuf()->append((char *)s_settings, 18);
    LS_DBG_H(getLogSession(), "Send SETTING frame, MAX_CONCURRENT_STREAMS: %d,"
             " INITIAL_WINDOW_SIZE: %d", m_iServerMaxStreams,
             m_iStreamInInitWindowSize);
    m_iFlag |= H2_CONN_FLAG_SETTING_SENT;

    sendWindowUpdateFrame(0, H2_FCW_INIT_SIZE * 3);
    m_iDataInWindow += H2_FCW_INIT_SIZE * 3;

    return 0;
}


int H2Connection::processPingFrame(H2FrameHeader *pHeader)
{
    struct timeval CurTime;
    long msec;
    if (pHeader->getStreamId() != 0)
    {
        //doGoAway(H2_ERROR_PROTOCOL_ERROR);
        LS_DBG_L(getLogSession(), "Invalid PING frame id %d",
                 pHeader->getStreamId());
        return LS_FAIL;
    }

    if (!(pHeader->getFlags() & H2_FLAG_ACK) || m_timevalPing.tv_sec == 0)
    {
        uint8_t payload[H2_PING_FRAME_PAYLOAD_SIZE];
        m_bufInput.moveTo((char *)payload, H2_PING_FRAME_PAYLOAD_SIZE);
        m_iCurrentFrameRemain -= H2_PING_FRAME_PAYLOAD_SIZE;
        if (pHeader->getFlags() & H2_FLAG_ACK)
        {
            LS_DBG_L(getLogSession(), "Unexpected PING frame, %.8s", payload);
            return 0;
        }
        return sendPingFrame(H2_FLAG_ACK, payload);
    }

    gettimeofday(&CurTime, NULL);
    msec = (CurTime.tv_sec - m_timevalPing.tv_sec) * 1000;
    msec += (CurTime.tv_usec - m_timevalPing.tv_usec) / 1000;
    LS_DBG_H(getLogSession(), "Received PING, Round trip "
             "times=%ld milli-seconds", msec);
    m_timevalPing.tv_sec = 0;
    return 0;
}


H2Stream *H2Connection::findStream(uint32_t uiStreamID)
{
    StreamMap::iterator it = m_mapStream.find((void *)(long)uiStreamID);
    if (it == m_mapStream.end())
        return NULL;
    return it.second();
}


int H2Connection::flush()
{
    BufferedOS::flush();
    if (!isEmpty())
        getStream()->continueWrite();
    getStream()->flush();
    return LS_DONE;
}


int H2Connection::onCloseEx()
{
    if (getStream()->isReadyToRelease())
        return 0;
    LS_DBG_L(getLogSession(), "H2Connection::onCloseEx()");

    getStream()->tobeClosed();
    releaseAllStream();
    return 0;
};


int H2Connection::onTimerEx()
{
    int result = 0;
    if (m_iFlag & H2_CONN_FLAG_GOAWAY)
        result = releaseAllStream();
    else
        result = timerRoutine();
    return result;
}


int H2Connection::processGoAwayFrame(H2FrameHeader *pHeader)
{
    if (!(m_iFlag & H2_CONN_FLAG_GOAWAY))
    {
        doGoAway((pHeader->getStreamId() != 0) ?
                 H2_ERROR_PROTOCOL_ERROR :
                 H2_ERROR_NO_ERROR);
    }
    m_iFlag |= (short)H2_CONN_FLAG_GOAWAY;

    onCloseEx();
    return LS_OK;
}


int H2Connection::doGoAway(H2ErrorCode status)
{
    LS_DBG_L(getLogSession(), "H2Connection::doGoAway(), status = %d",
             status);
    sendGoAwayFrame(status);
    releaseAllStream();
    getStream()->tobeClosed();
    getStream()->continueWrite();
    return 0;
}


int H2Connection::sendGoAwayFrame(H2ErrorCode status)
{
    sendFrame8Bytes(H2_FRAME_GOAWAY, 0, m_uiLastStreamId, status);
    flush();
    return 0;
}


int H2Connection::releaseAllStream()
{
    StreamMap::iterator itn, it = m_mapStream.begin();
    for (; it != m_mapStream.end();)
    {
        itn = m_mapStream.next(it);
        recycleStream(it);
        it = itn;
    }
    getStream()->handlerReadyToRelease();
    return 0;
}


int H2Connection::timerRoutine()
{
    int stuckRead = 0;
    StreamMap::iterator itn, it = m_mapStream.begin();
    for (; it != m_mapStream.end();)
    {
        itn = m_mapStream.next(it);
        it.second()->onTimer();
        if (it.second()->getState() != HIOS_CONNECTED)
            recycleStream(it);
        else if (it.second()->isStuckOnRead())
            ++stuckRead;
        it = itn;
    }
    if (m_mapStream.size() == 0)
    {

        if (m_tmIdleBegin == 0)
            m_tmIdleBegin = DateTime::s_curTime;
        else
        {
            int idle = DateTime::s_curTime - m_tmIdleBegin;
            if (idle > HttpServerConfig::getInstance().getSpdyKeepaliveTimeout())
            {
                LS_DBG_L(getLogSession(),
                         "Session idle for %d seconds, GOAWAY.", idle);

                doGoAway(H2_ERROR_NO_ERROR);
            }
        }
    }
    else
    {
        if (stuckRead > 0)
        {
            if (m_timevalPing.tv_sec == 0)
            {
                LS_DBG_L(getLogSession(),
                         "Send PING to check if peer is still alive.");
                sendPingFrame(0, (uint8_t *)"RUALIVE?");
                m_timevalPing.tv_sec = DateTime::s_curTime;
                m_timevalPing.tv_usec = DateTime::s_curTimeUs;

            }
            else if (DateTime::s_curTime - m_timevalPing.tv_sec > 20)
            {
                LS_DBG_L(getLogSession(), "PING timeout.");
                doGoAway(H2_ERROR_PROTOCOL_ERROR);
            }
        }
        m_tmIdleBegin = 0;
    }

    return 0;
}


#define H2_TMP_HDR_BUFF_SIZE 65536
#define MAX_LINE_COUNT_OF_MULTILINE_HEADER  100

int H2Connection::encodeHeaders(HttpRespHeaders *pRespHeaders,
                                unsigned char *buf, int maxSize)
{
    unsigned char *pCur = buf;
    unsigned char *pBufEnd = pCur + maxSize;

    iovec iov[MAX_LINE_COUNT_OF_MULTILINE_HEADER];
    iovec *pIov;
    iovec *pIovEnd;
    int count;
    char *key;
    int keyLen;

    char *p = (char *)HttpStatusCode::getInstance().getCodeString(
                  pRespHeaders->getHttpCode()) + 1;
    pCur = m_hpack.encHeader(pCur, pBufEnd, (char *)":status", 7, p, 3, 0);

    pRespHeaders->dropConnectionHeaders();

    for (int pos = pRespHeaders->HeaderBeginPos();
         pos != pRespHeaders->HeaderEndPos();
         pos = pRespHeaders->nextHeaderPos(pos))
    {
        key = NULL;
        keyLen = 0;
        count = pRespHeaders->getHeader(pos, &key, &keyLen, iov,
                                        MAX_LINE_COUNT_OF_MULTILINE_HEADER);

        if (count <= 0)
            continue;

        char *p = key;
        char *pKeyEnd = key + keyLen;
        //to lowercase
        while (p < pKeyEnd)
        {
            *p = tolower(*p);
            ++p;
        }

        if (keyLen + 8 > pBufEnd - pCur)
            return LS_FAIL;

        pIov = iov;
        pIovEnd = &iov[count];
        for (pIov = iov; pIov < pIovEnd; ++pIov)
            pCur = m_hpack.encHeader(pCur, pBufEnd, key, keyLen,
                                     (char *)pIov->iov_base, pIov->iov_len, 0);
    }

    return pCur - buf;
}


int H2Connection::sendRespHeaders(HttpRespHeaders *pRespHeaders,
                                  uint32_t uiStreamID, uint8_t flag)
{
    LS_DBG_H(getLogger(), "[%s-%d] sendRespHeaders()",
             getLogId(), uiStreamID);

    unsigned char achHdrBuf[H2_TMP_HDR_BUFF_SIZE];
    int rc = encodeHeaders(pRespHeaders, achHdrBuf, H2_TMP_HDR_BUFF_SIZE);
    if (rc < 0)
        return LS_FAIL;
    return sendHeaderContFrame(uiStreamID, flag, H2_FRAME_HEADERS, 
                               (const char *)achHdrBuf, rc);
}

int H2Connection::sendHeaderContFrame(uint32_t uiStreamID, uint8_t flag, 
                                      H2FrameType type, const char *pBuf, int size)
{
    const char *p = pBuf;
    int frameSize;
    while(size > 0)
    {
        if (size > m_iPeerMaxFrameSize)
        {
            frameSize = m_iPeerMaxFrameSize;
            size -= m_iPeerMaxFrameSize;
        }
        else
        {
            frameSize = size;
            size = 0;
            flag |= H2_FLAG_END_HEADERS;
        }
        getBuf()->guarantee(frameSize + 9);
        appendCtrlFrameHeader(type, frameSize, flag, uiStreamID);   //
        getBuf()->append((const char *)p, frameSize);
        if (size > 0)
        {
            p += frameSize;
            type = H2_FRAME_CONTINUATION;
            flag = 0;
        }
    }
    return 0;
}


int H2Connection::sendPushPromise(uint32_t streamId, uint32_t promise_streamId, 
                                  ls_str_t* pUrl, ls_str_t* pHost, 
                                  ls_strpair_t *headers)
{
    unsigned char achHdrBuf[H2_TMP_HDR_BUFF_SIZE];
    unsigned char *pCur = achHdrBuf;
    unsigned char *pBufEnd = achHdrBuf + H2_TMP_HDR_BUFF_SIZE;
    uint32_t sid = htonl(promise_streamId);
    memcpy(pCur, &sid, 4);
    pCur += 4;
    pCur = m_hpack.encHeader(pCur, pBufEnd, ":method", 7, "GET", 3, 0);
    pCur = m_hpack.encHeader(pCur, pBufEnd, ":path",   5, pUrl->ptr, 
                             pUrl->len, 0);
    pCur = m_hpack.encHeader(pCur, pBufEnd, ":authority", 10, pHost->ptr, 
                             pHost->len, 0);
    pCur = m_hpack.encHeader(pCur, pBufEnd, ":scheme", 7, "https", 5, 0);
    
//     if (etag)
//         pCur = m_hpack.encHeader(pCur, pBufEnd, "if-match", 8, etag->ptr, 
//                              etag->len, 0);
//     if (lastmod)
//         pCur = m_hpack.encHeader(pCur, pBufEnd, "if-modified-since", 17,
//                                  lastmod->ptr, lastmod->len, 0);
    if (headers)
    {
        while(headers->key.ptr)
        {
            pCur = m_hpack.encHeader(pCur, pBufEnd, 
                                     headers->key.ptr,
                                     headers->key.len,
                                     headers->val.ptr,
                                     headers->val.len, 0);

            ++headers;
        }
    }
    
    int total = pCur - achHdrBuf;
    return sendHeaderContFrame(streamId, 0, H2_FRAME_PUSH_PROMISE, 
                               (const char *)achHdrBuf, total);
    return 0;
}


H2Stream* H2Connection::createPushStream(uint32_t pushStreamId, ls_str_t* pUrl, 
                                    ls_str_t* pHost, ls_strpair_t* headers)
{
    H2Stream *pStream;
    HioHandler *pSession = HioHandlerFactory::getHioHandler(HIOS_PROTO_HTTP);
    if (!pSession)
        return NULL;
    pStream = new H2Stream();
    m_mapStream.insert((void *)(long)pushStreamId, pStream);
    if (m_tmIdleBegin)
        m_tmIdleBegin = 0;
    pStream->init(pushStreamId, this, pSession, NULL);
    pStream->setPriority(HIO_PRIORITY_PUSH);
    pStream->setProtocol(HIOS_PROTO_HTTP2);
    pStream->setFlag(HIO_FLAG_PEER_SHUTDOWN | HIO_FLAG_FLOWCTRL | HIO_FLAG_INIT_PUSH
                     | HIO_FLAG_WANT_WRITE, 1);

    pStream->appendInputData("GET ", 4);
    pStream->appendInputData(pUrl->ptr, pUrl->len);
    pStream->appendInputData(" HTTP/1.1\r\n", 11);
    pStream->appendInputData("host: ", 6);
    pStream->appendInputData(pHost->ptr, pHost->len);
    pStream->appendInputData("\r\n", 2);

    if (headers)
    {
        while(headers->key.ptr)
        {
            pStream->appendInputData(headers->key.ptr, headers->key.len);
            pStream->appendInputData(": ", 2);
            pStream->appendInputData(headers->val.ptr, headers->val.len);
            pStream->appendInputData("\r\n", 2);

            ++headers;
        }
    }
    pStream->appendInputData("\r\n", 2);

    m_priQue[pStream->getPriority()].append(pStream);
    ++m_iCurPushStreams;
    
    return pStream;
}



int H2Connection::pushPromise(uint32_t streamId, ls_str_t* pUrl, 
                              ls_str_t* pHost, ls_strpair_t *headers)
{
    if (m_iCurPushStreams >= m_iMaxPushStreams)
    {
        LS_DBG_L(getLogSession(),
                    "reached max concurrent Server PUSH streams limit, skip push.");
        return -1; 
    }
    uint32_t pushStreamId = m_uiPushStreamId;
    m_uiPushStreamId += 2;
    int ret = sendPushPromise(streamId, pushStreamId, pUrl, pHost, 
                              headers);
    if (ret == 0)
        if (createPushStream(pushStreamId, pUrl, pHost, headers) == NULL)
            ret = -1;
    return ret;
}


void H2Connection::add2PriorityQue(H2Stream *pH2Stream)
{
    if (pH2Stream->next())
        pH2Stream->remove();
    LS_DBG_H(getLogger(), "[%s-%d] add to priority queue: %d",
             getLogId(), pH2Stream->getStreamID(), pH2Stream->getPriority());

    m_priQue[pH2Stream->getPriority()].append(pH2Stream);
    m_iFlag |= H2_CONN_FLAG_WAIT_PROCESS;
    if (m_iCurDataOutWindow > 0 && !getStream()->isWantWrite())
        getStream()->continueWrite();
}


int H2Connection::onWriteEx()
{
    H2Stream *pH2Stream = NULL;
    int wantWrite = 0;


    LS_DBG_H(getLogSession(),
             "onWriteEx() state: %d, output buffer size = %d, Data Out Window: %d",
             m_iState, getBuf()->size(), m_iCurDataOutWindow);
    if (getBuf()->size() > 4096)
    {
        flush();
        if (!isEmpty())
            return 0;
    }
    if (getStream()->canWrite() & HIO_FLAG_BUFF_FULL)
        return 0;

    TDLinkQueue<H2Stream> *pQue = &m_priQue[0];
    TDLinkQueue<H2Stream> *pEnd = &m_priQue[H2_STREAM_PRIORITYS];


    for (; pQue < pEnd && m_iCurDataOutWindow > 0; ++pQue)
    {
        if (pQue->empty())
            continue;
        int count = pQue->size();
        while (count-- > 0 && m_iCurDataOutWindow > 0
               && (pH2Stream = pQue->pop_front()) != NULL)
        {
            if (pH2Stream->getFlag(HIO_FLAG_INIT_PUSH))
            {
                pH2Stream->setFlag(HIO_FLAG_INIT_PUSH, 0);
                pH2Stream->onInitConnected();
            }
            if (pH2Stream->isWantWrite())
            {
                pH2Stream->onWrite();
                if (pH2Stream->isWantWrite() && (pH2Stream->getWindowOut() > 0))
                {
                    ++wantWrite;
                    if (!pH2Stream->next())
                        m_priQue[pH2Stream->getPriority()].append(pH2Stream);
                }
            }
            if (pH2Stream->getState() != HIOS_CONNECTED)
                recycleStream(pH2Stream->getStreamID());
        }
        if (getStream()->canWrite() & HIO_FLAG_BUFF_FULL)
            return 0;
        if (wantWrite > 0)
            break;
    }

    if (!isEmpty())
        flush();

    if ((wantWrite == 0 || m_iCurDataOutWindow <= 0) && isEmpty())
        getStream()->suspendWrite();
    return 0;
}


void H2Connection::recycle()
{
    LS_DBG_H(getLogSession(), "H2Connection::recycle()");
    if (m_mapStream.size() > 0)
        releaseAllStream();
    detachStream();
    delete this;
}


NtwkIOLink *H2Connection::getNtwkIoLink()
{
    return getStream()->getNtwkIoLink();
}

