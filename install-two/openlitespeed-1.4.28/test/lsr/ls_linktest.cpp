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

#include <lsr/ls_link.h>
#include "unittest-cpp/UnitTest++.h"


SUITE(ls_linktest)
{
    TEST(ls_testlink)
    {
        ls_link_t *pobj1, * pobj2;
        ls_link_t obj3;
        pobj1 = ls_link_new(NULL);
        pobj2 = ls_link_new(NULL);
        CHECK(pobj1 != NULL);
        CHECK(pobj2 != NULL);
        ls_link(&obj3, NULL);

        CHECK(ls_link_next(pobj1) == NULL);
        CHECK(ls_link_getobj(pobj1) == NULL);
        CHECK(ls_link_next(pobj2) == NULL);
        CHECK(ls_link_getobj(pobj2) == NULL);
        CHECK(ls_link_next(&obj3) == NULL);
        CHECK(ls_link_getobj(&obj3) == NULL);

        ls_link_addnext(pobj1, pobj2);
        CHECK(ls_link_next(pobj1) == pobj2);
        CHECK(ls_link_next(pobj2) == NULL);

        ls_link_addnext(pobj1, &obj3);
        CHECK(ls_link_next(pobj1) == &obj3);
        CHECK(ls_link_next(pobj2) == NULL);
        CHECK(ls_link_next(&obj3) == pobj2);

        CHECK(ls_link_removenext(pobj2) == NULL);
        CHECK(ls_link_next(pobj1) == &obj3);
        CHECK(ls_link_next(pobj2) == NULL);
        CHECK(ls_link_next(&obj3) == pobj2);

        CHECK(ls_link_removenext(&obj3) == pobj2);
        CHECK(ls_link_next(pobj1) == &obj3);
        CHECK(ls_link_next(pobj2) == NULL);
        CHECK(ls_link_next(&obj3) == NULL);

        ls_link_addnext(&obj3, pobj2);
        CHECK(ls_link_next(pobj1) == &obj3);
        CHECK(ls_link_next(pobj2) == NULL);
        CHECK(ls_link_next(&obj3) == pobj2);

        CHECK(ls_link_removenext(pobj1) == &obj3);
        CHECK(ls_link_next(pobj1) == pobj2);
        CHECK(ls_link_next(pobj2) == NULL);
        CHECK(ls_link_next(&obj3) == NULL);

        CHECK(ls_link_removenext(pobj1) == pobj2);
        CHECK(ls_link_next(pobj1) == NULL);
        CHECK(ls_link_next(pobj2) == NULL);

        ls_link_delete(pobj1);
        ls_link_delete(pobj2);
    }

    TEST(ls_testdlink)
    {
        ls_dlink_t *pobj1, * pobj2;
        ls_dlink_t obj3;
        pobj1 = ls_dlink_new(NULL, NULL);
        pobj2 = ls_dlink_new(NULL, NULL);
        CHECK(pobj1 != NULL);
        CHECK(pobj2 != NULL);
        ls_dlink(&obj3, NULL, NULL);

        CHECK(ls_dlink_next(pobj1) == NULL);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_getobj(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == NULL);
        CHECK(ls_dlink_getobj(pobj2) == NULL);
        CHECK(ls_dlink_next(&obj3) == NULL);
        CHECK(ls_dlink_prev(&obj3) == NULL);
        CHECK(ls_dlink_getobj(&obj3) == NULL);

        ls_dlink_addnext(pobj1, pobj2);
        CHECK(ls_dlink_next(pobj1) == pobj2);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == pobj1);

        ls_dlink_addnext(pobj1, &obj3);
        CHECK(ls_dlink_next(pobj1) == &obj3);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == &obj3);
        CHECK(ls_dlink_next(&obj3) == pobj2);
        CHECK(ls_dlink_prev(&obj3) == pobj1);

        CHECK(ls_dlink_removenext(pobj2) == NULL);
        CHECK(ls_dlink_next(pobj1) == &obj3);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == &obj3);
        CHECK(ls_dlink_next(&obj3) == pobj2);
        CHECK(ls_dlink_prev(&obj3) == pobj1);

        CHECK(ls_dlink_removenext(&obj3) == pobj2);
        CHECK(ls_dlink_next(pobj1) == &obj3);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == NULL);
        CHECK(ls_dlink_next(&obj3) == NULL);
        CHECK(ls_dlink_prev(&obj3) == pobj1);

        ls_dlink_addnext(&obj3, pobj2);
        CHECK(ls_dlink_next(pobj1) == &obj3);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == &obj3);
        CHECK(ls_dlink_next(&obj3) == pobj2);
        CHECK(ls_dlink_prev(&obj3) == pobj1);

        CHECK(ls_dlink_remove(pobj2) == NULL);
        CHECK(ls_dlink_next(pobj1) == &obj3);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == NULL);
        CHECK(ls_dlink_next(&obj3) == NULL);
        CHECK(ls_dlink_prev(&obj3) == pobj1);

        ls_dlink_addnext(&obj3, pobj2);
        CHECK(ls_dlink_next(pobj1) == &obj3);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == &obj3);
        CHECK(ls_dlink_next(&obj3) == pobj2);
        CHECK(ls_dlink_prev(&obj3) == pobj1);

        CHECK(ls_dlink_remove(&obj3) == pobj2);
        CHECK(ls_dlink_next(pobj1) == pobj2);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == pobj1);
        CHECK(ls_dlink_next(&obj3) == NULL);
        CHECK(ls_dlink_prev(&obj3) == NULL);

        ls_dlink_addnext(pobj1, &obj3);
        CHECK(ls_dlink_next(pobj1) == &obj3);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == &obj3);
        CHECK(ls_dlink_next(&obj3) == pobj2);
        CHECK(ls_dlink_prev(&obj3) == pobj1);

        CHECK(ls_dlink_removenext(pobj1) == &obj3);
        CHECK(ls_dlink_next(pobj1) == pobj2);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == pobj1);
        CHECK(ls_dlink_next(&obj3) == NULL);
        CHECK(ls_dlink_prev(&obj3) == NULL);

        CHECK(ls_dlink_removenext(pobj1) == pobj2);
        CHECK(ls_dlink_next(pobj1) == NULL);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == NULL);
        CHECK(ls_dlink_next(&obj3) == NULL);
        CHECK(ls_dlink_prev(&obj3) == NULL);

        ls_dlink_addprev(pobj2, pobj1);
        CHECK(ls_dlink_next(pobj1) == pobj2);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == pobj1);

        ls_dlink_addprev(pobj2, &obj3);
        CHECK(ls_dlink_next(pobj1) == &obj3);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == &obj3);
        CHECK(ls_dlink_next(&obj3) == pobj2);
        CHECK(ls_dlink_prev(&obj3) == pobj1);

        CHECK(ls_dlink_removeprev(pobj1)  == NULL);
        CHECK(ls_dlink_next(pobj1) == &obj3);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == &obj3);
        CHECK(ls_dlink_next(&obj3) == pobj2);
        CHECK(ls_dlink_prev(&obj3) == pobj1);

        CHECK(ls_dlink_removeprev(&obj3)  == pobj1);
        CHECK(ls_dlink_next(pobj1) == NULL);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == &obj3);
        CHECK(ls_dlink_next(&obj3) == pobj2);
        CHECK(ls_dlink_prev(&obj3) == NULL);

        ls_dlink_addprev(&obj3, pobj1);
        CHECK(ls_dlink_next(pobj1) == &obj3);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == &obj3);
        CHECK(ls_dlink_next(&obj3) == pobj2);
        CHECK(ls_dlink_prev(&obj3) == pobj1);

        CHECK(ls_dlink_removeprev(pobj2)  == &obj3);
        CHECK(ls_dlink_next(pobj1) == pobj2);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == pobj1);
        CHECK(ls_dlink_next(&obj3) == NULL);
        CHECK(ls_dlink_prev(&obj3) == NULL);

        CHECK(ls_dlink_removeprev(pobj2)  == pobj1);
        CHECK(ls_dlink_next(pobj1) == NULL);
        CHECK(ls_dlink_prev(pobj1) == NULL);
        CHECK(ls_dlink_next(pobj2) == NULL);
        CHECK(ls_dlink_prev(pobj2) == NULL);
        CHECK(ls_dlink_next(&obj3) == NULL);
        CHECK(ls_dlink_prev(&obj3) == NULL);

        ls_dlink_delete(pobj1);
        ls_dlink_delete(pobj2);
    }
}

#endif
