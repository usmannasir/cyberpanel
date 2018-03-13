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

#include <lsr/ls_llmq.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_atomic.h>

//#define LSR_LLQ_DEBUG

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdbool.h>
#include <linux/futex.h>
#include <sys/syscall.h>
#include <errno.h>
#include <lsdef.h>

static inline bool llmq_atom_cmp_and_swap(
    ls_atom_uint_t *pVal, unsigned *pcmp, unsigned swap)
{
    unsigned prev = (unsigned)
                    ls_atomic_casvint((ls_atom_32_t *)pVal, (int32_t)(*pcmp), (int32_t)swap);
    if (prev == *pcmp)
        return true;
    *pcmp = prev;
    return false;
}

typedef struct
{
    ls_atom_uint_t  m_iSeq;
    void            *m_data;
} qobj_t;

#define CACHE_SIZE  64
typedef char cachepad_t [CACHE_SIZE];

struct ls_llmq_s
{
    cachepad_t       m_pad0;
    qobj_t          *m_QObjs;
    unsigned int     m_mask;
    cachepad_t       m_pad1;
    ls_atom_uint_t  m_iPutIndx;
    cachepad_t       m_pad2;
    ls_atom_uint_t  m_iGetIndx;
    cachepad_t       m_pad3;
    ls_atom_uint_t  m_iPutWait;
    ls_atom_uint_t  m_iGetWait;
};

#ifdef LSR_LLQ_DEBUG
static int MYINDX;
#endif

static inline qobj_t *indx2qobj(ls_llmq_t *pThis, int indx)
{
    return &pThis->m_QObjs[indx & pThis->m_mask];
}

static inline int no_wait(struct timespec *timeout)
{
    return (timeout && (timeout->tv_sec == 0) && (timeout->tv_nsec == 0));
}

static inline int do_wait(ls_atom_uint_t *pCnt, ls_atom_uint_t *pIndx,
                          int val, struct timespec *timeout)
{
    int ret = 0;
    ls_atomic_add((int *)pCnt, 1);
    if (syscall(SYS_futex, (int *)pIndx, FUTEX_WAIT, val, timeout, NULL,
                0) < 0)
    {
        if ((errno == ETIMEDOUT) || (errno == EINVAL))
            ret = -1;
#ifdef LSR_LLQ_DEBUG
        else if (errno == EWOULDBLOCK)
            printf("%d] EWOULDBLOCK %d\n",
                   ls_atomic_add(&MYINDX, 1),
                   val);
#endif
    }
    ls_atomic_sub((int *)pCnt, 1);
    return ret;
}

#ifdef LSR_LLQ_DEBUG
static inline void do_wake(int cnt, ls_atom_uint_t *ptr, char *msg,
                           ls_llmq_t *pThis, int xxx)
{
    int ret;
    int retry = 5;
    printf("%d] WAKE UP %s: xxx=%d, put=%d, get=%d\n",
           ls_atomic_add(&MYINDX, 1),
           msg, xxx, (int)pThis->m_iPutIndx, (int)pThis->m_iGetIndx);
    while (((ret =
                 syscall(SYS_futex, (int *)ptr, FUTEX_WAKE, cnt, NULL, NULL, 0)) < 1)
           && (--retry > 0))
    {
        printf("RETRY wake up %s: ret=%d\n", msg, ret);
        ;
    }
    printf("%d] WAKE UP: put=%d, get=%d, woke=%d\n",
           ls_atomic_add(&MYINDX, 1),
           (int)pThis->m_iPutIndx, (int)pThis->m_iGetIndx, ret);
    return;
}
#else
static inline void do_wake(int cnt, ls_atom_uint_t *ptr)
{
    int retry = 5;
    while ((
               syscall(SYS_futex, (int *)ptr, FUTEX_WAKE, cnt, NULL, NULL, 0) < 1)
           && (--retry > 0))
        ;
    return;
}
#endif

static inline void wake_producers(ls_llmq_t *pThis, int indx)
{
    ls_atom_uint_t val;
    ls_atomic_load(val, &pThis->m_iPutWait);
    if (val != 0)
    {
        do_wake(1, &pThis->m_iGetIndx
#ifdef LSR_LLQ_DEBUG
                , (char *)"put", pThis, indx
#endif
               );
    }
    return;
}

static inline void wake_consumers(ls_llmq_t *pThis, int indx)
{
    ls_atom_uint_t val;
    ls_atomic_load(val, &pThis->m_iGetWait);
    if (val != 0)
    {
        do_wake(1, &pThis->m_iPutIndx
#ifdef LSR_LLQ_DEBUG
                , (char *)"get", pThis, indx
#endif
               );
    }
    return;
}

ls_llmq_t *ls_llmq_new(unsigned int size)
{
    ls_llmq_t *pThis;
    if ((pThis = (ls_llmq_t *)ls_palloc(sizeof(*pThis))) != NULL)
    {
        if (ls_llmq_init(pThis, size) < 0)
        {
            ls_pfree(pThis);
            pThis = NULL;
        }
    }

    return pThis;
}

