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
#ifndef LINKQUEUE_H
#define LINKQUEUE_H

#include <lsr/ls_lfqueue.h>

#include <cstddef>

class LinkedQueue
{
private:
    ls_lfqueue_t *m_pQueue;

    LinkedQueue(const LinkedQueue &rhs);
    void operator=(LinkedQueue &rhs);

public:
    LinkedQueue()
    {
        m_pQueue = ls_lfqueue_new();
    }

    ~LinkedQueue()
    {
        ls_lfqueue_delete(m_pQueue);
    }

    int put(ls_lfnodei_t *pNode);
    int put(ls_lfnodei_t **pNodes, int size);

    ls_lfnodei_t *get();
    int get(ls_lfnodei_t **pNodes, int size);

    int empty()
    {
        return ls_lfqueue_empty(m_pQueue);
    }
};



#endif //LINKQUEUE_H

