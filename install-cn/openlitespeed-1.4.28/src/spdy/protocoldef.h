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
#ifndef SPDYPROTOCOLDEF_H
#define SPDYPROTOCOLDEF_H

#include <inttypes.h>

typedef struct
{
    char *pName;
    char *pValue;
    uint16_t nameLen;
    uint16_t ValueLen;
} NameValuePair;


static inline uint16_t beReadUint16(const unsigned char *p)
{
    return ((uint16_t)(*p)) << 8 | *(p + 1);
}

static inline uint32_t beReadUint32(const unsigned char *p)
{
    uint32_t v = *p++;
    v = (v << 8) | *p++;
    v = (v << 8) | *p++;
    v = (v << 8) | *p;
    return v ;
}

static inline uint16_t beReadUint16Adv(unsigned char *&p)
{
    uint16_t v = *p++;
    v = (v << 8) | *p++;
    return v;
}

static inline uint32_t beReadUint32Adv(unsigned char *&p)
{
    uint32_t v = *p++;
    v = (v << 8) | *p++;
    v = (v << 8) | *p++;
    v = (v << 8) | *p++;
    return v ;
}

static inline char *beWriteUint16(char *p, uint16_t v)
{
    *p++ = v >> 8;
    *p++ = v & 0xff;
    return p;
}

static inline char *beWriteUint32(char *p, uint32_t v)
{
    *p++ = v >> 24;
    *p++ = (v >> 16) & 0xff;
    *p++ = (v >> 8) & 0xff;
    *p++ = v & 0xff;
    return p;

}

#endif //SPDYPROTOCOLDEF_H