int ls_llmq_init(ls_llmq_t *pThis, unsigned int size)
{
    if ((size < 2) || ((size & (size - 1)) != 0))
        return LS_FAIL;
    qobj_t *pPtr;
    if ((pPtr = (qobj_t *)ls_palloc(size * sizeof(*pPtr))) == NULL)
        return LS_FAIL;
    pThis->m_QObjs = pPtr;

    unsigned int i;
    for (i = 0; i < size; ++i)
    {
        ls_atomic_store(&pPtr->m_iSeq, i);
        ++pPtr;
    }
    ls_atomic_store(&pThis->m_iPutIndx, 0);
    ls_atomic_store(&pThis->m_iGetIndx, 0);
    pThis->m_mask = size - 1;

    return 0;
}

void ls_llmq_destroy(ls_llmq_t *pThis)
{
    if (pThis)
    {
        if (pThis->m_QObjs != NULL)
            ls_pfree((void *)pThis->m_QObjs);
        memset(pThis, 0, sizeof(*pThis));
    }
    return;
}

void ls_llmq_delete(ls_llmq_t *pThis)
{
    if (pThis)
    {
        ls_llmq_destroy(pThis);
        ls_pfree(pThis);
    }
    return;
}

static int llmq_put(ls_llmq_t *pThis, void *data, int *pWaitVal)
{
    unsigned int indx;
    qobj_t *pPtr;
    unsigned int seq;
    int diff;
    while (1)
    {
        ls_atomic_load(indx, &pThis->m_iPutIndx);
        pPtr = indx2qobj(pThis, indx);
        ls_atomic_load(seq, &pPtr->m_iSeq);
        diff = (int)seq - (int)indx;
        if (diff == 0)
        {
            if (llmq_atom_cmp_and_swap(&pThis->m_iPutIndx, &indx, indx + 1))
                break;
        }
        else if (diff < 0)
        {
            *pWaitVal = seq - 1;
            return LS_FAIL;
        }
    }
    pPtr->m_data = data;
#ifdef LSR_LLQ_DEBUG
    int putIndx = (int)pThis->m_iPutIndx;
    int getIndx = (int)pThis->m_iGetIndx;
    int myIndx = ls_atomic_add(&MYINDX, 1);
#endif
    ++indx;
    ls_atomic_store(&pPtr->m_iSeq, indx);
#ifdef LSR_LLQ_DEBUG
    printf("%d] PUT=%d,%d: %d/%d\n",
           myIndx,
           (int)data, indx - 1, putIndx, getIndx);
#endif
    wake_consumers(pThis, indx);

    return 0;
}

int ls_llmq_timedput(ls_llmq_t *pThis, void *data,
                     struct timespec *timeout)
{
    int waitval;
    while (llmq_put(pThis, data, &waitval) < 0)
    {
        if (no_wait(timeout))                   /* no wait timeout */
            return LS_FAIL;
#ifdef LSR_LLQ_DEBUG
        printf("%d] WAITING to put, put[%d] %d/%d\n",
               ls_atomic_add(&MYINDX, 1),
               waitval, (int)pThis->m_iPutIndx, (int)pThis->m_iGetIndx);
#endif
        if (do_wait(&pThis->m_iPutWait, &pThis->m_iGetIndx, waitval, timeout) < 0)
            return LS_FAIL;
    }
    return 0;
}

static void *llmq_get(ls_llmq_t *pThis, int *pWaitVal)
{
    unsigned int indx;
    qobj_t *pPtr;
    unsigned int seq;
    int diff;
    while (1)
    {
        ls_atomic_load(indx, &pThis->m_iGetIndx);
        pPtr = indx2qobj(pThis, indx);
        ls_atomic_load(seq, &pPtr->m_iSeq);
        diff = (int)seq - (int)(indx + 1);
        if (diff == 0)
        {
            if (llmq_atom_cmp_and_swap(&pThis->m_iGetIndx, &indx, indx + 1))
                break;
        }
        else if (diff < 0)
        {
            *pWaitVal = seq;
            return NULL;
        }
    }
    void *data = pPtr->m_data;
#ifdef LSR_LLQ_DEBUG
    int putIndx = (int)pThis->m_iPutIndx;
    int getIndx = (int)pThis->m_iGetIndx;
    int myIndx = ls_atomic_add(&MYINDX, 1);
#endif
    indx += (1 + pThis->m_mask);
    ls_atomic_store(&pPtr->m_iSeq, indx);

#ifdef LSR_LLQ_DEBUG
    printf("%d] GOT=%d,%d: %d/%d\n",
           myIndx,
           (int)data, indx - (1 + pThis->m_mask), putIndx, getIndx);
#endif
    wake_producers(pThis, indx);

    return data;
}

void *ls_llmq_timedget(ls_llmq_t *pThis, struct timespec *timeout)
{
    int waitval = 0;
    void *data;
    while ((data = llmq_get(pThis, &waitval)) == NULL)
    {
        if (no_wait(timeout))       /* no wait timeout */
            return NULL;
#ifdef LSR_LLQ_DEBUG
        printf("%d] WAITING to get... get[%d] %d/%d\n",
               ls_atomic_add(&MYINDX, 1),
               waitval, (int)pThis->m_iPutIndx, (int)pThis->m_iGetIndx);
#endif
        if (do_wait(&pThis->m_iGetWait, &pThis->m_iPutIndx, waitval, timeout) < 0)
            return NULL;
    }
    return data;
}

