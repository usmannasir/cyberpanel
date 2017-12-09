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
#include "handlertype.h"

#include <string.h>

const char *HandlerType::s_sHandlerType[HT_END] =
{
    "static",
    "ssi",
    "action",
    "redirect",
    "jwebapp",
    "rails",
    "module",
    "cgi",
    "fcgi",
    "proxy",
    "jk",
    "lsapi",
    "logger",
    "loadbalancer"

};


int HandlerType::getHandlerType(const char *pType, int &role)
{
    int iType = HT_END;
    role = ROLE_RESPONDER;
    if (pType)
    {
        if (strcasecmp(pType, "NULL") == 0)
            iType = HT_NULL;
        else if (strcasecmp(pType, "static") == 0)
            iType = HT_STATIC;
        else if (strcasecmp(pType, "ssi") == 0)
            iType = HT_SSI;
        else if (strcasecmp(pType, "action") == 0)
            iType = HT_ACTION;
        else if (strcasecmp(pType, "redirect") == 0)
            iType = HT_REDIRECT;
        else if (strcasecmp(pType, "webapp") == 0)
            iType = HT_JAVAWEBAPP;
        else if (strcasecmp(pType, "rails") == 0)
            iType = HT_RAILS;
        else if (strcasecmp(pType, "cgi") == 0)
            iType = HT_CGI;
        else if (strcasecmp(pType, "fcgi") == 0)
            iType = HT_FASTCGI;
        else if (strcasecmp(pType, "fcgiauth") == 0)
        {
            iType = HT_FASTCGI;
            role  = ROLE_AUTHORIZER;
        }
        else if (strcasecmp(pType, "servlet") == 0)
            iType = HT_SERVLET;
        else if (strcasecmp(pType, "jsp") == 0)
            iType = HT_JSP;
        else if (strcasecmp(pType, "proxy") == 0)
            iType = HT_PROXY;
        else if (strcasecmp(pType, "lsapi") == 0)
            iType = HT_LSAPI;
        else if (strcasecmp(pType, "logger") == 0)
            iType = HT_LOGGER;
        else if (strcasecmp(pType, "loadbalancer") == 0)
            iType = HT_LOADBALANCER;
        else if (strcasecmp(pType, "module") == 0)
            iType = HT_MODULE;
    }
    return iType;
}

