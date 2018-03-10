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
#ifndef FCGICONNECTION_H
#define FCGICONNECTION_H

#include "fcgidef.h"
#include "fcgienv.h"

#include <lsdef.h>
#include <edio/bufferedos.h>
#include <extensions/extconn.h>
#include <extensions/httpextprocessor.h>
#include <util/autobuf.h>

//#define FCGI_MPLX

#define FCGI_MAX_PACKET_SIZE    8192

class FcgiApp;
class Multiplexer;
class FcgiConnection : public ExtConn
    , public HttpExtProcessor
{
private:

    BufferedOS      m_bufOS;
    AutoBuf         m_bufRec;
    FCGI_Header     m_recCur;
    uint16_t        m_recSize;
    uint16_t        m_iRecStatus;
    uint16_t        m_iContentLen;
    uint16_t        m_iRecId;

    int             m_iId;
    //int           m_iWantRead;
    int             m_iWantWrite;
    int             m_iTotalPending;
    int             m_iCurStreamHeader;
    char            m_streamHeaders[sizeof(FCGI_Header) * 8 ];
    IOVec           m_iovec;
    FcgiEnv         m_env;

    int             m_lReqSentTime;
    int             m_lReqBeginTime;


    int cacheOutput(const char *pBuf, int len);
    int sendStreamPacket(int streamType, int id,
                         const char *pBuf, int size);
    //int processFcgiRecord( char * pBuf, int size, int& used);
    int buildFcgiRecHeader(char *pBuf, int size, int &len);
    int processFcgiRecData(char *pBuf, int size, int &end);

    //int processFcgiDataNew();
    int processFcgiData();
    int queryAppAttr();
    bool isOutputBufEmpty();
    void processManagementVal(char *pName, int nameLen,
                              char *pValue, int valLen);
    int processManagementRec(char *pBuf, int size);
    int processEndOfRequestRecord(char *pBuf, int size);
    int flushOutBuf();

    int  pendingEndStream(int type);
    int  pendingWrite(const char *pBuf, int size, int type);
    int  sendAbortRec();

    enum
    {
        REC_HEADER,
        REC_CONTENT,
        REC_PADDING
    };

protected:
    virtual int doRead();
    virtual int doError(int err);
    int addRequest(ExtRequest *pReq);
    void retryProcessor();
    ExtRequest *getReq() const;

public:
    static const char s_padding[8];
    FcgiConnection();
    ~FcgiConnection();
    void init(int fd, Multiplexer *pMplx);
    int sendRecord(const char *rec, int size);
    int writeStream(int streamType, int id,
                    const char *pBuf, int size);
    int endOfStream(int streamType, int id);
    bool wantRead();
    bool wantWrite();

    int removeRequest(ExtRequest *pReq);

    int close()    {   m_bufOS.flush(); ExtConn::close(); return 0;    }
    void finishRecvBuf();
    int readStdOut(int iReqId, char *pBuf, int size);

    void suspendWrite();
    void continueWrite();
    virtual int doWrite();

    virtual int  begin();
    int  sendSpecial(const char *pBuf, int size);
    int  sendReqBody(const char *pBuf, int size);
    int  sendReqHeader();
    int  beginReqBody();
    int  endOfReqBody();
    int  readResp(char *pBuf, int size);
    void abort();
    void cleanUp();
    int  flush();


    //char wantRead() const   {   return 1;               }
    //char wantWrite() const  {   return m_iWantWrite;    }

    //int  onExtWrite();
    int  onStdOut();
    int  processStdOut(char *pBuf, int size);
    int  processStdErr(char *pBuf, int size);
    int  endOfRequest(int code, int status);
    int  sendEndOfStream(int type);

    int  connUnavail();

    void dump();


    LS_NO_COPY_ASSIGN(FcgiConnection);
};

#endif
