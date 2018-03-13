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

#include <lsr/ls_tsstack.h>
#include <thread/thread.h>
#include <thread/worker.h>
#include <util/misc/profiletime.h>

#include <stdio.h>
#include <cstddef>


#define STACK_LOOPCOUNTER 100000
#define STACK_NUMWORKERS 20
#define STACK_NUMPRODUCERS 10
#define STACK_NUMITEMS (STACK_NUMPRODUCERS + 1) * STACK_LOOPCOUNTER
#define STACK_OFFSET 5


class StackNode
{
private:
    ls_nodei_t m_node;
    int m_iVal;
public:
    StackNode()
        : m_iVal(0)
    {
        m_node.next = NULL;
    }

    StackNode(int val)
        : m_iVal(val)
    {
        m_node.next = NULL;
    }

    int getVal() const              {    return m_iVal;     }
    ls_nodei_t *getNodePtr()       {    return &m_node;    }

    void setVal(int iVal)         {   m_iVal = iVal;      }

    static StackNode *getStackNodePtr(ls_nodei_t *pNode)
    {
        return (StackNode *)pNode;
    }
};

class StackPair
{
public:
    ls_tsstack_t *m_pJob;
    ls_tsstack_t *m_pFinish;
public:
    StackPair()
    {
        m_pJob = ls_tsstack_new();
        m_pFinish = ls_tsstack_new();
    }

    ~StackPair()
    {
        ls_tsstack_delete(m_pJob);
        ls_tsstack_delete(m_pFinish);
    }
};

class ProducerArg
{
public:
    StackPair *m_pSp;
    int m_iOffset;
public:
    ProducerArg(StackPair *pSp, int offset)
    {
        m_pSp = pSp;
        m_iOffset = offset;
    }
    ~ProducerArg()
    {}
};

static void *ls_tsstack_printtest(void *arg)
{
    StackPair *pPair = (StackPair *)arg;
//     usleep( 1000 );
    ls_nodei_t *ptr = ls_tsstack_pop(pPair->m_pJob);
    if (!ptr)
        return NULL;
    StackNode *pNode = StackNode::getStackNodePtr(ptr);
    pNode->setVal(pNode->getVal() - STACK_OFFSET);
//     printf( "%lx Got val: %d\n", pthread_self(), pNode->getVal() );
    ls_tsstack_push(pPair->m_pFinish, pNode->getNodePtr());
    return NULL;
}

static void *ls_tsstack_producer(void *arg)
{
    ProducerArg *pArg = (ProducerArg *)arg;
    StackPair *pPair = pArg->m_pSp;
    int iOffset = pArg->m_iOffset;
    int i;

    for (i = 0; i < STACK_LOOPCOUNTER; ++i)
    {
        StackNode *pNode = new StackNode(i + iOffset + STACK_OFFSET);
        ls_tsstack_push(pPair->m_pJob, pNode->getNodePtr());
    }
    return pArg;
}

static int multiThreadTest()
{
    StackPair *pPair = new StackPair();
    int i, off, iSuccess, aPairCount[STACK_NUMITEMS] = {0};
    void *ret;
    Worker *aWorker[STACK_NUMWORKERS], *aProducers[STACK_NUMPRODUCERS];

    for (i = 0; i < STACK_NUMWORKERS; ++i)
    {
        aWorker[i] = new Worker(ls_tsstack_printtest);
        aWorker[i]->run(pPair);
    }

    for (i = 0; i < STACK_NUMPRODUCERS; ++i)
    {
        off = i * STACK_LOOPCOUNTER;
        aProducers[i] = new Worker(ls_tsstack_producer);
        ProducerArg *pArg = new ProducerArg(pPair, off);
        aProducers[i]->run(pArg);
    }

    off = STACK_NUMPRODUCERS * STACK_LOOPCOUNTER;

    for (i = 0; i < STACK_LOOPCOUNTER; ++i)
    {
        StackNode *pNode = new StackNode(i + off + STACK_OFFSET);
        ls_tsstack_push(pPair->m_pJob, pNode->getNodePtr());
    }

    for (i = 0; i < STACK_NUMITEMS; ++i)
    {
        ls_nodei_t *ls_pNode;
        do
        {
//             printf( "loop\n" );
            ls_pNode = ls_tsstack_pop(pPair->m_pFinish);
        }
        while (ls_pNode == NULL);
        StackNode *pNode = StackNode::getStackNodePtr(ls_pNode);
        aPairCount[pNode->getVal()]++;
    }

    for (i = 0; i < STACK_NUMPRODUCERS; ++i)
    {
        aProducers[i]->join(&ret);
        ProducerArg *pArg = (ProducerArg *)ret;
        delete pArg;
        delete aProducers[i];
    }

    for (i = 0; i < STACK_NUMWORKERS; ++i)
    {
        aWorker[i]->setStop();
        aWorker[i]->join(&ret);
        delete aWorker[i];
    }

    iSuccess = 0;
    for (i = 0; i < STACK_NUMITEMS; ++i)
    {
        switch (aPairCount[i])
        {
        case 0:
            iSuccess = 1;
            break;
        case 1:
            break;
        default:
            iSuccess = 1;
            break;
        }
    }
    return iSuccess;
}

