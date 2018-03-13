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

#include <lsr/ls_buf.h>
#include <lsr/ls_xpool.h>
#include "unittest-cpp/UnitTest++.h"

#include <stdio.h>

TEST(ls_buftest_test)
{
    ls_buf_t buf;
#ifdef LSR_BUF_DEBUG
    printf("Start LSR Buf Test\n");
#endif
    CHECK(0 == ls_buf(&buf, 0));
    CHECK(0 == ls_buf_size(&buf));
    CHECK(0 == ls_buf_capacity(&buf));
    CHECK(0 == ls_buf_reserve(&buf, 0));
    CHECK(0 == ls_buf_capacity(&buf));
    CHECK(ls_buf_end(&buf) == ls_buf_begin(&buf));

    CHECK(0 == ls_buf_reserve(&buf, 1024));
    CHECK(1024 <= ls_buf_capacity(&buf));
    CHECK(1048 >= ls_buf_available(&buf));
    ls_buf_used(&buf, 10);
    CHECK(ls_buf_reserve(&buf, 15) == 0);
    CHECK(ls_buf_size(&buf) == ls_buf_end(&buf) - ls_buf_begin(&buf));
    CHECK(ls_buf_available(&buf) == ls_buf_capacity(&buf) - ls_buf_size(&buf));
    ls_buf_clear(&buf);
    CHECK(0 == ls_buf_size(&buf));

    const char *pStr = "Test String 123  343";
    int len = (int)strlen(pStr);
    CHECK((int)strlen(pStr) == ls_buf_append2(&buf, pStr, strlen(pStr)));
    CHECK(ls_buf_size(&buf) == (int)strlen(pStr));
    CHECK(0 == strncmp(pStr, ls_buf_begin(&buf), strlen(pStr)));
    char pBuf[128];
    CHECK(len == ls_buf_popfrontto(&buf, pBuf, 100 + len));
    CHECK(ls_buf_empty(&buf));

    for (int i = 0 ; i < 129 ; i ++)
    {
        int i1 = ls_buf_append2(&buf, pStr, len);
        if (i1 == 0)
            CHECK(ls_buf_full(&buf));
        else if (i1 < len)
            CHECK(ls_buf_full(&buf));
        if (ls_buf_full(&buf))
        {
            CHECK(128 == ls_buf_popfrontto(&buf, pBuf, 128));
            CHECK(20 == ls_buf_popfront(&buf, 20));
            CHECK(30 == ls_buf_popend(&buf, 30));
            CHECK(ls_buf_size(&buf) == ls_buf_capacity(&buf) - 128 - 20 - 30);
        }
    }
    ls_buf_t lbuf;
    ls_buf(&lbuf, 0);
    ls_buf_swap(&buf, &lbuf);
    ls_buf_reserve(&buf, 200);
    CHECK(200 <= ls_buf_capacity(&buf));
    CHECK(ls_buf_capacity(&buf) >= ls_buf_size(&buf));
    for (int i = 0; i < ls_buf_capacity(&buf); ++i)
        CHECK(1 == ls_buf_append2(&buf, pBuf, 1));

    CHECK(ls_buf_full(&buf));
    CHECK(ls_buf_reserve(&buf, 500) == 0);
    CHECK(500 <= ls_buf_capacity(&buf));
    ls_buf_clear(&buf);
    CHECK(ls_buf_reserve(&buf, 800) == 0);
    CHECK(ls_buf_available(&buf) >= 800);

    ls_buf_used(&buf, 500);
    CHECK(ls_buf_popfront(&buf, 400) == 400);
    ls_buf_used(&buf, 700);
    CHECK(ls_buf_popend(&buf, 100) == 100);
    CHECK(ls_buf_popend(&buf, 700) == 700);
    CHECK(ls_buf_empty(&buf));
    int oldSize = ls_buf_size(&buf);
    ls_buf_used(&buf, 60);
    CHECK(ls_buf_size(&buf) == oldSize + 60);

    ls_buf_d(&buf);
    ls_buf_d(&lbuf);
}

