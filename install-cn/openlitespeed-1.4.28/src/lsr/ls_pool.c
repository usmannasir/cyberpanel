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
/**
 * @file
 * Implementation for pool std
 */


#include <lsdef.h>
#include <lsr/ls_lock.h>
#include <lsr/ls_atomic.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_internal.h>
#include <stdlib.h>
#include <pthread.h>
#include <lsr/ls_memcheck.h>
        
#ifdef DEBUG_POOL

#define ls_pool_getblk     ls_sys_getblk
#define ls_pool_putblk     ls_sys_putblk
#define ls_pool_putnblk    ls_sys_putnblk

#else

#define ls_pool_getblk     ls_lkstd_getblk
#define ls_pool_putblk     ls_lkstd_putblk
#define ls_pool_putnblk    ls_lkstd_putnblk

#endif


#define SMFREELISTBUCKETS       256
#define SMFREELISTINTERVAL      16
#define SMFREELIST_MAXBYTES     (SMFREELISTBUCKETS*SMFREELISTINTERVAL)
#define LGFREELISTBUCKETS       64
#define LGFREELISTINTERVAL      1024
#define LGFREELIST_MAXBYTES     (LGFREELISTBUCKETS*LGFREELISTINTERVAL)
#define REALLOC_DIFF            1024
#define MAX_HEAP_PTRS           16
#define MAX_HEAP_MASK           15

#define FREELISTBUCKETS         (256 + 64)
#define FREELIST_MULTI          16
#define FREELIST_MULTI_MASK     15

#define MAGIC     (0x506f4f6c) //"PoOl"

enum { LSR_ALIGN = 16 };

typedef struct _alink_s
{
    struct _alink_s    *next;
} _alink_t;


typedef struct
{
    __link_t           *head;
    __link_t           *tail;
    size_t     blkcnt;
    ls_spinlock_t       lck;
} ls_blkctrl_t;


typedef struct heap_ptr_s
{
    char               *start_free;
    char               *end_free;
    ls_spinlock_t       heap_lock;
    ls_atom_32_t        lock_fails;
    ls_atom_32_t        lock_oks;
} heap_ptr_t;


typedef struct ls_pool_s
{
    ls_blkctrl_t        freelists[FREELIST_MULTI][FREELISTBUCKETS];
    heap_ptr_t          heaps[MAX_HEAP_PTRS];
    int32_t             thr_seq;
    int32_t             pad;
    size_t              heap_size; /* approximate cumulative
                                       allocated bytes, not threadsafe
                                       so may be off a bit */
#ifdef POOL_TESTING
    unsigned short      cur_heaps;
    unsigned short      cur_multi[FREELISTBUCKETS];
#endif /* POOL_TESTING */
} ls_pool_t;


typedef struct ls_pool_tls_s 
{
    int             thr_seq;
    int             heap_switch;
    heap_ptr_t     *heap_ptr;
    ls_blkctrl_t   *flist_ptrs[FREELISTBUCKETS];
    int             flist_switch[FREELISTBUCKETS];
} ls_pool_tls_t;


/* Global pool structure.
*/
static ls_pool_t ls_pool_g =
{
    { },                /* freelists[][] */
    {                   /* heaps - start */
        {               /* heaps[0] - start */
            NULL,       /* start_free */
            NULL,       /* end_free */

            LS_LOCK_AVAIL,  /* _heap_lock */
            0,          /* lock_fails */
            0,          /* lock_oks */

        }               /* heaps[0] - end */
    },                  /* heaps - end */
    0,                  /* thr_seq      */
    0,
    0,                  /* _heap_size */
#ifdef POOL_TESTING
    0,                  /* cur_heaps */
    {                   /* cur_multi */
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    },
#endif /* POOL_TESTING */
};


__thread ls_pool_tls_t _tls = 
{
    -1,  /* _thr_seq */
    0,
    &ls_pool_g.heaps[0],
    {NULL},
    {0},
};


/**
 * @ls_sys_getblk
 */
ls_inline void *ls_sys_getblk(ls_blkctrl_t *p, size_t size)
{
    return malloc(size);
}


/**
 * @ls_sys_putblk
 */
ls_inline void ls_sys_putblk(size_t size, ls_blkctrl_t *p, void *pNew)
{
    free(pNew);
    return;
}


