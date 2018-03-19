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

#include <lsr/ls_xpool.h>
#include <lsr/ls_lock.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_lfstack.h>
#include <lsdef.h>
#include <lsr/ls_internal.h>
#include <lsr/ls_memcheck.h>
// #include <lsr/ls_xpool_int.h>

#define LS_XPOOL_DATA_ALIGN         (8)
#define LS_XPOOL_NUMFREELISTS       (16)
#define LS_XPOOL_FLINTERVAL         (16)
#define LS_XPOOL_FLINTERVAL_SHIFT   (4)
#define LS_XPOOL_FLMAXBYTES         (256)
#define LS_XPOOL_SUPBLK_SIZE        (4*1024)
#define LS_XPOOL_MAXLGBLK_SIZE      (LS_XPOOL_SUPBLK_SIZE)
#define LS_XPOOL_MAXSMBLK_SIZE      1024

#define LS_XPOOL_NOFREE    1

#define LS_XPOOL_MAGIC     (0x58704f6c) //"XpOl"

// #       include <lsr/ls_xpool_std.h>

typedef __link_t            ls_xblkctrl_t;

typedef struct ls_xpool_sb_s        ls_xpool_sb_t;
typedef struct xpool_alink_s        xpool_alink_t;
typedef struct xpool_qlist_s        xpool_qlist_t;

/**
 * @ls_pool_insptr
 */
ls_inline void ls_pool_insptr(ls_pool_blk_t **pBase, ls_pool_blk_t *pNew)
{
    pNew->next = *pBase;
    *pBase = pNew;
    return;
}



int xpool_freelistinit(ls_xpool_t *pool);

/**
 * @struct ls_qlist_s
 * @brief Session memory pool list management.
 */
struct xpool_qlist_s
{
    xpool_alink_t      *ptr;
    ls_lfstack_t        stack;
    ls_spinlock_t       lock;
};

/**
 * @struct ls_xpool_s
 * @brief Session memory pool top level management.
 */
struct ls_xpool_s
{
    ls_pool_blk_t      *psuperblk;
    xpool_qlist_t       smblk;
    xpool_qlist_t       lgblk;
    ls_xpool_bblk_t    *pbigblk;
    ls_xblkctrl_t      *pfreelists;
    int                 flag;
    int                 init;
    ls_spinlock_t       lock;
    ls_spinlock_t       freelistlock;
};

/**
 * @ls_xpool_chkinit
 */
ls_inline int ls_xpool_chkinit(
        ls_xpool_t *pPool, ls_xblkctrl_t **pPtr, int *pFlag)
{
    int ret = 0;
    ls_spinlock_lock(&pPool->freelistlock);
    if (*pPtr == NULL) {
        ret = xpool_freelistinit(pPool);
    }
    ls_spinlock_unlock(&pPool->freelistlock);
    return ret;
}

/**
 * @ls_xpool_setup
 */
ls_inline void ls_xpool_setup(ls_xblkctrl_t *p)
{
    return;
}

/**
 * @ls_xpool_cleanup
 */
ls_inline void ls_xpool_cleanup(ls_xblkctrl_t *p)
{
    return;
}

/**
 * @ls_xpool_getblk
 */
ls_inline void *ls_xpool_getblk(ls_xblkctrl_t *p)
{
    __link_t *pNew = p->next;
    if (pNew)
    {
        MEMCHK_UNPOISON(pNew, sizeof(__link_t));
        MEMCHK_UNPOISON(p->next, sizeof(__link_t));
        p->next = pNew->next;
    }
    return (void *)pNew;
}

/**
 * @ls_xpool_putblk
 */
ls_inline void ls_xpool_putblk(ls_xblkctrl_t *p, void *pNew)
{
    MEMCHK_UNPOISON(pNew, sizeof(__link_t));
    //MEMCHK_UNPOISON(p, sizeof(ls_xblkctrl_t));
    ((__link_t *)pNew)->next = p->next;
    p->next = (__link_t *)pNew;
    MEMCHK_POISON(pNew, sizeof(__link_t));
    return;
}

