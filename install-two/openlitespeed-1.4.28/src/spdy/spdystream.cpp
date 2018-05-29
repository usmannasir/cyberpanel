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
#include "spdystream.h"
#include "spdyconnection.h"

#include <log4cxx/logger.h>
#include <lsr/ls_strtool.h>
#include <util/datetime.h>
#include <util/iovec.h>

SpdyStream::SpdyStream()
    : m_uiStreamID(0)
    , m_pSpdyConn(NULL)
{
}


const char *SpdyStream::buildLogId()
{
    int len ;
    AutoStr2 &id = getIdBuf();

    len = ls_snprintf(id.buf(), MAX_LOGID_LEN, "%s-%d",
                      m_pSpdyConn->getStream()->getLogId(), m_uiStreamID);
    id.setLen(len);
    return id.c_str();
}


int SpdyStream::init(uint32_t StreamID,
                     int Priority, SpdyConnection *pSpdyConn, uint8_t flags,
                     HioHandler *pHandler)
{
    HioStream::reset(DateTime::s_curTime);
    pHandler->attachStream(this);
    clearLogId();

    setState(HIOS_CONNECTED);
    setFlag((flags & (SPDY_CTRL_FLAG_FIN | SPDY_CTRL_FLAG_UNIDIRECTIONAL)), 1);

    m_bufIn.clear();
    m_uiStreamID  = StreamID;
    m_iWindowOut = pSpdyConn->getStreamOutInitWindowSize();
    m_iWindowIn = pSpdyConn->getStreamInInitWindowSize();
    setPriority(Priority);
    m_pSpdyConn = pSpdyConn;
    LS_DBG_L(this, "SpdyStream::init(), id: %d. ", StreamID);
    return 0;
}


int SpdyStream::onInitConnected()
{
    getHandler()->onInitConnected();
    if (isWantRead())
        getHandler()->onReadEx();
    if (isWantWrite())
        if (next() == NULL)
            m_pSpdyConn->add2PriorityQue(this);
    return 0;
}

SpdyStream::~SpdyStream()
{
    m_bufIn.clear();
}

int SpdyStream::appendReqData(char *pData, int len, uint8_t flags)
{
    if (m_bufIn.append(pData, len) == -1)
        return LS_FAIL;
    if (isFlowCtrl())
        m_iWindowIn -= len;
    //Note: SPDY_CTRL_FLAG_FIN is directly mapped to HIO_FLAG_PEER_SHUTDOWN
    //      SPDY_CTRL_FLAG_UNIDIRECTIONAL is directly mapped to HIO_FLAG_LOCAL_SHUTDOWN
    if (flags & (SPDY_CTRL_FLAG_FIN | SPDY_CTRL_FLAG_UNIDIRECTIONAL))
        setFlag(flags & (SPDY_CTRL_FLAG_FIN | SPDY_CTRL_FLAG_UNIDIRECTIONAL), 1);

    if (isWantRead())
        getHandler()->onReadEx();
    return len;
}


//***int SpdyStream::read( char * buf, int len )***//
// return > 0:  number of bytes of that has been read
// return = 0:  0 byte of data has been read, but there will be more data coming,
//              need to read again
// return = -1: EOF (End of File) There is no more data need to be read, the
//              stream can be removed
int SpdyStream::read(char *buf, int len)
{
    int ReadCount;
    if (getState() == HIOS_DISCONNECTED)
        return LS_FAIL;

    ReadCount = m_bufIn.moveTo(buf, len);
    if (ReadCount == 0)
    {
        if (getFlag(HIO_FLAG_PEER_SHUTDOWN))
        {
            return LS_FAIL; //EOF (End of File) There is no more data need to be read
        }
    }
    if (ReadCount > 0)
        setActiveTime(DateTime::s_curTime);

    return ReadCount;
}

void SpdyStream::continueRead()
{
    LS_DBG_L(this, "SpdyStream::continueRead()");
    setFlag(HIO_FLAG_WANT_READ, 1);
    if (m_bufIn.size() > 0)
        getHandler()->onReadEx();
}


void SpdyStream:: continueWrite()
{
    LS_DBG_L(this, "SpdyStream::continueWrite()");
    setFlag(HIO_FLAG_WANT_WRITE, 1);
    if (next() == NULL)
        m_pSpdyConn->add2PriorityQue(this);
    m_pSpdyConn->continueWrite();
}


void SpdyStream::onTimer()
{
    getHandler()->onTimerEx();
}


uint16_t SpdyStream::getEvents() const
{
    return m_pSpdyConn->getEvents();
}


int SpdyStream::isFromLocalAddr() const
{   return m_pSpdyConn->isFromLocalAddr();  }


NtwkIOLink *SpdyStream::getNtwkIoLink()
{   return m_pSpdyConn->getNtwkIoLink();    }


int SpdyStream::shutdown()
{
    if (getState() == HIOS_SHUTDOWN)
        return 0;

    setState(HIOS_SHUTDOWN);

    LS_DBG_L(this, "SpdyStream::shutdown()");
    m_pSpdyConn->sendFinFrame(m_uiStreamID);
    m_pSpdyConn->flush();
    return 0;
}


