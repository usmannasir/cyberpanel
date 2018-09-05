/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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
#ifndef CHAINHIOSTREAM_H
#define CHAINHIOSTREAM_H

#include <http/hiostream.h>

class HttpSession;

class HioChainStream :  public HioStream
{
public:
    HioChainStream();
    ~HioChainStream();
    virtual void onTimer();
    virtual void switchWriteToRead();
    virtual void continueWrite();
    virtual void suspendWrite();
    virtual void continueRead();
    virtual void suspendRead();
    virtual int sendRespHeaders(HttpRespHeaders *pHeaders);
    virtual int sendfile(int fdSrc, off_t off, off_t size);
    virtual int read(char *pBuf, int size);
    virtual int close();
    virtual int flush();
    virtual int writev(const iovec *vector, int count);
    virtual int writev(IOVec &pVec, int total);
    virtual int write(const char *pBuf, int size);
    virtual const char *buildLogId();
    virtual uint16_t getEvents() const  {   return 0;   }
    virtual int isFromLocalAddr() const {   return 1;   }
    virtual NtwkIOLink *getNtwkIoLink() {  return NULL;    }

    int onWrite();

    void setParentSession(HttpSession *p)   {   m_pParentSession = p;      }
    HttpSession *getParentSession() const     {   return m_pParentSession;   }


    int appendReqBody(const char *pBuf, int len);
    void setSequence(int iSubReqSeq)
    {   m_iSequence = iSubReqSeq;   }
    int getSequence() const     {   return m_iSequence;     }

    void setDepth(int d)      {   m_iDepth = d;           }
    int getDepth() const        {   return m_iDepth;        }

    HttpRespHeaders *getRespHeaders() const
    {   return m_pRespHeaders;  }


private:
    HioChainStream(const HioChainStream &other);
    HioChainStream &operator=(const HioChainStream &other);
    bool operator==(const HioChainStream &other);
    int passSetCookieToParent();

private:
    HttpSession *m_pParentSession;
    int           m_iDepth: 8;
    int           m_iSequence: 24;
    HttpRespHeaders *m_pRespHeaders;
};

#endif // CHAINHIOSTREAM_H
