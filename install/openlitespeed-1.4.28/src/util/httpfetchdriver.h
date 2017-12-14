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
#ifndef HTTPFETCHDRIVER_H
#define HTTPFETCHDRIVER_H

#include <lsdef.h>
#include <edio/eventreactor.h>
#include <time.h>

class HttpFetch;

class HttpFetchDriver : public EventReactor
{
    HttpFetch *m_pHttpFetch;
    time_t m_start;
    HttpFetchDriver(const HttpFetchDriver &other);
    void operator=(const HttpFetchDriver &other);
public:
    virtual int handleEvents(short int event);
    virtual void onTimer();

    HttpFetchDriver(HttpFetch *pHttpFetch);
    virtual ~HttpFetchDriver()                      {   };
    void start();
    void stop();

    void switchWriteToRead();
    void switchReadToWrite();
};

#endif // HTTPFETCHDRIVER_H