/**
 * @ls_sys_putnblk
 */
ls_inline void ls_sys_putnblk(size_t size, ls_blkctrl_t *p, void *pNew, void *pTail, size_t count)
{
    __link_t *pPtr;
    do
    {
        pPtr = (__link_t *)pNew;
        pNew = pPtr->next;
        free(pPtr);
    }
    while (pPtr != pTail);
    return;
}


#ifdef DEBUG_LKSTD
ls_inline void ls_lkstd_verifyblkcnt_do(ls_blkctrl_t * p)
{
    __link_t * pHead = NULL;
    size_t ct = 0;
    for (pHead = p->head; pHead != NULL; pHead = pHead->next, ct++) 
    {}
    fprintf(stderr, "verify block count %ld should be %ld\n", ct, p->blkcnt);
    assert(ct == p->blkcnt);
}
#define ls_lkstd_verifyblkcnt(a) ls_lkstd_verifyblkcnt_do(a)
#else
#define ls_lkstd_verifyblkcnt(a)
#endif


/**
 * @ls_lkstd_getblk
 *
 * warning: assumes p locked
 */
ls_inline void *ls_lkstd_getblk(ls_blkctrl_t *p, size_t size)
{
    __link_t *ptr;

    ls_lkstd_verifyblkcnt(p);

    if ((ptr = p->head) != NULL)
    {
        MEMCHK_UNPOISON(ptr, sizeof(*ptr));
        if ((p->head = ptr->next) == NULL)
            p->tail = NULL;

        p->blkcnt--;

        ls_lkstd_verifyblkcnt(p);
    }
    return (void *)ptr;
}


/**
 * @ls_lkstd_putblk
 *
 * warning: assumes p locked
 */
ls_inline void ls_lkstd_putblk(size_t size, ls_blkctrl_t *p, void *pNew)
{

    ls_lkstd_verifyblkcnt(p);

    if (p->tail == NULL)
        p->head = (__link_t *)pNew;
    else
    {
        MEMCHK_UNPOISON(p->tail, sizeof(__link_t));
        p->tail->next = (__link_t *)pNew;
        MEMCHK_POISON(p->tail, sizeof(__link_t));
    }
    p->tail = (__link_t *)pNew;

    MEMCHK_POISON(pNew, sizeof(__link_t));

    p->blkcnt++;
    ls_lkstd_verifyblkcnt(p);

    return;
}


/**
 * @ls_lkstd_putnblk
 *
 * warning: assumes p locked
 */
ls_inline void ls_lkstd_putnblk(size_t size, ls_blkctrl_t *p, 
                                void *pNew, void *pTail, size_t nblocks)
{

    ls_lkstd_verifyblkcnt(p);

    if (p->tail == NULL)
        p->head = (__link_t *)pNew;
    else
    {
        MEMCHK_UNPOISON(p->tail, sizeof(__link_t));
        p->tail->next = (__link_t *)pNew;
        MEMCHK_POISON(p->tail, sizeof(__link_t));
    }
    p->tail = (__link_t *)pTail;
    p->blkcnt += nblocks;
    ls_lkstd_verifyblkcnt(p);
    return;
}


ls_inline size_t pool_roundup(size_t bytes)
{ return (((bytes) + (size_t)LSR_ALIGN - 1) & ~((size_t)LSR_ALIGN - 1)); }


/* skew offset to handle requests expected to be in round k's
*/
#define LGFREELISTSKEW \
    ( ( sizeof(ls_xpool_bblk_t) + sizeof(ls_pool_blk_t) \
        + (size_t)LSR_ALIGN-1 ) & ~((size_t)LSR_ALIGN-1) )
ls_inline size_t freelistindex(size_t bytes)
{
    if (bytes <= (size_t)SMFREELIST_MAXBYTES)
        return (((bytes) + (size_t)SMFREELISTINTERVAL - 1)
                / (size_t)SMFREELISTINTERVAL - 1);
    else
        return (((bytes) - LGFREELISTSKEW + (size_t)
                 LGFREELISTINTERVAL - 1)
                    / (size_t)LGFREELISTINTERVAL - 1) + SMFREELISTBUCKETS;
}