TEST(ls_bufXtest_test)
{
    ls_xpool_t *pool = ls_xpool_new();
    ls_buf_t buf;
#ifdef LSR_BUF_DEBUG
    printf("Start LSR Buf X Test\n");
#endif
    CHECK(0 == ls_buf_x(&buf, 0, pool));
    CHECK(0 == ls_buf_size(&buf));
    CHECK(0 == ls_buf_capacity(&buf));
    CHECK(0 == ls_buf_xreserve(&buf, 0, pool));
    CHECK(0 == ls_buf_capacity(&buf));
    CHECK(ls_buf_end(&buf) == ls_buf_begin(&buf));

    CHECK(0 == ls_buf_xreserve(&buf, 1024, pool));
    CHECK(1024 <= ls_buf_capacity(&buf));
    CHECK(1048 >= ls_buf_available(&buf));
    ls_buf_used(&buf, 10);
    CHECK(ls_buf_xreserve(&buf, 15, pool) == 0);
    CHECK(ls_buf_size(&buf) == ls_buf_end(&buf) - ls_buf_begin(&buf));
    CHECK(ls_buf_available(&buf) == ls_buf_capacity(&buf) - ls_buf_size(&buf));
    ls_buf_clear(&buf);
    CHECK(0 == ls_buf_size(&buf));

    const char *pStr = "Test String 123  343";
    int len = (int)strlen(pStr);
    CHECK((int)strlen(pStr) == ls_buf_xappend2(&buf, pStr, strlen(pStr),
            pool));
    CHECK(ls_buf_size(&buf) == (int)strlen(pStr));
    CHECK(0 == strncmp(pStr, ls_buf_begin(&buf), strlen(pStr)));
    char pBuf[128];
    CHECK(len == ls_buf_popfrontto(&buf, pBuf, 100 + len));
    CHECK(ls_buf_empty(&buf));

    for (int i = 0 ; i < 129 ; i ++)
    {
        int i1 = ls_buf_xappend2(&buf, pStr, len, pool);
        if (i1 == 0)
            CHECK(ls_buf_full(&buf));
        else if (i1 < len)
            CHECK(ls_buf_full(&buf));
        if (ls_buf_full(&buf))
        {
            CHECK(128 == ls_buf_popfrontto(&buf, pBuf, 128));
            CHECK(20 == ls_buf_popfront(&buf, 20));
            CHECK(30 == ls_buf_popend(&buf, 30));
            CHECK(ls_buf_size(&buf) == ls_buf_capacity(&buf) - 128 - 20 - 30);
        }
    }
    ls_buf_t lbuf;
    ls_buf_x(&lbuf, 0, pool);
    ls_buf_swap(&buf, &lbuf);
    ls_buf_xreserve(&buf, 200, pool);
    CHECK(200 <= ls_buf_capacity(&buf));
    CHECK(ls_buf_capacity(&buf) >= ls_buf_size(&buf));
    for (int i = 0; i < ls_buf_capacity(&buf); ++i)
        CHECK(1 == ls_buf_xappend2(&buf, pBuf, 1, pool));

    CHECK(ls_buf_full(&buf));
    CHECK(ls_buf_xreserve(&buf, 500, pool) == 0);
    CHECK(500 <= ls_buf_capacity(&buf));
    ls_buf_clear(&buf);
    CHECK(ls_buf_xreserve(&buf, 800, pool) == 0);
    CHECK(ls_buf_available(&buf) >= 800);

    ls_buf_used(&buf, 500);
    CHECK(ls_buf_popfront(&buf, 400) == 400);
    ls_buf_used(&buf, 700);
    CHECK(ls_buf_popend(&buf, 100) == 100);
    CHECK(ls_buf_popend(&buf, 700) == 700);
    CHECK(ls_buf_empty(&buf));
    int oldSize = ls_buf_size(&buf);
    ls_buf_used(&buf, 60);
    CHECK(ls_buf_size(&buf) == oldSize + 60);

    ls_buf_xd(&buf, pool);
    ls_buf_xd(&lbuf, pool);
    ls_xpool_delete(pool);
}

