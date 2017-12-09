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

/*
 * ls_thrsafetest
 *
 * usage:
 *      see usage() function
 */

#include <iostream>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <unistd.h>
#include <iomanip>
#include <sstream>

#include "timer.cpp"
#include <lsr/ls_pool.h>
#include <lsr/ls_xpool.h>
#include <lsr/ls_poolint.h>

#include <sys/time.h>

static int mode = 0;    /* 0 = global pool mode, 1 = session pool */
static long allocCount = 10;
static int loopCount = 2;
static int runs = 10;
static int numThreads = 5;

static int verbose = 0;

static ls_xpool_t *xpool = NULL;

typedef struct
{
    pthread_t   m_thread;
    int         m_exit;
    int         m_id;
    int         m_error;
    int         m_waitCount;
} myThread_t;
static myThread_t threadMap[1000000];

static void showEnd(int numThreads)
{
    int i;
    myThread_t *p;
    p = threadMap;
    for (i = 0; i < numThreads; i++, p++)
    {
        if (!p->m_error)
            continue;

        printf("DONE %d [m_error = %d waitCount=%d] %d\n",
               p->m_id,
               p->m_error,
               p->m_waitCount,
               p->m_exit);
    }
}

static void *testOneAlloc(int id, int size)
{
    void *ptr;

    ptr = (mode ? ls_xpool_alloc(xpool, size) : ls_palloc(size));
#define TEST_CONTENTS
#ifdef TEST_CONTENTS
    // int fill = id & 0xFF;
    int fill = random() & 0xFF;
    unsigned char *p;

    if (ptr != NULL)
    {
        memset(ptr, fill, size);
        p = (unsigned char *)ptr;
        while (--size >= 0)
        {
            if (*p++ != fill) {
                return NULL;
            }
        }
    }
#endif
    return ptr;
}

static inline void freeOneAlloc(void *ptr)
{
    if (mode)
        ls_xpool_free(xpool, ptr);
    else
        ls_pfree(ptr);
}

static void *runTest(void *o)
{
    // static int sizes[] = { 32, 8, 256, 48, 4096, 64 * 1024 };
    static int sizes[] = {
        32, 8, 256, 48, 4096, 64 * 1024,
        1, 27, 129, 455, 72, 99, 14352,
        7, 327, 29, 55, 872, 991, 214352,
        32, 8, 256, 48, 4096, 64 * 1024
    };
//     static int sizes[] = { 32, 8, 256, 48, 128, 16 };

    unsigned short ptrSize = sizeof(sizes) / sizeof(sizes[0]);

    void *ptrs[ptrSize* allocCount];
    myThread_t *p = (myThread_t *)o;

    if (verbose) printf("runTest %d\n", p->m_id);

    long cnt;
    for (cnt = 0; cnt < allocCount; ++cnt)
    {
        int *psizes = sizes;
        int i = ptrSize;
        while (--i >= 0)
        {
            sched_yield();
            usleep(1000 * (random() % 30));
            if ((ptrs[cnt * ptrSize + i] = testOneAlloc(p->m_id, *psizes++)) == NULL)
                ++p->m_error;
        }
    }
    for (cnt = 0; cnt < allocCount; ++cnt)
    {
        int i = ptrSize;
        while (--i >= 0) {
            sched_yield();
            usleep(1000 * (random() % 30));
            freeOneAlloc(ptrs[cnt * ptrSize + i]);
        }
    }

    pthread_exit((void *)(long) - p->m_id);
    return NULL;
}

static int s_start = 0;
static void * (*alloc)(size_t) = ls_palloc;
static void (*dealloc)(void *) = ls_pfree;

