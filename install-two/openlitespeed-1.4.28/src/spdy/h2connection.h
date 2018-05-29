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
#ifndef H2CONNECTION_H
#define H2CONNECTION_H

#include <edio/bufferedos.h>
#include <http/hiostream.h>
#include <spdy/h2protocol.h>
#include <spdy/hpack.h>
#include <util/autobuf.h>
#include <util/dlinkqueue.h>
#include <util/ghash.h>

#include <lsdef.h>

#include <sys/time.h>
#include <limits.h>


#define H2_CONN_FLAG_GOAWAY         (1<<0)
#define H2_CONN_FLAG_PREFACE        (1<<1)
#define H2_CONN_FLAG_SETTING_RCVD   (1<<2)
#define H2_CONN_FLAG_SETTING_SENT   (1<<3)
#define H2_CONN_FLAG_CONFIRMED      (1<<4)
#define H2_CONN_FLAG_FLOW_CTRL      (1<<5)
#define H2_CONN_HEADERS_START       (1<<6)
#define H2_CONN_FLAG_WAIT_PROCESS   (1<<7)
#define H2_CONN_FLAG_NO_PUSH        (1<<8)

#define H2_STREAM_PRIORITYS         (8)


class H2Stream;

class H2Connection: public HioHandler, public BufferedOS
{
public:
    H2Connection();
    virtual ~H2Connection();
    int onReadEx();
    int onReadEx2();
    int onWriteEx();

    int isOutBufFull() const
    {
        return ((m_iCurDataOutWindow <= 0) || (getBuf()->size() >= 65535));
    }

    int getAllowedDataSize(int wanted) const
    {
        if (wanted > m_iCurDataOutWindow)
            wanted = m_iCurDataOutWindow;
        if (wanted > m_iPeerMaxFrameSize)
            wanted = m_iPeerMaxFrameSize;
        if (m_buf.size() > 8192 && wanted > 2048)
            wanted = 2048;
        return wanted;
    }

    int flush();

    int onCloseEx();

    void recycle();

    //Following functions are just placeholder

    //Placeholder
    int init();
    int onInitConnected();

    int onTimerEx();
    void add2PriorityQue(H2Stream *pH2Stream);
    int timerRoutine();

    void continueWrite()
    {   getStream()->continueWrite();   }

    int32_t getStreamInInitWindowSize() const
    {   return m_iStreamInInitWindowSize;    }

    int32_t getStreamOutInitWindowSize() const
    {   return m_iStreamOutInitWindowSize;    }

    int32_t getCurDataOutWindow() const
    {   return m_iCurDataOutWindow;         }

    int32_t getPeerMaxFrameSize() const
    {   return m_iPeerMaxFrameSize;         }

    int sendRespHeaders(HttpRespHeaders *pRespHeaders, uint32_t uiStreamID,
                        uint8_t flag);

    int sendHeaderContFrame(uint32_t uiStreamID, uint8_t flag, 
                           H2FrameType type, const char *pBuf, int size);
    
    int sendWindowUpdateFrame(uint32_t id, int32_t delta)
    {   return sendFrame4Bytes(H2_FRAME_WINDOW_UPDATE, id, delta);   }

    int sendRstFrame(uint32_t uiStreamID, H2ErrorCode code)
    {
        return sendFrame4Bytes(H2_FRAME_RST_STREAM, uiStreamID, code);
    }

    int sendFinFrame(uint32_t uiStreamID)
    {
        return sendFrame0Bytes(H2_FRAME_DATA, H2_FLAG_END_STREAM, uiStreamID);
    }

    int sendDataFrame(uint32_t uiStreamID, int flag, IOVec *pIov, int total);
    int sendDataFrame(uint32_t uiStreamId, int flag, const char *pBuf,
                      int len);

    int h2cUpgrade(HioHandler *pSession);

    void recycleStream(uint32_t uiStreamID);

    uint16_t getEvents()
    {   return getStream()->getEvents();    }
    int isFromLocalAddr() const
    {   return getStream()->isFromLocalAddr();  }

    NtwkIOLink *getNtwkIoLink();

    static HioHandler *get();

    void setPendingWrite()
    {
        if (isEmpty() && !getStream()->isWantWrite())
            getStream()->continueWrite();
    }

    void incShutdownStream()    {   ++m_uiShutdownStreams;  }
    void decShutdownStream()    {   --m_uiShutdownStreams;  }
    int pushPromise(uint32_t streamId, ls_str_t* pUrl, ls_str_t* pHost, 
                    ls_strpair_t *headers);

private:
    typedef THash< H2Stream * > StreamMap;

