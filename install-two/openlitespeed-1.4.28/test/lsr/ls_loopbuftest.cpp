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

#include <lsr/ls_loopbuf.h>
#include <lsr/ls_xpool.h>
#include "unittest-cpp/UnitTest++.h"

#include <stdio.h>

TEST(ls_loopbuftest_test)
{
    ls_loopbuf_t *buf = ls_loopbuf_new(0);
#ifdef LSR_LOOPBUF_DEBUG
    printf("Start LSR LoopBuf Test\n");
#endif
    CHECK(0 == ls_loopbuf_size(buf));
    CHECK(0 < ls_loopbuf_capacity(buf));
    CHECK(0 == ls_loopbuf_reserve(buf, 0));
    CHECK(0 == ls_loopbuf_capacity(buf));
    CHECK(ls_loopbuf_end(buf) == ls_loopbuf_begin(buf));

    CHECK(ls_loopbuf_reserve(buf, 1024) == 0);
    CHECK(1024 <= ls_loopbuf_capacity(buf));
    CHECK(ls_loopbuf_guarantee(buf, 1048) == 0);
    CHECK(1048 <= ls_loopbuf_available(buf));
    ls_loopbuf_used(buf, 10);
    CHECK(ls_loopbuf_reserve(buf, 15) == 0);
    CHECK(ls_loopbuf_size(buf) == ls_loopbuf_end(buf) - ls_loopbuf_begin(buf));
    CHECK(ls_loopbuf_available(buf) == ls_loopbuf_capacity(
              buf) - ls_loopbuf_size(buf) - 1);
    ls_loopbuf_clear(buf);
    CHECK(0 == ls_loopbuf_size(buf));
    const char *pStr = "Test String 123  343";
    int len = (int)strlen(pStr);

    CHECK((int)strlen(pStr) == ls_loopbuf_append(buf, pStr, strlen(pStr)));
    CHECK(ls_loopbuf_size(buf) == (int)strlen(pStr));
    CHECK(0 == strncmp(pStr, ls_loopbuf_begin(buf), strlen(pStr)));
    char pBuf[128];
    CHECK(len == ls_loopbuf_moveto(buf, pBuf, 100 + len));
    CHECK(ls_loopbuf_empty(buf));

    for (int i = 0 ; i < 129 ; i ++)
    {
        int i1 = ls_loopbuf_append(buf, pStr, len);
        if (i1 == 0)
            CHECK(ls_loopbuf_full(buf));
        else if (i1 < len)
            CHECK(ls_loopbuf_full(buf));
        if (ls_loopbuf_full(buf))
        {
            CHECK(128 == ls_loopbuf_moveto(buf, pBuf, 128));
            CHECK(20 == ls_loopbuf_popfront(buf, 20));
            CHECK(30 == ls_loopbuf_popback(buf, 30));
            CHECK(ls_loopbuf_size(buf) == ls_loopbuf_capacity(buf) - 128 - 20 - 30);
        }
    }
    for (int i = 129 ; i < 1000 ; i ++)
    {
        int i1 = ls_loopbuf_append(buf, pStr, len);
        if (i1 == 0)
            CHECK(ls_loopbuf_full(buf));
        else if (i1 < len)
            CHECK(ls_loopbuf_full(buf));
        if (ls_loopbuf_full(buf))
        {
            CHECK(128 == ls_loopbuf_moveto(buf, pBuf, 128));
            CHECK(20 == ls_loopbuf_popfront(buf, 20));
            CHECK(30 == ls_loopbuf_popback(buf, 30));
            CHECK(ls_loopbuf_size(buf) == ls_loopbuf_capacity(buf) - 128 - 20 - 30);
        }
    }
    ls_loopbuf_t lbuf;
    ls_loopbuf(&lbuf, 0);
    ls_loopbuf_swap(buf, &lbuf);
    ls_loopbuf_reserve(buf, 200);
    CHECK(200 <= ls_loopbuf_capacity(buf));
    CHECK(ls_loopbuf_capacity(buf) >= ls_loopbuf_size(buf));
    for (int i = 0; i < ls_loopbuf_capacity(buf) - 1; ++i)
        CHECK(1 == ls_loopbuf_append(buf, pBuf, 1));
    CHECK(ls_loopbuf_full(buf));
    char *p0 = ls_loopbuf_end(buf);
    CHECK(ls_loopbuf_inc(buf, &p0) == ls_loopbuf_begin(buf));
    CHECK(ls_loopbuf_reserve(buf, 500) == 0);
    CHECK(500 <= ls_loopbuf_capacity(buf));
    CHECK(ls_loopbuf_contiguous(buf) == ls_loopbuf_available(buf));
    ls_loopbuf_clear(buf);
    CHECK(ls_loopbuf_guarantee(buf, 800) == 0);
    CHECK(ls_loopbuf_available(buf) >= 800);

    ls_loopbuf_used(buf, 500);
    CHECK(ls_loopbuf_popfront(buf, 400) == 400);
    ls_loopbuf_used(buf, 700);
    CHECK(ls_loopbuf_popback(buf, 100) == 100);
    CHECK(ls_loopbuf_begin(buf) > ls_loopbuf_end(buf));
    CHECK(ls_loopbuf_contiguous(buf)
          == ls_loopbuf_begin(buf) - ls_loopbuf_end(buf) - 1);
    ls_loopbuf_straight(buf);
    CHECK(ls_loopbuf_begin(buf) < ls_loopbuf_end(buf));
    CHECK(ls_loopbuf_popfront(buf, 400) == 400);
    ls_loopbuf_used(buf, 400);
    CHECK(ls_loopbuf_popback(buf, 100) == 100);
    CHECK(ls_loopbuf_begin(buf) > ls_loopbuf_end(buf));
    CHECK(ls_loopbuf_contiguous(buf)
          == ls_loopbuf_begin(buf) - ls_loopbuf_end(buf) - 1);
    CHECK(ls_loopbuf_popback(buf, 600) == 600);
    CHECK(ls_loopbuf_empty(buf));
    int oldSize = ls_loopbuf_size(buf);
    ls_loopbuf_used(buf, 60);
    CHECK(ls_loopbuf_size(buf) == oldSize + 60);
    p0 = ls_loopbuf_begin(buf);
    for (int i = 0 ; i < ls_loopbuf_capacity(buf); ++i)
    {
        CHECK(p0 == ls_loopbuf_getptr(buf, i));
        ls_loopbuf_inc(buf, &p0);
    }

    ls_loopbuf_delete(buf);
    ls_loopbuf_d(&lbuf);
}

