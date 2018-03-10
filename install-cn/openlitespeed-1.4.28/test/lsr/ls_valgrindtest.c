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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_xpool.h>
#include <lsr/ls_internal.h>
#include <valgrind/memcheck.h>

/*
 * ls_valgrindtest
 *
 * use the accompanying run_valgrindtest.sh to collect valgrind results
 * and compare against expected output
 *
 * NOTE: if you change the tests, generate new expected output in
 * valgrind.exp.stdout and valgrind.exp.stderr
 */

/*
 * global pool test
 */

#define SIZE_1      (350*16+8)
#define SIZE_2      (370*16+8)      /* larger than SIZE_1, but in same bucket */
#define SIZE_BIG    (64*1024+LSR_POOL_DATA_ALIGN)
/* ls_pool calls malloc directly */

struct malloclink
{
    struct malloclink *pNext;
    char *pMalloc;
};
static struct malloclink *pMalloclink = NULL;

static void gpool_test()
{
    char c;
    char *ptr;

    ls_pinit(); // only used for valgrind

    ptr = (char *)ls_palloc(100);
    ptr[0] = 'A';
    ls_pfree(ptr);
    ptr = (char *)ls_palloc(SIZE_1);
    ptr[SIZE_1 - 1] = 'A';
    c = ptr[SIZE_1];        /* fails outside range */
    c = ptr[SIZE_2];        /* fails outside range */
    ls_pfree(ptr);
    c = ptr[SIZE_1 - 1];    /* freed space */
    ptr = (char *)ls_palloc(SIZE_2);
    ptr[SIZE_1 - 1] = 'A';
    ptr[SIZE_1] = 'A';      /* same buffer, now inside range */
    c = ptr[SIZE_1];
    ptr[SIZE_1] = c;
    c = ptr[SIZE_2];        /* fails outside range */
    ls_pfree(ptr);

    ptr = (char *)malloc(SIZE_BIG);
    ptr[SIZE_2] = 'A';
    c = ptr[SIZE_BIG];      /* fails outside range */
    /* definitely lost, attached to stack pointer */
#ifdef notdef
    free(ptr);
#endif

    struct malloclink *p;
    p = (struct malloclink *)malloc(sizeof(*p));
    p->pNext = pMalloclink;
    pMalloclink = p;

    ptr = (char *)malloc(SIZE_BIG);
    p->pMalloc = ptr;
    /* still reachable, attached to static, global, or heap pointer */
#ifdef notdef
    free(ptr);
#endif

    p = (struct malloclink *)malloc(sizeof(*p));
    p->pNext = pMalloclink;
    pMalloclink = p;

    ptr = (char *)ls_palloc(SIZE_BIG);        /* calls malloc directly */
    p->pMalloc = ptr;
    p->pMalloc[SIZE_2] = 'A';
    c = p->pMalloc[SIZE_BIG];   /* fails outside range */
    /* possibly lost, attached to returned stack pointer from ls_palloc */
#ifdef notdef
    ls_pfree(p->pMalloc);
    c = p->pMalloc[0];          /* freed space */
#endif

    return;
}

/*
 * session pool (xpool) test
 */

#define LSR_XPOOL_SB_SIZE   4096    /* size of superblock */
#define XSIZE_1      (253)          /* example small block */
#define XSIZE_2      (1032)         /* example large block */
#define XSIZE_BIG    (LSR_XPOOL_SB_SIZE)

static ls_xpool_t *pool;

static void xpool_test()
{
    char c;
    char *ptr;

    pool = ls_xpool_new();

    ptr = (char *)ls_xpool_alloc(pool, 100);       /* from superblock */
    ptr[0] = 'A';
    c = ptr[0];
    ptr[0] = c;
    c = ptr[100];                           /* fails outside range */
    ls_xpool_free(pool, ptr);
    c = ptr[8];                             /* freed space */

    ptr = (char *)ls_xpool_alloc(pool, 100);       /* from freelist */
    ptr[0] = 'A';
    c = ptr[100];                           /* fails outside range */
    ptr = (char *)ls_xpool_alloc(pool, 100);
    c = ptr[104];                           /* fails outside range */
    ls_xpool_free(pool, ptr);

    ptr = (char *)ls_xpool_alloc(pool, XSIZE_1);   /* new small block */
    ptr[0] = 'A';
    ptr[XSIZE_1 - 1] = 'A';
    c = ptr[XSIZE_1];                       /* fails outside range */
    ls_xpool_free(pool, ptr);
    c = ptr[XSIZE_1 - 1];                   /* freed space */

    ptr = (char *)ls_xpool_alloc(pool, XSIZE_2);   /* new large block */
    ptr[0] = 'A';
    ptr[XSIZE_2 - 1] = 'A';
    c = ptr[XSIZE_2];                       /* fails outside range */
    ls_xpool_free(pool, ptr);
    c = ptr[8];                             /* freed space */

    ls_xpool_alloc(pool, XSIZE_1);                 /* new small block */
    ptr = (char *)ls_xpool_alloc(pool,
                                 XSIZE_1);   /* small block from large list */
    ptr[0] = 'A';
    ptr[XSIZE_1 - 1] = 'A';
    c = ptr[XSIZE_1];                       /* fails outside range */
    ls_xpool_free(pool, ptr);
    c = ptr[XSIZE_1 - 1];                   /* freed space */

    ptr = (char *)ls_xpool_alloc(pool, XSIZE_BIG);     /* new `big' block */
    ptr[0] = 'A';
    ptr[XSIZE_BIG - 1] = 'A';
    c = ptr[XSIZE_BIG];                     /* fails outside range */
    ls_xpool_free(pool, ptr);
    c = ptr[0];                             /* freed space */

    ptr = (char *)ls_xpool_alloc(pool,
                                 XSIZE_2);   /* large block to small block */
    ptr[XSIZE_2 - 1] = 'A';
    c = ptr[XSIZE_2 - 1];
    ptr = (char *)ls_xpool_realloc(pool, ptr, XSIZE_1);
    c = ptr[XSIZE_2 - 1];                   /* fails outside range */
    ls_xpool_free(pool, ptr);

    ptr = (char *)ls_xpool_alloc(pool,
                                 XSIZE_1);   /* small block to large block */
    ptr[XSIZE_1 - 1] = 'A';
    c = ptr[XSIZE_1 - 1];
    ptr = (char *)ls_xpool_realloc(pool, ptr, XSIZE_2);
    c = ptr[XSIZE_1 - 1];
    ls_xpool_free(pool, ptr);

    ls_xpool_delete(pool);

    return;
}

/*
 */
int main(int ac, char *av[])
{
    if (0 == RUNNING_ON_VALGRIND) {
#if __has_feature(address_sanitizer) || defined(__SANITIZE_ADDRESS__)
        fprintf(stderr, "Using address sanitizer instead of valgrind, check results manually\n");
#else
        fprintf(stderr, "Must run this test with valgrind!\n");
        fprintf(stderr, "Recommended usage: run from the shell script run_valgrindtest.sh for PASS/FAIL comparison against expected results.\n");
        exit(1);
#endif
    }

    printf("hello world!\n");

    gpool_test();
    xpool_test();

    printf("end!\n");
    fflush(NULL);

    return 0;
}


