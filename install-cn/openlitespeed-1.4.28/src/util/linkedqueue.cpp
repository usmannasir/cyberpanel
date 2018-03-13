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
#include <util/linkedqueue.h>
#include <lsdef.h>

int LinkedQueue::put(ls_lfnodei_t *pNode)
{
    return ls_lfqueue_put(m_pQueue, pNode);
}

int LinkedQueue::put(ls_lfnodei_t **pNodes, int size)
{
    if (pNodes == NULL || size <= 0)
        return LS_FAIL;
    int ret;
    ls_lfnodei_t **p = pNodes + size;
    while (pNodes < p)
    {
        if ((ret = put(*(pNodes++))) != 0)
            return ret;
    }
    return size;
}

ls_lfnodei_t *LinkedQueue::get()
{
    return ls_lfqueue_get(m_pQueue);
}

int LinkedQueue::get(ls_lfnodei_t **pNodes, int size)
{
    int iGot = 0;
    ls_lfnodei_t *ptr;
    while (iGot < size)
    {
        ptr = get();
        if (!ptr)
            break;
        *(pNodes + (iGot++)) = ptr;
    }

    return iGot;
}