ls_inline void chk_tid_seq()
{
    if (_tls.thr_seq != -1) 
    {
        return;
    }
    _tls.thr_seq = ls_atomic_fetch_add(&ls_pool_g.thr_seq, 1);
}


#ifdef POOL_TESTING
/* statistics functions start */

unsigned short ls_pool_cur_heaps() 
{
    unsigned short h;
    ls_pool_g.cur_heaps = 0;
    for (h = 0; h < MAX_HEAP_PTRS; h++) 
    {
        if (ls_pool_g.heaps[h].start_free) 
        {
            ls_pool_g.cur_heaps++;
        }
    }
    return ls_pool_g.cur_heaps;
}


unsigned short * ls_pool_get_multi(short *len) 
{
    // this is only called from test code, and the pool is not locked
    // (neither are the freelists)
    // so it's possible for it to poison improperly - though it should
    // only be called from the main thread after join() the test threads,
    // for safety, lock the each freelist before reading it
    unsigned short b, m;
    *len = FREELISTBUCKETS;
    for ( b = 0; b < FREELISTBUCKETS; b++) 
    {
        ls_pool_g.cur_multi[b] = 0;
        for (m = 0; m < FREELIST_MULTI; m++) 
        {
            ls_spinlock_lock(&ls_pool_g.freelists[m][b].lck);
            if (ls_pool_g.freelists[m][b].blkcnt) 
            {
                ls_pool_g.cur_multi[b]++;
            }
            ls_spinlock_unlock(&ls_pool_g.freelists[m][b].lck);
        }
    }
    return ls_pool_g.cur_multi;
}
#endif /* POOL_TESTING */


ls_inline ls_blkctrl_t *get_locked_freelist_ptr(size_t size)
{

    size_t size_index = freelistindex(size);
    ls_blkctrl_t **pflist = &_tls.flist_ptrs[size_index];
    int tries;
    
    if (!*pflist)
        *pflist = &ls_pool_g.freelists[size_index & FREELIST_MULTI_MASK][size_index];
    if (!ls_spinlock_trylock(&(*pflist)->lck)) 
    {
        return *pflist;
    }
    
    // dynamic switching avoidance
    for (tries = 0; tries <= _tls.flist_switch[size_index]; tries++) 
    {
        if (!ls_spinlock_trylock(&(*pflist)->lck)) 
        {
            return *pflist;
        }
        usleep(50);
    }

    *pflist += FREELISTBUCKETS;
    if (*pflist >= &ls_pool_g.freelists[FREELIST_MULTI][0])
        *pflist -= FREELIST_MULTI * FREELISTBUCKETS;

    ls_spinlock_lock(&(*pflist)->lck);
    return *pflist;
}


ls_inline heap_ptr_t *get_locked_heap_ptr()
{
    if (!ls_spinlock_trylock(&_tls.heap_ptr->heap_lock))
    {
        return _tls.heap_ptr;
    }
    while(_tls.heap_switch < MAX_HEAP_MASK)
    {
        ++_tls.heap_ptr;
        ++_tls.heap_switch;
        if (!ls_spinlock_trylock(&_tls.heap_ptr->heap_lock))
        {
            return _tls.heap_ptr;
        }
    }
    chk_tid_seq();
    _tls.heap_ptr = &ls_pool_g.heaps[_tls.thr_seq & MAX_HEAP_MASK];
    ls_spinlock_lock(&_tls.heap_ptr->heap_lock);

    return _tls.heap_ptr;
}


ls_inline size_t lglist_roundup(size_t bytes)
{
    return ((((bytes) - LGFREELISTSKEW + (size_t)
                    LGFREELISTINTERVAL - 1)
                & ~((size_t)LGFREELISTINTERVAL - 1)) + LGFREELISTSKEW);
}


ls_inline void freelist_put(size_t size, ls_pool_blk_t *pNew)
{
    ls_blkctrl_t *pFreeList = get_locked_freelist_ptr(size);
    ls_pool_putblk(size, pFreeList, (void *)pNew);
    ls_spinlock_unlock(&pFreeList->lck);
}


