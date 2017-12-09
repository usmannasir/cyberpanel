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
#ifndef SPDYCONNECTION_H
#define SPDYCONNECTION_H

#include "protocoldef.h"
#include "spdyprotocol.h"
#include "spdyzlibfilter.h"

#include <lsdef.h>
#include <edio/bufferedos.h>
#include <http/hiostream.h>
#include <util/autobuf.h>
#include <util/dlinkqueue.h>
#include <util/ghash.h>

#include <limits.h>
#include <sys/time.h>

#define SPDY_CONN_FLAG_GOAWAY           (1<<0)
#define SPDY_CONN_FLAG_FLOW_CTRL        (1<<1)
#define SPDY_CONN_FLAG_WAIT_PROCESS     (1<<2)

#define SPDY_STREAM_PRIORITYS          8

class SpdyStream;

class SpdyConnection: public HioHandler, public BufferedOS
{
public:
    SpdyConnection();
    virtual ~SpdyConnection();

    static HioHandler *get(HiosProtocol proto);

    int onReadEx();
    int onReadEx2();
    int onWriteEx();

    int isOutBufFull() const
    {   return ((m_iCurDataOutWindow <= 0) || (getBuf()->size() >= 65535)); }

    int flush();

    int onCloseEx();

    void recycle();

    //Following functions are just placeholder

    //Placeholder
    int init(HiosProtocol ver);
    int onInitConnected();

    int onTimerEx();
    void add2PriorityQue(SpdyStream *pSpdyStream);
    int timerRoutine();

    void continueWrite()
    {   getStream()->continueWrite();   }

    int32_t getStreamInInitWindowSize() const
    {   return m_iStreamInInitWindowSize;    }

    int32_t getStreamOutInitWindowSize() const
    {   return m_iStreamOutInitWindowSize;    }

    int32_t getCurDataOutWindow() const
    {   return m_iCurDataOutWindow;         }

    int appendPing(uint32_t uiStreamID)
    {   return sendFrame4Bytes(SPDY_FRAME_PING, uiStreamID);  }

    int addBufToGzip(int iSpdyVer, struct iovec *iov, int iov_count,
                     LoopBuf *buf, int &total, int flushWhenEnd = 0);
    int addBufToGzip(int iSpdyVer, const char *s, int len, LoopBuf *buf,
                     int &total);
    int  sendRespHeaders(HttpRespHeaders *pRespHeaders, uint32_t uiStreamID,
                         int isNoBody);

    int sendWindowUpdateFrame(uint32_t id, int32_t delta)
    {
        return sendFrame8Bytes(SPDY_FRAME_WINDOW_UPDATE,
                               id, delta);
    }

    int sendRstFrame(uint32_t uiStreamID, SpdyRstErrorCode code)
    {
        return sendFrame8Bytes(SPDY_FRAME_RST_STREAM, uiStreamID, code);
    }
    int sendFinFrame(uint32_t uiStreamID)
    {
        char achHeader[8];
        uint32_t *pHeader = (uint32_t *)achHeader;
        *pHeader = htonl(uiStreamID);
        achHeader[4] = 1;
        achHeader[5] = 0;
        achHeader[6] = 0;
        achHeader[7] = 0;
        return cacheWrite(achHeader, sizeof(achHeader));
    }

    void dataFrameSent(int bytes)
    {
        if (isFlowCtrl())
            m_iCurDataOutWindow -= bytes;
    }


    void enableSessionFlowCtrl()    {   m_flag |= SPDY_CONN_FLAG_FLOW_CTRL;  }
    short isFlowCtrl() const    {   return m_flag & SPDY_CONN_FLAG_FLOW_CTRL;  }

    int getAllowedDataSize(int wanted) const
    {
        if (wanted > m_iCurDataOutWindow)
            wanted = m_iCurDataOutWindow;
        if (m_buf.size() > 8192 && wanted > 2048)
            wanted = 2048;
        return wanted;
    }

