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

#include <lsr/ls_lfqueue.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_atomic.h>

//#define LSR_LLQ_DEBUG

#include <stdio.h>
#include <stdlib.h>
#include <string.h>


struct ls_mpscq_s
{
    volatile ls_lfnoden_t    *m_pHead;
    ls_lfnoden_t             *m_pTail;
};

#ifdef LSR_LLQ_DEBUG
static int MYINDX;
#endif


ls_mpscq_t *ls_mpscq_new(ls_lfnoden_t *pNode)
{
    ls_mpscq_t *pThis;
    if ((pThis = (ls_mpscq_t *)ls_palloc(sizeof(*pThis))) != NULL)
    {
        if (ls_mpscq_init(pThis, pNode) < 0)
        {
            ls_pfree(pThis);
            pThis = NULL;
        }
    }

    return pThis;
}

int ls_mpscq_init(ls_mpscq_t *pThis, ls_lfnoden_t *pNode)
{
    pNode->next = NULL;
    pThis->m_pHead = pNode;
    pThis->m_pTail = pNode;

    return 0;
}

void ls_mpscq_destroy(ls_mpscq_t *pThis)
{
    if (pThis)
        memset(pThis, 0, sizeof(*pThis));
    return;
}

void ls_mpscq_delete(ls_mpscq_t *pThis)
{
    if (pThis)
    {
        ls_mpscq_destroy(pThis);
        ls_pfree(pThis);
    }
    return;
}

int ls_mpscq_put(ls_mpscq_t *pThis, ls_lfnoden_t *data)
{
    data->next = NULL;
    ls_lfnoden_t *prev = ls_atomic_setptr((void **)&pThis->m_pHead, data);
    prev->next = data;

    return 0;
}

ls_lfnoden_t *ls_mpscq_get(ls_mpscq_t *pThis)
{
    ls_lfnoden_t *tail = pThis->m_pTail;
    ls_lfnoden_t *next = (ls_lfnoden_t *)tail->next;
    if (next)
    {
        pThis->m_pTail = next;
        tail->pobj = next->pobj;
        return tail;
    }

    return NULL;
}

int ls_mpscq_empty(ls_mpscq_t *pThis)
{
    return (pThis->m_pTail->next == NULL);
}