ls_inline ls_pool_blk_t *freelist_get(size_t size)
{
    ls_blkctrl_t *pFreeList = get_locked_freelist_ptr(size);
    ls_pool_blk_t * ret = (ls_pool_blk_t *)ls_pool_getblk(pFreeList, size);
    ls_spinlock_unlock(&pFreeList->lck);
    return ret;
}


ls_inline void freelist_putn(
        size_t size, ls_pool_blk_t *pNew, ls_pool_blk_t *pTail, size_t count)
{
    ls_blkctrl_t *pFreeList = get_locked_freelist_ptr(size);
    ls_pool_putnblk(size, pFreeList, (void *)pNew, (void *)pTail, count);
    ls_spinlock_unlock(&pFreeList->lck);
}


#ifndef DEBUG_POOL
/* Allocates a chunk for nobjs of size size.  nobjs may be reduced
 * if it is inconvenient to allocate the requested number.
 */
static char *chunk_alloc(heap_ptr_t * heap_ptrs, size_t size, int *pNobjs);


/* Gets an object of size num, and optionally adds to size num.
 * free list.
 */
static void *refill(size_t num);
#endif /* DEBUG_POOL */


char *ls_pdupstr(const char *p)
{
    if (p != NULL)
        return ls_pdupstr2(p, strlen(p) + 1);
    return NULL;
}


char *ls_pdupstr2(const char *p, int len)
{
    if (p != NULL)
    {
        char *ps = (char *)ls_palloc(len);
        if (ps != NULL)
            memmove(ps, p, len);
        return ps;
    }
    return NULL;
}


void ls_pinit()
{
    MEMCHK_NEWPOOL(&ls_pool_g, 0, 0);
    return;
}


void *ls_palloc_slab(size_t size)
{
    size_t rndnum;
    void *ptr;

    if (size > (size_t)LGFREELIST_MAXBYTES)
        return malloc(size);
    else
    {
        rndnum = pool_roundup(size);
        ptr = freelist_get(rndnum);
        if (ptr == NULL)
        {
            if (rndnum > (size_t)SMFREELIST_MAXBYTES)
            {
                size_t memnum = lglist_roundup(rndnum);
                ptr = malloc(memnum);
                MEMCHK_POISON_CHKNUL(ptr, memnum); 
            }
#ifndef DEBUG_POOL
            else
                ptr = refill(rndnum);
#endif
        }
    }
    MEMCHK_ALLOC_CHKNUL(&ls_pool_g, ptr, size); 
    return ptr;
}


void ls_pfree_slab(void *p, size_t size)
{
    if (p == NULL)
        return;
    size = pool_roundup(size);
    if (size > (size_t)LGFREELIST_MAXBYTES)
        ls_sys_putblk(size, NULL, p);
    else
    {
        ls_pool_blk_t *pBlk = (ls_pool_blk_t *)p;
        pBlk->next = NULL;
        MEMCHK_FREE(&ls_pool_g, pBlk, size); 
        freelist_put(size, pBlk);
    }
}


ls_inline void *ls_prealloc_slab_int(void *old_p, size_t old_sz, size_t new_sz, int copy)
{
    void *result;
    size_t copy_sz;

    if ((old_sz > (size_t) LGFREELIST_MAXBYTES)
            && (new_sz > (size_t) LGFREELIST_MAXBYTES))
        return realloc(old_p, new_sz);
    result = ls_palloc_slab(new_sz);
    if (result == NULL)
        return NULL;
    if (copy)
    {
        copy_sz = new_sz > old_sz ? old_sz : new_sz;
        if (copy_sz)
        {
            memmove(result, old_p, copy_sz);
        }
    }
    if (old_sz)
        ls_pfree_slab(old_p, old_sz);
    return (result);
}


void *ls_prealloc_slab(void *old_p, size_t old_sz, size_t new_sz)
{
    if (old_p == NULL)
        return ls_palloc_slab(new_sz);

    if (old_sz >= new_sz && old_sz - new_sz <= REALLOC_DIFF)
    {
        MEMCHK_UNPOISON(old_p, new_sz); 
        MEMCHK_POISON(old_p + new_sz, old_sz - new_sz); 
        return old_p;
    }
    return ls_prealloc_slab_int(old_p, old_sz, new_sz, 1);
}