TEST(ls_loopbufSearchTest)
{
    ls_loopbuf_t *buf;
    const char *ptr, *ptr2, *pAccept = NULL;
#ifdef LSR_LOOPBUF_DEBUG
    printf("Start LSR LoopBuf Search Test");
#endif
    buf = ls_loopbuf_new(0);
    ls_loopbuf_append(buf,
                      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1"
                      "23456789101112131415161718192021222324252627282930313233343536", 127);
    ls_loopbuf_popfront(buf, 20);
    ls_loopbuf_append(buf, "37383940414243444546", 20);
    pAccept = "2021222324";
    ptr = ls_loopbuf_search(buf, 0, pAccept, 10);
    ptr2 = ls_loopbuf_getptr(buf, 73);
    CHECK(ptr == ptr2);
    pAccept = "2333435363";
    ptr = ls_loopbuf_search(buf, 0, pAccept, 10);
    ptr2 = ls_loopbuf_getptr(buf, 98);
    CHECK(ptr == ptr2);
    pAccept = "6373839404";
    ptr = ls_loopbuf_search(buf, 0, pAccept, 10);
    ptr2 = ls_loopbuf_getptr(buf, 106);
    CHECK(ptr == ptr2);
    pAccept = "9404142434";
    ptr = ls_loopbuf_search(buf, 0, pAccept, 10);
    ptr2 = ls_loopbuf_getptr(buf, 112);
    CHECK(ptr == ptr2);
    pAccept = "233343536a";
    ptr = ls_loopbuf_search(buf, 0, pAccept, 10);
    CHECK(ptr == NULL);
    pAccept = "637383940a";
    ptr = ls_loopbuf_search(buf, 0, pAccept, 10);
    CHECK(ptr == NULL);

    ls_loopbuf_clear(buf);
    ls_loopbuf_append(buf,
                      "afafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafaf"
                      "afafafafafafafafafafafafafafafafafafafafafafafafafafafabkbkbkbk", 127);
    ls_loopbuf_popfront(buf, 20);
    ls_loopbuf_append(buf, "bkbkbkbafafafafafafa" , 20);
    pAccept = "bkbkbkbkba";
    ptr = ls_loopbuf_search(buf, 0, pAccept, 10);
    ptr2 = ls_loopbuf_getptr(buf, 105);
    CHECK(ptr == ptr2);

    ls_loopbuf_delete(buf);
}



