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

#include "vmembuftest.h"
#include <util/blockbuf.h>
#include <util/vmembuf.h>

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include "unittest-cpp/UnitTest++.h"



SUITE(VMemBufTest)
{

    TEST(testStatic)
    {
        char achBuf1[1];
        char achBuf2[4096];
        BlockBuf *pBlock = new BlockBuf(achBuf1, 1);
        VMemBuf *pVmemBuf = new VMemBuf();
        pVmemBuf->set(pBlock);
        char *pBuf;
        size_t size;

        pBuf = pVmemBuf->getWriteBuffer(size);
        CHECK(pBuf == achBuf1);
        CHECK(size == 1);
        pBuf = pVmemBuf->getWriteBuffer(size);
        CHECK(pBuf == achBuf1);
        CHECK(size == 1);
        pVmemBuf->writeUsed(size);
        pBuf = pVmemBuf->getWriteBuffer(size);
        CHECK(pBuf == NULL);
        pBuf = pVmemBuf->getWriteBuffer(size);
        CHECK(pBuf == NULL);
        CHECK(false == pVmemBuf->empty());

        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pBuf == achBuf1);
        CHECK(size == 1);
        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pBuf == achBuf1);
        CHECK(size == 1);
        pVmemBuf->readUsed(size);
        CHECK(true == pVmemBuf->empty());
        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pBuf == NULL);

        pVmemBuf->deallocate();

        pBlock = new BlockBuf(achBuf2, 4096);
        pVmemBuf->set(pBlock);

        pBuf = pVmemBuf->getWriteBuffer(size);
        CHECK(pBuf == achBuf2);
        CHECK(size == 4096);
        pBuf = pVmemBuf->getWriteBuffer(size);
        CHECK(pBuf == achBuf2);
        CHECK(size == 4096);
        pVmemBuf->writeUsed(2048);
        CHECK(false == pVmemBuf->empty());

        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pBuf == achBuf2);
        CHECK(size == 2048);
        pVmemBuf->readUsed(1024);
        CHECK(false == pVmemBuf->empty());

        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pBuf == achBuf2 + 1024);
        CHECK(size == 1024);
        pVmemBuf->readUsed(1024);
        CHECK(true == pVmemBuf->empty());

        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pBuf == achBuf2 + 2048);
        CHECK(size == 0);

        pBuf = pVmemBuf->getWriteBuffer(size);
        CHECK(pBuf == achBuf2 + 2048);
        CHECK(size == 2048);
        pVmemBuf->writeUsed(size);
        pBuf = pVmemBuf->getWriteBuffer(size);
        CHECK(pBuf == NULL);
        CHECK(false == pVmemBuf->empty());

        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pBuf == achBuf2 + 2048);
        CHECK(size == 2048);
        pVmemBuf->readUsed(size);

        CHECK(true == pVmemBuf->empty());
        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pBuf == NULL);
        delete pVmemBuf;
    }

    TEST(testMalloc)
    {
        char *pMallocBuf = (char *)malloc(4096);
        CHECK(pMallocBuf);
        BlockBuf *pBlock = new MallocBlockBuf(pMallocBuf, 4096);
        VMemBuf *pVmemBuf = new VMemBuf();
        pVmemBuf->set(pBlock);
        char *pBuf;
        size_t size;

        pBuf = pVmemBuf->getWriteBuffer(size);
        CHECK(pBuf == pMallocBuf);
        CHECK(size == 4096);
        pBuf = pVmemBuf->getWriteBuffer(size);
        CHECK(pBuf == pMallocBuf);
        CHECK(size == 4096);
        pVmemBuf->writeUsed(2048);
        pBuf = pVmemBuf->getWriteBuffer(size);
        CHECK(pBuf == pMallocBuf + 2048);
        CHECK(size == 2048);
        pVmemBuf->writeUsed(size);
        pBuf = pVmemBuf->getWriteBuffer(size);
        CHECK(pBuf == NULL);

        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pBuf == pMallocBuf);
        CHECK(size == 4096);
        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pBuf == pMallocBuf);
        CHECK(size == 4096);
        pVmemBuf->readUsed(2048);
        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pBuf == pMallocBuf + 2048);
        CHECK(size == 2048);
        pVmemBuf->readUsed(size);
        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pBuf == NULL);
        delete pVmemBuf;
    }

    TEST(testMmap)
    {
        VMemBuf *pVmemBuf = new VMemBuf();
        char *pBuf;
        char *pBuf1;
        size_t size;
        CHECK(pVmemBuf->set("testVmemBuf.mmap", -1) == 0);
        CHECK(pVmemBuf->getCurWBlkPos() == 0);
        CHECK(pVmemBuf->getCurFileSize() == 0);
        pBuf = pVmemBuf->getWriteBuffer(size);
        CHECK(pVmemBuf->getCurFileSize() == pVmemBuf->getMinMmapSize());
        CHECK(pVmemBuf->getCurWBlkPos() == pVmemBuf->getBlockSize());
        CHECK(pBuf != NULL);
        CHECK(size == (size_t)pVmemBuf->getBlockSize());
        pVmemBuf->writeUsed(size);
        CHECK(false == pVmemBuf->empty());
        pBuf1 = pVmemBuf->getWriteBuffer(size);
        CHECK(pBuf1 != NULL);
        CHECK(pBuf1 != pBuf);
        CHECK(size == (size_t)pVmemBuf->getBlockSize());
        CHECK(pVmemBuf->getCurWBlkPos() == pVmemBuf->getBlockSize() * 2);
        pVmemBuf->writeUsed(size);
        CHECK(false == pVmemBuf->empty());
        pBuf = pVmemBuf->getWriteBuffer(size);
        CHECK(pVmemBuf->getCurWBlkPos() == pVmemBuf->getBlockSize() * 3);
        CHECK(pBuf != NULL);
        CHECK(size == (size_t)pVmemBuf->getBlockSize());
        CHECK(pVmemBuf->getCurFileSize() >= pVmemBuf->getBlockSize() * 3);
        pVmemBuf->writeUsed(1024);
        CHECK(false == pVmemBuf->empty());

        CHECK(pVmemBuf->getCurRBlkPos() == pVmemBuf->getBlockSize());
        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pVmemBuf->getCurRBlkPos() == pVmemBuf->getBlockSize());
        CHECK(pBuf != NULL);
        CHECK(size == (size_t)pVmemBuf->getBlockSize());
        pVmemBuf->readUsed(size);
        CHECK(false == pVmemBuf->empty());

        pBuf1 = pVmemBuf->getReadBuffer(size);
        CHECK(pBuf1 != NULL);
        CHECK(pBuf1 != pBuf);
        CHECK(size == (size_t)pVmemBuf->getBlockSize());
        CHECK(pVmemBuf->getCurRBlkPos() == pVmemBuf->getBlockSize() * 2);
        pVmemBuf->readUsed(size);
        CHECK(false == pVmemBuf->empty());

        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pVmemBuf->getCurRBlkPos() == pVmemBuf->getBlockSize() * 3);
        CHECK(pBuf != NULL);
        CHECK(size == 1024);
        pVmemBuf->readUsed(size);
        CHECK(true == pVmemBuf->empty());

        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pVmemBuf->getCurRBlkPos() == pVmemBuf->getBlockSize() * 3);
        CHECK(pBuf != NULL);
        CHECK(size == 0);

        pBuf = pVmemBuf->getWriteBuffer(size);
        CHECK(pVmemBuf->getCurWBlkPos() == pVmemBuf->getBlockSize() * 3);
        CHECK(pBuf != NULL);
        CHECK(size == (size_t)pVmemBuf->getBlockSize() - 1024);
        pVmemBuf->writeUsed(size);
        CHECK(false == pVmemBuf->empty());

        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pVmemBuf->getCurRBlkPos() == pVmemBuf->getBlockSize() * 3);
        CHECK(pBuf != NULL);
        CHECK(size == (size_t)pVmemBuf->getBlockSize() - 1024);
        pVmemBuf->readUsed(size);

        CHECK(true == pVmemBuf->empty());
        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pVmemBuf->getCurRBlkPos() == pVmemBuf->getBlockSize() * 3);
        CHECK(pBuf == NULL);

        pBuf = pVmemBuf->getWriteBuffer(size);
        CHECK(pVmemBuf->getCurWBlkPos() == pVmemBuf->getBlockSize() * 4);
        CHECK(pBuf != NULL);
        CHECK(size == (size_t)pVmemBuf->getBlockSize());
        CHECK(pVmemBuf->getCurFileSize() >= pVmemBuf->getBlockSize() * 4);
        pVmemBuf->writeUsed(size);
        CHECK(false == pVmemBuf->empty());

        pBuf = pVmemBuf->getReadBuffer(size);
        CHECK(pVmemBuf->getCurRBlkPos() == pVmemBuf->getBlockSize() * 4);
        CHECK(pBuf != NULL);
        CHECK(size == (size_t)pVmemBuf->getBlockSize());
        pVmemBuf->readUsed(size);
        CHECK(true == pVmemBuf->empty());

        delete pVmemBuf;

    }

    TEST(testOpenCloseMmapFile)
    {

//    for( int i = 0; i < 2000; ++i )
//    {
//        VMemBuf * pVmemBuf = new VMemBuf();
//        CHECK( pVmemBuf->set( -1 ) == 0 );
//        delete pVmemBuf;
//
//    }
    }
}

#endif

