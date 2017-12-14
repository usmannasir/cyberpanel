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
#include <iostream>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <unistd.h>

#include "timer.cpp"
#include <lsr/ls_lock.h>
#include <lsdef.h>


int bigValue        = 0;
int bigCount        = 0;
int loopCount       = 10000000;
int numThreads      = 5;

#ifdef notdef
#define barrier() __sync_synchronize()
#else
#define barrier() asm volatile("": : :"memory")
#endif

static inline int ls_xxx_spin_unlock(ls_spinlock_t *p)
{
    __sync_lock_release(p);
    return 0;
}

static inline int ls_yyy_spin_unlock(ls_spinlock_t *p)
{
    barrier();
    *p = LS_LOCK_AVAIL;
    return 0;
}

static inline int ls_xxx_spin_lock(ls_spinlock_t *p)
{
    while (1)
    {
        if ((*p == LS_LOCK_AVAIL)
            && __sync_bool_compare_and_swap(p, LS_LOCK_AVAIL, LS_LOCK_INUSE))
            return 0;
        cpu_relax();
    }
}

static inline int ls_yyy_spin_lock(ls_spinlock_t *p)
{
    while (1)
    {
        if (__sync_bool_compare_and_swap(p, LS_LOCK_AVAIL, LS_LOCK_INUSE))
            return 0;
        cpu_relax();
    }
}

static inline int ls_zzz_spin_lock(ls_spinlock_t *p)
{
    while (1)
    {
        barrier();
        if ((*p == LS_LOCK_AVAIL)
            && __sync_bool_compare_and_swap(p, LS_LOCK_AVAIL, LS_LOCK_INUSE))
            return 0;
    }
}

#define LSI_SETUP1   ls_atomic_spin_setup
#define LSI_TRYLOCK1 ls_atomic_spin_trylock
#define LSI_LOCK1    ls_atomic_spin_lock
#define LSI_UNLOCK1  ls_atomic_spin_unlock
typedef int          LOCK_TYPE1;

#define LSI_SETUP2   ls_futex_setup
#define LSI_TRYLOCK2 ls_futex_trylock
#define LSI_LOCK2    ls_futex_lock
#define LSI_UNLOCK2  ls_futex_unlock
typedef int          LOCK_TYPE2;

#define LSI_SETUP3   ls_futex_setup
#define LSI_TRYLOCK3 ls_futex_trylock
#define LSI_LOCK3    ls_futex_safe_lock
#define LSI_UNLOCK3  ls_futex_safe_unlock
typedef int          LOCK_TYPE3;

#define LSI_SETUP4   ls_pspinlock_setup
#define LSI_TRYLOCK4 ls_pspinlock_trylock
#define LSI_LOCK4    ls_pspinlock_lock
#define LSI_UNLOCK4  ls_pspinlock_unlock
typedef ls_pspinlock_t  LOCK_TYPE4;

#define LSI_SETUP5   ls_pthread_mutex_setup
#define LSI_TRYLOCK5 pthread_mutex_trylock
#define LSI_LOCK5    pthread_mutex_lock
#define LSI_UNLOCK5  pthread_mutex_unlock
typedef pthread_mutex_t  LOCK_TYPE5;

#define LSI_SETUP6   ls_lock_setup
#define LSI_TRYLOCK6 ls_lock_trylock
#define LSI_LOCK6    ls_lock_lock
#define LSI_UNLOCK6  ls_lock_unlock
typedef ls_lock_t    LOCK_TYPE6;

//#define TRYLOCK

typedef struct
{
    pthread_t   m_thread;
    void       *m_exit;
    int         m_id;
    int         m_bigValue;
    int         m_myCount;
    int         m_waitCount;
    void       *m_data;
} myThread_t;
static myThread_t threadMap[1000000];

static void showEnd(int numthreads)
{
    int i;
    myThread_t *p;
    p = threadMap;
    for (i = 0; i < numthreads; i++, p++)
    {
        printf("DONE %d [bigValue = %d myCount = %d waitCount=%d] %ld\n",
               p->m_id,
               p->m_bigValue,
               p->m_myCount,
               p->m_waitCount,
               (long)p->m_exit);
    }
}


/*
 * NOTE: the runTest routines exist separately
 *   so that the lock functions may be called inline
 */
