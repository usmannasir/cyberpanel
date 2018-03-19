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

#include <lsr/ls_internal.h>
#include <lsr/ls_lfqueue.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_atomic.h>

//#define LSR_LLQ_DEBUG

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sched.h>
#include <unistd.h>

#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
#include <linux/futex.h>
#include <sys/syscall.h>


static inline int do_wait(void *volatile *ptr, struct timespec *timeout)
{
    int ret = 0;
    // glibc does not provide a wrapper for futex(2)
    if (syscall(SYS_futex, (int *)ptr, FUTEX_WAIT, 0, timeout, NULL, 0) < 0)
    {
        if ((errno == ETIMEDOUT) || (errno == EINVAL))
            ret = -1;
#ifdef notdef
        else if (errno == EWOULDBLOCK)
            ;
#endif
    }
    return ret;
}


static inline void do_wake(void *volatile *ptr)
{
    int retry = 3;
    // glibc does not provide a wrapper for futex(2)
    while ((syscall(SYS_futex, (int *)ptr, FUTEX_WAKE, 1, NULL, NULL, 0) < 1)
           && (--retry > 0))
        ;
    return;
}


static inline int no_wait(struct timespec *timeout)
{
    return (timeout && (timeout->tv_sec == 0) && (timeout->tv_nsec == 0));
}
#endif


#define MYPAUSE     sched_yield()
//#define MYPAUSE     usleep( 250 )


ls_lfqueue_t *ls_lfqueue_new()
{
    ls_lfqueue_t *pThis;
    if ((pThis = (ls_lfqueue_t *)ls_palloc(sizeof(*pThis))) != NULL)
    {
        if (ls_lfqueue_init(pThis) < 0)
        {
            ls_pfree(pThis);
            pThis = NULL;
        }
    }

    return pThis;
}


int ls_lfqueue_init(ls_lfqueue_t *pThis)
{
    pThis->tail.m_ptr = NULL;
    pThis->tail.m_seq = 0;
    pThis->phead = (volatile ls_lfnodei_t * volatile *)&pThis->tail.m_ptr;

    return 0;
}


void ls_lfqueue_destroy(ls_lfqueue_t *pThis)
{
    if (pThis)
        memset(pThis, 0, sizeof(*pThis));
    return;
}


void ls_lfqueue_delete(ls_lfqueue_t *pThis)
{
    if (pThis)
    {
        ls_lfqueue_destroy(pThis);
        ls_pfree(pThis);
    }
    return;
}


int ls_lfqueue_put(ls_lfqueue_t *pThis, ls_lfnodei_t *data)
{
    data->next = NULL;
    ls_lfnodei_t *prev = ls_atomic_setptr((void **)&pThis->phead, data);
    prev->next = data;
#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
    if (prev == (ls_lfnodei_t *)&pThis->tail.m_ptr)
        do_wake(&pThis->tail.m_ptr);
#endif

    return 0;
}


int ls_lfqueue_putn(
    ls_lfqueue_t *pThis, ls_lfnodei_t *data1, ls_lfnodei_t *datan)
{
    datan->next = NULL;
    ls_lfnodei_t *prev = ls_atomic_setptr((void **)&pThis->phead, datan);
    prev->next = data1;
#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
    if (prev == (ls_lfnodei_t *)&pThis->tail.m_ptr)
        do_wake(&pThis->tail.m_ptr);
#endif

    return 0;
}


ls_lfnodei_t *ls_lfqueue_get(ls_lfqueue_t *pThis)
{
    ls_atom_xptr_t tail;

    tail.m_ptr = pThis->tail.m_ptr;
    tail.m_seq = pThis->tail.m_seq;
    while (1)
    {
        ls_atom_xptr_t prev;
        ls_atom_xptr_t xchg;
        ls_lfnodei_t *pnode = (ls_lfnodei_t *)tail.m_ptr;
        if (pnode == NULL)
            return NULL;

        if (pnode->next)
        {
            xchg.m_ptr = (void *)pnode->next;
            xchg.m_seq = tail.m_seq + 1;

            ls_atomic_dcasv(
                (ls_atom_xptr_t *)&pThis->tail, &tail, &xchg, &prev);

            if ((prev.m_ptr == tail.m_ptr) && (prev.m_seq == tail.m_seq))
                return pnode;
        }
        else
        {
            ls_lfnodei_t *p = (ls_lfnodei_t *)pThis->phead;
            if (pnode != p)
            {
                MYPAUSE;
                tail.m_ptr = pThis->tail.m_ptr;
                tail.m_seq = pThis->tail.m_seq;
                continue;
            }
            xchg.m_ptr = NULL;
            xchg.m_seq = tail.m_seq + 1;

            ls_atomic_dcasv(
                (ls_atom_xptr_t *)&pThis->tail, &tail, &xchg, &prev);

            if ((prev.m_ptr == tail.m_ptr) && (prev.m_seq == tail.m_seq))
            {
                ls_lfnodei_t *prevhead = (ls_lfnodei_t *)ls_atomic_casvptr(
                                             (volatile void **)&pThis->phead, pnode, (void *)&pThis->tail.m_ptr);

                if (prevhead == pnode)
                    return pnode;

                while (pnode->next == NULL)
                    MYPAUSE;
                pThis->tail.m_ptr = (void *)pnode->next;

                return pnode;
            }
        }
        tail.m_ptr = prev.m_ptr;
        tail.m_seq = prev.m_seq;
    }
}


#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
ls_lfnodei_t *ls_lfqueue_timedget(ls_lfqueue_t *pThis,
                                  struct timespec *timeout)
{
    ls_lfnodei_t *data;
    while ((data = ls_lfqueue_get(pThis)) == NULL)
    {
        if (no_wait(timeout))       /* no wait timeout */
            break;
        if (do_wait(&pThis->tail.m_ptr, timeout) < 0)
            break;
    }
    return data;
}
#endif


int ls_lfqueue_empty(ls_lfqueue_t *pThis)
{
    return (pThis->tail.m_ptr == NULL);
}
