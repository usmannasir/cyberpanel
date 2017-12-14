
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

#include <lsdef.h>
#include <util/radixtree.h>

#include <stdio.h>
#include <stdlib.h>

#include "unittest-cpp/UnitTest++.h"

// #define RADIXTREE_DEBUG
// #define RADIXTREE_PRINTTREE
#define RT_DOREGTEST
#define RT_DOWCTEST

#define RTTEST_NOCONTEXT    (1 << 0)
#define RTTEST_GLOBALPOOL   (1 << 1)
#define RTTEST_MERGE        (1 << 2)

const char *pInputs[] =
{
    "/home/one/user/dir",
    "/home/two/user/dir",
    "/home/one/client/",
    "/home/one/client/dir",
    "/home/one",
    "/home/one/client1",
    "/home/one/client2",
    "/home/one/client3",
    "/home/one/client4",
    "/home/one/client5",
    "/home/one/client6",
    "/home/one/client7",
    "/home/one/client8",
    "/home/one/client9",
    "/home/one/client10",
    "/home/one/client11",
    "/home/one/client12",
    "/home/one/client13",
    "/home/one/client14",
    "/home/one/client15",
    "/home/one/client16",
    "/home/one/client17",
    "/home/one/client18",
    "/home/one/client19",
    "/not/starting/with/slash",
    "/not",
    "/home/one/two/three/four/five/six/seven/eight/nine/ten/"
};
const int iInputLen = 27;

const char *pWCTest[] =
{
    "/home/user*",
    "/home/test*",
    "/home/newbegin*",
    "/home/end*",
    "/home/*diff",
    "/home/in*middle",
    "/home/username/",
    "/home/testing",
    "/home/test/wherewillthisgo",
    "/home/testing/where/this/will/go",
    "/home/*",
    "/home/*/has/children",
    "/home/*/has/multi",
    "/home/*/should/these/be/found/",
    "/home/*/multi/layer*",
    "/home/*/to/be.sure",
    "/home/one/*"
};
const int iWCLen = 17;
// How got to this value:
// 1 - /home/* added obj to /home/test
// 9 - /home/*/to/be.sure added 9 objects, and was not deleted at the end.
// - 4 - When erasing, erased the original objects as well.
const int iMergeIncr = 1 + 9 - 4;

const char *pWCFind[] =
{
    "/home/usermatch/",
    "/home/testmatch/",
    "/home/newbeginning",
    "/home/ending",
    "/home/blah/to/be.sure",
    "/home/updating",
    "/home/one/match"
};
const int iWCFindLen = 7;

static int test_for_each(void *pObj, const char *pKey, int iKeyLen)
{
#ifdef RADIXTREE_DEBUG
    printf("%.*s, %p\n", iKeyLen, pKey, pObj);
#endif
    return 0;
}


static int test_for_each2(void *pObj, void *pUData, const char *pKey,
                          int iKeyLen)
{
#ifdef RADIXTREE_DEBUG
    int *p = (int *)pUData;
    printf("%.*s, %p %d\n", iKeyLen, pKey, pObj, ++(*p));
#endif
    return 0;
}


