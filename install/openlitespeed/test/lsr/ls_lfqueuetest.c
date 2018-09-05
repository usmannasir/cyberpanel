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

#include <lsdef.h>
#include <lsr/ls_lfqueue.h>
#include <lsr/ls_atomic.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <assert.h>

#define NUMCONSUMERS    5       /* number of consumer threads */
#define NUMPRODUCERS    5       /* number of producer threads */
#define TIMECONSUMER    100     /* timeout (usec) of consumer function */
#define TIMEPRODUCER    1       /* timeout (usec) between producer queue calls */

static int timeconsumer = TIMECONSUMER;
static int timeproducer = TIMEPRODUCER;
struct timespec timeoutcons;
struct timespec timeoutprod;
struct timespec *ptimeoutcons;
struct timespec *ptimeoutprod;
static int loopproduce = 1000;
static unsigned int totgetfail;
static void *pThis;

#define FAIL_CODE   0xf0

typedef struct
{
    union
    {
        struct      /* intrusive */
        {
            ls_lfnodei_t nodei;
            long val;
        };
        struct      /* non-intrusive */
        {
            ls_lfnoden_t noden;
        };
    };
    int ret;
} job_t;
job_t *myjobs;

volatile int
mycnt;             /* to know when all producers are finished */

/* wrappers for ls_lfqueue
 */
static void *mpmc_new()
{
    return (void *)ls_lfqueue_new();
}
static int mpmc_put(job_t *pjob, long val)
{
    pjob->val = val;
    return ls_lfqueue_put((ls_lfqueue_t *)pThis, &pjob->nodei);
}
static long mpmc_get()
{
    ls_lfnodei_t *ptr;
#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
    struct timespec tv;
    tv.tv_sec = 1;
    tv.tv_nsec = 0;
    if ((ptr = ls_lfqueue_timedget((ls_lfqueue_t *)pThis, &tv)) == NULL)
#else
    if ((ptr = ls_lfqueue_get((ls_lfqueue_t *)pThis)) == NULL)
#endif
        return LS_FAIL;
    return *((long *)(ptr + 1));
}
static void mpmc_delete()
{
    ls_lfqueue_delete((ls_lfqueue_t *)pThis);
}

/* wrappers for ls_mpscq
 */
static void *mpsc_new()
{
    return (void *)ls_mpscq_new(&myjobs[mycnt * loopproduce].noden);
}
static int mpsc_put(job_t *pjob, long val)
{
    pjob->noden.next = NULL;
    pjob->noden.pobj = (void *)val;
    return ls_mpscq_put((ls_mpscq_t *)pThis, &pjob->noden);
}
static long mpsc_get()
{
    ls_lfnoden_t *ptr;
    if ((ptr = ls_mpscq_get((ls_mpscq_t *)pThis)) == NULL)
        return LS_FAIL;
    return (long)ptr->pobj;
}
static void mpsc_delete()
{
    ls_mpscq_delete((ls_mpscq_t *)pThis);
}

static void *(*func_new)() = mpmc_new;
static int (*func_put)() = mpmc_put;
static long (*func_get)() = mpmc_get;
static void (*func_delete)() = mpmc_delete;

static void *thr_putjob(void *arg)
{
    long indx = (long)arg * loopproduce;
    job_t *pjob = &myjobs[indx];
    int i = loopproduce;
    while (--i >= 0)
    {
        if ((*func_put)(pjob, indx) < 0)
            pjob->ret = FAIL_CODE;
        ++pjob;
        ++indx;

        if (timeproducer > 0)
            usleep(timeproducer);
    }
    ls_atomic_sub(&mycnt, 1);
    return NULL;
}

static void *thr_getjob(void *arg)
{
    static int retry;
    pthread_setcanceltype(PTHREAD_CANCEL_ASYNCHRONOUS, NULL);
    while (1)
    {
        long val;
        if ((val = (*func_get)()) < 0)
        {
            if (mycnt <= 0)
            {
                if (++retry >= 3)
                    break;
            }
            else
                ++totgetfail;
        }
        else
        {
            myjobs[ val ].ret++;

            if (timeconsumer > 0)
                usleep(timeconsumer);
        }
    }
    return NULL;
}

static pthread_t *thr_init(int numthreads, void *(*func)(void *))
{
    pthread_t *pthr;

    if ((pthr = (pthread_t *)malloc(numthreads * sizeof(*pthr))) != NULL)
    {
        int i;
        for (i = 0; i < numthreads; ++i)
            pthread_create(&pthr[i], NULL, func, (void *)(long)i);
    }
    return pthr;
}

#ifdef notdef
static void thr_cancel(pthread_t *pthr, int numthreads)
{
    int i;

    for (i = 0; i < numthreads; ++i)
        pthread_cancel(pthr[i]);
}
#endif

static void thr_destroy(pthread_t *pthr, int numthreads)
{
    int i;
    void *m_exit;

    for (i = 0; i < numthreads; ++i)
        pthread_join(pthr[i], (void **)&m_exit);
    free(pthr);
    return;
}