static void *runTestHighContention(void *o)
{
    static int sizes[] = {
        32
    };

    unsigned short ptrSize = sizeof(sizes) / sizeof(sizes[0]);

    void *ptrs[ptrSize* allocCount];
    void **ptr;
    myThread_t *p = (myThread_t *)o;

    if (verbose) printf("start thread %d\n", p->m_id);
    while(s_start == 0)
        usleep(200);

    if (verbose) printf("test begin %d\n", p->m_id);
    
    for (int loop = 0; loop < loopCount; loop++) {
        long cnt;
        ptr = ptrs; 
        for (cnt = 0; cnt < allocCount; ++cnt)
        {
            if ((*ptr++ = (*alloc)(32)) == NULL)
                ++p->m_error;
        }

        ptr = ptrs;
        for (cnt = 0; cnt < allocCount; ++cnt)
        {
            (*dealloc)(*ptr++);
        }
    }

    if (verbose) printf("test end %d\n", p->m_id);

    pthread_exit((void *)(long) - p->m_id);
    return NULL;
}


#ifdef notdef
static void *runTest2(void *o)
{
    static int sizes[] = { 32, 8, 256, 48, 4096, 64 * 1024 };
//     static int sizes[] = { 32, 8, 256, 48, 128, 16 };
    int iNumElems = sizeof(sizes) / sizeof(sizes[0]);
    int iRepetitions = 2;
    myThread_t *p = (myThread_t *)o;
    void **ptrs = (void **)ls_palloc(sizeof(void *) * allocCount);

    printf("runTest2 %d\n", p->m_id);
    int count;
    for (; iRepetitions > 0; --iRepetitions)
    {
        int iChunkSize;
        for (count = 0; count < iNumElems; ++count)
        {
            iChunkSize = sizes[count];
            long iter;
            for (iter = 0; iter < allocCount; ++iter)
            {
                if ((ptrs[iter] = testOneAlloc(p->m_id, iChunkSize)) == NULL)
                    ++p->m_error;
            }
            for (iter = 0; iter < allocCount; ++iter)
                freeOneAlloc(ptrs[iter]);
        }
    }
    ls_pfree(ptrs);
    pthread_exit((void *)(long) - p->m_id);
    return NULL;
}
#endif

int testthrsafe(void *(*runTest)(void *))
{
    myThread_t *p;
    int i;

    if (verbose) printf("\nRUNNING mode %d numThreads %d allocCount %ld\n",
            mode, numThreads, allocCount);
    
    p = threadMap;

    if (mode)
        xpool = ls_xpool_new();

    s_start = 0;

    for (i = 0; i < numThreads; i++, p++)
    {
        p->m_exit = 0;
        p->m_id = i;
        p->m_error = 0;
        p->m_waitCount = 0;

        if (pthread_create(&p->m_thread, NULL, runTest, (void *)p))
        {
            std::cerr << "Thread creation failed, total threads completed " << i << std::endl;
            numThreads = i;
            break;
        }
    }
    s_start = 1;
    //std::cerr << "Thread creation completed, total threads " << i << std::endl;
    p = threadMap;
    for (i = 0; i < numThreads; i++, p++)
        if (int err = pthread_join(p->m_thread, (void **)&p->m_exit)) {
            std::cerr << "FAILED to join thread " << p->m_thread << " error "
                << err << " exit " << p->m_exit << std::endl;
        };

    if (mode)
        ls_xpool_delete(xpool);

    if (verbose) printf("DONE RUNNING numThreads %d allocCount %ld\n", numThreads, allocCount);

    showEnd(numThreads);

    return 0;
}

void usage(const char * s)
{
    std::cout <<
        "Usage: " << s << "[options]" << std::endl <<
        " -v: verbose output" << std::endl <<
        " -m num: num = 0 for pool (default), 1 for xpool" << std::endl <<
        " -r num: run test num times" << std::endl <<
        " -n num: run num threads" << std::endl <<
        " -p num: run allocation loop num times" << std::endl<<
        " -a num: do num allocations_per_loop" << std::endl <<
        " -h: run high contention test instead of standarad sizes" << std::endl <<
        " -e: use malloc / free instead of ls_palloc ls_pfree (only for HighContention test)" << std::endl <<
        std::endl;
    exit(1);
}