void doTest(RadixTree *pTree, char **pDynamicInputs, int count)
{
    int i;
    RadixTree tree2;
#ifdef RADIXTREE_PRINTTREE
    pTree->printTree();
#endif
    for (i = 0; i < count; ++i)
    {
#ifdef RADIXTREE_DEBUG
        printf("Testing add %s\n", pDynamicInputs[i]);
#endif
        CHECK(pTree->insert(pDynamicInputs[i], strlen(pDynamicInputs[i]),
                            pTree) != NULL);
#ifdef RADIXTREE_PRINTTREE
        pTree->printTree();
#endif
    }

    for (i = 0; i < count; i += 2)
    {
#ifdef RADIXTREE_DEBUG
        printf("Testing update %s\n", pDynamicInputs[i]);
#endif
        CHECK(pTree->update(pDynamicInputs[i], strlen(pDynamicInputs[i]),
                            &tree2) == pTree);
#ifdef RADIXTREE_PRINTTREE
        pTree->printTree();
#endif
    }

    for (i = 0; i < count; i += 2)
    {
#ifdef RADIXTREE_DEBUG
        printf("Testing find %s\n", pDynamicInputs[i]);
#endif
        CHECK(pTree->find(pDynamicInputs[i], strlen(pDynamicInputs[i])) == &tree2);
#ifdef RADIXTREE_PRINTTREE
        pTree->printTree();
#endif
    }

    for (i = 1; i < count; i += 2)
    {
#ifdef RADIXTREE_DEBUG
        printf("Testing find %s\n", pDynamicInputs[i]);
#endif
        CHECK(pTree->find(pDynamicInputs[i], strlen(pDynamicInputs[i])) == pTree);
    }

    const char *pBegin = pDynamicInputs[26];
    const char *pNext = (const char *)memchr(pBegin + 1, '/',
                        strlen(pBegin) - 1);
    void *pOut, *data = pTree->bestMatch(pDynamicInputs[4],
                                         strlen(pDynamicInputs[4]));
    CHECK((pOut = pTree->bestMatch(pBegin, pNext - pBegin)) == NULL);
#ifdef RADIXTREE_DEBUG
    printf("Should be null: %p\n", pOut);
#endif
    if (pTree->getNoContext() == 0)
    {
        while ((pNext = (const char *)memchr(pNext + 1, '/',
                                             strlen(pNext) - 1)) != NULL)
        {
            CHECK((pOut = pTree->bestMatch(pBegin, pNext - pBegin)) == data);
#ifdef RADIXTREE_DEBUG
            printf("Should match: %p %p\n", pOut, data);
#endif
        }
    }
    else
    {
        pNext = (const char *)memchr(pNext + 1, '/', strlen(pNext) - 1);
        CHECK((pOut = pTree->bestMatch(pBegin, pNext - pBegin)) == data);
        while ((pNext = (const char *)memchr(pNext + 1, '/',
                                             strlen(pNext) - 2)) != NULL)
        {
            CHECK((pOut = pTree->bestMatch(pBegin, pNext - pBegin)) == NULL);
#ifdef RADIXTREE_DEBUG
            printf("Should be NULL: %p\n", pOut);
#endif
        }
        CHECK((pOut = pTree->bestMatch(pBegin, strlen(pBegin))) == &tree2);

    }

    CHECK(pTree->for_each(test_for_each) == count);
    int p = 0;
    CHECK(pTree->for_each2(test_for_each2, &p) == count);
}