    void recycleStream(uint32_t uiStreamID);
    static void replaceZero(char *pValue, int ilength);
    uint16_t getEvents()
    {   return getStream()->getEvents();    }
    int isFromLocalAddr() const
    {   return getStream()->isFromLocalAddr();  }

    NtwkIOLink *getNtwkIoLink();

private:
    typedef THash< SpdyStream * > StreamMap;

    SpdyStream *findStream(uint32_t uiStreamID);
    int releaseAllStream();

    int processControlFrame(SpdyFrameHeader *pHeader);
    void printLogMsg(SpdyFrameHeader *pHeader);

    int checkReqline(char *pName, int ilength, uint8_t &flags);

    int processDataFrame(SpdyFrameHeader *pHeader);
    int parseHeaders(char *pHeader, int ilength, int &NVPairCnt);
    SpdyStream *getNewStream(uint32_t uiStreamID,
                             int iPriority, uint8_t ubSpdy_Flags);

    int processSettingFrame(SpdyFrameHeader *pHeader);
    int processSynStreamFrame(SpdyFrameHeader *pHeader);
    int processHeaderFrame(SpdyFrameHeader *pHeader);
    int processPingFrame(SpdyFrameHeader *pHeader);
    int processGoAwayFrame(SpdyFrameHeader *pHeader);
    int processRstFrame(SpdyFrameHeader *pHeader);
    int processWindowUpdateFrame(SpdyFrameHeader *pHeader);

    int sendPing();
    int sendSingleSettings(uint32_t uiID, uint32_t uiValue, uint8_t flags);
    int sendSettings(uint32_t uiMaxStreamNum, uint32_t uiWindowSize);
    int sendGoAwayFrame(SpdyGoAwayStatus status);
    int doGoAway(SpdyGoAwayStatus status);
    int append400BadReqReply(uint32_t uiStreamID);
    void resetStream(SpdyStream *pStream, SpdyRstErrorCode code);
    void resetStream(StreamMap::iterator it, SpdyRstErrorCode code);

    int  appendCtrlFrameHeader(SpdyFrameType type, uint8_t len);
    int  sendFrame8Bytes(SpdyFrameType type, uint32_t uiVal1, uint32_t uiVal2);
    int  sendFrame4Bytes(SpdyFrameType type, uint32_t uiVal1);

    void recycleStream(StreamMap::iterator it);
    int isSpdy3() const     {   return (m_bVersion == 3);    }
    void logDeflateInflateError(int n, int iDeflate);
    int appendReqHeaders(SpdyStream *arg1, int arg2);
    int extractCompressedData();
    void skipRemainData();
    int compressHeaders(HttpRespHeaders *pRespHeaders);

    static int getKeepaliveTimeout();

private:
    LoopBuf         m_bufInput;
    AutoBuf         m_bufInflate;
    SpdyZlibFilter  m_deflator;
    SpdyZlibFilter  m_inflator;
    uint32_t        m_uiServerStreamID;
    uint32_t        m_uiLastPingID;
    uint32_t        m_uiLastStreamID;
    uint32_t        m_uiGoAwayId;
    int32_t         m_iCurrentFrameRemain;
    struct timeval  m_timevalPing;
    NameValuePair   m_NameValuePairList[100];
    NameValuePair   m_NameValuePairListReqline[3];
    TDLinkQueue<SpdyStream> m_priQue[SPDY_STREAM_PRIORITYS];
    StreamMap       m_mapStream;
    short           m_state;
    short           m_flag;
    char            m_bVersion;

    int32_t         m_iCurDataOutWindow;
    int32_t         m_iCurInBytesToUpdate;
    int32_t         m_iDataInWindow;

    int32_t         m_iStreamInInitWindowSize;
    int32_t         m_iServerMaxStreams;
    int32_t         m_iStreamOutInitWindowSize;
    int32_t         m_iClientMaxStreams;
    int32_t         m_tmIdleBegin;
    int32_t         m_SpdyHeaderMem[10];
    SpdyFrameHeader *m_pcurrentSpdyHeader;


    LS_NO_COPY_ASSIGN(SpdyConnection);

};

#endif // SPDYCONNECTION_H
