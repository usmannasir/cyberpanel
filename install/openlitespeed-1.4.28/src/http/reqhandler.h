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
#ifndef REQHANDLER_H
#define REQHANDLER_H


class HttpSession;
class HttpContext;
class HttpHandler;
class ReqHandler
{
    int                 m_iType;

    ReqHandler(const ReqHandler &rhs);
    void operator=(const ReqHandler &rhs);
public:
    ReqHandler(): m_iType(0)  {};
    virtual ~ReqHandler()       {};
    virtual int process(HttpSession *pSession,
                        const HttpHandler *pHandler) = 0;
    virtual int onWrite(HttpSession *pSession) = 0;
    virtual int cleanUp(HttpSession *pSession) = 0;
    virtual int onRead(HttpSession *pSession)
    {   return 0;   }
    virtual void abortReq()     {};
    virtual bool notAllowed(int Method) const;
    virtual void reset()        {}
    virtual void onTimer()      {}
    virtual void dump()         {}
    virtual int  dumpAborted()  {   return 0;           }
    void setType(int iType)   {   m_iType = iType;    }
    int  getType() const        {   return m_iType;     }

};

#endif
