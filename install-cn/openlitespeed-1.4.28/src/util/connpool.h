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
#ifndef CONNPOOL_H
#define CONNPOOL_H



#include <lsdef.h>
#include <util/gpointerlist.h>
#include <util/iconnection.h>
#include <assert.h>

class ConnPool
{
    TPointerList<IConnection>   m_connList;
    TPointerList<IConnection>   m_freeList;
    TPointerList<IConnection>   m_badList;
    int                         m_iMaxConns;
public:
    ConnPool() : m_iMaxConns(0) {};
    ~ConnPool();

    int setMaxConns(int max);
    void decMaxConn()           {   --m_iMaxConns;      }
    int getMaxConns() const     {   return m_iMaxConns; }
    void adjustMaxConns()       {   m_iMaxConns = m_connList.size();    }

    int getTotalConns() const   {   return m_connList.size();   }

    int getFreeConns() const    {   return m_freeList.size();   }

    int getUsedConns() const    {   return m_connList.size() - m_freeList.size();   }

    int regConn(IConnection *pConn);

    IConnection *getFreeConn()
    {
        if (m_freeList.empty())
            return NULL;
        else
            return m_freeList.pop_back();
    }

    IConnection *getBadConn()
    {
        if (m_badList.empty())
            return NULL;
        else
            return m_badList.pop_back();
    }

    void for_each(gpl_for_each_fn fn)
    {   m_connList.for_each(m_connList.begin(), m_connList.end(), fn);    }

    void reuse(IConnection *pConn)
    {
        assert(pConn);
        m_freeList.unsafe_push_back(pConn);
    }

    int  inFreeList(IConnection *pConn);
    void removeConn(IConnection *pConn);
    int canAddMore() const
    {   return m_iMaxConns > (int)m_connList.size(); }


    LS_NO_COPY_ASSIGN(ConnPool);
};


#endif