static void   *runTest1(void *o)
{
    myThread_t  *p = (myThread_t *)o;
    printf("runTest1 %d\n", p->m_id);

    int    i;
    for (i = 0; i < loopCount; i++)
    {
#ifdef TRYLOCK
        if (LSI_TRYLOCK1((LOCK_TYPE1 *)p->m_data) != 0)
        {
            p->m_waitCount++;
            LSI_LOCK1((LOCK_TYPE1 *)p->m_data);
        }
#else
        LSI_LOCK1((LOCK_TYPE1 *)p->m_data);
#endif
        if (++bigCount > loopCount)
        {
            p->m_myCount = i;
            i = loopCount;
        }
        else
        {
            bigValue += p->m_id;
            p->m_bigValue = bigValue;
        }
        LSI_UNLOCK1((LOCK_TYPE1 *)p->m_data);
    }
    if (i == loopCount)     /* bigCount did *not* terminate loop */
        p->m_myCount = i;

    pthread_exit((void *)(long) - p->m_id);
    return NULL;
}


static void   *runTest2(void *o)
{
    myThread_t  *p = (myThread_t *)o;
    printf("runTest2 %d\n", p->m_id);

    int    i;
    for (i = 0; i < loopCount; i++)
    {
#ifdef TRYLOCK
        if (LSI_TRYLOCK2((LOCK_TYPE2 *)p->m_data) != 0)
        {
            p->m_waitCount++;
            LSI_LOCK2((LOCK_TYPE2 *)p->m_data);
        }
#else
        LSI_LOCK2((LOCK_TYPE2 *)p->m_data);
#endif
        if (++bigCount > loopCount)
        {
            p->m_myCount = i;
            i = loopCount;
        }
        else
        {
            bigValue += p->m_id;
            p->m_bigValue = bigValue;
        }
        LSI_UNLOCK2((LOCK_TYPE2 *)p->m_data);
    }
    if (i == loopCount)     /* bigCount did *not* terminate loop */
        p->m_myCount = i;

    pthread_exit((void *)(long) - p->m_id);
    return NULL;
}


static void   *runTest3(void *o)
{
    myThread_t  *p = (myThread_t *)o;
    printf("runTest3 %d\n", p->m_id);

    int    i;
    for (i = 0; i < loopCount; i++)
    {
#ifdef TRYLOCK
        if (LSI_TRYLOCK3((LOCK_TYPE3 *)p->m_data) != 0)
        {
            p->m_waitCount++;
            LSI_LOCK3((LOCK_TYPE3 *)p->m_data);
        }
#else
        LSI_LOCK3((LOCK_TYPE3 *)p->m_data);
#endif
        if (++bigCount > loopCount)
        {
            p->m_myCount = i;
            i = loopCount;
        }
        else
        {
            bigValue += p->m_id;
            p->m_bigValue = bigValue;
        }
        LSI_UNLOCK3((LOCK_TYPE3 *)p->m_data);
    }
    if (i == loopCount)     /* bigCount did *not* terminate loop */
        p->m_myCount = i;

    pthread_exit((void *)(long) - p->m_id);
    return NULL;
}


static void   *runTest4(void *o)
{
    myThread_t  *p = (myThread_t *)o;
    printf("runTest4 %d\n", p->m_id);

    int    i;
    for (i = 0; i < loopCount; i++)
    {
#ifdef TRYLOCK
        if (LSI_TRYLOCK4((LOCK_TYPE4 *)p->m_data) != 0)
        {
            p->m_waitCount++;
            LSI_LOCK4((LOCK_TYPE4 *)p->m_data);
        }
#else
        LSI_LOCK4((LOCK_TYPE4 *)p->m_data);
#endif
        if (++bigCount > loopCount)
        {
            p->m_myCount = i;
            i = loopCount;
        }
        else
        {
            bigValue += p->m_id;
            p->m_bigValue = bigValue;
        }
        LSI_UNLOCK4((LOCK_TYPE4 *)p->m_data);
    }
    if (i == loopCount)     /* bigCount did *not* terminate loop */
        p->m_myCount = i;

    pthread_exit((void *)(long) - p->m_id);
    return NULL;
}


static void   *runTest5(void *o)
{
    myThread_t  *p = (myThread_t *)o;
    printf("runTest5 %d\n", p->m_id);

    int    i;
    for (i = 0; i < loopCount; i++)
    {
#ifdef TRYLOCK
        if (LSI_TRYLOCK5((LOCK_TYPE5 *)p->m_data) != 0)
        {
            p->m_waitCount++;
            LSI_LOCK5((LOCK_TYPE5 *)p->m_data);
        }
#else
        LSI_LOCK5((LOCK_TYPE5 *)p->m_data);
#endif
        if (++bigCount > loopCount)
        {
            p->m_myCount = i;
            i = loopCount;
        }
        else
        {
            bigValue += p->m_id;
            p->m_bigValue = bigValue;
        }
        LSI_UNLOCK5((LOCK_TYPE5 *)p->m_data);
    }
    if (i == loopCount)     /* bigCount did *not* terminate loop */
        p->m_myCount = i;

    pthread_exit((void *)(long) - p->m_id);
    return NULL;
}