TEST(ls_xbuftest_test)
{
    ls_xbuf_t buf;
    ls_xpool_t *pool = ls_xpool_new();
#ifdef LSR_BUF_DEBUG
    printf("Start LSR XBuf Test\n");
#endif
    
    CHECK(0 == ls_xbuf(&buf, 0, pool));
    CHECK(0 == ls_xbuf_size(&buf));
    CHECK(0 == ls_xbuf_capacity(&buf));
    CHECK(0 == ls_xbuf_reserve(&buf, 0));
    CHECK(0 == ls_xbuf_capacity(&buf));
    CHECK(ls_xbuf_end(&buf) == ls_xbuf_begin(&buf));

    CHECK(0 == ls_xbuf_reserve(&buf, 1024));
    CHECK(1024 <= ls_xbuf_capacity(&buf));
    CHECK(1048 >= ls_xbuf_available(&buf));
    ls_xbuf_used(&buf, 10);
    CHECK(ls_xbuf_reserve(&buf, 15) == 0);
    CHECK(ls_xbuf_size(&buf) == ls_xbuf_end(&buf) - ls_xbuf_begin(&buf));
    CHECK(ls_xbuf_available(&buf) == ls_xbuf_capacity(&buf) - ls_xbuf_size(
              &buf));
    ls_xbuf_clear(&buf);
    CHECK(0 == ls_xbuf_size(&buf));

    const char *pStr = "Test String 123  343";
    int len = (int)strlen(pStr);
    CHECK((int)strlen(pStr) == ls_xbuf_append2(&buf, pStr, strlen(pStr)));
    CHECK(ls_xbuf_size(&buf) == (int)strlen(pStr));
    CHECK(0 == strncmp(pStr, ls_xbuf_begin(&buf), strlen(pStr)));
    char pBuf[128];
    CHECK(len == ls_xbuf_popfrontto(&buf, pBuf, 100 + len));
    CHECK(ls_xbuf_empty(&buf));

    for (int i = 0 ; i < 129 ; i ++)
    {
        int i1 = ls_xbuf_append2(&buf, pStr, len);
        if (i1 == 0)
            CHECK(ls_xbuf_full(&buf));
        else if (i1 < len)
            CHECK(ls_xbuf_full(&buf));
        if (ls_xbuf_full(&buf))
        {
            CHECK(128 == ls_xbuf_popfrontto(&buf, pBuf, 128));
            CHECK(20 == ls_xbuf_popfront(&buf, 20));
            CHECK(30 == ls_xbuf_popend(&buf, 30));
            CHECK(ls_xbuf_size(&buf) == ls_xbuf_capacity(&buf) - 128 - 20 - 30);
        }
    }
    ls_xbuf_t lbuf;
    ls_xbuf(&lbuf, 0, pool);
    ls_xbuf_swap(&buf, &lbuf);
    ls_xbuf_reserve(&buf, 200);
    CHECK(200 <= ls_xbuf_capacity(&buf));
    CHECK(ls_xbuf_capacity(&buf) >= ls_xbuf_size(&buf));
    for (int i = 0; i < ls_xbuf_capacity(&buf); ++i)
        CHECK(1 == ls_xbuf_append2(&buf, pBuf, 1));

    CHECK(ls_xbuf_full(&buf));
    CHECK(ls_xbuf_reserve(&buf, 500) == 0);
    CHECK(500 <= ls_xbuf_capacity(&buf));
    ls_xbuf_clear(&buf);
    CHECK(ls_xbuf_reserve(&buf, 800) == 0);
    CHECK(ls_xbuf_available(&buf) >= 800);

    ls_xbuf_used(&buf, 500);
    CHECK(ls_xbuf_popfront(&buf, 400) == 400);
    ls_xbuf_used(&buf, 700);
    CHECK(ls_xbuf_popend(&buf, 100) == 100);
    CHECK(ls_xbuf_popend(&buf, 700) == 700);
    CHECK(ls_xbuf_empty(&buf));
    int oldSize = ls_xbuf_size(&buf);
    ls_xbuf_used(&buf, 60);
    CHECK(ls_xbuf_size(&buf) == oldSize + 60);

    ls_xbuf_d(&buf);
    ls_xbuf_d(&lbuf);
    ls_xpool_delete(pool);
}

#endif