struct xpool_alink_s
{
    ls_xpool_header_t header;
    union
    {
        struct xpool_alink_s *next;
        char data[1];
    };
};

static int xpool_maxgetablk_trys =
3;   /* how many attempts to find a suitable block */
static int xpool_maxblk_trys =
3;       /* how many attempts until moving block */

/* Get a new superblock from Global Pool/OS */
static xpool_alink_t *ls_xpool_getsuperblk(ls_xpool_t *pool);

/* Get a big allocation for any requests for allocations bigger than the superblock */
static void *ls_xpool_bblkalloc(ls_xpool_t *pool, uint32_t nsize);

/* Get a block */
static xpool_alink_t *xpool_blkget(ls_xpool_t *pool, uint32_t size);
static xpool_alink_t *xpool_getablk(
        ls_xpool_t *pool, xpool_qlist_t *pHead, uint32_t size);


/* Carve a piece from an existing block */
ls_inline xpool_alink_t *xpool_blkcarve(xpool_alink_t *pNew, uint32_t size)
{
    MEMCHK_UNPOISON(&pNew->header, sizeof(pNew->header));
    pNew->header.size = size;
    pNew->header.magic = LS_XPOOL_MAGIC;
    return pNew;
}


enum {_XPOOL_ALIGN = 16 };
ls_inline size_t ls_xpool_roundup(size_t bytes)
{ return (((bytes) + (size_t) _XPOOL_ALIGN - 1) & ~((size_t) _XPOOL_ALIGN - 1)); }


/* Release big block to OS */
ls_inline void ls_xpool_bblkfree(ls_xpool_bblk_t *pBblk)
{
    ls_pfree((void *)pBblk);
}


/* Manage freelist pointers */
ls_inline int xpool_freelistindx(size_t size)
{   return ((size >> LS_XPOOL_FLINTERVAL_SHIFT) - 1);   }


ls_inline ls_xblkctrl_t *size2xfreelistptr(ls_xpool_t *pool, size_t size)
{
    return &pool->pfreelists[ xpool_freelistindx(size) ];
}


int xpool_freelistinit(ls_xpool_t *pool)
{
    ls_xblkctrl_t *ptr;
    if ((ptr = ls_xpool_alloc(
                    pool, sizeof(*(pool->pfreelists)) * LS_XPOOL_NUMFREELISTS)) == NULL)
        return LS_FAIL;
    memset(ptr, 0, sizeof(*(pool->pfreelists)) * LS_XPOOL_NUMFREELISTS);

    ls_xblkctrl_t *p = ptr;
    int i = LS_XPOOL_NUMFREELISTS;
    while (--i >= 0)
    {
        ls_xpool_setup(p);
        ++p;
    }
    pool->pfreelists = ptr;

    return LS_OK;
}


#if !defined( LS_VG_DEBUG )
/* Put on freelist */
ls_inline void xfreelistput(ls_xpool_t *pool, xpool_alink_t *pFree,
        size_t size)
{
    ls_xblkctrl_t *pFreeList = size2xfreelistptr(pool, size); // which list
    ls_spinlock_lock(&pool->freelistlock);
    ls_xpool_putblk(pFreeList, (void *)pFree->data);
    ls_spinlock_unlock(&pool->freelistlock);
    return;
}
#endif //!defined( LS_VG_DEBUG )


/* Get from freelist */
ls_inline xpool_alink_t *xfreelistget(ls_xpool_t *pool, size_t size)
{
    ls_xblkctrl_t *pFreeList = size2xfreelistptr(pool, size);
    ls_spinlock_lock(&pool->freelistlock);
    char *ptr = (char *)ls_xpool_getblk(pFreeList);
    ls_spinlock_unlock(&pool->freelistlock);

    if (ptr == NULL)
        return NULL;
    return (xpool_alink_t *)(ptr - sizeof(ls_xpool_header_t));
}


