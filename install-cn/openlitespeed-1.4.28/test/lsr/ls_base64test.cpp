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

#include <lsr/ls_base64.h>

#include <stdio.h>
#include <string.h>
#include "unittest-cpp/UnitTest++.h"

TEST(ls_Base64Test_test)
{
#ifdef LSR_BASE64_DEBUG
    printf("Start LSR Base64 Test\n");
#endif
    const char *pEncoded = "QWxhZGRpbjpvcGVuIHNlc2FtZQ==";
    char achDecoded[50];
    const char *pResult = "Aladdin:open sesame";
    CHECK(-1 != ls_base64_decode(pEncoded, strlen(pEncoded), achDecoded));
    CHECK(0 == strcmp(pResult, achDecoded));

    const char *pDecoded = "Aladdin:open sesame";
    char achEncoded[50];
    unsigned int len = ls_base64_encode(pDecoded, strlen(pDecoded),
                                        achEncoded);
    achEncoded[len] = 0;

    CHECK(len == strlen(pEncoded));
    CHECK(0 == memcmp(achEncoded, pEncoded, len));


}

#endif
