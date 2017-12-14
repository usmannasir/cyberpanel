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
#ifndef LSAPICONN_H
#define LSAPICONN_H

#include "lsapidef.h"
#include "lsapireq.h"

#include <lsdef.h>
#include <extensions/extconn.h>
#include <extensions/httpextprocessor.h>

#define LSAPI_CONN_IDLE             0
#define LSAPI_CONN_READ_RESP_INFO   1
#define LSAPI_CONN_READ_HEADER_LEN  2
#define LSAPI_CONN_READ_HEADER      3
#define LSAPI_CONN_READ_RESP_BODY   4

class LsapiConn: public ExtConn
    , public HttpExtProcessor
{
    int                         m_pid;
    IOVec                       m_iovec;
    int                         m_iTotalPending;
    int                         m_iPacketLeft;
    int                         m_iPacketHeaderLeft;
    long                        m_lReqBeginTime;
    long                        m_lReqSentTime;
    LsapiReq                    m_lsreq;

    int                         m_respState;
    //short                       m_reqReceived;
    int                         m_iCurRespHeader;
    char                       *m_pRespHeader;
    char                       *m_pRespHeaderBufEnd;
    char                       *m_pRespHeaderProcess;
    struct lsapi_packet_header  m_respHeader;
    struct lsapi_resp_info      m_respInfo;
    char                        m_respBuf[4096];


    int     processPacketHeader(char *pBuf, int len);
    int     processRespBuffed();
    int     processRespHeader(char *pEnd, int &status);
    void    setRespBuf(char *pStart);

    int     processResp();
    int     readRespBody();
    int     sendAbortReq();
    int     processRespHeader();
    int     readStderrStream();
protected:
    virtual int doRead();
    virtual int doWrite();
    virtual int doError(int err);
    virtual int addRequest(ExtRequest *pReq);
    virtual ExtRequest *getReq() const;
    virtual void init(int fd, Multiplexer *pMplx);
    virtual void onTimer();
    virtual int connect(Multiplexer *pMplx);


public:
    LsapiConn();

    ~LsapiConn();

public:
    virtual int removeRequest(ExtRequest *pReq);

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
    virtual void dump();
    virtual int  close();

    virtual int sendReqHeader();
    void reset();


    LS_NO_COPY_ASSIGN(LsapiConn);
};

#endif
