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
#ifndef FCGIREQUEST_H
#define FCGIREQUEST_H

#include "fcgidef.h"
#include "fcgienv.h"

#include <lsdef.h>
#include <extensions/extrequest.h>
#include <extensions/httpextprocessor.h>
#include <util/iovec.h>

/*
 * Mask for flags component of FCGI_BeginRequestBody
 */
#define FCGI_KEEP_CONN  1


class FcgiConnection;
class HttpExtConnector;

class FcgiRequest : public HttpExtProcessor, public ExtRequest
{
    int     m_iId;
    int     m_iProtocolStatus;
    //int    m_iWantRead;
    int     m_iWantWrite;
    int     m_iCurStreamHeader;
    IOVec   m_iovec;
    int     m_iTotalPending;
    FcgiEnv m_env;
    char    m_streamHeaders[sizeof(FCGI_Header) * 8 ];
    //FCGI_Header             m_streamHeaders[5];
    //FCGI_BeginRequestRecord m_beginReqRec;

    FcgiConnection   *m_pFcgiConn;

    int  pendingEndStream(int type);
    int  pendingWrite(const char *pBuf, int size, int type);
    int  sendAbortRec();

    enum
    {
        WANT_READ = 1,
        WANT_WRITE = 2
    };

public:

    explicit FcgiRequest(HttpExtConnector *pConnector = 0);
    ~FcgiRequest();
    void reset();

    void setFcgiConn(FcgiConnection *pConn)
    {   m_pFcgiConn = pConn;    }

    FcgiConnection *getFcgiConn() const
    {   return m_pFcgiConn;     }

    void setId(int id)    {   m_iId = id; }
    int  getId() const      {   return m_iId;   }
    int  begin();
    int  beginRequest(int Role, int iKeepConn = FCGI_KEEP_CONN);
    int  sendSpecial(const char *pBuf, int size);
    int  sendReqBody(const char *pBuf, int size);
    int  sendReqHeader();
    int  beginReqBody();
    int  endOfReqBody();
    int  readResp(char *pBuf, int size);
    void abort();
    void cleanUp();
    int  flush();

    void suspendRead()      {}//    m_iWantRead = 0;    }
    void continueRead()     {}
    void suspendWrite()     {    m_iWantWrite = 0;   }
    void continueWrite();

    char wantRead() const   {   return 1;               }
    char wantWrite() const  {   return m_iWantWrite;    }
    bool wantAbort() const
    {   return m_iProtocolStatus == FCGI_ABORT_REQUEST; }

    //int  onExtWrite();
    int  onStdOut();
    int  onError();
    int  processStdOut(char *pBuf, int size);
    int  processStdErr(char *pBuf, int size);
    int  endOfRequest(int code, int status);
    int  sendEndOfStream(int type);

    int  connUnavail();

    void finishRecvBuf();
    void onProcessorTimer();
    virtual HttpExtConnector *getExtConnector()
    {   return HttpExtProcessor::getConnector();    }

    LS_NO_COPY_ASSIGN(FcgiRequest);
};

#endif
