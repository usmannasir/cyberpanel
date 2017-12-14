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
#include <util/ghash.h>

#include <new>

#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

hash_key_t GHash::hfString(const void *__s)
{
    return XXH((const char *)__s, strlen((const char *)__s), 0);
}


int  GHash::cmpString(const void *pVal1, const void *pVal2)
{   return strcmp((const char *)pVal1, (const char *)pVal2);  }


hash_key_t GHash::hfCiString(const void *__s)
{
    hash_key_t __h = 0;
    const char *p = (const char *)__s;
    char ch = *(const char *)p++;
    for (; ch; ch = *((const char *)p++))
    {
        if (ch >= 'A' && ch <= 'Z')
            ch += 'a' - 'A';
        __h = __h * 31 + (ch);
    }
    return __h;
}


int  GHash::cmpCiString(const void *pVal1, const void *pVal2)
{   return strncasecmp((const char *)pVal1, (const char *)pVal2, strlen((const char *)pVal1));  }


hash_key_t GHash::hfIpv6(const void *pKey)
{
    hash_key_t key;
    if (sizeof(hash_key_t) == 4)
    {
        key = *((const hash_key_t *)pKey) +
              *(((const hash_key_t *)pKey) + 1) +
              *(((const hash_key_t *)pKey) + 2) +
              *(((const hash_key_t *)pKey) + 3);
    }
    else
    {
        key = *((const hash_key_t *)pKey) +
              *(((const hash_key_t *)pKey) + 1);
    }
    return key;
}


int  GHash::cmpIpv6(const void *pVal1, const void *pVal2)
{
    return memcmp(pVal1, pVal2, 16);
}


