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
#include <thread/workcrew.h>

#include <stdio.h>
#include "unittest-cpp/UnitTest++.h"

#define WORKCREWTEST_NUMWORKERS 16
#define DOWORKCREWTEST


#ifdef DOWORKCREWTEST

typedef struct
{
    ls_lfnodei_t m_node;
    int         m_oval;
    int         m_val;
} workcrewtest_t;

static void *workCrewTest(ls_lfnodei_t *item)
{
    workcrewtest_t *wct = (workcrewtest_t *)((char *)item - offsetof(
                              workcrewtest_t, m_node));
    wct->m_val++;
    return NULL;
}

TEST(THREAD_WORKCREW_TEST)
{
    printf("Start work crew test!\n");
    int i, ret;
    ls_lfqueue_t *pFinishedQueue = ls_lfqueue_new();
    WorkCrew *wc = new WorkCrew(0);

    CHECK(0 == wc->size()); // despite MIN/MAX defines, newly created have size 0

    ret = wc->resize(40);
    CHECK(LS_WORKCREW_MAXWORKER == wc->size());
    CHECK(0 == ret);

    ret = wc->resize(LS_WORKCREW_MINWORKER);
    CHECK(LS_WORKCREW_MINWORKER == wc->size());
    CHECK(0 == ret);

    for (i = 0; i < 50; ++i)
    {
        workcrewtest_t *wct = (workcrewtest_t *)ls_palloc(sizeof(workcrewtest_t));
        wct->m_node.next = NULL;
        wct->m_oval = i;
        wct->m_val = i;
        CHECK(wc->addJob((ls_lfnodei_t *)((char *)wct + offsetof(workcrewtest_t,
                                          m_node))) == 0);
    }

    CHECK(wc->startJobProcessor(WORKCREWTEST_NUMWORKERS,
                                pFinishedQueue,
                                workCrewTest) == 0);
    CHECK(WORKCREWTEST_NUMWORKERS == wc->size());

    for (; i < 100; ++i)
    {
        workcrewtest_t *wct = (workcrewtest_t *)ls_palloc(sizeof(workcrewtest_t));
        wct->m_node.next = NULL;
        wct->m_oval = i;
        wct->m_val = i;
        CHECK(wc->addJob((ls_lfnodei_t *)((char *)wct + offsetof(workcrewtest_t,
                                          m_node))) == 0);
    }

    CHECK(WORKCREWTEST_NUMWORKERS == wc->size());


    for (i = 0; i < 100; ++i)
    {
        ls_lfnodei_t *pNode = NULL;
        workcrewtest_t *wct = NULL;
        while ((pNode = ls_lfqueue_get(pFinishedQueue)) != NULL)
        {
            wct = (workcrewtest_t *)((char *)pNode - offsetof(workcrewtest_t, m_node));
            CHECK(wct->m_oval == wct->m_val-1);
            ls_pfree(wct);
        }
    }
    CHECK(i == 100);

    wc->resize(4);
    CHECK(4 == wc->size());
    delete wc;
    ls_lfqueue_delete(pFinishedQueue);
    printf("End work crew test!\n");
}
#endif

#endif



