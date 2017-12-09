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
#include "fdindex.h"

#include <errno.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

FdIndex::FdIndex()
    : m_pIndexes(NULL)
    , m_capacity(0)
{
}
FdIndex::~FdIndex()
{
    deallocate();
}

int FdIndex::allocate(int capacity)
{
    unsigned short *pIndexes = (unsigned short *) realloc(m_pIndexes,
                               capacity * sizeof(short));
    if (!pIndexes)
        return LS_FAIL;
    if (capacity > m_capacity)
        memset(pIndexes + m_capacity, -1,
               sizeof(short) * (capacity - m_capacity));
    m_pIndexes = pIndexes;
    m_capacity = capacity;
    return LS_OK;
}

int FdIndex::deallocate()
{
    if (m_pIndexes)
        free(m_pIndexes);
    return LS_OK;
}


