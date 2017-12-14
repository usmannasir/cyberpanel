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

#include <lsr/ls_sha1.h>

#include <stdio.h>
#include <string.h>
#include "unittest-cpp/UnitTest++.h"

static unsigned char ls_sha1_buf[3][57] =
{
    "abc",
    "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
    ""
};

static const int ls_sha1_buflen[3] =
{
    3, 56, 1000
};

static const unsigned char ls_sha1_sum[3][20] =
{
    {
        0xA9, 0x99, 0x3E, 0x36, 0x47, 0x06, 0x81, 0x6A, 0xBA, 0x3E,
        0x25, 0x71, 0x78, 0x50, 0xC2, 0x6C, 0x9C, 0xD0, 0xD8, 0x9D
    },
    {
        0x84, 0x98, 0x3E, 0x44, 0x1C, 0x3B, 0xD2, 0x6E, 0xBA, 0xAE,
        0x4A, 0xA1, 0xF9, 0x51, 0x29, 0xE5, 0xE5, 0x46, 0x70, 0xF1
    },
    {
        0x34, 0xAA, 0x97, 0x3C, 0xD4, 0xC4, 0xDA, 0xA4, 0xF6, 0x1E,
        0xEB, 0x2B, 0xDB, 0xAD, 0x27, 0x31, 0x65, 0x34, 0x01, 0x6F
    }
};

TEST(ls_sha1test_test)
{
#ifdef LSR_SHA1_DEBUG
    printf("Start LSR SHA-1 Test\n");
#endif
    unsigned char sum[20];
    unsigned char buf[1024];
    int i, j;

    for (i = 0; i < 3; i++)
    {
        ls_sha1_ctx_t ctx;
        ls_sha1_init(&ctx);

        if (i == 2)
        {
            memset(buf, 'a', 1000);

            for (j = 0; j < 1000; j++)
                ls_sha1_update(&ctx, buf, 1000);
            ls_sha1_finish(&ctx, sum);
        }
        else
            ls_sha1(ls_sha1_buf[i], ls_sha1_buflen[i], sum);

        CHECK(memcmp(sum, ls_sha1_sum[i], 20) == 0);

#ifdef LSR_SHA1_DEBUG
        printf("\n");
        for (j = 0; j < 20; ++j)
            printf("%02x ", sum[j]);
        printf("\n");
#endif

        ls_sha1_free(&ctx);
    }
}

#endif