static void   *runTest6(void *o)
{
    myThread_t  *p = (myThread_t *)o;
    printf("runTest6 %d\n", p->m_id);

    int    i;
    for (i = 0; i < loopCount; i++)
    {
#ifdef TRYLOCK
        if (LSI_TRYLOCK6((LOCK_TYPE6 *)p->m_data) != 0)
        {
            p->m_waitCount++;
            LSI_LOCK6((LOCK_TYPE6 *)p->m_data);
        }
#else
        LSI_LOCK6((LOCK_TYPE6 *)p->m_data);
#endif
        if (++bigCount > loopCount)
        {
            p->m_myCount = i;
            i = loopCount;
        }
        else
        {
            bigValue += p->m_id;
            p->m_bigValue = bigValue;
        }
        LSI_UNLOCK6((LOCK_TYPE6 *)p->m_data);
    }
    if (i == loopCount)     /* bigCount did *not* terminate loop */
        p->m_myCount = i;

    pthread_exit((void *)(long) - p->m_id);
    return NULL;
}


int         myLock1;
int         myLock2;
int         myLock3;
pthread_spinlock_t  myLock4;
pthread_mutex_t     myLock5;
ls_lock_t  myLock6;

static struct testinfo
{
    void *(* testFunc)(void *);
    void *pLock;
    const char *pName;
} testinfo[] =
{
    { runTest1, (void *) &myLock1, "ATOMIC-SPIN" },
    { runTest2, (void *) &myLock2, "FUTEX" },
    { runTest3, (void *) &myLock3, "PID-FUTEX" },
    { runTest4, (void *) &myLock4, "PTHREAD-SPIN" },
    { runTest5, (void *) &myLock5, "PTHREAD-MUTEX" },
    { runTest6, (void *) &myLock6, "LSR-LOCK" },
};


int testlock(int numthreads, int index)
{
    myThread_t *p;
    int i;
    void *plock;

    bigValue = 0;
    bigCount = 0;

    /* initialize the data */
    plock = testinfo[index].pLock;
    switch (index)
    {
    case 0:
        LSI_SETUP1((LOCK_TYPE1 *)plock);
        break;
    case 1:
        LSI_SETUP2((LOCK_TYPE2 *)plock);
        break;
    case 2:
        LSI_SETUP3((LOCK_TYPE3 *)plock);
        break;
    case 3:
        LSI_SETUP4((LOCK_TYPE4 *)plock);
        break;
    case 4:
        LSI_SETUP5((LOCK_TYPE5 *)plock);
        break;
    case 5:
        LSI_SETUP6((LOCK_TYPE6 *)plock);
        break;
    default:
        return LS_FAIL;
    }

    printf("\nRUNNING numThreads %d loop %d\n", numthreads, loopCount);
    p = threadMap;

    Timer x(testinfo[index].pName);
    for (i = 0; i < numthreads; i++, p++)
    {
        p->m_exit = (void *)0;
        p->m_id = i;
        p->m_bigValue = 0;
        p->m_myCount = 0;
        p->m_waitCount = 0;
        p->m_data = plock;
        /* runTest((void *)p); */

        if (pthread_create(&p->m_thread, NULL, testinfo[index].testFunc,
                           (void *)p))
        {
            numthreads = i;
            break;
        }
    }
    p = threadMap;
    double expected = 0.0;
    for (i = 0; i < numthreads; i++, p++)
    {
        pthread_join(p->m_thread, (void **)&p->m_exit);
        expected += (p->m_id * (double)p->m_myCount);
    }

    x.setCount(numthreads);
    std::cout << "RUNNING numThreads " << numthreads
              << " loop " << loopCount;
    std::cout << " TEST RESULT " << x << "\n";

    showEnd(numthreads);

    if (expected != bigValue)
    {
        printf("\nRUNNING numThreads %d loop %d\n", numthreads, loopCount);
        printf("ERROR BIGVALUE = %d %8.0lf %s\n", bigValue, expected,
               ((int)expected == bigValue) ? "MATCH" : "NOT-MATCH-RACE");
    }
    return 0;
}


/*
 *  Simple lock test
 */
int main(int ac, char *av[])
{
    int i;
    int index;

    if (ac > 2)
    {
        numThreads = atoi(av[2]);
        if (ac > 3)
            loopCount = atoi(av[3]);
    }
    for (i = 0; i < 3; i++)
    {
        std::cout << "\n";
        for (index = 0; index < (int)(sizeof(testinfo) / sizeof(testinfo[0]));
             index++)
        {
            fprintf(stderr, "%d: %s\n", i, testinfo[index].pName);
            testlock(numThreads, index);
        }
    }
    std::cout << "Bye.\n";
}

