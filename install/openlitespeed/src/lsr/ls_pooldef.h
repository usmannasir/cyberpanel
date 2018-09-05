/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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
#ifndef LS_POOLDEF_H
#define LS_POOLDEF_H

#include <stdlib.h>
#include <sys/types.h>
#include <lsr/ls_types.h>
#include <lsr/ls_internal.h>


/**
 * @file
 * The global (and session) memory pools may be configured in a number of ways
 * selectable through conditional compilation.
 * The default (no #defines) is to always use the system malloc and free.
 *
 * \li USE_LSRSTD_POOL - Define for standard lsr memory pool.
 * \li USE_THRSAFE_POOL - Define for thread safe lsr memory pool.
 * \li USE_VALGRIND - Define for valgrind tracking of lsr memory pool,
 *   applicable only if one of the lsr memory pools has been defined.
 *
 */


#ifdef __cplusplus
extern "C" {
#endif


/* default memory management is system malloc/free */

/* define for standard lsr memory pool */
//#define USE_LSRSTD_POOL

/* define for thread safe lsr memory pool */
//#define USE_THRSAFE_POOL

/* define for valgrind tracking of lsr memory pool */
//#define USE_VALGRIND

#ifdef USE_VALGRIND
#include <valgrind/memcheck.h>
#endif /* USE_VALGRIND */

typedef struct __link_s
{
    struct __link_s *next;
} __link_t;

#ifdef USE_THRSAFE_POOL
#undef USE_LSRSTD_POOL
#include <lsr/ls_lock.h>
#include <lsr/ls_atomic.h>
#include <lsr/ls_lfqueue.h>
#include <lsr/ls_lfstack.h>

typedef ls_lfqueue_t       ls_blkctrl_t;
#define ls_pool_chkinit    ls_lfq_chkinit
#define ls_pool_setup      ls_lfq_setup
#define ls_pool_getblk     ls_lfq_getblk
#define ls_pool_putblk     ls_lfq_putblk
#define ls_pool_putnblk    ls_lfq_putnblk
#define ls_pool_getlist    ls_lfq_getlist
#define ls_pool_inslist    ls_lfq_inslist
#define ls_pool_insptr     ls_lfq_insptr
typedef ls_lfstack_t       ls_xblkctrl_t;
#define ls_xpool_chkinit   ls_lfs_xchkinit
#define ls_xpool_setup     ls_lfs_xsetup
#define ls_xpool_cleanup   ls_lfs_xcleanup
#define ls_xpool_getblk    ls_lfs_getxblk
#define ls_xpool_putblk    ls_lfs_putxblk

#else /* USE_THRSAFE_POOL */
#ifdef USE_LSRSTD_POOL

typedef struct
{
    __link_t *head;
    __link_t *tail;
}                           ls_blkctrl_t;
#define ls_pool_chkinit    ls_std_chkinit
#define ls_pool_setup      ls_std_setup
#define ls_pool_getblk     ls_std_getblk
#define ls_pool_putblk     ls_std_putblk
#define ls_pool_putnblk    ls_std_putnblk
#define ls_pool_getlist    ls_std_getlist
#define ls_pool_inslist    ls_std_inslist
#define ls_pool_insptr     ls_std_insptr
typedef __link_t            ls_xblkctrl_t;
#define ls_xpool_chkinit   ls_std_xchkinit
#define ls_xpool_setup     ls_std_xsetup
#define ls_xpool_cleanup   ls_std_xcleanup
#define ls_xpool_getblk    ls_std_getxblk
#define ls_xpool_putblk    ls_std_putxblk

#else /* DEBUG_POOL */
//#define DEBUG_POOL
#undef USE_VALGRIND

typedef unsigned char       ls_blkctrl_t;
#define ls_pool_chkinit    ls_sys_chkinit
#define ls_pool_setup      ls_sys_setup
#define ls_pool_getblk     ls_sys_getblk
#define ls_pool_putblk     ls_sys_putblk
#define ls_pool_putnblk    ls_sys_putnblk
#define ls_pool_getlist    ls_std_getlist
#define ls_pool_inslist    ls_std_inslist
#define ls_pool_insptr     ls_std_insptr
typedef __link_t            ls_xblkctrl_t;
#define ls_xpool_chkinit   ls_std_xchkinit
#define ls_xpool_setup     ls_std_xsetup
#define ls_xpool_cleanup   ls_std_xcleanup
#define ls_xpool_getblk    ls_std_getxblk
#define ls_xpool_putblk    ls_std_putxblk

#endif /* USE_LSRSTD_POOL */
#endif /* USE_THRSAFE_POOL */

/* memory pool initialization status */
#define PINIT_NEED      2
#define PINIT_INPROG    1
#define PINIT_DONE      0
void ls_pinit();
int  xpool_freelistinit(ls_xpool_t *pPool);


/**
 * @ls_sys_chkinit
 */
ls_inline void ls_sys_chkinit(int *pInit)
{
    return;
}

/**
 * @ls_sys_setup
 */
ls_inline void ls_sys_setup(ls_blkctrl_t *p)
{
    return;
}

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
ls_inline void ls_sys_putblk(ls_blkctrl_t *p, void *pNew)
{
    free(pNew);
    return;
}

/**
 * @ls_sys_putnblk
 */
ls_inline void ls_sys_putnblk(ls_blkctrl_t *p, void *pNew, void *pTail)
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

#ifdef USE_LSRSTD_POOL
/**
 * @ls_std_chkinit
 */
ls_inline void ls_std_chkinit(int *pInit)
{
    if (*pInit != PINIT_DONE)
    {
        ls_pinit();
        *pInit = PINIT_DONE;
    }
    return;
}

/**
 * @ls_std_setup
 */
ls_inline void ls_std_setup(ls_blkctrl_t *p)
{
    return;
}

/**
 * @ls_std_getblk
 */
ls_inline void *ls_std_getblk(ls_blkctrl_t *p, size_t size)
{
    __link_t *ptr;
    if ((ptr = p->head) != NULL)
    {
#ifdef USE_VALGRIND
        VALGRIND_MAKE_MEM_DEFINED(ptr, sizeof(*ptr));
#endif /* USE_VALGRIND */
        if ((p->head = ptr->next) == NULL)
            p->tail = NULL;
    }
    return (void *)ptr;
}

/**
 * @ls_std_putblk
 */
ls_inline void ls_std_putblk(ls_blkctrl_t *p, void *pNew)
{
    if (p->tail == NULL)
        p->head = (__link_t *)pNew;
    else
    {
#ifdef USE_VALGRIND
        VALGRIND_MAKE_MEM_DEFINED(p->tail, sizeof(*(p->tail)));
#endif /* USE_VALGRIND */
        p->tail->next = (__link_t *)pNew;
#ifdef USE_VALGRIND
        VALGRIND_MAKE_MEM_NOACCESS(p->tail, sizeof(*(p->tail)));
#endif /* USE_VALGRIND */
    }
    p->tail = (__link_t *)pNew;
    return;
}

/**
 * @ls_std_putnblk
 */
ls_inline void ls_std_putnblk(ls_blkctrl_t *p, void *pNew, void *pTail)
{
    if (p->tail == NULL)
        p->head = (__link_t *)pNew;
    else
    {
#ifdef USE_VALGRIND
        VALGRIND_MAKE_MEM_DEFINED(p->tail, sizeof(*(p->tail)));
#endif /* USE_VALGRIND */
        p->tail->next = (__link_t *)pNew;
#ifdef USE_VALGRIND
        VALGRIND_MAKE_MEM_NOACCESS(p->tail, sizeof(*(p->tail)));
#endif /* USE_VALGRIND */
    }
    p->tail = (__link_t *)pTail;
    return;
}
#endif

/**
 * @ls_std_getlist
 */
ls_inline ls_xpool_bblk_t *ls_std_getlist(ls_xpool_bblk_t **pList)
{
    ls_xpool_bblk_t *pPtr = *pList;
    *pList = NULL;
    return pPtr;
}

/**
 * @ls_std_inslist
 */
ls_inline void ls_std_inslist(
    ls_xpool_bblk_t **pList, ls_xpool_bblk_t *pNew, ls_xpool_bblk_t *pTail)
{
    pTail->next = *pList;
    *pList = pNew;
    return;
}

/**
 * @ls_std_insptr
 */
ls_inline void ls_std_insptr(ls_pool_blk_t **pBase, ls_pool_blk_t *pNew)
{
    pNew->next = *pBase;
    *pBase = pNew;
    return;
}

/**
 * @ls_std_xchkinit
 */
ls_inline int ls_std_xchkinit(
    ls_xpool_t *pPool, ls_xblkctrl_t **pPtr, int *pFlag)
{
    return ((*pPtr == NULL) ? xpool_freelistinit(pPool) : 0);
}

/**
 * @ls_std_xsetup
 */
ls_inline void ls_std_xsetup(ls_xblkctrl_t *p)
{
    return;
}

/**
 * @ls_std_xcleanup
 */
ls_inline void ls_std_xcleanup(ls_xblkctrl_t *p)
{
    return;
}

/**
 * @ls_std_getxblk
 */
ls_inline void *ls_std_getxblk(ls_xblkctrl_t *p)
{
    __link_t *pNew = ((__link_t *)p)->next;
    if (pNew)
    {
#ifdef USE_VALGRIND
        VALGRIND_MAKE_MEM_DEFINED(pNew, sizeof(((__link_t *)p)->next));
#endif /* USE_VALGRIND */
        ((__link_t *)p)->next = pNew->next;
    }
    return (void *)pNew;
}

/**
 * @ls_std_putxblk
 */
ls_inline void ls_std_putxblk(ls_xblkctrl_t *p, void *pNew)
{
#ifdef USE_VALGRIND
    VALGRIND_MAKE_MEM_DEFINED(pNew, sizeof(((__link_t *)p)->next));
#endif /* USE_VALGRIND */
    ((__link_t *)pNew)->next = ((__link_t *)p)->next;
    ((__link_t *)p)->next = (__link_t *)pNew;
#ifdef USE_VALGRIND
    VALGRIND_MAKE_MEM_NOACCESS(pNew, sizeof(((__link_t *)p)->next));
#endif /* USE_VALGRIND */
    return;
}

#ifdef USE_THRSAFE_POOL
/**
 * @ls_lfq_chkinit
 */
ls_inline void ls_lfq_chkinit(int *pInit)
{
    if (*pInit != PINIT_DONE)
    {
        if (ls_atomic_setint(pInit, PINIT_INPROG) == PINIT_NEED)
        {
            ls_pinit();
            ls_atomic_store(pInit, PINIT_DONE);
        }
        else
        {
            while (*pInit != PINIT_DONE)
                sched_yield();
        }
    }
    return;
}

/**
 * @ls_lfq_setup
 */
ls_inline void ls_lfq_setup(ls_blkctrl_t *p)
{
    ls_lfqueue_init(p);
    return;
}

/**
 * @ls_lfq_getblk
 */
ls_inline void *ls_lfq_getblk(ls_blkctrl_t *p, size_t size)
{
    return (void *)ls_lfqueue_get(p);
}

/**
 * @ls_lfq_putblk
 */
ls_inline void ls_lfq_putblk(ls_blkctrl_t *p, void *pNew)
{
#ifdef USE_VALGRIND
    VALGRIND_MAKE_MEM_DEFINED(pNew, sizeof(ls_lfnodei_t));
#endif /* USE_VALGRIND */
    ls_lfqueue_put(p, (ls_lfnodei_t *)pNew);
    return;
}

/**
 * @ls_lfq_putnblk
 */
ls_inline void ls_lfq_putnblk(ls_blkctrl_t *p, void *pNew, void *pTail)
{
#ifdef USE_VALGRIND
    VALGRIND_MAKE_MEM_DEFINED(pTail, sizeof(ls_lfnodei_t));
#endif /* USE_VALGRIND */
    ls_lfqueue_putn(p, (ls_lfnodei_t *)pNew, (ls_lfnodei_t *)pTail);
    return;
}

/**
 * @ls_lfq_getlist
 */
ls_inline ls_xpool_bblk_t *ls_lfq_getlist(ls_xpool_bblk_t **pList)
{
    return (ls_xpool_bblk_t *)ls_atomic_setptr(pList, NULL);
}

/**
 * @ls_lfq_inslist
 */
ls_inline void ls_lfq_inslist(
    ls_xpool_bblk_t **pList, ls_xpool_bblk_t *pNew, ls_xpool_bblk_t *pTail)
{
    do
    {
        ls_atomic_load(pTail->next, pList);
    }
    while (!ls_atomic_casptr(pList, pTail->next, pNew));
    return;
}

/**
 * @ls_lfq_insptr
 */
ls_inline void ls_lfq_insptr(volatile ls_pool_blk_t **pBase,
                             ls_pool_blk_t *pNew)
{
    pNew->next = NULL;
    ls_pool_blk_t *pPrev = (ls_pool_blk_t *)ls_atomic_setptr(pBase, pNew);
    pNew->next = pPrev;
    return;
}

/**
 * @ls_lfs_xchkinit
 */
ls_inline int ls_lfs_xchkinit(
    ls_xpool_t *pPool, ls_xblkctrl_t **pPtr, int *pFlag)
{
    if (*pPtr == NULL)
    {
        if (ls_atomic_setint(pFlag, 1) == 0)
        {
            if (xpool_freelistinit(pPool) < 0)
            {
                ls_atomic_clrint(pFlag);
                return -1;
            }
        }
        else
        {
            while (*pPtr == NULL)
                sched_yield();
        }
    }
    return 0;
}

/**
 * @ls_lfs_xsetup
 */
ls_inline void ls_lfs_xsetup(ls_xblkctrl_t *p)
{
    ls_lfstack_init(p);
    return;
}

/**
 * @ls_lfs_xcleanup
 */
ls_inline void ls_lfs_xcleanup(ls_xblkctrl_t *p)
{
    ls_lfstack_destroy(p);
    return;
}

/**
 * @ls_lfs_getxblk
 */
ls_inline void *ls_lfs_getxblk(ls_xblkctrl_t *p)
{
    return (void *)ls_lfstack_pop(p);
}

/**
 * @ls_lfs_putxblk
 */
ls_inline void ls_lfs_putxblk(ls_xblkctrl_t *p, void *pNew)
{
    ls_lfstack_push(p, (ls_lfnodei_t *)pNew);
    return;
}
#endif


#ifdef __cplusplus
}
#endif

#endif //LS_POOLDEF_H
