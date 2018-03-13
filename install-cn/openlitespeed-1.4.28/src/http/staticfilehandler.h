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
#ifndef STATICFILEHANDLER_H
#define STATICFILEHANDLER_H

#include <http/reqhandler.h>
#include <http/httphandler.h>


class StaticFileHandler : public ReqHandler, public HttpHandler
{
public:
    StaticFileHandler();
    ~StaticFileHandler();
    virtual const char *getName() const;
    virtual int process(HttpSession *pSession, const HttpHandler *pHandler);
    virtual int onWrite(HttpSession *pSession);
    virtual int cleanUp(HttpSession *pSession);
    virtual bool notAllowed(int Method) const;

};

class RedirectHandler : public HttpHandler
{
public:
    RedirectHandler();
    ~RedirectHandler();
    virtual const char *getName() const;
};


#endif
