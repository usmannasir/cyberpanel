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
#ifndef MULTIPLEX_H
#define MULTIPLEX_H

#include <lsdef.h>

#include <edio/eventreactor.h>

class Multiplexer
{
    int m_iFLTag;
protected:
    Multiplexer();
public:
    virtual ~Multiplexer() {};
    enum
    {
        DEFAULT_CAPACITY = 16
    };
    virtual int getHandle() const          {    return -1;  }
    virtual int init(int capacity = DEFAULT_CAPACITY) { return LS_OK; };
    virtual int add(EventReactor *pHandler, short mask) = 0;
    virtual int remove(EventReactor *pHandler) = 0;
    virtual int waitAndProcessEvents(int iTimeoutMilliSec) = 0;
    virtual void timerExecute() = 0;
    virtual void setPriHandler(EventReactor::pri_handler handler) = 0;

    virtual void continueRead(EventReactor *pHandler);
    virtual void suspendRead(EventReactor *pHandler);
    virtual void continueWrite(EventReactor *pHandler);
    virtual void suspendWrite(EventReactor *pHandler);
    virtual void switchWriteToRead(EventReactor *pHandler);
    virtual void switchReadToWrite(EventReactor *pHandler);
    virtual void modEvent(EventReactor *pHandler, short mask, int add_remove);

    int  getFLTag() const   {   return m_iFLTag;        }
    void setFLTag(int tag)  {   m_iFLTag = tag;         }

    LS_NO_COPY_ASSIGN(Multiplexer);

};

#endif
