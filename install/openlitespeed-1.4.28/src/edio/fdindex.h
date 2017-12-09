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
#ifndef FDINDEX_H
#define FDINDEX_H


#include <lsdef.h>

class FdIndex
{
    unsigned short *m_pIndexes;
    int             m_capacity;

    int deallocate();

public:
    FdIndex();
    ~FdIndex();
    int getCapacity() const     {   return m_capacity;      }
    unsigned short get(int fd) const     {   return m_pIndexes[fd];  }
    int allocate(int capacity);
    int set(int fd, int index)
    {
        if (fd >= m_capacity)
        {
            int new_cap = m_capacity * 2;
            if (new_cap <= fd)
                new_cap = fd + 1;
            if (allocate(new_cap) == -1)
                return LS_FAIL;
        }
        m_pIndexes[fd] = index;
        return LS_OK;
    }

    LS_NO_COPY_ASSIGN(FdIndex);
};

#endif
