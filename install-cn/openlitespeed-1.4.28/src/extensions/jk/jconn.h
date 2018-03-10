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
#ifndef JCONN_H
#define JCONN_H

#include "jkajp13.h"

#include <lsdef.h>
#include <extensions/extconn.h>
#include <extensions/httpextprocessor.h>
#include <util/iovec.h>

#define AJP_MIN_PACKET_SIZE 6

class JConn : public ExtConn
    , public HttpExtProcessor
{
    char           *m_pReqHeaderEnd;
    char           *m_pBufEnd;
    int             m_iPendingBody;
    int             m_iTotalPending;
    IOVec           m_iovec;
    char            m_buf[AJP_MAX_PACKET_SIZE + 8];

    int             m_curPacketSize;
    int             m_packetLeft;
    int             m_chunkLeft;
    int             m_iNumHeader;
    unsigned char *m_pCurPos;
    int             m_packetType;
    int             m_iPacketState;
    unsigned char *m_pRespBufEnd;
    unsigned char   m_respBuf[AJP_MAX_PACKET_SIZE];

    enum
    {
        PACKET_HEADER,
        CHUNK_LEN,
        CHUNK_DATA,
        STATUS_CODE,
        STATUS_MSG,
        NUM_HEADERS,
        RESP_HEADER
    };
    int processRespData();
    int processPacketData(unsigned char *&p);
    int processPacketHeader(unsigned char *&p);
    int processPacketContent(unsigned char *&p, unsigned char *pEnd);
    int readRespHeader(unsigned char *&p, unsigned char *pEnd);
    int sendReqBodyPacket();

protected:
    virtual int doRead();
    virtual int doWrite();
    virtual int doError(int err);
    virtual int addRequest(ExtRequest *pReq);
    virtual ExtRequest *getReq() const;
    virtual void init(int fd, Multiplexer *pMplx);

public:
    virtual int removeRequest(ExtRequest *pReq);
    JConn();
    ~JConn();

    virtual void finishRecvBuf();

    virtual bool wantRead();
    virtual bool wantWrite();


    virtual void abort();
    virtual int  begin();
    virtual int  beginReqBody();
    virtual int  endOfReqBody();
    virtual int  sendReqBody(const char *pBuf, int size);
    virtual int  readResp(char *pBuf, int size);
    virtual int  flush();
    virtual void cleanUp();

    int buildReqHeader();
    int sendReqHeader();
    void reset();

    LS_NO_COPY_ASSIGN(JConn);
};

#endif
