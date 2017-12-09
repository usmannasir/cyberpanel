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
#include "hiostream.h"

static const char *s_sProtoName[] =
{
    "HTTP/1.x",
    "SPDY/2",
    "SPDY/3",
    "SPDY/3.1",
    "HTTP/2"
};

const char *HioStream::getProtocolName(HiosProtocol proto)
{
    if (proto >= HIOS_PROTO_MAX)
        return "UNKNOWN";
    return s_sProtoName[proto];
}


HioStream::~HioStream()
{

}


void HioStream::handlerOnClose()
{
    if (!isReadyToRelease())
        m_pHandler->onCloseEx();
    if (m_pHandler && isReadyToRelease())
    {
        m_pHandler->recycle();
        m_pHandler = NULL;
    }
}


HioHandler::~HioHandler()
{

}


int HioHandler::h2cUpgrade(HioHandler *pOld)
{
    return LS_FAIL;
}


