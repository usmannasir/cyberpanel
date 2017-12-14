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
#ifndef HANDLERTYPE_H
#define HANDLERTYPE_H



class HandlerType
{
    HandlerType();
    ~HandlerType();
public:

    enum
    {
        HT_NULL = 0,
        HT_STATIC = HT_NULL,
        HT_SSI,
        HT_ACTION,
        HT_REDIRECT,
        HT_DYNAMIC,
        HT_JAVAWEBAPP = HT_DYNAMIC,
        HT_RAILS,
        HT_MODULE,
        HT_CGI,
        HT_FASTCGI,
        HT_PROXY,
        HT_SERVLET,
        HT_JSP = HT_SERVLET,
        HT_LSAPI,
        HT_LOGGER,
        HT_LOADBALANCER,
        HT_END
    };
    enum
    {
        ROLE_UNKNOWN,
        ROLE_RESPONDER,
        ROLE_AUTHORIZER
    };
private:
    static const char *s_sHandlerType[HT_END];
public:
    static int getHandlerType(const char *pType, int &role);
    static const char *getHandlerTypeString(int type)
    {   return s_sHandlerType[type];    }
};

#endif
