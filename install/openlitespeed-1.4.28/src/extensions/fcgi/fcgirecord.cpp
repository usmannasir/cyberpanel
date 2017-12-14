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
#include "fcgirecord.h"

FcgiRecord::FcgiRecord()
{
}


FcgiRecord::~FcgiRecord()
{
}


void FcgiRecord::setRecordHeader(FCGI_Header &header, unsigned char iType,
                                 uint16_t iRequestId, uint16_t iContentLength)
{
    header.version = FCGI_VERSION_1;
    header.type = iType;
    header.requestIdB1 = (iRequestId >> 8) & 0xff;
    header.requestIdB0 = (iRequestId) & 0xff;
    header.contentLengthB1 = (iContentLength >> 8) & 0xff;
    header.contentLengthB0 = (iContentLength) & 0xff;
    header.paddingLength = (8 - iContentLength) & 0x7;

}