/* Put on large or small block list */
ls_inline void xpool_blkput(xpool_qlist_t *head, xpool_alink_t *pFree)
{
    MEMCHK_UNPOISON(&pFree->header, sizeof(pFree->header));
    pFree->header.magic = 0; /* reset - use as failure counter */
    MEMCHK_POISON(&pFree->header, sizeof(pFree->header));
    ls_spinlock_lock(&head->lock);
    MEMCHK_UNPOISON(&pFree->next, sizeof(pFree->next));
    pFree->next = head->ptr;
    head->ptr = pFree;
    MEMCHK_POISON(&pFree->next, sizeof(pFree->next));
    ls_spinlock_unlock(&head->lock);
}


/* Remove from large or small block list */
ls_inline void xpool_blkremove(
        xpool_qlist_t *pHead, xpool_alink_t *pPrev, xpool_alink_t *pPtr)
{
    if (pPrev == NULL)
        pHead->ptr = pPtr->next;
    else
    {
        MEMCHK_UNPOISON(&pPrev->next, sizeof(pPrev->next));
        pPrev->next = pPtr->next;
        MEMCHK_POISON(&pPrev->next, sizeof(pPrev->next));
    }
}


void ls_xpool_init(ls_xpool_t *pool)
{
    memset(pool, 0, sizeof(ls_xpool_t));
#if ( LS_LOCK_AVAIL != 0 )
    NEED TO SETUP LOCKS
#endif
    MEMCHK_NEWPOOL(pool, 0, 0);
}


void ls_xpool_destroy(ls_xpool_t *pool)
{
    ls_spinlock_lock(&pool->freelistlock);
    if (pool->pfreelists != NULL)
    {
        ls_xblkctrl_t *p = pool->pfreelists;
        int i = LS_XPOOL_NUMFREELISTS;
        while (--i >= 0)
        {
            ls_xpool_cleanup(p); // this is a no-op
            ++p;
        }
    }
    ls_spinlock_unlock(&pool->freelistlock);

    ls_plistfree((ls_pool_blk_t *)pool->psuperblk, LS_XPOOL_SUPBLK_SIZE);

    ls_psavepending(pool->pbigblk);
    ls_pfreepending();

    memset(pool, 0, sizeof(ls_xpool_t));
    MEMCHK_DESTROY_POOL(pool);
}


void ls_xpool_reset(ls_xpool_t *pool)
{
    ls_xpool_destroy(pool);
#if ( LS_LOCK_AVAIL != 0 )
    NEED TO SETUP LOCKS
#endif
    MEMCHK_NEWPOOL(pool, 0, 0);
}


int ls_xpool_isempty(ls_xpool_t *pool)
{
    assert(pool);
    return ((pool->psuperblk == NULL) && (pool->pbigblk == NULL));
}


void *ls_xpool_alloc(ls_xpool_t *pool, uint32_t size)
{
    uint32_t nsize;
    xpool_alink_t *pNew;
    nsize = ls_xpool_roundup(size + sizeof(ls_xpool_header_t));
#if !defined( LS_VG_DEBUG )
    if (nsize > LS_XPOOL_MAXLGBLK_SIZE)
#endif
    {
        return ls_xpool_bblkalloc(pool, nsize);
    }

    if (nsize <= LS_XPOOL_FLMAXBYTES && (pool->pfreelists != NULL))
    {
        if ((pNew = xfreelistget(pool, nsize)) != NULL)
        {
            MEMCHK_ALLOC(pool, pNew, size + sizeof(ls_xpool_header_t));
            MEMCHK_POISON(&pNew->header, sizeof(pNew->header));
            return pNew->data;   /* do *not* change real size of block */
        }
    }
    pNew = xpool_blkget(pool, nsize);
    MEMCHK_ALLOC(pool, pNew, size + sizeof(ls_xpool_header_t));
    MEMCHK_POISON(&pNew->header, sizeof(pNew->header));
    return pNew->data;
}