TEST(ls_loopbufxtest_test)
{
    ls_xpool_t *pool = ls_xpool_new();
    ls_loopbuf_t *buf = ls_loopbuf_xnew(0, pool);
#ifdef LSR_LOOPBUF_DEBUG
    printf("Start LSR LoopBuf X Test\n");
#endif
    CHECK(0 == ls_loopbuf_size(buf));
    CHECK(0 < ls_loopbuf_capacity(buf));
    CHECK(0 == ls_loopbuf_xreserve(buf, 0, pool));
    CHECK(0 == ls_loopbuf_capacity(buf));
    CHECK(ls_loopbuf_end(buf) == ls_loopbuf_begin(buf));

    CHECK(ls_loopbuf_xreserve(buf, 1024, pool) == 0);
    CHECK(1024 <= ls_loopbuf_capacity(buf));
    CHECK(ls_loopbuf_xguarantee(buf, 1048, pool) == 0);
    CHECK(1048 <= ls_loopbuf_available(buf));
    ls_loopbuf_used(buf, 10);
    CHECK(ls_loopbuf_xreserve(buf, 15, pool) == 0);
    CHECK(ls_loopbuf_size(buf) == ls_loopbuf_end(buf) - ls_loopbuf_begin(buf));
    CHECK(ls_loopbuf_available(buf) == ls_loopbuf_capacity(
              buf) - ls_loopbuf_size(buf) - 1);
    ls_loopbuf_clear(buf);
    CHECK(0 == ls_loopbuf_size(buf));
    const char *pStr = "Test String 123  343";
    int len = (int)strlen(pStr);

    CHECK((int)strlen(pStr) == ls_loopbuf_xappend(buf, pStr, strlen(pStr),
            pool));
    CHECK(ls_loopbuf_size(buf) == (int)strlen(pStr));
    CHECK(0 == strncmp(pStr, ls_loopbuf_begin(buf), strlen(pStr)));
    char pBuf[128];
    CHECK(len == ls_loopbuf_moveto(buf, pBuf, 100 + len));
    CHECK(ls_loopbuf_empty(buf));

    for (int i = 0 ; i < 129 ; i ++)
    {
        int i1 = ls_loopbuf_xappend(buf, pStr, len, pool);
        if (i1 == 0)
            CHECK(ls_loopbuf_full(buf));
        else if (i1 < len)
            CHECK(ls_loopbuf_full(buf));
        if (ls_loopbuf_full(buf))
        {
            CHECK(128 == ls_loopbuf_moveto(buf, pBuf, 128));
            CHECK(20 == ls_loopbuf_popfront(buf, 20));
            CHECK(30 == ls_loopbuf_popback(buf, 30));
            CHECK(ls_loopbuf_size(buf) == ls_loopbuf_capacity(buf) - 128 - 20 - 30);
        }
    }
    for (int i = 129 ; i < 1000 ; i ++)
    {
        int i1 = ls_loopbuf_xappend(buf, pStr, len, pool);
        if (i1 == 0)
            CHECK(ls_loopbuf_full(buf));
        else if (i1 < len)
            CHECK(ls_loopbuf_full(buf));
        if (ls_loopbuf_full(buf))
        {
            CHECK(128 == ls_loopbuf_moveto(buf, pBuf, 128));
            CHECK(20 == ls_loopbuf_popfront(buf, 20));
            CHECK(30 == ls_loopbuf_popback(buf, 30));
            CHECK(ls_loopbuf_size(buf) == ls_loopbuf_capacity(buf) - 128 - 20 - 30);
        }
    }
    ls_loopbuf_t lbuf;
    ls_loopbuf_x(&lbuf, 0, pool);
    ls_loopbuf_swap(buf, &lbuf);
    ls_loopbuf_xreserve(buf, 200, pool);
    CHECK(200 <= ls_loopbuf_capacity(buf));
    CHECK(ls_loopbuf_capacity(buf) >= ls_loopbuf_size(buf));
    for (int i = 0; i < ls_loopbuf_capacity(buf) - 1; ++i)
        CHECK(1 == ls_loopbuf_xappend(buf, pBuf, 1, pool));
    CHECK(ls_loopbuf_full(buf));
    char *p0 = ls_loopbuf_end(buf);
    CHECK(ls_loopbuf_inc(buf, &p0) == ls_loopbuf_begin(buf));
    CHECK(ls_loopbuf_xreserve(buf, 500, pool) == 0);
    CHECK(500 <= ls_loopbuf_capacity(buf));
    CHECK(ls_loopbuf_contiguous(buf) == ls_loopbuf_available(buf));
    ls_loopbuf_clear(buf);
    CHECK(ls_loopbuf_xguarantee(buf, 800, pool) == 0);
    CHECK(ls_loopbuf_available(buf) >= 800);

    ls_loopbuf_used(buf, 500);
    CHECK(ls_loopbuf_popfront(buf, 400) == 400);
    ls_loopbuf_used(buf, 700);
    CHECK(ls_loopbuf_popback(buf, 100) == 100);
    CHECK(ls_loopbuf_begin(buf) > ls_loopbuf_end(buf));
    CHECK(ls_loopbuf_contiguous(buf)
          == ls_loopbuf_begin(buf) - ls_loopbuf_end(buf) - 1);
    ls_loopbuf_xstraight(buf, pool);
    CHECK(ls_loopbuf_begin(buf) < ls_loopbuf_end(buf));
    CHECK(ls_loopbuf_popfront(buf, 400) == 400);
    ls_loopbuf_used(buf, 400);
    CHECK(ls_loopbuf_popback(buf, 100) == 100);
    CHECK(ls_loopbuf_begin(buf) > ls_loopbuf_end(buf));
    CHECK(ls_loopbuf_contiguous(buf)
          == ls_loopbuf_begin(buf) - ls_loopbuf_end(buf) - 1);
    CHECK(ls_loopbuf_popback(buf, 600) == 600);
    CHECK(ls_loopbuf_empty(buf));
    int oldSize = ls_loopbuf_size(buf);
    ls_loopbuf_used(buf, 60);
    CHECK(ls_loopbuf_size(buf) == oldSize + 60);
    p0 = ls_loopbuf_begin(buf);
    for (int i = 0 ; i < ls_loopbuf_capacity(buf); ++i)
    {
        CHECK(p0 == ls_loopbuf_getptr(buf, i));
        ls_loopbuf_inc(buf, &p0);
    }

    ls_loopbuf_xdelete(buf, pool);
    ls_loopbuf_xd(&lbuf, pool);
    ls_xpool_delete(pool);
}

