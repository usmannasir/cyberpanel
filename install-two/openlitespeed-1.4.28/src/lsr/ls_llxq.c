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

#include <lsr/ls_llxq.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_atomic.h>
#include <lsr/ls_lock.h>

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

#ifdef cpu_relax
#undef cpu_relax
#endif
#if defined(__i386__) || defined(__ia64__) || defined(__x86_64) || defined(__x86_64__)
#define cpu_relax()         asm volatile("pause\n": : :"memory")
#else
#define cpu_relax()         ;
#endif

static inline bool llxq_atom_cmp_and_swap(
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

typedef struct
{
    cachepad_t       m_pad0;
    ls_atom_uint_t  m_iPutIndx;
    ls_atom_uint_t  m_iRefCnt;
    cachepad_t       m_pad1;
    ls_atom_uint_t  m_iGetIndx;
    cachepad_t       m_pad2;
    int              m_mask;
    qobj_t           m_QObjs[1];
} llxqinfo_t;

#define NUM_QUEUES  0x08    /* must be power of 2 */
struct ls_llxq_s
{
    cachepad_t       m_pad0;
    volatile llxqinfo_t   *m_pQInfo[NUM_QUEUES];
    cachepad_t       m_pad1;
    ls_atom_uint_t  m_iQPutIndx;
    cachepad_t       m_pad2;
    ls_atom_uint_t  m_iQGetIndx;
    cachepad_t       m_pad3;
    ls_atom_uint_t  m_iPutWait;
    ls_atom_uint_t  m_iGetWait;
};

#ifdef LSR_LLQ_DEBUG
static int MYINDX;
#endif

static inline qobj_t *indx2qobj(llxqinfo_t *pInfo, int indx)
{
    return &pInfo->m_QObjs[indx & pInfo->m_mask];
}

static inline volatile llxqinfo_t **indx2pqinfo(ls_llxq_t *pThis, int indx)
{
    return &pThis->m_pQInfo[indx & (NUM_QUEUES - 1)];
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
                           llxqinfo_t *pInfo, int xxx)
{
    int ret;
    int retry = 5;
    printf("%d] WAKE UP %s: xxx=%d, put=%d, get=%d\n",
           ls_atomic_add(&MYINDX, 1),
           msg, xxx, (int)pInfo->m_iPutIndx, (int)pInfo->m_iGetIndx);
    while (((ret =
                 syscall(SYS_futex, (int *)ptr, FUTEX_WAKE, cnt, NULL, NULL, 0)) < 1)
           && (--retry > 0))
    {
        printf("RETRY wake up %s: ret=%d\n", msg, ret);
        ;
    }
    printf("%d] WAKE UP: put=%d, get=%d, woke=%d\n",
           ls_atomic_add(&MYINDX, 1),
           (int)pInfo->m_iPutIndx, (int)pInfo->m_iGetIndx, ret);
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

static inline void wake_producers(ls_atom_uint_t *pCnt, llxqinfo_t *pInfo,
                                  int indx)
{
    ls_atom_uint_t cnt;
    ls_atomic_load(cnt, pCnt);
    if (cnt != 0)
    {
        do_wake(((indx <= 0) ? cnt + 5 : 1), &pInfo->m_iGetIndx
#ifdef LSR_LLQ_DEBUG
                , (char *)"put", pInfo, indx
#endif
               );
    }

    return;
}

static inline void wake_consumers(ls_atom_uint_t *pCnt, llxqinfo_t *pInfo,
                                  int indx)
{
    ls_atom_uint_t cnt;
    ls_atomic_load(cnt, pCnt);
    if (cnt != 0)
    {
        do_wake(((indx <= 0) ? cnt + 5 : 1), &pInfo->m_iPutIndx
#ifdef LSR_LLQ_DEBUG
                , (char *)"get", pInfo, indx
#endif
               );
    }
    return;
}

static inline void add_refcnt(llxqinfo_t *pInfo)
{
    ls_atomic_add((int *)&pInfo->m_iRefCnt, 1);
}

static inline void sub_refcnt(llxqinfo_t *pInfo)
{
    ls_atomic_sub((int *)&pInfo->m_iRefCnt, 1);
}

static inline void adv_getqueue(ls_llxq_t *pThis, llxqinfo_t *pInfo,
                                int qgindx)
{
#ifdef LSR_LLQ_DEBUG
    int indx = pInfo->m_iGetIndx;
#endif
    ls_atomic_store(&pThis->m_iQGetIndx, qgindx + 1);
#ifdef LSR_LLQ_DEBUG
    pInfo = (llxqinfo_t *)*indx2pqinfo(pThis, (int)pThis->m_iQGetIndx);
    printf("%d] SWAP(%d)%d, new %d/%d\n",
           ls_atomic_add(&MYINDX, 1),
           qgindx, indx, (int)pInfo->m_iPutIndx, (int)pInfo->m_iGetIndx);
#endif
    return;
}

static ls_lock_t llxqlock;

ls_llxq_t *ls_llxq_new(unsigned int size)
{
    ls_llxq_t *pThis;
    if ((pThis = (ls_llxq_t *)ls_palloc(sizeof(*pThis))) != NULL)
    {
        if (ls_llxq_init(pThis, size) < 0)
        {
            ls_pfree(pThis);
            pThis = NULL;
        }
    }
    return pThis;
}

int ls_llxq_init(ls_llxq_t *pThis, unsigned int size)
{
    memset(pThis, 0, sizeof(*pThis));
    ls_atomic_store(&pThis->m_iQPutIndx, -1);
    ls_lock_setup(&llxqlock);
    return ls_llxq_newqueue(pThis, size);
}

int ls_llxq_newqueue(ls_llxq_t *pThis, unsigned int size)
{
    if ((size < 2) || ((size & (size - 1)) != 0))
        return LS_FAIL;
    int qpindx;
    int qgindx;
    int nowindx;
    ls_atomic_load(qpindx, &pThis->m_iQPutIndx);
    ls_lock_lock(&llxqlock);
    ls_atomic_load(nowindx, &pThis->m_iQPutIndx);
    if (nowindx != qpindx)      /* someone else added a newqueue */
    {
        ls_lock_unlock(&llxqlock);
        return 1;
    }
    llxqinfo_t *oldpinfo;
    ls_atomic_load(qgindx, &pThis->m_iQGetIndx);
    if ((qpindx - qgindx) >= (NUM_QUEUES - 1))  /* prevent wrap around */
    {
#ifdef LSR_LLQ_DEBUG
        oldpinfo = (llxqinfo_t *)*indx2pqinfo(pThis, qgindx);
        printf("%d] NEWQUEUE(%d) size=%d WRAP, ref=%d %d/%d\n",
               ls_atomic_add(&MYINDX, 1),
               qpindx + 1, size,
               oldpinfo->m_iRefCnt, oldpinfo->m_iPutIndx, oldpinfo->m_iGetIndx);
#endif
        ls_lock_unlock(&llxqlock);
        return LS_FAIL;
    }

    /* if the buffer we are about to replace is the same size as the new one,
     * and it is currently `empty',
     * do not bother to create a new buffer.
     */
    int pindx;
    int gindx;
    if ((oldpinfo = (llxqinfo_t *)*indx2pqinfo(pThis, qpindx)) != NULL)
    {
        ls_atomic_load(pindx, &oldpinfo->m_iPutIndx);
        ls_atomic_load(gindx, &oldpinfo->m_iGetIndx);
        if (((unsigned int)(oldpinfo->m_mask + 1) == size)
            && ((pindx - gindx) < 3))
        {
            ls_lock_unlock(&llxqlock);
            return 0;
        }
    }
    llxqinfo_t *pinfo;
    llxqinfo_t *pprev;
    int infosize = sizeof(*pinfo) + ((size - 1) * sizeof(pinfo->m_QObjs[0]));
    if ((pinfo = (llxqinfo_t *)ls_palloc(infosize)) == NULL)
    {
        ls_lock_unlock(&llxqlock);
        return LS_FAIL;
    }
    memset(pinfo, 0, infosize);
    unsigned int i;
    qobj_t *pPtr = pinfo->m_QObjs;
    for (i = 0; i < size; ++i)
    {
        ls_atomic_store(&pPtr->m_iSeq, i);
        ++pPtr;
    }
    ls_atomic_store(&pinfo->m_iPutIndx, 0);
    ls_atomic_store(&pinfo->m_iGetIndx, 0);
    pinfo->m_mask = size - 1;
    pprev = ls_atomic_setptr(
                (void **)indx2pqinfo(pThis, qpindx + 1), (void *)pinfo);
    if (pprev != NULL)
        ls_pfree((void *)pprev);
    ls_atomic_store(&pThis->m_iQPutIndx, qpindx + 1);
    ls_lock_unlock(&llxqlock);
#ifdef LSR_LLQ_DEBUG
    printf("%d] NEWQUEUE(%d) size=%d\n",
           ls_atomic_add(&MYINDX, 1),
           qpindx + 1, size);
#endif

    wake_producers(&pThis->m_iPutWait, oldpinfo, 0);
    ls_atomic_load(qgindx, &pThis->m_iQGetIndx);
    oldpinfo = (llxqinfo_t *)*indx2pqinfo(pThis, qgindx);
    wake_consumers(&pThis->m_iGetWait, oldpinfo, 0);

    return 0;
}

void ls_llxq_destroy(ls_llxq_t *pThis)
{
    if (pThis)
    {
        int i;
        volatile llxqinfo_t **ppinfo = pThis->m_pQInfo;
        i = (int)(sizeof(pThis->m_pQInfo) / sizeof(pThis->m_pQInfo[0]));
        while (--i >= 0)
        {
            if (*ppinfo != NULL)
                ls_pfree((void *)*ppinfo);
            ++ppinfo;
        }
        memset(pThis, 0, sizeof(*pThis));
    }
    return;
}

void ls_llxq_delete(ls_llxq_t *pThis)
{
    if (pThis)
    {
        ls_llxq_destroy(pThis);
        ls_pfree(pThis);
    }
    return;
}

static int llxq_put(ls_llxq_t *pThis, void *data, llxqinfo_t **pPInfo,
                    int *pWaitVal)
{
    unsigned int qpindx;
    unsigned int qgindx;
    unsigned int qgindx2;
    llxqinfo_t *pinfo;
    llxqinfo_t *ginfo;
    unsigned int indx;
    qobj_t *pPtr;
    unsigned int seq;
    int diff;
    while (1)
    {
        ls_atomic_load(qgindx, &pThis->m_iQGetIndx);
        ls_atomic_load(qpindx, &pThis->m_iQPutIndx);
        pinfo = (llxqinfo_t *)*indx2pqinfo(pThis, qpindx);
        add_refcnt(pinfo);
        ls_atomic_load(indx, &pinfo->m_iPutIndx);
        pPtr = indx2qobj(pinfo, indx);
        ls_atomic_load(seq, &pPtr->m_iSeq);
        diff = (int)seq - (int)indx;
        /* if queue get index changed,
         * we should not put more on the old queue.
         */
        ginfo = (llxqinfo_t *)*indx2pqinfo(pThis, qgindx);
        ls_atomic_load(qgindx2, &pThis->m_iQGetIndx);
        if (qgindx != qgindx2)
        {
#ifdef LSR_LLQ_DEBUG
            printf("%d] getqueue change: qput[%d], qget[%d]\n",
                   ls_atomic_add(&MYINDX, 1),
                   qpindx, qgindx);
#endif
            ;
        }
        else if (diff == 0)
        {
            if (llxq_atom_cmp_and_swap(&pinfo->m_iPutIndx, &indx, indx + 1))
                break;
        }
        else if (diff < 0)
        {
            *pPInfo = pinfo;
            *pWaitVal = seq - 1;
            sub_refcnt(pinfo);
            wake_consumers(&pThis->m_iGetWait, ginfo, 0);
            return LS_FAIL;
        }
        sub_refcnt(pinfo);
    }
    pPtr->m_data = data;
#ifdef LSR_LLQ_DEBUG
    int putIndx = (int)pinfo->m_iPutIndx;
    int getIndx = (int)pinfo->m_iGetIndx;
    int myIndx = ls_atomic_add(&MYINDX, 1);
#endif
    ++indx;
    ls_atomic_store(&pPtr->m_iSeq, indx);
    sub_refcnt(pinfo);

#ifdef LSR_LLQ_DEBUG
    printf("%d] PUT=%d,%d: ref=%d %d/%d\n",
           myIndx,
           (int)data, indx - 1, (int)pinfo->m_iRefCnt, putIndx, getIndx);
#endif
    wake_consumers(&pThis->m_iGetWait, ginfo, indx);

    return 0;
}

int ls_llxq_put(ls_llxq_t *pThis, void *data)
{
    int waitval;
    llxqinfo_t *pinfo;
    int retry = 5;
    do
    {
        if (llxq_put(pThis, data, &pinfo, &waitval) == 0)
            return 0;
        if (--retry == 1)
        {
            if (ls_llxq_newqueue(pThis, (pinfo->m_mask + 1) << 1) < 0)
                return LS_FAIL;
            retry = 5;
        }
        else
            cpu_relax();
    }
    while (1);
}

int ls_llxq_timedput(ls_llxq_t *pThis, void *data,
                     struct timespec *timeout)
{
    int waitval;
    llxqinfo_t *pinfo;
    while (llxq_put(pThis, data, &pinfo, &waitval) < 0)
    {
        if (no_wait(timeout))                   /* no wait timeout */
            return LS_FAIL;
#ifdef LSR_LLQ_DEBUG
        printf("%d] WAITING to put, put[%d] %d/%d\n",
               ls_atomic_add(&MYINDX, 1),
               waitval, (int)pinfo->m_iPutIndx, (int)pinfo->m_iGetIndx);
#endif
        if (do_wait(&pThis->m_iPutWait, &pinfo->m_iGetIndx, waitval, timeout) < 0)
            return LS_FAIL;
    }
    return 0;
}

static void *llxq_get(ls_llxq_t *pThis, llxqinfo_t **pPInfo, int *pWaitVal)
{
    unsigned int qgindx;
    ls_atomic_load(qgindx, &pThis->m_iQGetIndx);
    llxqinfo_t *pinfo = (llxqinfo_t *)*indx2pqinfo(pThis, qgindx);
    unsigned int indx;
    qobj_t *pPtr;
    unsigned int seq;
    int diff;
    while (1)
    {
        ls_atomic_load(indx, &pinfo->m_iGetIndx);
        pPtr = indx2qobj(pinfo, indx);
        ls_atomic_load(seq, &pPtr->m_iSeq);
        diff = (int)seq - (int)(indx + 1);
        if (diff == 0)
        {
            if (llxq_atom_cmp_and_swap(&pinfo->m_iGetIndx, &indx, indx + 1))
                break;
        }
        else if (diff < 0)
        {
            unsigned int curqindx;
            unsigned int curpindx;
            unsigned int refcnt;
            ls_atomic_load(curqindx, &pThis->m_iQPutIndx);
            ls_atomic_load(curpindx, &pinfo->m_iPutIndx);
            ls_atomic_load(refcnt, &pinfo->m_iRefCnt);
            if ((qgindx < curqindx) && (indx == curpindx) && (refcnt == 0))
            {
                adv_getqueue(pThis, pinfo, qgindx);
                wake_consumers(&pThis->m_iGetWait, pinfo, 0);
                ls_atomic_load(qgindx, &pThis->m_iQGetIndx);
                pinfo = (llxqinfo_t *)*indx2pqinfo(pThis, qgindx);
            }
            else
            {
                *pPInfo = pinfo;
                *pWaitVal = seq;
                return NULL;
            }
        }
    }
    void *data = pPtr->m_data;
#ifdef LSR_LLQ_DEBUG
    int putIndx = (int)pinfo->m_iPutIndx;
    int getIndx = (int)pinfo->m_iGetIndx;
    int myIndx = ls_atomic_add(&MYINDX, 1);
#endif
    indx += (1 + pinfo->m_mask);
    ls_atomic_store(&pPtr->m_iSeq, indx);

#ifdef LSR_LLQ_DEBUG
    printf("%d] GOT=%d,%d: %d/%d\n",
           myIndx,
           (int)data, indx - 1 - pinfo->m_mask, putIndx, getIndx);
#endif
    wake_producers(&pThis->m_iPutWait, pinfo, indx);

    return data;
}

void *ls_llxq_timedget(ls_llxq_t *pThis, struct timespec *timeout)
{
    int waitval = 0;
    llxqinfo_t *pinfo = NULL;
    void *data;
    while ((data = llxq_get(pThis, &pinfo, &waitval)) == NULL)
    {
        if (no_wait(timeout))       /* no wait timeout */
            return NULL;
#ifdef LSR_LLQ_DEBUG
        printf("%d] WAITING to get... get[%d] %d/%d\n",
               ls_atomic_add(&MYINDX, 1),
               waitval, (int)pinfo->m_iPutIndx, (int)pinfo->m_iGetIndx);
#endif
        if (do_wait(&pThis->m_iGetWait, &pinfo->m_iPutIndx, waitval, timeout) < 0)
            return NULL;
    }
    return data;
}
