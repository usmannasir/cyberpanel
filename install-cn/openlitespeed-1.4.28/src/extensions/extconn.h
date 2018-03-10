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
#ifndef EXTCONN_H
#define EXTCONN_H

#include <lsdef.h>
#include <edio/ediostream.h>
#include <log4cxx/ilog.h>
#include <util/iconnection.h>

#include <time.h>

class ExtRequest;
class ExtWorker;

class ExtConn : public EdStream, public IConnection
    , virtual public LOG4CXX_NS::ILog
{
    char            m_iState;
    char            m_iToStop;
    char            m_iInProcess;
    char            m_iCPState;
    time_t          m_tmLastAccess;
    int             m_iReqProcessed;
    ExtWorker      *m_pWorker;


protected:
    int connError(int error);
    int connectEx(Multiplexer *pMplx);

    virtual int doRead() = 0;
    virtual int doError(int err) = 0;
    virtual int doWrite() = 0;
    virtual int addRequest(ExtRequest *pReq) = 0;
    virtual int connect(Multiplexer *pMplx);
public:
    virtual int removeRequest(ExtRequest *pReq) = 0;
    enum
    {
        DISCONNECTED,
        CONNECTING,
        PROCESSING,
        PROTOCOL_ERROR,
        ABORT,
        CLOSING,
        ERROR_STATE
    };

    enum
    {
        UNKNOWN,
        FREE,
        INUSE
    };

    ExtConn();
    virtual ~ExtConn();
    void  setState(char state)    {   m_iState = state;       }
    char  getState() const          {   return m_iState;        }

    void  setToStop(char n)       {   m_iToStop = n;          }
    char  getToStop() const         {   return m_iToStop;       }

    void  setInProcess(char s)    {   m_iInProcess = s;       }
    char  getInProcess() const      {   return m_iInProcess;    }

    void  setCPState(char s)      {   m_iCPState = s;         }
    char  getCPState() const        {   return m_iCPState;      }

    void  access(time_t tm)       {   m_tmLastAccess = tm;    }
    time_t getLastAccess() const    {   return m_tmLastAccess;  }

    void  setWorker(ExtWorker *pWorker)
    {   m_pWorker = pWorker;      }
    ExtWorker *getWorker() const
    {   return m_pWorker;   }

    //void reset();
    virtual void init(int fd, Multiplexer *pMplx) = 0;
    virtual int  close();

    int  onRead();
    int  onWrite();
    int  onError();
    int  onEventDone();
    int  onInitConnected();
    void onSecTimer();
    void onTimer();

    int  reconnect();

    int  getReqProcessed() const    {   return m_iReqProcessed; }
    void incReqProcessed()          {   ++m_iReqProcessed;      }
    void setReqProcessed(int n)    {   m_iReqProcessed = n;    }


    int  assignReq(ExtRequest *req);
    virtual ExtRequest *getReq() const = 0;
    void recycle();

    void checkInProcess();

#ifndef _NDEBUG
    void continueRead();
    void suspendRead();

    void continueWrite();
    void suspendWrite();
#endif
    LS_NO_COPY_ASSIGN(ExtConn);
};

#endif
