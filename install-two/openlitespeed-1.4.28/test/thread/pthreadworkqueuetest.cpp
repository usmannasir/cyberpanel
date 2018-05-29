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
#ifdef RUN_TEST


#include <lsr/ls_lfqueue.h>
#include <lsr/ls_pool.h>
#include <thread/pthreadworkqueue.h>
#include <thread/worker.h>

#include <stdio.h>
#include "unittest-cpp/UnitTest++.h"

#define PTHREADWORKQUEUE_LOOP_COUNT 10000

#define DOPTHREADWORKQUEUETEST

#ifdef DOPTHREADWORKQUEUETEST

typedef struct
{
    ls_lfnodei_t m_node;
    int m_val;
} ptwq_t;

static ls_lfnodei_t *getPTWQNodePtr(ptwq_t *ptr)
{   return (ls_lfnodei_t *)((char *)ptr + offsetof(ptwq_t, m_node));  }
static ptwq_t *getPTWQPtr(ls_lfnodei_t *pNode)
{   return (ptwq_t *)((char *)pNode - offsetof(ptwq_t, m_node));}

static void *testGuaranteed(void *arg)
{
    PThreadWorkQueue *pQueue = (PThreadWorkQueue *)arg;
    int size = 1;
    ls_lfnodei_t *item;
    CHECK(pQueue->get(&item, size) == 0);
    if (size == 0)
        return NULL;
    getPTWQPtr(item)->m_val = 1;
    CHECK(pQueue->append(&item, size) == 0);
    return NULL;
}

static void *testTry(void *arg)
{
    PThreadWorkQueue *pQueue = (PThreadWorkQueue *)arg;
    int ret, size = 1;
    ls_lfnodei_t *item;
    ret = pQueue->tryget(&item, size);
    if (size != 0 && ret == 0)
    {
        getPTWQPtr(item)->m_val = 1;
        CHECK(pQueue->append(&item, size) == 0);
    }
    return NULL;
}

TEST(pthreadworkqueue_test)
{
    printf("Start PThreadWorkQueue Test!\n");
    int i, ret, iTmpSize, aEndCount[3] = {0};
    Worker worker1(testGuaranteed);
    Worker worker2(testGuaranteed);
    PThreadWorkQueue *wq = new PThreadWorkQueue();
    ls_lfnodei_t *aNodes[PTHREADWORKQUEUE_LOOP_COUNT];
    void *aRet[10];
    ls_lfnodei_t *aTmpNodes[10];

    for (i = 0; i < PTHREADWORKQUEUE_LOOP_COUNT; ++i)
    {
        ptwq_t *ptr = (ptwq_t *)ls_palloc(sizeof(ptwq_t));
        ptr->m_node.next = NULL;
        ptr->m_val = 0;
        aNodes[i] = getPTWQNodePtr(ptr);
    }

    wq->start();

    CHECK(wq->append(aNodes, PTHREADWORKQUEUE_LOOP_COUNT) == 0);

    worker1.run(wq);
    worker2.run(wq);
    sched_yield(); //Yield to provide a more random result.
    for (i = 0; i < PTHREADWORKQUEUE_LOOP_COUNT; ++i)
    {
        iTmpSize = 10;
        CHECK(wq->get(aTmpNodes, iTmpSize) == 0);
        if (iTmpSize == 0)
            continue;
        for (int j = 0; j < iTmpSize; ++j)
            getPTWQPtr(aTmpNodes[j])->m_val = 2;
        CHECK(wq->append(aTmpNodes, iTmpSize) == 0);
    }

    worker1.setStop();
    worker2.setStop();
    CHECK(worker1.join(aRet) == 0);
    CHECK(worker2.join(aRet) == 0);

    iTmpSize = PTHREADWORKQUEUE_LOOP_COUNT;
    CHECK(wq->get(aNodes, iTmpSize) == 0);
    CHECK(iTmpSize == PTHREADWORKQUEUE_LOOP_COUNT);

    for (i = 0; i < PTHREADWORKQUEUE_LOOP_COUNT; ++i)
    {
        ptwq_t *ptr = getPTWQPtr(aNodes[i]);
        int n = ptr->m_val;
        aEndCount[n]++;
        ptr->m_val = 0;
    }
    printf("Notice: The final count should be random each time.\n");
    printf("Final Count (REGULAR): 0: %d, 1: %d, 2: %d\n",
           aEndCount[0], aEndCount[1], aEndCount[2]);
    aEndCount[0] = 0;
    aEndCount[1] = 0;
    aEndCount[2] = 0;

    worker1.setWorkFn(testTry);
    worker2.setWorkFn(testTry);

    CHECK(wq->append(aNodes, PTHREADWORKQUEUE_LOOP_COUNT) == 0);

    worker1.run(wq);
    worker2.run(wq);

    for (i = 0; i < PTHREADWORKQUEUE_LOOP_COUNT; ++i)
    {
        iTmpSize = 10;
        ret = wq->tryget(aTmpNodes, iTmpSize);
        if (iTmpSize != 0 && ret == 0)
        {
            for (int j = 0; j < iTmpSize; ++j)
                getPTWQPtr(aTmpNodes[j])->m_val = 2;
            CHECK(wq->append(aTmpNodes, iTmpSize) == 0);
        }
    }

    worker1.setStop();
    worker2.setStop();
    CHECK(worker1.join(aRet) == 0);
    CHECK(worker2.join(aRet) == 0);

    iTmpSize = PTHREADWORKQUEUE_LOOP_COUNT;
    CHECK(wq->get(aNodes, iTmpSize) == 0);
    CHECK(iTmpSize == PTHREADWORKQUEUE_LOOP_COUNT);

    for (i = 0; i < PTHREADWORKQUEUE_LOOP_COUNT; ++i)
    {
        ptwq_t *ptr = getPTWQPtr(aNodes[i]);
        int n = ptr->m_val;
        aEndCount[n]++;
        ls_pfree(ptr);
    }
    printf("Final Count (TRY): 0: %d, 1: %d, 2: %d\n",
           aEndCount[0], aEndCount[1], aEndCount[2]);

    wq->shutdown();
    delete wq;
}
#endif

#endif



