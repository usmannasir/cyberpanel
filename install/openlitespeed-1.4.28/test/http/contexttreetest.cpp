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

#include "contexttreetest.h"
#include <http/contexttree.h>
#include <http/httpcontext.h>
#include "unittest-cpp/UnitTest++.h"

#include <unistd.h>

SUITE(ContextTreeTest)
{
    TEST(ContextTreeTest_runTest)
    {
        char r1[] = "/www/";
        char u0[] = "/";

        char u1[] = "/PL1/L2/L3/L4/";
        char l1[] = "/www/PL1/L2/L3/L4/";

        char u2[] = "/PL1/L2.html";
        char l2[] = "/www/PL1/L2.html";

        char u3[] = "/aL1/L2/L3/";
        char l3[] = "/www/aL1/L2/L3/";

        char u4[] = "/bL1/L2/";
        char l4[] = "/www/bL1/L2/";

        char u5[] = "/bL1/L2/L3/L4/";
        char l5[] = "/www/bL1/L2/L3/L4/";

        char u6[] = "/PL1/L2/";
        char l6[] = "/www/PL1/L2/";

        char u7[] = "/PL1/";
        char l7[] = "/www/PL1/";

        char t1[] = "/c/abd/sdf/";
        char t2[] = "/PL1/L2/L3/";
        char t3[] = "/PL1/L2/L3.abc";
        char t4[] = "/aL1/L2/L3/L4/asd.ds";
        char t5[] = "/aL1/L2/";
        char t6[] = "/bL1/";
        char t7[] = "/bL1/L2/L3/";

        char s1[] = "/www/c/abd/sdf/";
        char s2[] = "/www/PL1/L2/L3/";
        char s3[] = "/www/PL1/L2/L3.abc";
        char s4[] = "/www/aL1/L2/L3/L4/asd.ds";
        char s5[] = "/www/aL1/L2/";
        char s6[] = "/www/bL1/";
        char s7[] = "/www/bL1/L2/L3/";
        char s8[] = "/www1/bL1/L2/L3/";

        ContextTree tree;
        HttpContext *c0, *c1, *c2, *c3, *c4, *c5, *c6, *c7;
        HttpContext *pRoot;
        pRoot = new HttpContext();
        pRoot->set(u0, r1, NULL);
        tree.setRootContext(pRoot);
        tree.setRootLocation(r1, strlen(r1));

        c0 = new HttpContext();
        c0->set(u0, r1, NULL);
        c1 = new HttpContext();
        c1->set(u1, l1, NULL);
        c2 = new HttpContext();
        c2->set(u2, l2, NULL);
        c3 = new HttpContext();
        c3->set(u3, l3, NULL);
        c4 = new HttpContext();
        c4->set(u4, l4, NULL);
        c5 = new HttpContext();
        c5->set(u5, l5, NULL);
        c6 = new HttpContext();
        c6->set(u6, l6, NULL);
        c7 = new HttpContext();
        c7->set(u7, l7, NULL);

        CHECK(tree.add(c0) == 0);
        CHECK(c0->getParent() == pRoot);
        CHECK(tree.add(c1) == 0);
        CHECK(c1->getParent() == c0);
        CHECK(tree.add(c2) == 0);
        CHECK(c2->getParent() == c0);
        CHECK(tree.add(c3) == 0);
        CHECK(c3->getParent() == c0);
        CHECK(tree.add(c4) == 0);
        CHECK(c4->getParent() == c0);
        CHECK(tree.add(c5) == 0);
        CHECK(c5->getParent() == c4);
        CHECK(tree.add(c6) == 0);
        CHECK(c6->getParent() == c0);
        CHECK(c1->getParent() == c6);
        CHECK(tree.add(c5) > 0);
        CHECK(tree.add(c7) == 0);
        CHECK(c7->getParent() == c0);
        CHECK(c6->getParent() == c7);
        CHECK(c2->getParent() == c7);
        CHECK(c1->getParent() == c6);

        CHECK(tree.bestMatch(u0, strlen(u0)) == c0);
        CHECK(tree.bestMatch(u1, strlen(u1)) == c1);
        CHECK(tree.bestMatch(u2, strlen(u2)) == c2);
        CHECK(tree.bestMatch(u3, strlen(u3)) == c3);
        CHECK(tree.bestMatch(u4, strlen(u4)) == c4);
        CHECK(tree.bestMatch(u5, strlen(u5)) == c5);
        CHECK(tree.bestMatch(u6, strlen(u6)) == c6);

        CHECK(tree.matchLocation(r1, strlen(r1)) == c0);
        CHECK(tree.matchLocation(l1, strlen(l1)) == c1);
        CHECK(tree.matchLocation(l2, strlen(l2)) == c2);
        CHECK(tree.matchLocation(l3, strlen(l3)) == c3);
        CHECK(tree.matchLocation(l4, strlen(l4)) == c4);
        CHECK(tree.matchLocation(l5, strlen(l5)) == c5);
        CHECK(tree.matchLocation(l6, strlen(l6)) == c6);

        CHECK(tree.bestMatch(t1, strlen(t1)) == c0);
        CHECK(tree.bestMatch(t2, strlen(t2)) == c6);
        CHECK(tree.bestMatch(t3, strlen(t3)) == c6);
        CHECK(tree.bestMatch(t4, strlen(t4)) == c3);
        CHECK(tree.bestMatch(t5, strlen(t5)) == c0);
        CHECK(tree.bestMatch(t6, strlen(t6)) == c0);
        CHECK(tree.bestMatch(t7, strlen(t7)) == c4);

        CHECK(tree.matchLocation(s1, strlen(s1)) == c0);
        CHECK(tree.matchLocation(s2, strlen(s2)) == c6);
        CHECK(tree.matchLocation(s3, strlen(s3)) == c6);
        CHECK(tree.matchLocation(s4, strlen(s4)) == c3);
        CHECK(tree.matchLocation(s5, strlen(s5)) == c0);
        CHECK(tree.matchLocation(s6, strlen(s6)) == c0);
        CHECK(tree.matchLocation(s7, strlen(s7)) == c4);
        CHECK(tree.matchLocation(s8, strlen(s8)) == NULL);

        delete pRoot;
    }




    TEST(ContextTreeTest_testLocationMatch)
    {
        char p0[] = "/xingwww/html/";
        char p1[] = "/xingwww/html/support/admin/";
        char u0[] = "/";
        char u1[] = "/support/admin/";
        ContextTree tree;
        HttpContext *pRoot, *pRoot1, *pAdmin;
        pRoot = new HttpContext();
        pRoot->set(u0, p0, NULL);
        tree.setRootContext(pRoot);
        tree.setRootLocation(p0, strlen(p0));
        pRoot1 = new HttpContext();
        pRoot1->set(u0, p0, NULL);
        pAdmin = new HttpContext();
        pAdmin->set(u1, p1, NULL);
        tree.add(pRoot1);
        tree.add(pAdmin);
        char l1[] = "/xingwww/html/support/kayako_mod/submit.php";
        CHECK(pRoot1 == tree.matchLocation(l1, strlen(l1)));

    }
}

#endif