void doWCTest(RadixTree *pTree)
{
    int i, count = iWCLen + iInputLen;
    RadixTree tree2;
    RadixTree tree3;
#ifdef RADIXTREE_PRINTTREE
    pTree->printTree();
#endif
    for (i = 0; i < iWCLen; ++i)
    {
#ifdef RADIXTREE_DEBUG
        printf("Testing add %s\n", pWCTest[i]);
#endif
        CHECK(pTree->insert(pWCTest[i], strlen(pWCTest[i]), pTree) != NULL);
#ifdef RADIXTREE_PRINTTREE
        pTree->printTree();
#endif
    }

    for (i = 0; i < iInputLen; ++i)
    {
#ifdef RADIXTREE_DEBUG
        printf("Testing add %s\n", pInputs[i]);
#endif
        CHECK(pTree->insert(pInputs[i], strlen(pInputs[i]), pTree) != NULL);
#ifdef RADIXTREE_PRINTTREE
        pTree->printTree();
#endif
    }

    for (i = 0; i < iInputLen; i += 2)
    {
#ifdef RADIXTREE_DEBUG
        printf("Testing update %s\n", pInputs[i]);
#endif
        CHECK(pTree->update(pInputs[i], strlen(pInputs[i]), &tree2) == pTree);
#ifdef RADIXTREE_PRINTTREE
        pTree->printTree();
#endif
    }

    for (i = 0; i < iInputLen; i += 2)
    {
#ifdef RADIXTREE_DEBUG
        printf("Testing find %s\n", pInputs[i]);
#endif
        CHECK(pTree->find(pInputs[i], strlen(pInputs[i])) == &tree2);
#ifdef RADIXTREE_PRINTTREE
        pTree->printTree();
#endif
    }

    for (i = 1; i < iInputLen; i += 2)
    {
#ifdef RADIXTREE_DEBUG
        printf("Testing find %s\n", pInputs[i]);
#endif
        CHECK(pTree->find(pInputs[i], strlen(pInputs[i])) == pTree);
    }

    for (i = 0; i < iWCFindLen; ++i)
    {
#ifdef RADIXTREE_DEBUG
        printf("Testing find %s\n", pWCFind[i]);
#endif
        CHECK(pTree->find(pWCFind[i], strlen(pWCFind[i])) == pTree);
    }

    for (i = 0; i < iWCFindLen; ++i)
    {
#ifdef RADIXTREE_DEBUG
        printf("Testing update %s\n", pWCFind[i]);
#endif
        CHECK(pTree->update(pWCFind[i], strlen(pWCFind[i]), &tree2) == NULL);
    }

    for (i = 0; i < iWCLen; ++i)
    {
#ifdef RADIXTREE_DEBUG
        printf("Testing update %s\n", pWCTest[i]);
#endif
        CHECK(pTree->update(pWCTest[i], strlen(pWCTest[i]), &tree3) == pTree);
#ifdef RADIXTREE_PRINTTREE
        pTree->printTree();
#endif
    }

    for (i = 0; i < iWCFindLen - 1; ++i)
    {
#ifdef RADIXTREE_DEBUG
        printf("Testing bestMatch %s\n", pWCFind[i]);
#endif
        CHECK(pTree->bestMatch(pWCFind[i], strlen(pWCFind[i])) == &tree3);
    }

    for (i = 0; i < iInputLen; i += 2)
    {
#ifdef RADIXTREE_DEBUG
        printf("Testing bestMatch %s\n", pInputs[i]);
#endif
        CHECK(pTree->bestMatch(pInputs[i], strlen(pInputs[i])) == &tree2);
#ifdef RADIXTREE_PRINTTREE
        pTree->printTree();
#endif
    }

    const char *pFindFail = "/home/undiff/has/no/children";
#ifdef RADIXTREE_DEBUG
    printf("Testing find %s\n", pFindFail);
#endif
    if (pTree->getNoContext())
        CHECK(pTree->find(pFindFail, strlen(pFindFail)) != NULL);
    else
        CHECK(pTree->find(pFindFail, strlen(pFindFail)) == NULL);

    if (pTree->getUseMerge())
    {
        const char *pEraseFail[] =
        {
            "/home/testing/has/children",
            "/home/testing/has/multi",
            "/home/*diff/multi/layer*",
            "/home/username/should/these/be/found"
        };
        const int iEraseFailCnt = 4;
        for (i = 0; i < iEraseFailCnt; ++i)
        {
#ifdef RADIXTREE_DEBUG
            printf("Testing find and erase %s\n", pEraseFail[i]);
#endif
            CHECK(pTree->find(pEraseFail[i], strlen(pEraseFail[i])) != NULL);
            CHECK(pTree->erase(pEraseFail[i], strlen(pEraseFail[i])) == NULL);
        }
#ifdef RADIXTREE_DEBUG
        printf("Testing erase %s\n", pWCTest[11]);
#endif
        CHECK(pTree->erase(pWCTest[11], strlen(pWCTest[11])) != NULL);
#ifdef RADIXTREE_DEBUG
        printf("Testing erase %s\n", pWCTest[12]);
#endif
        CHECK(pTree->erase(pWCTest[12], strlen(pWCTest[12])) != NULL);
#ifdef RADIXTREE_DEBUG
        printf("Testing erase %s\n", pWCTest[13]);
#endif
        CHECK(pTree->erase(pWCTest[13], strlen(pWCTest[13])) != NULL);
#ifdef RADIXTREE_DEBUG
        printf("Testing erase %s\n", pWCTest[14]);
#endif
        CHECK(pTree->erase(pWCTest[14], strlen(pWCTest[14])) != NULL);

        for (i = 0; i < iEraseFailCnt; ++i)
        {
#ifdef RADIXTREE_DEBUG
            printf("Testing find %s\n", pEraseFail[i]);
#endif
            CHECK(pTree->find(pEraseFail[i], strlen(pEraseFail[i])) == NULL);
        }
        if (pTree->getNoContext() != 0)
            count -= iEraseFailCnt;
        else
            count += iMergeIncr;
    }

    CHECK(pTree->for_each(test_for_each) == count);
    int p = 0;
    CHECK(pTree->for_each2(test_for_each2, &p) == count);
}

