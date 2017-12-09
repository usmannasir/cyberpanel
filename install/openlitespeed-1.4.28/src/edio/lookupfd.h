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
#ifndef LOOKUPFD_H
#define LOOKUPFD_H

#include <assert.h>
#include <lsdef.h>

class LookUpFD
{
    /// number of elements allocated in m_fd2client[]
    int m_iCapacity;

    /// Resizable lookup table indexed by fd to find entry in m_pfds or m_clients
    int *m_pIntArray;

public:
    explicit LookUpFD(int iCapacity = 16)
        : m_iCapacity(0)
        , m_pIntArray(0)
    {
        if (iCapacity > 0)
            allocate(iCapacity);
    }

    ~LookUpFD()
    {   deallocate(); }

    /** No descriptions */
    int    allocate(int capacity);
    /** No descriptions */
    int    deallocate();
    void   set(int fd, int index)
    {
        if (fd >= m_iCapacity)
            grow(fd);
        //assert( m_pIntArray[fd] == -1 );
        m_pIntArray[fd] = index;
    }
    int  capacity() const   {   return m_iCapacity; }
    int     get(int fd)
    {    return m_pIntArray[fd];  }
    /** No descriptions */
    int     grow(int fd);
    void    remove(int fd)
    {
        m_pIntArray[fd] = -1;
    }

    LS_NO_COPY_ASSIGN(LookUpFD);
};

#endif
