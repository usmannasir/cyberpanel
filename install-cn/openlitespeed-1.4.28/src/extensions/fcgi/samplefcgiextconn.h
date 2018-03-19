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
#ifndef SAMPLEFCGIEXTCONN_H
#define SAMPLEFCGIEXTCONN_H



#include <lsdef.h>
#include <http/httpextconnector.h>
#include <extensions/fcgi/fcgienv.h>

class SampleFcgiExtConn : public HttpExtConnector
{
    FcgiEnv m_env;
    //char * m_pBodyBuf;
    int m_iBodySize;
    int m_iBodySent;
public:
    SampleFcgiExtConn();
    ~SampleFcgiExtConn();

    //defined in ReqHandler
    virtual int process(HttpSession *pSession);
    virtual int onWrite(HttpSession *pSession) ;
    virtual int onRead(HttpSession *pSession);


    //functions called by the HttpExtProcessor
    virtual void extProcessorError(int errCode) ;
    virtual void extProcessorReady() ;
    virtual int processRespData(const char *pBuf, int len);
    virtual int processErrData(const char *pBuf, int len);
    virtual int endResponse(int endCode, int protocolStatus);
    virtual int processResp(const char *pBuf, int len);
    virtual int releaseProcessor() { return 0;}

    virtual int sendReqBody() ;
    virtual int cleanUp(HttpSession *pSession);
    virtual int writeReqBody();
    LS_NO_COPY_ASSIGN(SampleFcgiExtConn);
};

#endif