static job_t *job_init(int numjobs)
{
    int size;
    job_t *pjob;

    size = (numjobs + 1) * sizeof(*pjob);       /* extra one for init call */
    if ((pjob = (job_t *)malloc(size)) != NULL)
        memset(pjob, 0, size);

    return pjob;
}

static void print_results(job_t *pjob, int numthreads)
{
    int totgood = 0;
    int totfail = 0;
    int totmiss = 0;
    int totover = 0;
    int thr;
    for (thr = 0; thr < numthreads; ++thr)
    {
        int good = 0;
        int fail = 0;
        int miss = 0;
        int over = 0;
        int idx;
        for (idx = 0; idx < loopproduce; ++idx)
        {
            switch (pjob->ret)
            {
            case 0:
                ++miss;
                break;
            case 1:
                ++good;
                break;
            case FAIL_CODE:
                ++fail;
                break;
            default:
                ++over;
                break;
            }
            ++pjob;
        }
        if (good != loopproduce)
        {
            fprintf(stdout,
                    "thread[%2d]: total[%d] good[%d] fail[%d] miss[%d] other[%d]\n",
                    thr, loopproduce, good, fail, miss, over);
        }
        totgood += good;
        totfail += fail;
        totmiss += miss;
        totover += over;
    }
    fprintf(stdout,
            "SUMMARY:    total[%d] good[%d] fail[%d] miss[%d] other[%d], totgetfail[%u]\n",
            numthreads * loopproduce, totgood, totfail, totmiss, totover, totgetfail);
    return;
}

static struct timespec *str2timespec(char *str, struct timespec *tmspec)
{
    int val;

    if ((val = atoi(str)) < 0)
        return NULL;
    if (val >= 1000000)
    {
        tmspec->tv_sec = val / 1000000;
        val %= 1000000;
    }
    tmspec->tv_nsec = val * 1000;
    return tmspec;
}

void usage()
{
    fprintf(stderr,
            "usage: ls_lfqueuetest mode [ numcons numprod wtmcons wtmprod stmcons stmprod ]\n\
  mode    -  0=ls_lfqueue, 1=ls_mpscq (def=0)\n\
  numcons -  number of consumer threads (def=%d)\n\
  numprod -  number of producer threads (def=%d)\n\
  wtmcons -  wait timeout (usec) of consumer get (N/A)\n\
  wtmprod -  wait timeout (usec) of producer put (N/A)\n\
  stmcons -  sleep timeout (usec) of consumer function (def=%d)\n\
  stmprod -  sleep timeout (usec) between producer put calls (def=%d)\n",
            NUMCONSUMERS, NUMPRODUCERS, TIMECONSUMER, TIMEPRODUCER);
    return;
}

void cleanup()
{
    if (pThis)
        (*func_delete)();
    if (myjobs)
        free(myjobs);
    return;
}

int main(int ac, char *av[])
{
    pthread_t *producers;
    pthread_t *consumers;
    int numproducers = NUMPRODUCERS;
    int numconsumers = NUMCONSUMERS;

    switch (ac)
    {
    case 8:
        timeproducer = atoi(av[7]);
        timeconsumer = atoi(av[6]);
        ptimeoutprod = str2timespec(av[5], &timeoutprod);
        ptimeoutcons = str2timespec(av[4], &timeoutcons);
        numproducers = atoi(av[3]);
        numconsumers = atoi(av[2]);
        //fall through
    case 2:
        if (av[1][0] == '1')
        {
            func_new = mpsc_new;
            func_put = mpsc_put;
            func_get = mpsc_get;
            func_delete = mpsc_delete;
            numconsumers = 1;
        }
        else if (av[1][0] != '0')
        {
            usage();
            return 1;
        }
        //fall through
    case 1:
        break;
    default:
        usage();
        return 1;
    }

    if ((numconsumers <= 0) || (numproducers <= 0))
    {
        usage();
        return 1;
    }
    mycnt = numproducers;
    if ((myjobs = job_init(numproducers * loopproduce)) == NULL)
    {
        fprintf(stderr, "myjobs init failed!\n");
        cleanup();
        return 2;
    }
    if ((pThis = (*func_new)()) == NULL)
    {
        fprintf(stderr, "lsr init failed!\n");
        cleanup();
        return 3;
    }
    if ((producers = thr_init(numproducers, thr_putjob)) == NULL)
    {
        fprintf(stderr, "producer init failed!\n");
        cleanup();
        return 5;
    }
    if ((consumers = thr_init(numconsumers, thr_getjob)) == NULL)
    {
        fprintf(stderr, "consumer init failed!\n");
        cleanup();
        return 4;
    }

    thr_destroy(producers, numproducers);
#ifdef notdef
    sleep(10);
    thr_cancel(consumers, numconsumers);
#endif
    thr_destroy(consumers, numconsumers);

    print_results(myjobs, numproducers);
    cleanup();

    return 0;
}