TEST(ls_loopbufXSearchTest)
{
    ls_xpool_t *pool = ls_xpool_new();
    ls_loopbuf_t *buf;
    const char *ptr, *ptr2, *pAccept = NULL;
#ifdef LSR_LOOPBUF_DEBUG
    printf("Start LSR LoopBuf Search Test");
#endif
    buf = ls_loopbuf_xnew(0, pool);
    ls_loopbuf_xappend(buf,
                       "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1"
                       "23456789101112131415161718192021222324252627282930313233343536", 127,
                       pool);
    ls_loopbuf_popfront(buf, 20);
    ls_loopbuf_xappend(buf, "37383940414243444546", 20, pool);
    pAccept = "2021222324";
    ptr = ls_loopbuf_search(buf, 0, pAccept, 10);
    ptr2 = ls_loopbuf_getptr(buf, 73);
    CHECK(ptr == ptr2);
    pAccept = "2333435363";
    ptr = ls_loopbuf_search(buf, 0, pAccept, 10);
    ptr2 = ls_loopbuf_getptr(buf, 98);
    CHECK(ptr == ptr2);
    pAccept = "6373839404";
    ptr = ls_loopbuf_search(buf, 0, pAccept, 10);
    ptr2 = ls_loopbuf_getptr(buf, 106);
    CHECK(ptr == ptr2);
    pAccept = "9404142434";
    ptr = ls_loopbuf_search(buf, 0, pAccept, 10);
    ptr2 = ls_loopbuf_getptr(buf, 112);
    CHECK(ptr == ptr2);
    pAccept = "233343536a";
    ptr = ls_loopbuf_search(buf, 0, pAccept, 10);
    CHECK(ptr == NULL);
    pAccept = "637383940a";
    ptr = ls_loopbuf_search(buf, 0, pAccept, 10);
    CHECK(ptr == NULL);

    ls_loopbuf_clear(buf);
    ls_loopbuf_xappend(buf,
                       "afafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafaf"
                       "afafafafafafafafafafafafafafafafafafafafafafafafafafafabkbkbkbk", 127,
                       pool);
    ls_loopbuf_popfront(buf, 20);
    ls_loopbuf_xappend(buf, "bkbkbkbafafafafafafa" , 20, pool);
    pAccept = "bkbkbkbkba";
    ptr = ls_loopbuf_search(buf, 0, pAccept, 10);
    ptr2 = ls_loopbuf_getptr(buf, 105);
    CHECK(ptr == ptr2);

    ls_loopbuf_xdelete(buf, pool);
    ls_xpool_delete(pool);
}



