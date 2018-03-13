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
#ifndef HTTPEXTPROCESSOR_H
#define HTTPEXTPROCESSOR_H

#include <lsdef.h>
#include <edio/flowcontrol.h>
#include <log4cxx/ilog.h>

class HttpExtConnector;

class HttpExtProcessor : virtual public IOFlowControl
    , virtual public LOG4CXX_NS::ILog
{
    HttpExtConnector *m_pConnector;
protected:
    HttpExtConnector *getConnector() const
    {   return m_pConnector;    }
    void setConnector(HttpExtConnector *pConnector);
public:
    HttpExtProcessor()
        : m_pConnector(0) {};
    virtual ~HttpExtProcessor() {};
    virtual void abort() = 0;
    virtual int  begin() = 0;
    virtual int  beginReqBody() = 0;
    virtual int  endOfReqBody() = 0;
    virtual int  sendReqBody(const char *pBuf, int size) = 0;
    virtual int  sendReqHeader() = 0;
    virtual int  readResp(char *pBuf, int size) = 0;
    virtual void finishRecvBuf() = 0;
    virtual void dump() {}

    virtual void cleanUp() = 0;


    LOG4CXX_NS::Logger *getLogger() const;
    const char *getLogId();

    LS_NO_COPY_ASSIGN(HttpExtProcessor);
};

#endif
