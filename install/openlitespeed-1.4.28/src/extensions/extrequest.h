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
#ifndef EXTREQUEST_H
#define EXTREQUEST_H

#include <lsdef.h>
#include <log4cxx/ilog.h>
#include <util/linkedobj.h>


class HttpExtConnector;
class LoadBalancer;
class ExtConn;

class ExtRequest : public DLinkedObj
    , virtual public LOG4CXX_NS::ILog
{
    int             m_iAttempts;
    LoadBalancer   *m_pLB;
    int             m_iWorkerTrack;

public:
    ExtRequest(): m_iAttempts(0) {};
    virtual ~ExtRequest() {};

    void setAttempts(int att) {   m_iAttempts = att;  }
    int  getAttempts() const    {   return m_iAttempts; }
    int  incAttempts()          {   return ++m_iAttempts;   }

    void setLB(LoadBalancer *pLB)    {   m_pLB = pLB;    m_iWorkerTrack = 0;   }
    LoadBalancer *getLB() const        {   return m_pLB;   }

    int getWorkerTrack() const      {   return m_iWorkerTrack;  }
    void addWorkerTrack(int n)    {   m_iWorkerTrack |= (1 << n);   }


    virtual void resetConnector() = 0;
    virtual bool isRecoverable() = 0;
    virtual int  tryRecover() = 0;
    virtual void suspend() = 0;
    virtual int  isAlive() = 0;
    virtual int  endResponse(int endCode, int protocolStatus) = 0;
    virtual void setHttpError(int error) = 0;
    //virtual const char *  getLogId() const;
    //virtual LOG4CXX_NS::Logger* getLogger() const;

    LS_NO_COPY_ASSIGN(ExtRequest);
};

#endif
