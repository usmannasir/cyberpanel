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

#include <lsr/ls_md5.h>

#include <stdio.h>
#include <string.h>
#include "unittest-cpp/UnitTest++.h"

static unsigned char cases[4][63] =
{
    "The quick brown fox jumps over the lazy dog",
    "The quick brown fox jumps over the lazy dog.",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    ""
};

static const int caseLen[4] =
{
    43,
    44,
    62,
    0
};

static const unsigned char ls_md5_hash[4][16] =
{
    {
        0x9e, 0x10, 0x7d, 0x9d, 0x37, 0x2b, 0xb6, 0x82,
        0x6b, 0xd8, 0x1d, 0x35, 0x42, 0xa4, 0x19, 0xd6
    },
    {
        0xe4, 0xd9, 0x09, 0xc2, 0x90, 0xd0, 0xfb, 0x1c,
        0xa0, 0x68, 0xff, 0xad, 0xdf, 0x22, 0xcb, 0xd0
    },
    {
        0xd1, 0x74, 0xab, 0x98, 0xd2, 0x77, 0xd9, 0xf5,
        0xa5, 0x61, 0x1c, 0x2c, 0x9f, 0x41, 0x9d, 0x9f
    },
    {
        0xd4, 0x1d, 0x8c, 0xd9, 0x8f, 0x00, 0xb2, 0x04,
        0xe9, 0x80, 0x09, 0x98, 0xec, 0xf8, 0x42, 0x7e
    }
};


TEST(ls_md5test_test)
{
    unsigned char res[16];
#ifdef LSR_MD5_DEBUG
    printf("Start LSR MD5 Test\n");
#endif
    for (int i = 0; i < 4; ++i)
    {
        ls_md5(cases[i], caseLen[i], res);

        CHECK(memcmp(res, ls_md5_hash[i], 16) == 0);

#ifdef LSR_MD5_DEBUG
        printf("\n");
        for (int j = 0; j < 16; ++j)
            printf("%02x ", res[j]);
        printf("\n");
#endif
    }
}

#endif
