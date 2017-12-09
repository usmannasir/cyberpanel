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
#include <util/objpool.h>
#include <lsdef.h>

GObjPool::GObjPool(int chunkSize)
    : m_iChunkSize(chunkSize)
    , m_iPoolSize(0)
    , m_freeList()
{
}

int GObjPool::allocate(int size)
{
    if ((int)m_freeList.capacity() < m_iPoolSize + size)
        if (m_freeList.reserve(m_iPoolSize + size))
            return LS_FAIL;
    int i = 0;
    try
    {
        for (; i < size; ++i)
        {
            void *pObj = newObj();
            if (pObj)
            {
                m_freeList.unsafe_push_back(pObj);
                ++m_iPoolSize;
            }
            else
                return LS_FAIL;
        }
    }
    catch (...)
    {
        return LS_FAIL;
    }
    return 0;
}


