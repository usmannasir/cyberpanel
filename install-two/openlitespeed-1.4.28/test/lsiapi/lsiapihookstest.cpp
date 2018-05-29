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

#include <lsiapi/lsiapi.h>
#include <lsiapi/lsiapihooks.h>
#include <ls.h>
#include "unittest-cpp/UnitTest++.h"
#include <unistd.h>

/****************************************************************************************
Test Cases:
Default values of: size, capacity, begin, getFlag

::add(): 15 modules with various priorities to force reallocation and reordering of data
::get(): get each hook in the list and compare to known values
::size(): get size and compare to known values
::remove: remove middle, first and last elements
::dup:  duplicate hook list and compare to known values
::construct with optional parameter and compare to list passed in
::copy:  create copy and compare to known values
::find:  find last, last with bad callback, middle and first
******************************************************************************************/

TEST(LsiApiHooksTest)
{
    printf("============= Hook Test ==================\n");

    LsiApiHooks hooks;
    lsiapi_hook_t *pHook;

    int resultData[] = {0x6, 0x7, 0x8, 0xa, 0xb, 0xd, 0xe, 0xf, 0x5, 0x3, 0x4, 0x9, 0x2, 0x1, 0xc};
    int result2Data[] = {0x7, 0x8, 0xa, 0xb, 0xd, 0xf, 0x5, 0x3, 0x4, 0x9, 0x2, 0x1};


    lsi_module_t *pModule1 = (lsi_module_t *)(void *)0x01;
    lsi_module_t *pModule2 = (lsi_module_t *)(void *)0x02;
    lsi_module_t *pModule3 = (lsi_module_t *)(void *)0x03;
    lsi_module_t *pModule4 = (lsi_module_t *)(void *)0x04;
    lsi_module_t *pModule5 = (lsi_module_t *)(void *)0x05;
    lsi_module_t *pModule6 = (lsi_module_t *)(void *)0x06;
    lsi_module_t *pModule7 = (lsi_module_t *)(void *)0x07;
    lsi_module_t *pModule8 = (lsi_module_t *)(void *)0x08;
    lsi_module_t *pModule9 = (lsi_module_t *)(void *)0x09;
    lsi_module_t *pModule10 = (lsi_module_t *)(void *)0x0a;
    lsi_module_t *pModule11 = (lsi_module_t *)(void *)0x0b;
    lsi_module_t *pModule12 = (lsi_module_t *)(void *)0x0c;
    lsi_module_t *pModule13 = (lsi_module_t *)(void *)0x0d;
    lsi_module_t *pModule14 = (lsi_module_t *)(void *)0x0e;
    lsi_module_t *pModule15 = (lsi_module_t *)(void *)0x0f;

    //defaults
    CHECK(hooks.size() == 0);
    CHECK(hooks.capacity() == 4);
    CHECK(hooks.begin() - hooks.get(0) == 0);


    //fill hooks
    hooks.add(pModule1, (lsi_callback_pf)pModule1, 6);
    hooks.add(pModule2, (lsi_callback_pf)pModule1, 5);
    hooks.add(pModule3, (lsi_callback_pf)pModule1, 3);
    hooks.add(pModule4, (lsi_callback_pf)pModule1, 4);
    hooks.add(pModule5, (lsi_callback_pf)pModule1, 2);
    hooks.add(pModule6, (lsi_callback_pf)pModule1, 1);
    hooks.add(pModule7, (lsi_callback_pf)pModule1, 1);
    hooks.add(pModule8, (lsi_callback_pf)pModule1, 1);
    hooks.add(pModule9, (lsi_callback_pf)pModule1, 4);
    hooks.add(pModule10, (lsi_callback_pf)pModule1, 1);
    hooks.add(pModule11, (lsi_callback_pf)pModule1, 1);
    hooks.add(pModule12, (lsi_callback_pf)pModule1, 30);
    hooks.add(pModule13, (lsi_callback_pf)pModule1, 1);
    hooks.add(pModule14, (lsi_callback_pf)pModule1, 1);
    hooks.add(pModule15, (lsi_callback_pf)pModule1, 1);

    //debug data
    //printf ("add\n");
    int i = 0;
    for (pHook = hooks.begin(); pHook < hooks.end(); ++pHook)
    {
        //printf ("hook %x ",(*(int*)pHook));
        CHECK((*(int *)pHook) == resultData[i]);
        i++;
    }


    //constructor with optional parameter
    //printf ("const opt param\n");
    LsiApiHooks hooks3(hooks);
    //debug data
    i = 0;
    for (pHook = hooks3.begin(); pHook < hooks3.end(); ++pHook)
    {
        //printf ("hook %x ",(*(int*)pHook));
        CHECK((*(int *)pHook) == resultData[i]);
        i++;
    }

    //get
    //printf ("get\n");
    for (int i = 0; i < 15; i++)
    {
        pHook = hooks.get(i);
        //printf ("hook %x ",(*(int*)pHook));
        CHECK((*(int *)pHook) == resultData[i]);
    }

    //size
    CHECK(hooks.size() == 15);


    //remove
    hooks3.remove((hooks3.find(pModule14, (lsi_callback_pf)pModule1)));
    hooks3.remove((hooks3.find(pModule6, (lsi_callback_pf)pModule1)));
    hooks3.remove((hooks3.find(pModule12, (lsi_callback_pf)pModule1)));
    //debug data
    //printf ("remove\n");
    i = 0;
    for (pHook = hooks3.begin(); pHook < hooks3.end(); ++pHook)
    {
        //printf ("hook %x ",(*(int*)pHook));
        CHECK((*(int *)pHook) == result2Data[i]);
        i++;
    }

    //dup
    LsiApiHooks *hooks2 = hooks.dup();
    //debug data
    //printf ("dup\n");
    i = 0;
    for (pHook = hooks2->begin(); pHook < hooks2->end(); ++pHook)
    {
        //printf ("hook %x ",(*(int*)pHook));
        CHECK((*(int *)pHook) == resultData[i]);
        i++;
    }


    //copy
    LsiApiHooks hooks4;
    hooks4.copy(hooks);
    //printf ("copy\n");
    i = 0;
    for (pHook = hooks4.begin(); pHook < hooks4.end(); ++pHook)
    {
        //printf ("hook %x ",(*(int*)pHook));
        CHECK((*(int *)pHook) == resultData[i]);
        i++;
    }

    //find
    pHook = hooks.find(pModule12, (lsi_callback_pf)pModule1);
    CHECK(pHook->module == (lsi_module_t *)pModule12);
    pHook = hooks.find(pModule12, (lsi_callback_pf)pModule5);
    CHECK(pHook == (lsiapi_hook_t *)NULL);
    pHook = hooks.find(pModule6, (lsi_callback_pf)pModule1);
    CHECK(pHook->module == (lsi_module_t *)pModule6);
    pHook = hooks.find(pModule4, (lsi_callback_pf)pModule1);
    CHECK(pHook->module == (lsi_module_t *)pModule4);

    //printf("\n\n=============End Hook Test==================\n\n");

}

#endif
