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
#include "fcginamevaluepair.h"

#include <assert.h>
#include <inttypes.h>
#include <string.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <lsdef.h>

FcgiNameValuePair::FcgiNameValuePair()
{
}


FcgiNameValuePair::~FcgiNameValuePair() {}


int FcgiNameValuePair::append(char *pBuf, int &size,
                              const char *pName, const char *pValue)
{
    return append(pBuf, size, pName, strlen(pName),
                  pValue, strlen(pValue));
}


int FcgiNameValuePair::append(char *pBuf, int &size,
                              const char *pName, int nameLen, const char *pValue, int valLen)
{
    //assert( nameLen >= 0 );
    //assert( valLen >= 0 );
    int nameLenSize = (nameLen > 127) ? 4 : 1;
    int valLenSize = (valLen > 127) ? 4 : 1;
    int totalSize = nameLen + valLen + nameLenSize + valLenSize ;
    if (size < totalSize)
    {
        size = totalSize;
        return LS_FAIL;
    }
    if (nameLenSize == 1)
        *pBuf++ = nameLen;
    else
    {
#if defined( sparc )
        *pBuf++ = (nameLen >> 24) | 0x80;
        *pBuf++ = (nameLen >> 16) & 0xff;
        *pBuf++ = (nameLen >> 8) & 0xff;
        *pBuf++ = (nameLen & 0xff);
#else
        *((uint32_t *)pBuf) = htonl(nameLen | 0x80000000);
        pBuf += 4;
#endif
    }
    if (valLenSize == 1)
        *pBuf++ = valLen ;
    else
    {
#if defined( sparc )
        *pBuf++ = (valLen >> 24) | 0x80;
        *pBuf++ = (valLen >> 16) & 0xff;
        *pBuf++ = (valLen >> 8) & 0xff;
        *pBuf++ = (valLen & 0xff);
#else
        *((uint32_t *)pBuf) = htonl(valLen | 0x80000000);
        pBuf += 4;
#endif
    }
    memmove(pBuf, pName, nameLen);
    pBuf += nameLen;
    memmove(pBuf, pValue, valLen);
    return totalSize;
}


int FcgiNameValuePair::decode(char *pBuf, int size,
                              char *&pName, int &nameLen,
                              char *&pVal, int &valLen)
{
    if (size <= 0)
        return LS_FAIL;
    unsigned char *p = (unsigned char *)pBuf;
    unsigned char ch = *p++;
    if (ch >> 7)
    {
        if (size < 4)
            return LS_FAIL;
        nameLen = ((((((ch & 0x7f) << 8) | *p) << 8) |
                    *(p + 1)) << 8) | *(p + 2);
        p += 3;
        size -= 4;
    }
    else
    {
        nameLen = ch;
        --size;
    }
    if (size <= 0)
        return LS_FAIL;
    ch = *p++;
    if (ch >> 7)
    {
        if (size < 4)
            return LS_FAIL;
        valLen = ((((((ch & 0x7f) << 8) | *p) << 8) |
                   *(p + 1)) << 8) | *(p + 2);
        p += 3;
        size -= 4;
    }
    else
    {
        valLen = ch;
        --size;
    }
    if (size < nameLen + valLen)
        return LS_FAIL;
    pName = (char *) p;
    p += nameLen;
    pVal = (char *)p;
    p += valLen;
    return (char *)p - pBuf;
}

