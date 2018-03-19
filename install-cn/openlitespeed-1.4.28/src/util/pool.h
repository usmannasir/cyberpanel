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
#ifndef POOL_H
#define POOL_H



#ifdef _REENTRENT
#include <thread/tmutex.h>
#endif

#include <lsr/ls_pool.h>

class Pool
{
private:

public:

    Pool() {};
    ~Pool() {};

    // num must be > 0
    static void *allocate(size_t num)
    {   return ls_palloc(num);   }
    // p may not be 0
    static void   deallocate(void *p, size_t num)
    {   return ls_pfree(p);   }
    static void *reallocate(void *p, size_t old_sz, size_t new_sz)
    {   return ls_prealloc(p, new_sz);   }

    static void *allocate2(size_t num)
    {   return ls_palloc(num);   }
    static void   deallocate2(void *p)
    {   return ls_pfree(p);   }
    static void *reallocate2(void *p, size_t new_sz)
    {   return ls_prealloc(p, new_sz);   }

    static char *dupstr(const char *p)
    {   return ls_pdupstr(p);   }
    static char *dupstr(const char *p, int len)
    {   return ls_pdupstr2(p, len);   }
};

#endif