void *ls_xpool_calloc(ls_xpool_t *pool, uint32_t items, uint32_t size)
{
    void *pPtr;
    int allocsz = items * size;
    if ((pPtr = ls_xpool_alloc(pool, allocsz)) != NULL)
        memset(pPtr, 0, allocsz);
    return pPtr;
}


void *ls_xpool_realloc(ls_xpool_t *pool, void *pOld, uint32_t new_sz)
{
    if (pOld == NULL)
        return ls_xpool_alloc(pool, new_sz);
    ls_xpool_header_t *pHeader = (ls_xpool_header_t *)((char *)pOld - sizeof(
                ls_xpool_header_t));
    MEMCHK_UNPOISON(pHeader, sizeof(*pHeader));
    MEMCHK_UNPOISON(pHeader, pHeader->size);

    uint32_t old_sz = pHeader->size - sizeof(ls_xpool_header_t);
#ifdef LS_XPOOL_INTERNAL_DEBUG
    assert(pHeader->magic == LS_XPOOL_MAGIC);
#endif
    if (new_sz <= old_sz)
    {
        MEMCHK_FREE(pool, (xpool_alink_t *)pHeader, pHeader->size);
        MEMCHK_ALLOC(pool, (xpool_alink_t *)pHeader, new_sz + sizeof(ls_xpool_header_t));
        MEMCHK_POISON(&((xpool_alink_t *)pHeader)->header, sizeof(((xpool_alink_t*)pHeader)->header));
        MEMCHK_UNPOISON(pOld, new_sz);
        return pOld;
    }
    void *pNew;
    if ((pNew = ls_xpool_alloc(pool, new_sz)) != NULL)
    {
        memmove(pNew, pOld, old_sz);
        ls_xpool_free(pool, pOld);
    }
    return pNew;
}


static xpool_alink_t *xpool_blkget(ls_xpool_t *pool, uint32_t size)
{
    int remain;
    xpool_alink_t *pPtr;

    if ((size <= LS_XPOOL_MAXSMBLK_SIZE)
            // && (pool->smblk.ptr != NULL)    /* optimization in non-thread mode */
            && ((pPtr = xpool_getablk(pool, &pool->smblk, size)) != NULL))
        return pPtr;
    if (1
            // && (pool->lgblk.ptr != NULL)    /* optimization in non-thread mode */
            && ((pPtr = xpool_getablk(pool, &pool->lgblk, size)) != NULL))
        return pPtr;

    pPtr = ls_xpool_getsuperblk(pool);
    pPtr->header.size -= size;
    remain = (int)pPtr->header.size;
    if (remain < (int)(((LS_XPOOL_NUMFREELISTS + 1)
                    *LS_XPOOL_FLINTERVAL)))
    {
        /* return the full residual (or could have added to freelist)
        */
        size += remain;
        remain = 0;
    }
    else
    {
        xpool_blkput(((remain <= (int)(LS_XPOOL_MAXSMBLK_SIZE)) ?
                    &pool->smblk : &pool->lgblk), pPtr);
    }

    return xpool_blkcarve((xpool_alink_t *)((char *)pPtr + remain), size);
}