    H2Stream *findStream(uint32_t uiStreamID);
    int releaseAllStream();

    int processFrame(H2FrameHeader *pHeader);
    void printLogMsg(H2FrameHeader *pHeader);

    int checkReqline(char *pName, int ilength, uint8_t &flags);

    int processDataFrame(H2FrameHeader *pHeader);
    int parseHeaders(char *pHeader, int ilength, int &NVPairCnt);
    H2Stream *getNewStream(uint8_t ubH2_Flags);

    int decodeHeaders(unsigned char *src, int length,
                      unsigned char iHeaderFlag);
    int processPriorityFrame(H2FrameHeader *pHeader);
    int processSettingFrame(H2FrameHeader *pHeader);
    int processHeadersFrame(H2FrameHeader *pHeader);
    int processHeaderFrame(H2FrameHeader *pHeader);
    int processPingFrame(H2FrameHeader *pHeader);
    int processGoAwayFrame(H2FrameHeader *pHeader);
    int processRstFrame(H2FrameHeader *pHeader);
    int processWindowUpdateFrame(H2FrameHeader *pHeader);
    int processPushPromiseFrame(H2FrameHeader *pHeader);
    int processContinuationFrame(H2FrameHeader *pHeader);

    int processReqHeader(unsigned char iHeaderFlag);

    int sendPingFrame(uint8_t flags, uint8_t *pPayload);
    int sendSettingsFrame();
    int sendGoAwayFrame(H2ErrorCode status);
    int doGoAway(H2ErrorCode status);

    int resetStream(uint32_t id, H2Stream *pStream, H2ErrorCode code);

    int appendCtrlFrameHeader(H2FrameType type, uint32_t len,
                              unsigned char flags = 0, uint32_t uiStreamID = 0)
    {
        H2FrameHeader header(len, type, flags, uiStreamID);
        setPendingWrite();
        getBuf()->append((char *)&header, 9);
        return 0;
    }
    int  sendFrame8Bytes(H2FrameType type, uint32_t uiStreamId,
                         uint32_t uiVal1, uint32_t uiVal2);
    int  sendFrame4Bytes(H2FrameType type, uint32_t uiStreamId,
                         uint32_t uiVal2);
    int  sendFrame0Bytes(H2FrameType type, uint8_t  flags,
                         uint32_t uiStreamId);


    void recycleStream(StreamMap::iterator it);
    int appendReqHeaders(H2Stream *arg1, char *method = NULL,
                         int methodLen = 0,
                         char *uri = NULL, int uriLen = 0);
    int decodeData(unsigned char *pSrc, unsigned char *bufEnd,
                   char *method, int *methodLen, char **uri, int *uriLen);
    void skipRemainData();
    int encodeHeaders(HttpRespHeaders *pRespHeaders, unsigned char *buf,
                      int maxSize);

    int verifyClientPreface();
    int parseFrame();

    int sendPushPromise(uint32_t streamId, uint32_t promise_streamId, 
                        ls_str_t* pUrl, ls_str_t* pHost, 
                        ls_strpair_t *headers);
 
    H2Stream* createPushStream(uint32_t pushStreamId, ls_str_t* pUrl, 
                               ls_str_t* pHost,  ls_strpair_t* headers);


private:
    LoopBuf         m_bufInput;
    AutoBuf         m_bufInflate;
    uint32_t        m_uiPushStreamId;
    uint32_t        m_uiLastStreamId;
    uint32_t        m_uiShutdownStreams;
    uint32_t        m_uiGoAwayId;
    int32_t         m_iCurPushStreams;
    int32_t         m_iCurrentFrameRemain;
    uint32_t        m_tmLastFrameIn;
    struct timeval  m_timevalPing;

    TDLinkQueue<H2Stream>  m_priQue[H2_STREAM_PRIORITYS];
    StreamMap       m_mapStream;
    short           m_iState;
    short           m_iFlag;
    Priority_st     m_priority;
    char            m_bVersion;

    int32_t         m_iCurDataOutWindow;
    int32_t         m_iCurInBytesToUpdate;
    int32_t         m_iDataInWindow;

    int32_t         m_iStreamInInitWindowSize;
    int32_t         m_iServerMaxStreams;
    int32_t         m_iStreamOutInitWindowSize;
    int32_t         m_iMaxPushStreams;
    int32_t         m_iPeerMaxFrameSize;
    int32_t         m_tmIdleBegin;
    int32_t         m_iaH2HeaderMem[10];
    H2FrameHeader  *m_pCurH2Header;

private:
    Hpack m_hpack;

    LS_NO_COPY_ASSIGN(H2Connection);
};

#endif // H2CONNECTION_H