void *ls_palloc(size_t size)
{
    size_t rndnum;
    ls_pool_blk_t *ptr;
    size += sizeof(ls_pool_blk_t);
    rndnum = pool_roundup(size);
    ptr = (ls_pool_blk_t *)ls_palloc_slab(size);
    if (ptr)
    {
        ptr->header.size = rndnum;
        ptr->header.magic = MAGIC;
        MEMCHK_POISON(ptr, sizeof(*ptr)); 
        return (void *)(ptr + 1);
    }
    return NULL;
}


void ls_pfree(void *p)
{
    if (p != NULL)
    {
        ls_pool_blk_t *pBlk = ((ls_pool_blk_t *)p) - 1;
        MEMCHK_UNPOISON(pBlk, sizeof(*pBlk)); 
#ifdef INTERNAL_DEBUG
        assert(pBlk->m_header.m_magic == MAGIC);
#endif
        if (pBlk->header.size > (size_t)LGFREELIST_MAXBYTES)
            ls_sys_putblk(pBlk->header.size, NULL, (void *)pBlk);
        else
        {
            size_t size = pBlk->header.size;
            pBlk->next = NULL;
            MEMCHK_FREE(&ls_pool_g, pBlk, size); 
            freelist_put(size, pBlk);
        }
    }
}


ls_inline void *ls_prealloc_int(void *old_p, size_t new_sz, int copy)
{
    if (old_p == NULL)
        return ls_palloc(new_sz);

    ls_pool_blk_t *pBlk = ((ls_pool_blk_t *)old_p) - 1;
    MEMCHK_UNPOISON(pBlk, sizeof(*pBlk));    
#ifdef INTERNAL_DEBUG
    assert(pBlk->m_header.m_magic == MAGIC);
#endif
    size_t old_sz = pBlk->header.size;
    size_t val_sz = new_sz + sizeof(ls_pool_blk_t);
    val_sz = pool_roundup(val_sz);

    if (old_sz >= val_sz && old_sz - val_sz <= REALLOC_DIFF)
    {
        MEMCHK_POISON(pBlk, sizeof(*pBlk)); 
        MEMCHK_POISON(old_p + val_sz, old_sz - val_sz); 
        MEMCHK_UNPOISON(pBlk+1, new_sz); 
        return old_p;
    }
    if (copy)
    {
        MEMCHK_UNPOISON(pBlk, old_sz); 
    }

    pBlk = (ls_pool_blk_t *)ls_prealloc_slab_int(pBlk, old_sz, val_sz, copy);
    if (pBlk != NULL)
    {
        pBlk->header.size = val_sz;
        pBlk->header.magic = MAGIC;
        MEMCHK_POISON(pBlk, sizeof(*pBlk)); 
        return (void *)(pBlk + 1);
    }
    return NULL;
}


void *ls_prealloc(void *old_p, size_t new_sz)
{
    return ls_prealloc_int(old_p, new_sz, 1);
}


void *ls_preserve(void *old_p, size_t new_sz)
{
    return ls_prealloc_int(old_p, new_sz, 0);
}


#ifndef DEBUG_POOL
/*
 * try to allocate chunk of memory using current heap pointers
 *
 * called from refill(), which is called from ls_palloc_slab
 * when it can't find a block on a freelist to satisfy the ls_palloc
 * request
 * also called recursively if it had to get more memory (from malloc or
 * freelist_alloc)
 *
 * ls_palloc_slab calls refill() when size <= SMFREELIST_MAXBYTES, otherwise
 * it goes to malloc instead
 * since chunk_alloc calls itself, we must ensure invariant (below) - it should
 * never increase size before calling itself
 */