static xpool_alink_t *xpool_getablk(
        ls_xpool_t *pool, xpool_qlist_t *pHead, uint32_t size)
{
    int remain;
    int trys = xpool_maxgetablk_trys;
    ls_spinlock_lock(&pHead->lock);
    if (pHead->ptr == NULL)
    {
        ls_spinlock_unlock(&pHead->lock);
        return NULL;
    }
    xpool_alink_t *pPtr = pHead->ptr;
    xpool_alink_t *pPrev = NULL;
#ifdef LS_XPOOL_INTERNAL_DEBUG
    assert(pPtr != NULL);       /* guaranteed by caller */
    assert(trys > 0);
#endif
    do
    {
        MEMCHK_UNPOISON(pPtr, sizeof(*pPtr));
        if ((remain = (int)pPtr->header.size - (int)size) >= 0)
        {
            pPtr->header.size = remain;
            if (remain <
                    (int)(((LS_XPOOL_NUMFREELISTS + 1)*LS_XPOOL_FLINTERVAL)))
            {
                /* return the full residual (or could have added to freelist)
                */
                size += remain;
                remain = 0;
                xpool_blkremove(pHead, pPrev, pPtr);
            }
            /* check if a large block becomes a small block
            */
            else if ((pHead == &pool->lgblk)
                    && (remain <= (int)(LS_XPOOL_MAXSMBLK_SIZE)))
            {
                xpool_blkremove(pHead, pPrev, pPtr);
                xpool_blkput(&pool->smblk, pPtr);
            }
            ls_spinlock_unlock(&pHead->lock);
            return xpool_blkcarve(
                    (xpool_alink_t *)((char *)pPtr + remain), size);
        }
        /* if this block is `never' getting chosen, remove it
        */
        if (++pPtr->header.magic >= (uint32_t)xpool_maxblk_trys)
        {
            xpool_alink_t *pNext = pPtr->next;
            xpool_blkremove(pHead, pPrev, pPtr);
            if (pHead == &pool->lgblk)
                xpool_blkput(&pool->smblk, pPtr);
            pPtr = pNext;
        }
        else
        {
            pPrev = pPtr;
            pPtr = pPtr->next;
            MEMCHK_POISON(pPrev, sizeof(*pPrev));
        }
    }
    while ((pPtr != NULL) && (--trys >= 0));

    ls_spinlock_unlock(&pHead->lock);
    return NULL;
}


/* NOTE: when allocating an xpool superblock,
 * we overwrite the gpool header size/magic with the xpool superblock link,
 * (which is what ls_pfree does),
 * permitting us to later free the list as a whole.
 */
static xpool_alink_t *ls_xpool_getsuperblk(ls_xpool_t *pool)
{
    xpool_alink_t *pNew = (xpool_alink_t *)ls_palloc(LS_XPOOL_SUPBLK_SIZE);
    ls_pool_blk_t *pBlk = ((ls_pool_blk_t *)pNew) -
        1;  /* ptr to real gpool block */
    MEMCHK_UNPOISON(pBlk, sizeof(*pBlk));
    MEMCHK_POISON(pNew->data, pBlk->header.size
            - sizeof(ls_pool_blk_t)
            - sizeof(ls_xpool_header_t));
    ls_pool_insptr(&pool->psuperblk,
            pBlk);    /* overwrites size/magic with link */
    MEMCHK_POISON(pBlk, sizeof(*pBlk));
    pNew->header.size = LS_XPOOL_MAXLGBLK_SIZE;
    pNew->header.magic = LS_XPOOL_MAGIC;
    return pNew;
}


void *ls_xpool_bblkalloc(ls_xpool_t *pool, uint32_t nsize)
{
    ls_xpool_bblk_t *pNew;
    pNew = (ls_xpool_bblk_t *)ls_palloc(nsize + sizeof(ls_xpool_bblk_t)
            - sizeof(ls_xpool_header_t));
    pNew->header.size = nsize;
    pNew->header.magic = LS_XPOOL_MAGIC;
    pNew->prev = NULL;
    MEMCHK_POISON(&pNew->header, sizeof(pNew->header));
    ls_spinlock_lock(&pool->lock);
    pNew->next = pool->pbigblk;
    if (pool->pbigblk != NULL)
        pool->pbigblk->prev = pNew;
    pool->pbigblk = pNew;
    ls_spinlock_unlock(&pool->lock);
    return (void *)pNew->data;
}


static void ls_xpool_unlink(ls_xpool_t *pool, ls_xpool_bblk_t *pFree)
{
    ls_spinlock_lock(&pool->lock);
    ls_xpool_bblk_t *pNext = pFree->next;
    ls_xpool_bblk_t *pPrev = pFree->prev;

    if (pNext != NULL)
        pNext->prev = pPrev;
    if (pPrev != NULL)
        pPrev->next = pNext;
    else
        pool->pbigblk = pNext;
    ls_spinlock_unlock(&pool->lock);
}

