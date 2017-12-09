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
#ifndef CGICONNECTION_H
#define CGICONNECTION_H


#include <lsdef.h>
#include <edio/ediostream.h>
#include <extensions/httpextprocessor.h>

class HttpExtConnector;

class CgiConnection : public HttpExtProcessor,
    public EdStream
{
    static int s_iCgiCount;
public:
    CgiConnection();
    ~CgiConnection();

    //interface defined by EdStream
    virtual int onRead();
    virtual int onWrite();
    virtual int onError();
    virtual int onEventDone(short event);
    virtual bool wantRead();
    virtual bool wantWrite();

    //interface defined by HttpExtProcessor
    virtual int init(int fd, Multiplexer *pMultiplexer,
                     HttpExtConnector *pConn);

    virtual void abort();
    virtual void cleanUp();

    virtual int  begin();
    virtual int  beginReqBody();
    virtual int  endOfReqBody();
    virtual int  sendReqHeader();
    virtual int  sendReqBody(const char *pBuf, int size);
    virtual int  readResp(char *pBuf, int size);

    void onTimer() {}
    virtual void finishRecvBuf() {}
    void *operator new(size_t sz);
    void operator delete(void *p);
    static int getCgiCount()
    {   return s_iCgiCount; }
    LS_NO_COPY_ASSIGN(CgiConnection);
};

#endif