void setupTest(char **pDynamicInputs, int count)
{
    int i, iNumFlags = 1 << 2;
    RadixTree *pContTree, *pPtrTree;
#ifdef RT_DOREGTEST
    for (i = 0; i < iNumFlags; ++i)
    {
        pContTree = new RadixTree(RTMODE_CONTIGUOUS);
        pPtrTree = new RadixTree(RTMODE_POINTER);
        if ((i & RTTEST_NOCONTEXT) != 0)
        {
            pContTree->setNoContext();
            pPtrTree->setNoContext();
        }
        else
        {
            pContTree->setRootLabel("/", 1);
            pPtrTree->setRootLabel("/", 1);
        }
        if ((i & RTTEST_GLOBALPOOL) != 0)
        {
            pContTree->setUseGlobalPool();
            pPtrTree->setUseGlobalPool();
        }

        printf("CONTIGUOUS TEST: NoContext: %d, GlobalPool: %d\n",
               pContTree->getNoContext() != 0,
               pContTree->getUseGlobalPool() != 0);
        doTest(pContTree, pDynamicInputs, count);
        printf("END CONTIGUOUS TEST\n");

        printf("POINTER TEST: NoContext: %d, GlobalPool: %d\n",
               pPtrTree->getNoContext() != 0,
               pPtrTree->getUseGlobalPool() != 0);
        doTest(pPtrTree, pDynamicInputs, count);
        printf("END POINTER TEST\n");

        delete pContTree;
        delete pPtrTree;
    }
#endif
#ifdef RT_DOWCTEST
    iNumFlags = 1 << 3;
    for (i = 0; i < iNumFlags; ++i)
    {
        pContTree = new RadixTree(RTMODE_CONTIGUOUS);
        pPtrTree = new RadixTree(RTMODE_POINTER);
        pContTree->setUseWildCard();
        pPtrTree->setUseWildCard();
        if ((i & RTTEST_NOCONTEXT) != 0)
        {
            pContTree->setNoContext();
            pPtrTree->setNoContext();
        }
        else
        {
            pContTree->setRootLabel("/", 1);
            pPtrTree->setRootLabel("/", 1);
        }
        if ((i & RTTEST_GLOBALPOOL) != 0)
        {
            pContTree->setUseGlobalPool();
            pPtrTree->setUseGlobalPool();
        }
        if ((i & RTTEST_MERGE) != 0)
        {
            pContTree->setUseMerge();
            pPtrTree->setUseMerge();
        }

        printf("CONTIGUOUS TEST: NoContext: %d, GlobalPool: %d, Merge: %d\n",
               pContTree->getNoContext() != 0,
               pContTree->getUseGlobalPool() != 0,
               pContTree->getUseMerge());
        doWCTest(pContTree);
        printf("END CONTIGUOUS TEST\n");

        printf("POINTER TEST: NoContext: %d, GlobalPool: %d, Merge: %d\n",
               pPtrTree->getNoContext() != 0,
               pPtrTree->getUseGlobalPool() != 0,
               pPtrTree->getUseMerge());
        doWCTest(pPtrTree);
        printf("END POINTER TEST\n");
        delete pContTree;
        delete pPtrTree;
    }
#endif
}

TEST(radixtreetest)
{
    printf("Start Radix Tree Test!\n");
    int i, count = iInputLen, iDynamicCount = iInputLen;
    char **pDynamicInputs = (char **)malloc(sizeof(char *)*iDynamicCount);
    for (i = 0; i < iDynamicCount; ++i)
        pDynamicInputs[i] = strdup(pInputs[i]);

    setupTest(pDynamicInputs, count);

    for (i = 0; i < iDynamicCount; ++i)
        free(pDynamicInputs[i]);
    free(pDynamicInputs);
    printf("End Radix Tree Test!\n");
}


#endif

