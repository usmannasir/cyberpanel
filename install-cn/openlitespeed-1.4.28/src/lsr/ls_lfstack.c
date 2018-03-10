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

#include <lsr/ls_atomic.h>
#include <lsr/ls_lfstack.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_internal.h>

#include <stddef.h>
#include <string.h>
#include <unistd.h>


#define LSR_LFSTACK_SLEEP_TIME 250

ls_lfstack_t *ls_lfstack_new()
{
    ls_lfstack_t *pThis;
    if ((pThis = (ls_lfstack_t *)ls_palloc(sizeof(ls_lfstack_t))) != NULL)
        ls_lfstack_init(pThis);
    return pThis;
}

void ls_lfstack_init(ls_lfstack_t *pThis)
{
    pThis->head.m_ptr = NULL;
    pThis->head.m_seq = 0;
}

void ls_lfstack_destroy(ls_lfstack_t *pThis)
{
    if (pThis)
        memset(pThis, 0, sizeof(ls_lfstack_t));
    return;
}

void ls_lfstack_delete(ls_lfstack_t *pThis)
{
    if (pThis)
    {
        ls_lfstack_destroy(pThis);
        ls_pfree(pThis);
    }
    return;
}

static int ls_lfstack_trypush(ls_lfstack_t *pThis, ls_lfnodei_t *pNode)
{
    ls_atom_xptr_t oldHead;
    ls_atom_xptr_t newHead;
    ls_atomic_load(oldHead, (ls_atom_xptr_t *) & (pThis->head));
    pNode->next = oldHead.m_ptr;
    newHead.m_ptr = pNode;
    newHead.m_seq = oldHead.m_seq + 1;
    return ls_atomic_dcas((ls_atom_xptr_t *) & (pThis->head), &oldHead,
                          &newHead);
}

static int ls_lfstack_trypop(ls_lfstack_t *pThis, ls_lfnodei_t **ret)
{
    ls_atom_xptr_t oldHead;
    ls_atom_xptr_t newHead;
    *ret = NULL;
    ls_atomic_load(oldHead, (ls_atom_xptr_t *) & (pThis->head));
    if (oldHead.m_ptr == NULL)
        return 1;
    *ret = oldHead.m_ptr;
    ls_atomic_load(newHead.m_ptr, (void **) & ((*ret)->next));
    newHead.m_seq = oldHead.m_seq + 1;
    if (ls_atomic_dcas((ls_atom_xptr_t *) & (pThis->head), &oldHead, &newHead))
    {
        (*ret)->next = NULL;
        return 1;
    }
    return 0;
}


int ls_lfstack_push(ls_lfstack_t *pThis, ls_lfnodei_t *pNode)
{
    while (1)
    {
        if (ls_lfstack_trypush(pThis, pNode))
            return 0;
        usleep(LSR_LFSTACK_SLEEP_TIME);
    }
}

ls_lfnodei_t *ls_lfstack_pop(ls_lfstack_t *pThis)
{
    ls_lfnodei_t *ret;
    while (1)
    {
        if (ls_lfstack_trypop(pThis, &ret))
            return ret;
        usleep(LSR_LFSTACK_SLEEP_TIME);
    }
}



