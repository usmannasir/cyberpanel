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
#if 0
#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)

#ifndef RTSIGIO_H
#define RTSIGIO_H


#include <edio/fdindex.h>
#include <edio/poller.h>
#include <signal.h>

class RTSigData;
class RTsigio : public Poller
{
    sigset_t        m_sigset;
    FdIndex         m_fdindex;
    int allocate(int iInitCapacity);
    int deallocate();
    int enableSigio();

public:

    RTsigio();
    virtual ~RTsigio();
    virtual int init(int capacity);
    virtual int add(EventReactor *pHandler, short mask);
    virtual int remove(EventReactor *pHandler);
    virtual int waitAndProcessEvents(int iTimeoutMilliSec);

};

#endif

#endif

#endif
