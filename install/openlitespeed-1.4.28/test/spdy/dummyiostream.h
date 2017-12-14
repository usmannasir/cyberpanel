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
#ifndef DUMMYIOSTREAM_H
#define DUMMYIOSTREAM_H
#include "spdy/spdyconnection.h"
#include <http/hiostream.h>
#include <util/loopbuf.h>

class HttpRespHeaders;
class DummySpdyConnStream: public HioStream
{
    int             m_running;
    char           *m_pDatabuff;
    int             m_Datalen;
    LoopBuf         m_InputBuff;
public:
    DummySpdyConnStream();
    DummySpdyConnStream(char *buff, int length);
    ~DummySpdyConnStream() {};
    int read(char *buf, int len);
    int write(const char *buf, int len);
    int flush() {   return -1;   }

    ////////////////////////////
    int writev(IOVec &vector, int total) {return 0;};
    virtual int sendfile(int fdSrc, off_t off, off_t size)
    {   return 0;   }
    int close()  { return -1;};
    int sendRespHeaders(HttpRespHeaders *pHeaders, int isNoBody);


    void suspendRead()      { setFlag(HIO_FLAG_WANT_READ, 0);     }
    void continueRead()     { setFlag(HIO_FLAG_WANT_READ, 1);     }
    void suspendWrite() {return;};
    void continueWrite() {return;};
    void switchWriteToRead() {return;};
    void onTimer() {};
    uint32_t GetStreamID() {return 0;};
    virtual const char *buildLogId()   {   return getLogId();    }

    /////////////////////////////
private:
    void appendInputData(char *buff, int length);
    int eventLoop();
    int onInitConnected();

};

#endif // DUMMYIOSTREAM_H