int SpdyStream::close()
{
    if (getState() == HIOS_DISCONNECTED)
        return 0;
    if (getHandler() && !isReadyToRelease())
        getHandler()->onCloseEx();
    shutdown();
    setFlag(HIO_FLAG_WANT_WRITE, 1);
    setState(HIOS_DISCONNECTED);
    m_pSpdyConn->continueWrite();
    //if (getHandler())
    //{
    //    getHandler()->recycle();
    //    setHandler( NULL );
    //}
    m_pSpdyConn->recycleStream(m_uiStreamID);
    return 0;
}


int SpdyStream::flush()
{
    LS_DBG_L(this, "SpdyStream::flush()");
    return LS_DONE;
}

int SpdyStream::getDataFrameSize(int wanted)
{
    if ((m_pSpdyConn->isOutBufFull()) ||
        (0 >= m_iWindowOut))
    {
        setFlag(HIO_FLAG_BUFF_FULL | HIO_FLAG_WANT_WRITE, 1);
        if (next() == NULL)
            m_pSpdyConn->add2PriorityQue(this);
        m_pSpdyConn->continueWrite();
        return 0;
    }

    if (wanted > m_iWindowOut)
        wanted = m_iWindowOut;
    if (wanted > SPDY_MAX_DATAFRAM_SIZE)
        wanted = SPDY_MAX_DATAFRAM_SIZE;
    wanted = m_pSpdyConn->getAllowedDataSize(wanted);
    return wanted;
}

int SpdyStream::writev(IOVec &vector, int total)
{
    int size;
    int ret;
    if (getState() == HIOS_DISCONNECTED)
        return LS_FAIL;
    if (getFlag(HIO_FLAG_BUFF_FULL))
        return 0;
    size = getDataFrameSize(total);
    if (size <= 0)
        return 0;
    if (size < total)
    {
        //adjust vector
        IOVec iov(vector);
        total = iov.shrinkTo(size, 0);
        ret = sendData(&iov, size);
    }
    else
        ret = sendData(&vector, size);
    if (ret == -1)
        return LS_FAIL;
    return size;

}

int SpdyStream::writev(const struct iovec *vec, int count)
{
    IOVec iov(vec, count);
    return writev(iov, iov.bytes());
}


int SpdyStream::write(const char *buf, int len)
{
    IOVec iov;
    const char *p = buf;
    const char *pEnd = buf + len;
    int allowed;
    if (getState() == HIOS_DISCONNECTED)
        return LS_FAIL;
    while(pEnd - p > 0)
    {
        allowed = getDataFrameSize(pEnd - p);
        if (allowed <= 0)
            break;

        iov.append(p, allowed);
        if (sendData(&iov, allowed) == -1)
            return LS_FAIL;
        p += allowed;
        iov.clear();
    }
    return p - buf;
}


int SpdyStream::onWrite()
{
    LS_DBG_L(this, "SpdyStream::onWrite()");
    if (m_pSpdyConn->isOutBufFull())
        return 0;
    if (m_iWindowOut <= 0)
        return 0;
    setFlag(HIO_FLAG_BUFF_FULL, 0);

    if (isWantWrite())
        getHandler()->onWriteEx();
    if (isWantWrite())
        m_pSpdyConn->continueWrite();
    return 0;
}

void SpdyStream::buildDataFrameHeader(char *pHeader, int length)
{
    *(uint32_t *)pHeader = htonl(m_uiStreamID);
    *((uint32_t *)pHeader + 1) = htonl(length);
    if (getState() >= HIOS_CLOSING)
        pHeader[4] = 1;
}

int SpdyStream::sendData(IOVec *pIov, int total)
{
    char achHeader[8];
    int ret;
    buildDataFrameHeader(achHeader, total);
    m_pSpdyConn->getBuf()->append(achHeader, 8);
    ret = m_pSpdyConn->cacheWritev(*pIov, total);
    LS_DBG_L(this, "SpdyStream::sendData(), total: %d, ret: %d", total, ret);
    if (ret == -1)
    {
        setFlag(HIO_FLAG_ABORT, 1);
        return LS_FAIL;
    }

    setActiveTime(DateTime::s_curTime);
    bytesSent(total);
    m_pSpdyConn->dataFrameSent(total);
    if (isFlowCtrl())
    {
        m_iWindowOut -= total;
        if (m_iWindowOut <= 0)
            setFlag(HIO_FLAG_BUFF_FULL, 1);
    }
    return total;
}


int SpdyStream::sendRespHeaders(HttpRespHeaders *pHeaders, int isNoBody)
{
    if (getState() == HIOS_DISCONNECTED)
        return LS_FAIL;
    if (isNoBody)
    {
        LS_DBG_L(this, "No response body, set FLAG_FIN.");
        setState(HIOS_SHUTDOWN);
    }
    else
    {
        if (next() == NULL)
            m_pSpdyConn->add2PriorityQue(this);
    }
    return m_pSpdyConn->sendRespHeaders(pHeaders, m_uiStreamID, isNoBody);
}

int SpdyStream::adjWindowOut(int32_t n)
{
    if (isFlowCtrl())
    {
        m_iWindowOut += n;
        LS_DBG_L(this, "Stream WINDOW_UPDATE: %d, window size: %d ",
                 n, m_iWindowOut);
        if (m_iWindowOut < 0)
        {
            //window overflow
            return LS_FAIL;
        }
        else if (isWantWrite())
            continueWrite();
    }
    return 0;
}