/*
 *  Simple thread safe test
 */
int main(int ac, char *av[])
{
    int i;
    int hiCont = 0;

    char tmp;

    while ((tmp = getopt(ac, av, "vm:r:n:p:a:he")) != -1) {
        switch (tmp) {
            case 'v':
                verbose = 1;
                break;
            case 'm':
                mode = strtol(optarg, NULL, 10);
                break;
            case 'r':
                runs = strtol(optarg, NULL, 10);
                break;
            case 'n':
                numThreads = strtol(optarg, NULL, 10);
                break;
            case 'p':
                loopCount = strtol(optarg, NULL, 10);
                break;
            case 'a':
                allocCount = strtol(optarg, NULL, 10);
                break;
            case 'h':
                hiCont = 1;
                break;
            case 'e':
                alloc = malloc;
                dealloc = free;
                break;
            case '?':
                if (isprint (optopt))
                    fprintf (stderr, "Unknown option `-%c'.\n", optopt);
                else
                    fprintf (stderr,
                            "Unknown option character `\\x%x'.\n",
                            optopt);
            default:
                usage(av[0]);
                break;
        }
    }

    if (optind < ac) {
        usage(av[0]);
    }

    if (
            (mode < 0 || mode > 1)
       ) {
        usage(av[0]);
    }


    ls_pinit(); // only used for valgrind

    unsigned long tot_usecs = 0;
    for (i = 0; i < runs; ++i)
    {
        // std::cout << "\n";
        av[0] = (char *)(mode ? "THREAD-SAFE XPOOL" : "THREAD-SAFE POOL");
        if (verbose) fprintf(stderr, "%d: %s\n", i, av[0]);
        struct timeval tvStart, tvEnd;
        gettimeofday(&tvStart, NULL);
        if (hiCont) {
            testthrsafe(runTestHighContention);
        }
        else {
            testthrsafe(runTest);
        }
        gettimeofday(&tvEnd, NULL);

        unsigned long long deltaT =  1000000ull * (tvEnd.tv_sec  - tvStart.tv_sec) + (tvEnd.tv_usec - tvStart.tv_usec);
        tot_usecs += deltaT;
        // tvStart = tvEnd;


#ifdef POOL_TESTING
        short len;
        unsigned short * multi = ls_pool_get_multi(&len);
        std::stringstream fl_str;
        for (unsigned short i = 0; i < len; i++) {
            if (*(multi + i) > 0) {
                fl_str << i << ":" << (int) *(multi + i) << " ";
            }
        }
#endif /* POOL_TESTING */

        std::string type;
#ifdef DEBUG_POOL
        type += "DEBUG_POOL;";
#else
        type += "LKSTD_POOL;";
#endif

        std::cerr.imbue(std::locale(""));
        std::cerr
            << "[type " << type
            << " mode " << mode
            << " alloc " << ((alloc == ls_palloc) ? "ls_palloc/ls_pfree" : "malloc/free")
            << " threads " << numThreads
            << " alloc count " << allocCount
            << " loop count " << loopCount
            << "] => "
#ifdef POOL_TESTING
            << " cur_heaps " << ls_pool_cur_heaps()
            << " freelists: " << fl_str.str()
#endif /* POOL_TESTING */
            << " usecs " << deltaT
            << " (" << std::setprecision(4) << deltaT / 1000000.0 << "s)"
            << " nsec per alloc " << std::setprecision(3) << std::fixed << 1000.0 * deltaT / (double) allocCount / loopCount / numThreads
            << std::endl;
    }
    std::cerr << "Avg run usecs " << std::setprecision(0) << std::fixed << tot_usecs/(double)runs
        << " nsec per alloc " << std::setprecision(3) << std::fixed << 1000.0 * tot_usecs/(double)runs / allocCount / loopCount / numThreads<< std::endl;
    std::cout << "Bye.\n";
}