TEST(ls_xloopbuftest_test)
{
    ls_xpool_t *pool = ls_xpool_new();
    ls_xloopbuf_t *buf = ls_xloopbuf_new(0, pool);
#ifdef LSR_LOOPBUF_DEBUG
    printf("Start LSR XLoopBuf Test\n");
#endif
    CHECK(0 == ls_xloopbuf_size(buf));
    CHECK(0 < ls_xloopbuf_capacity(buf));
    CHECK(0 == ls_xloopbuf_reserve(buf, 0));
    CHECK(0 == ls_xloopbuf_capacity(buf));
    CHECK(ls_xloopbuf_end(buf) == ls_xloopbuf_begin(buf));

    CHECK(ls_xloopbuf_reserve(buf, 1024) == 0);
    CHECK(1024 <= ls_xloopbuf_capacity(buf));
    CHECK(ls_xloopbuf_guarantee(buf, 1048) == 0);
    CHECK(1048 <= ls_xloopbuf_available(buf));
    ls_xloopbuf_used(buf, 10);
    CHECK(ls_xloopbuf_reserve(buf, 15) == 0);
    CHECK(ls_xloopbuf_size(buf) == ls_xloopbuf_end(buf) - ls_xloopbuf_begin(
              buf));
    CHECK(ls_xloopbuf_available(buf) == ls_xloopbuf_capacity(
              buf) - ls_xloopbuf_size(buf) - 1);
    ls_xloopbuf_clear(buf);
    CHECK(0 == ls_xloopbuf_size(buf));
    const char *pStr = "Test String 123  343";
    int len = (int)strlen(pStr);

    CHECK((int)strlen(pStr) == ls_xloopbuf_append(buf, pStr, strlen(pStr)));
    CHECK(ls_xloopbuf_size(buf) == (int)strlen(pStr));
    CHECK(0 == strncmp(pStr, ls_xloopbuf_begin(buf), strlen(pStr)));
    char pBuf[128];
    CHECK(len == ls_xloopbuf_moveto(buf, pBuf, 100 + len));
    CHECK(ls_xloopbuf_empty(buf));

    for (int i = 0 ; i < 129 ; i ++)
    {
        int i1 = ls_xloopbuf_append(buf, pStr, len);
        if (i1 == 0)
            CHECK(ls_xloopbuf_full(buf));
        else if (i1 < len)
            CHECK(ls_xloopbuf_full(buf));
        if (ls_xloopbuf_full(buf))
        {
            CHECK(128 == ls_xloopbuf_moveto(buf, pBuf, 128));
            CHECK(20 == ls_xloopbuf_popfront(buf, 20));
            CHECK(30 == ls_xloopbuf_popback(buf, 30));
            CHECK(ls_xloopbuf_size(buf) == ls_xloopbuf_capacity(buf) - 128 - 20 - 30);
        }
    }
    for (int i = 129 ; i < 1000 ; i ++)
    {
        int i1 = ls_xloopbuf_append(buf, pStr, len);
        if (i1 == 0)
            CHECK(ls_xloopbuf_full(buf));
        else if (i1 < len)
            CHECK(ls_xloopbuf_full(buf));
        if (ls_xloopbuf_full(buf))
        {
            CHECK(128 == ls_xloopbuf_moveto(buf, pBuf, 128));
            CHECK(20 == ls_xloopbuf_popfront(buf, 20));
            CHECK(30 == ls_xloopbuf_popback(buf, 30));
            CHECK(ls_xloopbuf_size(buf) == ls_xloopbuf_capacity(buf) - 128 - 20 - 30);
        }
    }
    ls_xloopbuf_t lbuf;
    ls_xloopbuf(&lbuf, 0, pool);
    ls_xloopbuf_swap(buf, &lbuf);
    ls_xloopbuf_reserve(buf, 200);
    CHECK(200 <= ls_xloopbuf_capacity(buf));
    CHECK(ls_xloopbuf_capacity(buf) >= ls_xloopbuf_size(buf));
    for (int i = 0; i < ls_xloopbuf_capacity(buf) - 1; ++i)
        CHECK(1 == ls_xloopbuf_append(buf, pBuf, 1));
    CHECK(ls_xloopbuf_full(buf));
    char *p0 = ls_xloopbuf_end(buf);
    CHECK(ls_xloopbuf_inc(buf, &p0) == ls_xloopbuf_begin(buf));
    CHECK(ls_xloopbuf_reserve(buf, 500) == 0);
    CHECK(500 <= ls_xloopbuf_capacity(buf));
    CHECK(ls_xloopbuf_contiguous(buf) == ls_xloopbuf_available(buf));
    ls_xloopbuf_clear(buf);
    CHECK(ls_xloopbuf_guarantee(buf, 800) == 0);
    CHECK(ls_xloopbuf_available(buf) >= 800);

    ls_xloopbuf_used(buf, 500);
    CHECK(ls_xloopbuf_popfront(buf, 400) == 400);
    ls_xloopbuf_used(buf, 700);
    CHECK(ls_xloopbuf_popback(buf, 100) == 100);
    CHECK(ls_xloopbuf_begin(buf) > ls_xloopbuf_end(buf));
    CHECK(ls_xloopbuf_contiguous(buf)
          == ls_xloopbuf_begin(buf) - ls_xloopbuf_end(buf) - 1);
    ls_xloopbuf_straight(buf);
    CHECK(ls_xloopbuf_begin(buf) < ls_xloopbuf_end(buf));
    CHECK(ls_xloopbuf_popfront(buf, 400) == 400);
    ls_xloopbuf_used(buf, 400);
    CHECK(ls_xloopbuf_popback(buf, 100) == 100);
    CHECK(ls_xloopbuf_begin(buf) > ls_xloopbuf_end(buf));
    CHECK(ls_xloopbuf_contiguous(buf)
          == ls_xloopbuf_begin(buf) - ls_xloopbuf_end(buf) - 1);
    CHECK(ls_xloopbuf_popback(buf, 600) == 600);
    CHECK(ls_xloopbuf_empty(buf));
    int oldSize = ls_xloopbuf_size(buf);
    ls_xloopbuf_used(buf, 60);
    CHECK(ls_xloopbuf_size(buf) == oldSize + 60);
    p0 = ls_xloopbuf_begin(buf);
    for (int i = 0 ; i < ls_xloopbuf_capacity(buf); ++i)
    {
        CHECK(p0 == ls_xloopbuf_getptr(buf, i));
        ls_xloopbuf_inc(buf, &p0);
    }

    ls_xloopbuf_delete(buf);
    ls_xloopbuf_d(&lbuf);
    ls_xpool_delete(pool);
}

