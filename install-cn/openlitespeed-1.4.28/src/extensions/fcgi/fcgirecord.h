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
#ifndef FCGIRECORD_H
#define FCGIRECORD_H

#include <lsdef.h>
#include <inttypes.h>
#include <sys/types.h>

#include <extensions/fcgi/fcgidef.h>



class FcgiRecord
{
    FcgiRecord();
    ~FcgiRecord();
public:
    static void setRecordHeader(FCGI_Header &header, unsigned char iType,
                                uint16_t iRequestId, uint16_t iContentLength);
    static bool testRecord(FCGI_Header &header)
    {
        return ((header.version == FCGI_VERSION_1)
                && (header.type > 0) && (header.type <= FCGI_MAXTYPE));
    }

    static uint16_t  getContentLength(FCGI_Header &header)
    {
        uint16_t len = (((uint16_t)header.contentLengthB1) << 8)
                       | header.contentLengthB0;
        return len;
    }

    static uint16_t  getId(FCGI_Header &header)
    {
        uint16_t id = (((uint16_t)header.requestIdB1) << 8)
                      | header.requestIdB0;
        return id;
    }
    LS_NO_COPY_ASSIGN(FcgiRecord);
};

#endif
