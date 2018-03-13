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

#ifdef USE_BROTLI

#include <util/brotlibuf.h>
#include <util/vmembuf.h>
#include "unittest-cpp/UnitTest++.h"


TEST(BrotliBufTest_testBrotliFile)
{
    VMemBuf brFile;
    brFile.set("brotlibuftest.br" , -1);
    //gzFile.set( VMBUF_ANON_MAP , -1 );
    BrotliBuf brBuf;
    CHECK(0 == brBuf.init(BrotliBuf::COMPRESSOR_COMPRESS, 6));

    char achBuf[8192];
    memset(achBuf, 'A', 4096);
    memset(achBuf + 4096, 'b', 4096);

    brBuf.setCompressCache(&brFile);
    CHECK(0 == brBuf.beginStream());
    CHECK(8192 == brBuf.write(achBuf, 8192));
    CHECK(0 == brBuf.endStream());
    brFile.exactSize();
    brFile.close();

    brBuf.reset();
    brFile.deallocate();
    brFile.set("brotlibuftest2.br", -1);

    CHECK(0 == brBuf.beginStream());
    for (int i = 1; i < 1024; ++i)
        CHECK(i == brBuf.write(achBuf + 4096 - i / 2, i));
    CHECK(0 == brBuf.endStream());
    brFile.exactSize();
    brFile.close();

    brBuf.reset();
    brFile.deallocate();
    brFile.set("brotlibuftest3.br", -1);

    CHECK(0 == brBuf.beginStream());
    int num;
    for (int i = 1; i < 20000; ++i)
    {
        num = rand();
        CHECK(4 == brBuf.write((char *)&num, 4));
    }
    //printf( "before end stream, filesize=%d\n", gzFile.getCurFileSize() );
    CHECK(0 == brBuf.endStream());
    //printf( "after end stream, filesize=%d\n", gzFile.getCurFileSize() );
    brFile.exactSize();
    brFile.close();


}

#endif
#endif
