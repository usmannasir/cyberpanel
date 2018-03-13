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
#ifndef CGIDCONN_H
#define CGIDCONN_H


#include <lsdef.h>
#include <extensions/extconn.h>
#include <extensions/httpextprocessor.h>
#include <extensions/cgi/cgidreq.h>

class CgidConn  : public ExtConn
    , public HttpExtProcessor
{

    const char     *m_pPendingBuf;
    int             m_iTotalPending;
    CgidReq         m_req;

    int buildReqHeader();
    int buildSSIExecHeader(int checkContext);

protected:
    virtual int doRead();
    virtual int doWrite();
    virtual int doError(int err);
    virtual int addRequest(ExtRequest *pReq);
    virtual ExtRequest *getReq() const;
    virtual void init(int fd, Multiplexer *pMplx);
    virtual void onTimer();
    virtual int removeRequest(ExtRequest *pReq);

public:
    CgidConn();
    ~CgidConn();

    virtual void finishRecvBuf() {}

    virtual bool wantRead();
    virtual bool wantWrite();


    virtual void abort();
    virtual int  begin();
    virtual int  beginReqBody();
    virtual int  endOfReqBody();
    virtual int  sendReqBody(const char *pBuf, int size);
    virtual int  readResp(char *pBuf, int size);
    virtual int  endResp();
    virtual int  flush();
    virtual void cleanUp();
    virtual void dump();
    virtual int writeConnStatus(char *pBuf, int len) { return 0; }
    //{   return ExtConn::writeConnStatus( pBuf, len );   }

    virtual int sendReqHeader();
    void reset();

    LS_NO_COPY_ASSIGN(CgidConn);
};

#endif