void ls_xpool_free(ls_xpool_t *pool, void *data)
{
    if (data == NULL)
        return;
#if !defined( LS_VG_DEBUG )
    ls_xpool_header_t *pHeader = (ls_xpool_header_t *)
        ((char *)data - sizeof(ls_xpool_header_t));     /* header size */
    MEMCHK_UNPOISON(pHeader, sizeof(ls_xpool_header_t));
#ifdef LS_XPOOL_INTERNAL_DEBUG
    assert(pHeader->magic == LS_XPOOL_MAGIC);
#endif
    uint32_t size = pHeader->size; // what kind of block was it?
    if (size > LS_XPOOL_MAXLGBLK_SIZE)
    {
#endif
        ls_xpool_bblk_t *pFree = ((ls_xpool_bblk_t *)data) - 1; // big block
        ls_xpool_unlink(pool, pFree);
        ls_xpool_bblkfree(pFree);
        return;
#if !defined( LS_VG_DEBUG )
    }
    MEMCHK_FREE(pool, pHeader, size);
    if (pool->flag & LS_XPOOL_NOFREE)
        return;
    if (size <= LS_XPOOL_FLMAXBYTES) // freelist block
    {
        if (ls_xpool_chkinit(pool, &pool->pfreelists, &pool->init) == LS_OK)
            xfreelistput(pool, (xpool_alink_t *)pHeader, size);
    }
    else // from stack (qlist - smblk or lgblk
    {
        xpool_blkput(((size <= LS_XPOOL_MAXSMBLK_SIZE) ?
                    &pool->smblk : &pool->lgblk), (xpool_alink_t *)pHeader);
    }
#endif
}


void ls_xpool_skipfree(ls_xpool_t *pool)
{
    pool->flag |= LS_XPOOL_NOFREE;
}


ls_xpool_t *ls_xpool_new()
{
    ls_xpool_t *pool = ls_palloc(sizeof(ls_xpool_t));
    if (pool != NULL)
        ls_xpool_init(pool);
    return pool;
}


void ls_xpool_delete(ls_xpool_t *pool)
{
    ls_xpool_destroy(pool);
    ls_pfree(pool);
}


static ls_xpool_bblk_t    *s_pendingfree = NULL;

#define ls_pool_getlist    ls_std_getlist
#define ls_pool_inslist    ls_std_inslist


/**
 * @ls_std_getlist
 */
ls_inline ls_xpool_bblk_t *ls_std_getlist(ls_xpool_bblk_t **pList)
{
    ls_xpool_bblk_t *pPtr = ls_atomic_setptr(pList, NULL);
    return pPtr;
}

/**
 * @ls_std_inslist
 */
ls_inline void ls_std_inslist(
        ls_xpool_bblk_t **pList, ls_xpool_bblk_t *pNew, ls_xpool_bblk_t *pTail)
{
    ls_xpool_bblk_t *pOld, *pOld1;
    ls_atomic_load(pOld, pList);
    do
    {
        pTail->next = pOld1 = pOld;
    }
    while((pOld = ls_atomic_casvptr(pList, pNew, pOld)) != pOld1);
    return;
}


/* save the pending xpool `bigblock' linked list to be freed later.
 * NOTE: we do *not* maintain the reverse link.
 */
void ls_psavepending(ls_xpool_bblk_t *plist)
{
    if (plist == NULL)
        return;
    ls_xpool_bblk_t *pPtr = plist;
    while (pPtr->next != NULL)          /* find last in list */
        pPtr = pPtr->next;

    ls_pool_inslist((ls_xpool_bblk_t **)&s_pendingfree, plist, pPtr);

    return;
}


/* free the pending xpool `bigblock' linked list to where the pieces go.
 */
void ls_pfreepending()
{
    ls_xpool_bblk_t *pPtr;
    ls_xpool_bblk_t *pNext;
    pPtr = ls_pool_getlist((ls_xpool_bblk_t **)&s_pendingfree);

    while (pPtr != NULL)
    {
        pNext = pPtr->next;
        ls_pfree(pPtr);
        pPtr = pNext;
    }

    return;
}



