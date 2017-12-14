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
#ifndef CACHEHASH_H
#define CACHEHASH_H



#include <lsdef.h>
#include <lsr/xxhash.h>
#include <util/ghash.h>

#define HASH_KEY_LEN 8
class CacheHash
{
public:
    CacheHash();

    ~CacheHash();

    void copy(const CacheHash &rhs)
    {   *this = rhs;       }
    static void update(XXH64_state_t *pState, const char *pBuf, int len);

    const unsigned char *getKey() const
    {   return (unsigned char *)&m_key;     }
    void setKey(uint64_t digest)
    {    m_key = digest;     }

    static hash_key_t to_ghash_key(const void *__s);
    static int  compare(const void *pVal1, const void *pVal2);

private:
    uint64_t  m_key;
};

#endif
