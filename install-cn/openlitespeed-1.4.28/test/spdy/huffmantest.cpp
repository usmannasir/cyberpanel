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
#include "unittest-cpp/UnitTest++.h"
#include "spdy/hpack.h"
#include <stdlib.h>

void testBothEncAndDec(uint8_t *src, size_t src_len = 0);
void testBothEncAndDec(uint8_t *src, size_t src_len)
{
    if (src_len == 0)
        src_len = strlen((char *)src);

    size_t dst_len = HuffmanCode::calcHuffmanEncBufSize(src,
                     src + src_len) + 1;
    unsigned char *dst = (unsigned char *)malloc(dst_len);
    int real_dst_len = HuffmanCode::huffmanEnc(src, src + src_len, dst,
                       dst_len);
    CHECK(real_dst_len == (int)(dst_len - 1));

    size_t src_len2 = real_dst_len * 4 +
                      1; //at most 30 bit each char, so at most times 4.
    unsigned char *src2 = (unsigned char *)malloc(src_len2);
    int real_src_len2 = HuffmanCode::huffmanDec(dst, real_dst_len, src2,
                        src_len2, false);

    CHECK(real_src_len2 == (int)src_len);
    CHECK(memcmp(src, src2, src_len) == 0);

    free(dst);
    free(src2);
}


TEST(huffman_test)
{
    size_t src_len, i;
    uint8_t *src = (uint8_t *)"1234567890ABC1232p58456l;gfn./";
    testBothEncAndDec(src);
    src = (uint8_t *)
          "ABCslf90-4895lkjhcv][[67/..n jhkufdyfldhfyherewlr    pouirtl;k";
    testBothEncAndDec(src);
    src = (uint8_t *)"!@#$%^&*()_+=-=-';?><,.{}[][~1iOIGBV<PO";
    testBothEncAndDec(src);


    src_len = 8195;
    src = (uint8_t *)malloc(src_len);
    for (i = 0; i < src_len; ++i)
        src[i] = rand() % 256;
    testBothEncAndDec(src, src_len);

    src_len = 4096;
    for (i = 0; i < src_len; ++i)
        src[i] = rand() % 256;
    testBothEncAndDec(src, src_len);

    src_len = 1023;
    for (i = 0; i < src_len; ++i)
        src[i] = rand() % 256;
    testBothEncAndDec(src, src_len);

    src_len = 513;
    for (i = 0; i < src_len; ++i)
        src[i] = rand() % 256;
    testBothEncAndDec(src, src_len);


    free(src);
}



#endif
