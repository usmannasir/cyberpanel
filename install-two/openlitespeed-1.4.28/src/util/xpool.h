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
#ifndef XPOOL_H
#define XPOOL_H

#include <lsr/ls_xpool.h>

#include <inttypes.h>

class XPool : private ls_xpool_t
{
    XPool(const XPool &rhs);
    void operator=(const XPool &rhs);

public:
    XPool()
    {   ls_xpool_init(this);    }

    ~XPool()
    {   ls_xpool_destroy(this); }

    void reset()
    {   ls_xpool_reset(this);   }

    void *alloc(uint32_t size)
    {   return ls_xpool_alloc(this, size);   }

    void *calloc(uint32_t items, uint32_t size)
    {   return ls_xpool_calloc(this, items, size);  }

    void *realloc(void *pOld, uint32_t new_size)
    {   return ls_xpool_realloc(this, pOld, new_size);    }

    void free(void *data)
    {   ls_xpool_free(this, data);  }

    void skipfree()
    {   ls_xpool_skipfree(this);    }
};

#endif
