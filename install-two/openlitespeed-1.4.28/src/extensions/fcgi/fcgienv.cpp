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
#include "fcgienv.h"

#include <assert.h>
#include <inttypes.h>
#include <string.h>
#include <sys/types.h>
#include <netinet/in.h>

int FcgiEnv::add(const char *name, size_t nameLen,
                 const char *value, size_t valLen)
{
    if (!name)
        return 0;
    //assert( value );
    //assert( nameLen == strlen( name ) );
    //assert( valLen == strlen( value ) );
    if ((nameLen > 1024) || (valLen > 65535))
        return 0;
    int bufLen = m_buf.available();
    if (bufLen < (int)(nameLen + valLen + 5))
    {
        int grow = ((nameLen + valLen + 5 - bufLen + 1023) >> 10) << 10;
        int ret = m_buf.grow(grow);
        if (ret == -1)
            return ret;
    }
    char *pBuf = m_buf.end();
    *pBuf++ = nameLen;
    if (valLen < 128)
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
    memcpy(pBuf, name, nameLen);
    pBuf += nameLen;
    memcpy(pBuf, value, valLen);
    m_buf.used(pBuf - m_buf.end() + valLen);
    return 0;
}