TEST(ls_xloopbufSearchTest)
{
    ls_xpool_t *pool = ls_xpool_new();
    ls_xloopbuf_t *buf;
    const char *ptr, *ptr2, *pAccept = NULL;
#ifdef LSR_LOOPBUF_DEBUG
    printf("Start LSR XLoopBufSearch Test");
#endif
    buf = ls_xloopbuf_new(0, pool);
    ls_xloopbuf_append(buf,
                       "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1"
                       "23456789101112131415161718192021222324252627282930313233343536", 127);
    ls_xloopbuf_popfront(buf, 20);
    ls_xloopbuf_append(buf, "37383940414243444546", 20);
    pAccept = "2021222324";
    ptr = ls_xloopbuf_search(buf, 0, pAccept, 10);
    ptr2 = ls_xloopbuf_getptr(buf, 73);
    CHECK(ptr == ptr2);
    pAccept = "2333435363";
    ptr = ls_xloopbuf_search(buf, 0, pAccept, 10);
    ptr2 = ls_xloopbuf_getptr(buf, 98);
    CHECK(ptr == ptr2);
    pAccept = "6373839404";
    ptr = ls_xloopbuf_search(buf, 0, pAccept, 10);
    ptr2 = ls_xloopbuf_getptr(buf, 106);
    CHECK(ptr == ptr2);
    pAccept = "9404142434";
    ptr = ls_xloopbuf_search(buf, 0, pAccept, 10);
    ptr2 = ls_xloopbuf_getptr(buf, 112);
    CHECK(ptr == ptr2);
    pAccept = "233343536a";
    ptr = ls_xloopbuf_search(buf, 0, pAccept, 10);
    CHECK(ptr == NULL);
    pAccept = "637383940a";
    ptr = ls_xloopbuf_search(buf, 0, pAccept, 10);
    CHECK(ptr == NULL);

    ls_xloopbuf_clear(buf);
    ls_xloopbuf_append(buf,
                       "afafafafafafafafafafafafafafafafafafafafafafafafafafafafafafafaf"
                       "afafafafafafafafafafafafafafafafafafafafafafafafafafafabkbkbkbk", 127);
    ls_xloopbuf_popfront(buf, 20);
    ls_xloopbuf_append(buf, "bkbkbkbafafafafafafa" , 20);
    pAccept = "bkbkbkbkba";
    ptr = ls_xloopbuf_search(buf, 0, pAccept, 10);
    ptr2 = ls_xloopbuf_getptr(buf, 105);
    CHECK(ptr == ptr2);

    ls_xloopbuf_delete(buf);
    ls_xpool_delete(pool);
}


#endif