static void ls_stacktest()
{
    int i, j;
    ls_stack_t *pStack = ls_stack_new();
    int iLoops = 100;
    int iIterations = STACK_LOOPCOUNTER / 100;

    for (j = 0; j < iLoops; ++j)
    {
        for (i = 0; i < iIterations; ++i)
        {
            StackNode *pNode = new StackNode(i);
            ls_stack_push(pStack, pNode->getNodePtr());
        }

        for (i = 0; i < iIterations; ++i)
        {
            StackNode *pNode = StackNode::getStackNodePtr(ls_stack_pop(pStack));
            if (pNode->getVal() != iIterations - i - 1)
                printf("Iteration Miss!\n");
            delete pNode;
        }
    }
    ls_stack_delete(pStack);
}

static void *stackBenchRun(void *arg)
{
    int i, j;
    int iLoops = 100;
    int iIterations = STACK_LOOPCOUNTER / 100;
    ls_stack_t *pStack = (ls_stack_t *)arg;

    for (j = 0; j < iLoops; ++j)
    {
        for (i = 0; i < iIterations; ++i)
        {
            StackNode *pNode = new StackNode(1);
            ls_stack_push(pStack, pNode->getNodePtr());
        }

        for (i = 0; i < iIterations; ++i)
        {
            ls_nodei_t *pNode;
            while ((pNode = ls_stack_pop(pStack)) == NULL)
                ;
            StackNode *pSNode = StackNode::getStackNodePtr(pNode);
            delete pSNode;
        }
    }

    return NULL;
}

static void stackBenchTest(int iNumThreads, const char *pName)
{
    --iNumThreads;
    int i, loopCount = 10;
    void *pRet;
    ls_stack_t *pStack = ls_stack_new();
    Thread *aThread;
    if (iNumThreads)
        aThread = new Thread[iNumThreads];
    else
        aThread = NULL;
    ProfileTime timer(pName, loopCount, PROFILE_MICRO);
    while (--loopCount > 0)
    {
        for (i = 0; i < iNumThreads; ++i)
            aThread[i].run(stackBenchRun, pStack);
        pRet = stackBenchRun(pStack);
        if (pRet)
            printf("Something's wrong!\n");
        for (i = 0; i < iNumThreads; ++i)
            aThread[i].join(&pRet);
    }
//     timer.printTime();
}

static void *tsstackBenchRun(void *arg)
{
    int i, j;
    int iLoops = 100;
    int iIterations = STACK_LOOPCOUNTER / 100;
    ls_tsstack_t *pStack = (ls_tsstack_t *)arg;

    for (j = 0; j < iLoops; ++j)
    {
        for (i = 0; i < iIterations; ++i)
        {
            StackNode *pNode = new StackNode(1);
            ls_tsstack_push(pStack, pNode->getNodePtr());
        }

        for (i = 0; i < iIterations; ++i)
        {
            ls_nodei_t *pNode;
            while ((pNode = ls_tsstack_pop(pStack)) == NULL)
                ;
            StackNode *pSNode = StackNode::getStackNodePtr(pNode);
            delete pSNode;
        }
    }

    return NULL;
}

static void tsstackBenchTest(int iNumThreads, const char *pName)
{
    --iNumThreads;
    int i, loopCount = 10;
    void *pRet;
    ls_tsstack_t *pStack = ls_tsstack_new();
    Thread *aThread;
    if (iNumThreads)
        aThread = new Thread[iNumThreads];
    else
        aThread = NULL;
    ProfileTime timer(pName, loopCount, PROFILE_MICRO);
    while (--loopCount > 0)
    {
        for (i = 0; i < iNumThreads; ++i)
            aThread[i].run(tsstackBenchRun, pStack);
        pRet = tsstackBenchRun(pStack);
        if (pRet)
            printf("Something's wrong!\n");
        for (i = 0; i < iNumThreads; ++i)
            aThread[i].join(&pRet);
    }
//     timer.printTime();
}

static int doStackTest = 0;
static int doMultiThreadTest = 0;

static void stackBenchSuite()
{
    int i, numReps = 4;
    for (i = 0; i < numReps; ++i)
        stackBenchTest(1, "Stack, 1 thread, Sleep");

    printf("\n\n");

    for (i = 0; i < numReps; ++i)
        tsstackBenchTest(1, "TSStack, 1 thread, Sleep");

    printf("\n\n");

    for (i = 0; i < numReps; ++i)
        tsstackBenchTest(2, "TSStack, 2 thread, Sleep");

    printf("\n\n");

    for (i = 0; i < numReps; ++i)
        tsstackBenchTest(4, "TSStack, 4 thread, Sleep");
}

int main(int argc, char *argv[])
{
    if (doStackTest)
        ls_stacktest();
    if (doMultiThreadTest)
        multiThreadTest();

    stackBenchSuite();

    return 0;
}







