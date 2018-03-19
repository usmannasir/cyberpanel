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
#include <lsr/ls_llxq.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <assert.h>


#define NUMCONSUMERS    5       /* number of consumer threads */
#define NUMPRODUCERS    3       /* number of producer threads */
#define TIMECONSUMER    500     /* timeout (usec) of consumer function */
#define TIMEPRODUCER    1       /* timeout (usec) between producer queue calls */
#define TESTVALOFFSET   1000    /* artificial value offset for get/set,
                                 * since value is expected to be a pointer
                                 */

static int timeconsumer = TIMECONSUMER;
static int timeproducer = TIMEPRODUCER;
struct timespec timeoutcons;
struct timespec timeoutprod;
struct timespec *ptimeoutcons;
struct timespec *ptimeoutprod;
static int loopproduce = 1000;
static int szjobsbuf = 0x08;
static void *pThis;

#define FAIL_CODE   0xf0

typedef unsigned char job_t;
job_t *myjobs;

/* wrappers for ls_llmq
 */
static void *mq_new()
{
    return (void *)ls_llmq_new(szjobsbuf);
}
static int mq_put(void *data)
{
    return ls_llmq_timedput((ls_llmq_t *)pThis, data, ptimeoutprod);
}
static long mq_get()
{
    return (long)ls_llmq_timedget((ls_llmq_t *)pThis, ptimeoutcons);
}
static void mq_delete()
{
    ls_llmq_delete((ls_llmq_t *)pThis);
}

/* wrappers for ls_llxq
 */
static void *xq_new()
{
    return (void *)ls_llxq_new(szjobsbuf);
}
static int xq_put(void *data)
{
    return ls_llxq_put((ls_llxq_t *)pThis, data);
}
static long xq_get()
{
    return (long)ls_llxq_timedget((ls_llxq_t *)pThis, ptimeoutcons);
}
static void xq_delete()
{
    ls_llxq_delete((ls_llxq_t *)pThis);
}

static void *(*func_new)() = mq_new;
static int (*func_put)() = mq_put;
static long (*func_get)() = mq_get;
static void (*func_delete)() = mq_delete;

static void *thr_putjob(void *arg)
{
    int i;
    long pjob = (long)arg * loopproduce + TESTVALOFFSET;
    for (i = 0; i < loopproduce; ++i)
    {
#ifdef notdef
        if (((int)arg == 1) && (i == 150))
            ls_llxq_newqueue((ls_llxq_t *)pThis, 64);
        if (((int)arg == 2) && (i == 200))
            ls_llxq_newqueue((ls_llxq_t *)pThis, 128);
#endif
        if ((*func_put)((void *)pjob) < 0)
            myjobs[ pjob - TESTVALOFFSET ] = FAIL_CODE;
        ++pjob;

        if (timeproducer > 0)
            usleep(timeproducer);
    }
    return NULL;
}

static void *thr_getjob(void *arg)
{
    pthread_setcanceltype(PTHREAD_CANCEL_ASYNCHRONOUS, NULL);
    while (1)
    {
        long pjob;
        if ((pjob = (*func_get)()) == 0)
            printf("get TIMEOUT(%ld)\n", (long)arg);
        else
        {
            assert(pjob >= TESTVALOFFSET);
            myjobs[ pjob - TESTVALOFFSET ]++;

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

static void thr_cancel(pthread_t *pthr, int numthreads)
{
    int i;

    for (i = 0; i < numthreads; ++i)
        pthread_cancel(pthr[i]);
}

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

    size = numjobs * sizeof(*pjob);
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
            switch ((int)*pjob++)
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
            "SUMMARY:    total[%d] good[%d] fail[%d] miss[%d] other[%d]\n",
            numthreads * loopproduce, totgood, totfail, totmiss, totover);
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
            "usage: ls_llmqtest mode [ numcons numprod wtmcons wtmprod stmcons stmprod ]\n\
  mode    -  0=ls_llmq, 1=ls_llxq (def=0)\n\
  numcons -  number of consumer threads (def=%d)\n\
  numprod -  number of producer threads (def=%d)\n\
  wtmcons -  wait timeout (usec) of consumer get (def=-1,blocking)\n\
  wtmprod -  wait timeout (usec) of producer put (def=-1,blocking)\n\
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
    /* no break */
    case 2:
        if (av[1][0] == '1')
        {
            func_new = xq_new;
            func_put = xq_put;
            func_get = xq_get;
            func_delete = xq_delete;
        }
        else if (av[1][0] != '0')
        {
            usage();
            return 1;
        }
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
    if ((consumers = thr_init(numconsumers, thr_getjob)) == NULL)
    {
        fprintf(stderr, "consumer init failed!\n");
        cleanup();
        return 4;
    }
    sleep(1);
    if ((producers = thr_init(numproducers, thr_putjob)) == NULL)
    {
        fprintf(stderr, "producer init failed!\n");
        cleanup();
        return 5;
    }

    thr_destroy(producers, numproducers);
    sleep(1);
    thr_cancel(consumers, numconsumers);
    thr_destroy(consumers, numconsumers);

    print_results(myjobs, numproducers);
    cleanup();

    return 0;
}