static char *chunk_alloc(heap_ptr_t * heap_ptrs, size_t size, int *pNobjs)
{
    char *result;

    size_t total_bytes = size * (*pNobjs);
    size_t bytes_left = heap_ptrs->end_free - heap_ptrs->start_free;

    if (bytes_left >= total_bytes)
    {
        /* we have enough bytes on current heap to satisfy entire request */
        result = heap_ptrs->start_free;
        heap_ptrs->start_free += total_bytes;
        return result;
    }

    if (bytes_left >= size)
    {
        /* not enough for full request, but can fulfill at least 1 object */
        *pNobjs = (int)(bytes_left / size);
        total_bytes = size * (*pNobjs);
        result = heap_ptrs->start_free;
        heap_ptrs->start_free += total_bytes;
        return result;
    }

    /* invariant: as size <= SMFREELIST_MAXBYTES, if we got this far
       bytes_left  will not be > SMFREELIST_MAXBYTES */

    /* we don't have enough bytes in local heap ptrs to provide even 1 object. if
       large enough, save the left-over piece on a freelist */
    if (bytes_left >= pool_roundup(sizeof(ls_pool_blk_t)))
    {
        ls_pool_blk_t *pBlk = (ls_pool_blk_t *)heap_ptrs->start_free;
        MEMCHK_UNPOISON(pBlk, sizeof(*pBlk));
        pBlk->next = NULL;
        freelist_put(bytes_left, pBlk);
    }

    /* pick a size to allocate - start with double request size and add dynamic
       padding factor based on heap allocated so far */

    size_t bytes_to_get = 2 * total_bytes
        + pool_roundup(ls_pool_g.heap_size >> 4);


    /* try malloc */
    heap_ptrs->start_free = (char *)ls_sys_getblk(NULL, bytes_to_get);

    if (heap_ptrs->start_free != NULL) {
        /* got memory from malloc, set up heap size and ptrs and try allocating again */

        MEMCHK_POISON(heap_ptrs->start_free, bytes_to_get);
        ls_pool_g.heap_size += bytes_to_get;
        heap_ptrs->end_free = heap_ptrs->start_free + bytes_to_get;

        /* maintains size invariant */
        return chunk_alloc(heap_ptrs, size, pNobjs);
    }

    heap_ptrs->end_free = 0;    /* In case of exception. */
    *pNobjs = 0;
    /* couldn't allocate from a freelist either */
    return NULL;

}


static void *refill(size_t block_size)
{
    int nobjs = 16;

    /* thread local */
    heap_ptr_t * heap_ptrs = get_locked_heap_ptr();
    char *chunk = chunk_alloc(heap_ptrs, block_size, &nobjs);
    ls_spinlock_unlock(&heap_ptrs->heap_lock);
    _alink_t   *pPtr;
    char       *pNext;

    if (nobjs <= 1)
        return chunk;       /* freelist still empty; no head or tail */

    pNext = chunk + block_size;    /* skip past first block returned to caller */
    --nobjs;
    size_t count = nobjs;
    while (nobjs-- > 0)
    {
        pPtr = (_alink_t *)pNext;
        if (nobjs == 0)
            pNext = NULL;
        else
            pNext += block_size;
        MEMCHK_UNPOISON(pPtr, sizeof(*pPtr));
        pPtr->next = (_alink_t *)pNext;
        MEMCHK_POISON(pPtr, sizeof(*pPtr));
    }
    freelist_putn(block_size, (ls_pool_blk_t *)(chunk + block_size), (ls_pool_blk_t *)pPtr, count);

    return chunk;
}
#endif /* DEBUG_POOL */


/* free a null terminated linked list.
 * all the elements are expected to have the same size, `size'.
 */
void ls_plistfree(ls_pool_blk_t *plist, size_t size)
{
    if (plist == NULL)
        return;
    ls_pool_blk_t *pNext;
    size = pool_roundup(size + sizeof(ls_pool_blk_t));
#ifdef INTERNAL_DEBUG
    assert(plist->m_header.m_magic == MAGIC);
#endif
    if (size > (size_t)LGFREELIST_MAXBYTES)
    {
        do
        {
            pNext = plist->next;
            ls_sys_putblk(size, NULL, (void *)plist);
        }
        while ((plist = pNext) != NULL);
        return;
    }
    pNext = plist;
    size_t count = 1;
    MEMCHK_UNPOISON(pNext, sizeof(ls_pool_blk_t)); 
    while (pNext->next != NULL)         /* find last in list */
    {
        ls_pool_blk_t *pTmp = pNext;
        count++;
        pNext = pNext->next;
        MEMCHK_UNPOISON(pNext, sizeof(ls_pool_blk_t)); 
        MEMCHK_FREE(&ls_pool_g, pTmp, size); 
    }
    MEMCHK_FREE(&ls_pool_g, pNext, size); 
    freelist_putn(size, plist, pNext, count);

    return;
}




