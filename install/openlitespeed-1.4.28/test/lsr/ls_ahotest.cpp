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

#include "ls_ahotest.h"

#include <stdio.h>
#include <lsr/ls_pool.h>
#include "unittest-cpp/UnitTest++.h"

TEST(ls_AhoTest_test)
{
    int iNumTests = 9;
    size_t iOutStart = 0, iOutEnd = 0;
    ls_aho_t *pThis;
    ls_aho_state_t **outlast = (ls_aho_state_t **)ls_palloc(sizeof(
                                   ls_aho_state_t **));
#ifdef LS_AHO_DEBUG
    printf("Start lsr Aho Test");
#endif
    for (int i = 0; i < iNumTests; ++i)
    {
        pThis = ls_aho_initTree(ls_aho_TestAccept[i], ls_aho_TestAcceptLen[i],
                                ls_aho_Sensitive[i]);
        if (pThis == NULL)
        {
            printf("Init Tree failed.");
            ls_pfree(outlast);
            return;
        }

        ls_aho_search(pThis, NULL, ls_aho_TestInput[i], ls_aho_TestInputLen[i], 0,
                      &iOutStart, &iOutEnd, outlast);

        CHECK(iOutStart == ls_aho_OutStartRes[i]
              && iOutEnd == ls_aho_OutEndRes[i]);
        iOutStart = 0;
        iOutEnd = 0;
        ls_aho_delete(pThis);
    }
    ls_pfree(outlast);

}

ls_aho_t *ls_aho_initTree(const char *acceptBuf[], int bufCount,
                          int sensitive)
{
    int i;
    ls_aho_t *pThis;

    if ((pThis = ls_aho_new(sensitive)) == NULL)
    {
        printf("Init failed.");
        return NULL;
    }
    for (i = 0; i < bufCount; ++i)
    {
        if ((ls_aho_addpattern(pThis, acceptBuf[i], strlen(acceptBuf[i]))) == 0)
        {
            printf("Add patterns failed.");
            ls_aho_delete(pThis);
            return NULL;
        }
    }
    if ((ls_aho_maketree(pThis)) == 0)
    {
        printf("Make tree failed.");
        ls_aho_delete(pThis);
        return NULL;
    }
    if ((ls_aho_optimizetree(pThis)) == 0)
    {
        printf("Optimize failed.");
        ls_aho_delete(pThis);
        return NULL;
    }
    return pThis;
}

#endif
