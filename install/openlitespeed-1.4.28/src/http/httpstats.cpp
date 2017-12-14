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
#include "httpstats.h"
#include <http/reqstats.h>

int         HttpStats::s_i503AutoFix = 1;
int         HttpStats::s_i503Errors = 0;
long        HttpStats::s_iBytesRead = 0;
long        HttpStats::s_iBytesWritten = 0;
long        HttpStats::s_iSSLBytesRead = 0;
long        HttpStats::s_iSSLBytesWritten = 0;
int         HttpStats::s_iIdleConns = 0;
ReqStats    HttpStats::s_reqStats;

