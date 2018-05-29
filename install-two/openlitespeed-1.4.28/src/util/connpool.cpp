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
#include <util/connpool.h>

ConnPool::~ConnPool()
{
    m_connList.release_objects();
    m_badList.release_objects();
}

int ConnPool::setMaxConns(int max)
{
    if ((int)m_connList.capacity() < max)
    {
        if (m_connList.reserve(max))
            return LS_FAIL;
        if (m_freeList.reserve(max))
            return LS_FAIL;
        if (m_badList.reserve(max))
            return LS_FAIL;
    }
    if (m_iMaxConns < max)
        m_iMaxConns = max;
    return 0;
}

int ConnPool::regConn(IConnection *pConn)
{
    assert(pConn);
    if (m_freeList.full())
    {
        if (setMaxConns(m_connList.size() + 10))
            return LS_FAIL;
    }
    m_connList.unsafe_push_back(pConn);
    return 0;
}

void ConnPool::removeConn(IConnection *pConn)
{
    TPointerList<IConnection>::iterator iter;
    int found = 0;
    for (iter = m_connList.begin(); iter != m_connList.end(); ++iter)
    {
        if (*iter == pConn)
        {
            m_connList.erase(iter);
            found = 1;
            break;
        }
    }
    for (iter = m_freeList.begin(); iter != m_freeList.end(); ++iter)
    {
        if (*iter == pConn)
        {
            m_freeList.erase(iter);
            found = 1;
            break;
        }
    }
    if (found)
        m_badList.unsafe_push_back(pConn);
}

int  ConnPool::inFreeList(IConnection *pConn)
{
    TPointerList<IConnection>::iterator iter;
    TPointerList<IConnection>::iterator iterEnd = m_freeList.end();
    for (iter = m_freeList.begin(); iter != iterEnd; ++iter)
    {
        if (*iter == pConn)
            return 1;
    }
    return 0;
}



