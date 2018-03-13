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
#ifndef CEHEADER_H
#define CEHEADER_H

#include <inttypes.h>
#include <http/platforms.h>
#include <sys/types.h>

#define CE_ID MK_DWORD4( 'L', 'S', 'C', 'H' )
#define CACHE_ENTRY_MAGIC_LEN        4

struct CeHeader
{
public:
    CeHeader();

    ~CeHeader();

    enum
    {
        CEH_COMPRESSIBLE = 1,
        CEH_COMPRESSED   = 1 << 1,
        CEH_IN_CONSTRUCT = 1 << 2,
        CEH_PRIVATE      = 1 << 3,
        CEH_STALE        = 1 << 4,
        CEH_UPDATING     = 1 << 5,
        CEH_ESI          = 1 << 6
    };

    int32_t m_tmCreated;        //Created Time
    int32_t m_tmExpire;         //Expire Time
    int16_t m_flag;             //Combination of CEH_xxx flags
    int16_t m_msCreated;        //Milli-Seconds part of the creation time
    uint16_t m_tagLen;          //Cache Tag Length
    uint16_t m_keyLen;          //Cache Key Length
    int32_t m_statusCode;       //Response Status Code
    int32_t m_valPart1Len;      //Response Header Length
    int32_t m_valPart2Len;      //Response Body Length
    int32_t m_tmLastMod;        //Last Modified time parsed from response header if set
    int16_t m_offETag;          //ETag header value location
    int16_t m_lenETag;          //ETag Header size
    int16_t m_lenStxFilePath;   //For a static file caching, we store the orginal file path
    int16_t m_iPrivLen;         //ip and private cookie length, save it for compare cacheHeader need to exclude it
    off_t   m_lSize;
    ino_t   m_inode;
    time_t  m_lastMod;
};

#endif
