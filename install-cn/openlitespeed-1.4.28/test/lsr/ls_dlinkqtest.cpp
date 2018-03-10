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

#include <lsr/ls_dlinkq.h>
#include <lsr/ls_link.h>
#include "unittest-cpp/UnitTest++.h"


SUITE(ls_dlinkqtest)
{
    TEST(ls_testlinkq)
    {
        ls_linkq_t *pqobj;
        ls_link_t obj1, obj2, obj3;
        pqobj = ls_linkq_new();
        CHECK(pqobj != NULL);
        ls_link(&obj1, NULL);
        ls_link(&obj2, NULL);
        ls_link(&obj3, NULL);

        CHECK(ls_linkq_size(pqobj) == 0);
        CHECK(ls_linkq_begin(pqobj) == NULL);
        CHECK(ls_linkq_pop(pqobj) == NULL);

        ls_linkq_push(pqobj, &obj1);
        CHECK(ls_linkq_size(pqobj) == 1);
        CHECK(ls_linkq_begin(pqobj) == &obj1);

        ls_linkq_addnext(pqobj, ls_linkq_head(pqobj), &obj2);
        CHECK(ls_linkq_size(pqobj) == 2);
        CHECK(ls_linkq_begin(pqobj) == &obj2);

        CHECK(ls_linkq_pop(pqobj) == &obj2);
        CHECK(ls_linkq_size(pqobj) == 1);
        CHECK(ls_linkq_begin(pqobj) == &obj1);

        ls_linkq_push(pqobj, &obj3);
        ls_linkq_push(pqobj, &obj2);
        CHECK(ls_linkq_size(pqobj) == 3);
        CHECK(ls_linkq_begin(pqobj) == &obj2);

        CHECK(ls_linkq_removenext(pqobj, ls_linkq_head(pqobj))
              == &obj2);
        CHECK(ls_linkq_pop(pqobj) == &obj3);
        CHECK(ls_linkq_pop(pqobj) == &obj1);
        CHECK(ls_linkq_size(pqobj) == 0);
        CHECK(ls_linkq_begin(pqobj) == NULL);
        CHECK(ls_linkq_pop(pqobj) == NULL);

        ls_linkq_delete(pqobj);
    }

    TEST(ls_testdlinkq)
    {
        ls_dlinkq_t *pqobj;
        ls_dlink_t obj1, obj2, obj3;
        pqobj = ls_dlinkq_new();
        CHECK(pqobj != NULL);
        ls_dlink(&obj1, NULL, NULL);
        ls_dlink(&obj2, NULL, NULL);
        ls_dlink(&obj3, NULL, NULL);

        CHECK(ls_dlinkq_size(pqobj) == 0);
        CHECK(ls_dlinkq_empty(pqobj) == true);
        CHECK(ls_dlinkq_begin(pqobj) == ls_dlinkq_end(pqobj));
        CHECK(ls_dlinkq_begin(pqobj) != NULL);
        CHECK(ls_dlinkq_popfront(pqobj) == NULL);

        ls_dlinkq_append(pqobj, &obj1);
        CHECK(ls_dlinkq_size(pqobj) == 1);
        CHECK(ls_dlinkq_empty(pqobj) == false);
        CHECK(ls_dlinkq_begin(pqobj) != ls_dlinkq_end(pqobj));
        CHECK(ls_dlinkq_begin(pqobj) == &obj1);

        ls_dlinkq_append(pqobj, &obj2);
        CHECK(ls_dlinkq_size(pqobj) == 2);
        CHECK(ls_dlinkq_begin(pqobj) == &obj1);

        ls_dlinkq_pushfront(pqobj, &obj3);
        CHECK(ls_dlinkq_size(pqobj) == 3);
        CHECK(ls_dlinkq_begin(pqobj) == &obj3);

        ls_dlinkq_remove(pqobj, &obj1);
        CHECK(ls_dlinkq_size(pqobj) == 2);
        CHECK(ls_dlinkq_begin(pqobj) == &obj3);

        ls_dlinkq_append(pqobj, &obj1);
        CHECK(ls_dlinkq_size(pqobj) == 3);
        CHECK(ls_dlinkq_begin(pqobj) == &obj3);

        CHECK(ls_dlinkq_popfront(pqobj) == &obj3);
        CHECK(ls_dlinkq_size(pqobj) == 2);
        CHECK(ls_dlinkq_begin(pqobj) == &obj2);

        CHECK(ls_dlinkq_popfront(pqobj) == &obj2);
        CHECK(ls_dlinkq_size(pqobj) == 1);
        CHECK(ls_dlinkq_begin(pqobj) == &obj1);

        CHECK(ls_dlinkq_popfront(pqobj) == &obj1);
        CHECK(ls_dlinkq_size(pqobj) == 0);
        CHECK(ls_dlinkq_empty(pqobj) == true);
        CHECK(ls_dlinkq_begin(pqobj) == ls_dlinkq_end(pqobj));
        CHECK(ls_dlinkq_begin(pqobj) != NULL);
        CHECK(ls_dlinkq_popfront(pqobj) == NULL);

        ls_dlinkq_delete(pqobj);
    }
}

#endif
