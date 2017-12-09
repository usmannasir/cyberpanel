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

#include <lsr/ls_atomic.h>
#include <lsr/ls_lfstack.h>
#include <thread/worker.h>
#include <util/misc/profiletime.h>

#include <pthread.h>
#include <stdio.h>
#include <cstddef>
#include <sys/types.h>
#include <unistd.h>


#define LFSTACK_LOOPCOUNTER 100000
#define LFSTACK_NUMWORKERS 20
#define LFSTACK_NUMPRODUCERS 10
#define LFSTACK_NUMITEMS (LFSTACK_NUMPRODUCERS + 1) * LFSTACK_LOOPCOUNTER
#define LFSTACK_OFFSET 5

static int doLfStackTest = 0;
static int doLfStackBenchTest = 1;

class StackNode
{
private:
    ls_lfnodei_t m_node;
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
    ls_lfnodei_t *getNodePtr()      {    return &m_node;    }

    void setVal(int iVal)         {   m_iVal = iVal;      }

    static StackNode *getStackNodePtr(ls_lfnodei_t *pNode)
    {
        return (StackNode *)pNode;
    }
};

class StackPair
{
public:
    ls_lfstack_t *m_pJob;
    ls_lfstack_t *m_pFinish;
public:
    StackPair()
    {
        m_pJob = ls_lfstack_new();
        m_pFinish = ls_lfstack_new();
    }

    ~StackPair()
    {
        ls_lfstack_delete(m_pJob);
        ls_lfstack_delete(m_pFinish);
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

static void *ls_lfstack_printtest(void *arg)
{
    StackPair *pPair = (StackPair *)arg;
//     usleep( 1000 );
    ls_lfnodei_t *ptr = ls_lfstack_pop(pPair->m_pJob);
    if (!ptr)
        return NULL;
    StackNode *pNode = StackNode::getStackNodePtr(ptr);
    pNode->setVal(pNode->getVal() - LFSTACK_OFFSET);
//     printf( "%lx Got val: %d\n", pthread_self(), pNode->getVal() );
    ls_lfstack_push(pPair->m_pFinish, pNode->getNodePtr());
    return NULL;
}

static void *ls_lfstack_producer(void *arg)
{
    ProducerArg *pArg = (ProducerArg *)arg;
    StackPair *pPair = pArg->m_pSp;
    int iOffset = pArg->m_iOffset;
    int i;

    for (i = 0; i < LFSTACK_LOOPCOUNTER; ++i)
    {
        StackNode *pNode = new StackNode(i + iOffset + LFSTACK_OFFSET);
        ls_lfstack_push(pPair->m_pJob, pNode->getNodePtr());
    }
    return pArg;
}

static int lfstackTest()
{
    StackPair *pPair = new StackPair();
    int i, iSuccess, off, aPairCount[LFSTACK_NUMITEMS] = {0};
    void *ret;
    Worker *aWorker[LFSTACK_NUMWORKERS], *aProducers[LFSTACK_NUMPRODUCERS];

    for (i = 0; i < LFSTACK_NUMWORKERS; ++i)
    {
        aWorker[i] = new Worker(ls_lfstack_printtest);
        aWorker[i]->run(pPair);
    }

    for (i = 0; i < LFSTACK_NUMPRODUCERS; ++i)
    {
        off = i * LFSTACK_LOOPCOUNTER;
        aProducers[i] = new Worker(ls_lfstack_producer);
        ProducerArg *pArg = new ProducerArg(pPair, off);
        aProducers[i]->run(pArg);
    }

    off = LFSTACK_NUMPRODUCERS * LFSTACK_LOOPCOUNTER;

    for (i = 0; i < LFSTACK_LOOPCOUNTER; ++i)
    {
        StackNode *pNode = new StackNode(i + off + LFSTACK_OFFSET);
        ls_lfstack_push(pPair->m_pJob, pNode->getNodePtr());
    }

    for (i = 0; i < LFSTACK_NUMITEMS; ++i)
    {
        ls_lfnodei_t *ls_pNode;
        do
        {
//             printf( "loop\n" );
            ls_pNode = ls_lfstack_pop(pPair->m_pFinish);
        }
        while (ls_pNode == NULL);
        StackNode *pNode = StackNode::getStackNodePtr(ls_pNode);
        aPairCount[pNode->getVal()]++;
    }

    for (i = 0; i < LFSTACK_NUMPRODUCERS; ++i)
    {
        aProducers[i]->join(&ret);
        ProducerArg *pArg = (ProducerArg *)ret;
        delete pArg;
        delete aProducers[i];
    }

    for (i = 0; i < LFSTACK_NUMWORKERS; ++i)
    {
        aWorker[i]->setStop();
        aWorker[i]->join(&ret);
        delete aWorker[i];
    }

    iSuccess = 0;
    for (i = 0; i < LFSTACK_NUMITEMS; ++i)
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

static void *benchRun(void *arg)
{
    int i, j;
    int iLoops = 100;
    int iIterations = LFSTACK_LOOPCOUNTER / 100;
    StackNode *pNodes[iIterations];
    ls_lfstack_t *pStack = (ls_lfstack_t *)arg;
    for (i = 0; i < iIterations; ++i)
    {
        pNodes[i] = new StackNode(1);
    }
    
    for (j = 0; j < iLoops; ++j)
    {
        for (i = 0; i < iIterations; ++i)
        {
            ls_lfstack_push(pStack, pNodes[i]->getNodePtr());
        }

        for (i = 0; i < iIterations; ++i)
        {
            ls_lfnodei_t *pNode;
            while ((pNode = ls_lfstack_pop(pStack)) == NULL);
            pNodes[i] = StackNode::getStackNodePtr(pNode);
        }
    }
    for (i = 0; i < iIterations; ++i)
    {
        pthread_yield();
        delete pNodes[i];
    }
    return NULL;
}

static void benchTest(int iNumThreads, const char *pName)
{
    --iNumThreads;
    int i, loopCount = 10;
    void *pRet;
    ls_lfstack_t *pStack = ls_lfstack_new();
    Thread *aThread;
    if (iNumThreads)
        aThread = new Thread[iNumThreads];
    else
        aThread = NULL;
    ProfileTime timer(pName, loopCount, PROFILE_MICRO);
    while (--loopCount > 0)
    {
        for (i = 0; i < iNumThreads; ++i)
            aThread[i].run(benchRun, pStack);
        pRet = benchRun(pStack);
        if (pRet)
            printf("Something's wrong!\n");
        for (i = 0; i < iNumThreads; ++i)
            aThread[i].join(&pRet);
    }
//     timer.printTime();
}

int main(int argc, char *argv[])
{
    int i, numReps = 4;
    if (doLfStackTest && doLfStackBenchTest)
        lfstackTest();
//     if ( doLfStackBenchTest )
//         benchTest( 4 );
    for (i = 0; i < numReps; ++i)
        benchTest(1, "LFStack, 1 thread, No Sleep");

    printf("\n\n");

    for (i = 0; i < numReps; ++i)
        benchTest(2, "LFStack, 2 thread, No Sleep");

    printf("\n\n");

    for (i = 0; i < numReps; ++i)
        benchTest(4, "LFStack, 4 thread, No Sleep");

    printf("\n\n");

    return 0;
}









