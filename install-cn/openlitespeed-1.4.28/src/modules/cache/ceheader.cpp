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
#include "ceheader.h"

CeHeader::CeHeader()
    : m_tmCreated(0)
    , m_tmExpire(0)
    , m_flag(CEH_IN_CONSTRUCT)
    , m_msCreated(0)
    , m_tagLen(0)
    , m_keyLen(0)
    , m_statusCode(0)
    , m_valPart1Len(0)
    , m_valPart2Len(0)
    , m_tmLastMod(0)
    , m_offETag(0)
    , m_lenETag(0)
    , m_lenStxFilePath(0)
    , m_lSize(0)
    , m_inode(0)
    , m_lastMod(0)
{
}


CeHeader::~CeHeader()
{
}



