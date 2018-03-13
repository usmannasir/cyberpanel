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

#include <shm/lsshmpool.h>
#include <shm/lsshmhash.h>

#include <stdio.h>
#include <string.h>
#include <errno.h>
#include "unittest-cpp/UnitTest++.h"

static const char *g_pShmDirName = "/tmp";
static const char *g_pShmName = "SHMXTEST";
static const char *g_pPool1Name = "XPOOL678901234567";
static const char *g_pPool2Name = "XPOOL2";
static const char *g_pHashName = "XPOOLHASH";

#define SZ_TESTBCKT     32
#define SZ_TESTLIST     256
#define SZ_LISTMIN      256

typedef struct xxx_s
{
    int x[10];
} xxx_t;


TEST(shmPerProcess_test)
{
    char achShmFileName[255];
    char achLockFileName[255];
    snprintf(achShmFileName, sizeof(achShmFileName), "%s/%s.shm",
             g_pShmDirName, g_pShmName);
    snprintf(achLockFileName, sizeof(achLockFileName), "%s/%s.lock",
             g_pShmDirName, g_pShmName);
    unlink(achShmFileName);
    unlink(achLockFileName);

    fprintf(stdout, "shmperprocesstest: [%s/%s,%s/%s]\n",
            g_pShmName, g_pPool1Name, g_pPool2Name, g_pHashName);

    LsShm *pShm = NULL;
    LsShmPool *pGPool;
    LsShmPool *pPool1;
    LsShmPool *pPool2;
    LsShmHash *pHash1;
    LsShmHash *pHash2;
    LsShmOffset_t off0;
    LsShmOffset_t off1;
    LsShmOffset_t off2;
    LsShmOffset_t off3;
    const char *pMsg;

    CHECK((pShm = LsShm::open(g_pShmName, 0, "/etc")) == NULL);
    pMsg = LsShm::getErrMsg();
    CHECK(*pMsg != '\0');
    printf("pShm=%p, Expected Msg: [%s], stat=%d, errno=%d.\n",
           pShm, pMsg, LsShm::getErrStat(), LsShm::getErrNo());
    LsShm::clrErrMsg();
    CHECK(*pMsg == '\0');

    CHECK((pShm = LsShm::open(g_pShmName, 0, g_pShmDirName)) != NULL);
    if (unlink(achShmFileName) != 0)
        perror(achShmFileName);
    if (unlink(achLockFileName) != 0)
        perror(achLockFileName);
    if (pShm == NULL)
        return;
    CHECK(pShm->recoverOrphanShm() == 0);

    CHECK((pGPool = pShm->getGlobalPool()) != NULL);
    if (pGPool == NULL)
        return;
    CHECK((pPool1 = pShm->getNamedPool(g_pPool1Name)) != NULL);
    if (pPool1 == NULL)
        return;
    CHECK((pPool2 = pShm->getNamedPool(g_pPool2Name)) != NULL);
    if (pPool2 == NULL)
        return;

    CHECK((pHash1 = pPool1->getNamedHash(g_pHashName, 0, NULL, NULL,
                                         LSSHM_FLAG_NONE)) != NULL);
    if (pHash1 == NULL)
        return;
    const void *pKey = (const void *)0x11223344;
    int val = 0x01020304;
    CHECK(pHash1->insert(pKey, 0, (const void *)&val, sizeof(val)) != 0);
    CHECK(pHash1->insert(pKey, 0, (const void *)&val,
                         sizeof(val)) == 0); // dup
    CHECK((pHash2 = pPool2->getNamedHash(g_pHashName, 0, NULL, NULL,
                                         LSSHM_FLAG_NONE)) != NULL);
    if (pHash2 == NULL)
        return;

    // shmhash template test
    const char aKey[] = "tmplKey";
    const int iKeyLen = sizeof(aKey) - 1;
    xxx_t xxx;
    TShmHash<xxx_t> *pTHash;
    ls_strpair_t parms;
    LsShmHash::iteroffset off;
    int iValLen;
    int ret;

    pTHash = (TShmHash <xxx_t> *)pGPool->getNamedHash(
                 "tmplHash", 0, LsShmHash::hashXXH32, memcmp, LSSHM_FLAG_NONE);
    xxx.x[0] = 0x1234;
    CHECK(pTHash->update(aKey, iKeyLen, &xxx) == 0);
    CHECK((off.m_iOffset = pTHash->get(aKey, iKeyLen, &iValLen, &ret)) != 0);
    CHECK(iValLen == sizeof(xxx));
    CHECK(ret == LSSHM_VAL_CREATED);
    CHECK(pTHash->update(aKey, iKeyLen, &xxx) == off.m_iOffset);
    CHECK(pTHash->insert(aKey, iKeyLen, &xxx) == 0);
    CHECK(pTHash->find(aKey, iKeyLen, &ret) == off.m_iOffset);
    CHECK(ret == sizeof(xxx));

    xxx.x[0] = 0x5678;
    ls_str_set(&parms.key, (char *)aKey, iKeyLen);
    ls_str_set(&parms.val, (char *)&xxx, sizeof(xxx));
    CHECK(pTHash->insertIterator(&parms).m_iOffset == 0);
    CHECK((off = pTHash->getIterator(&parms, &ret)).m_iOffset != 0);
    CHECK(ret == LSSHM_VAL_NONE);
    if (off.m_iOffset != 0)
    {
        TShmHash<xxx_t>::iterator it(pTHash->offset2iterator(off));
        CHECK(memcmp(it.first(), aKey, iKeyLen) == 0);
        CHECK(((xxx_t *)it.second())->x[0] == 0x1234);
        CHECK(pTHash->setIterator(&parms).m_iOffset == off.m_iOffset);
        CHECK(pTHash->findIterator(&parms).m_iOffset == off.m_iOffset);
        CHECK(((xxx_t *)it.second())->x[0] == 0x5678);
    }

    int remap = 0;
    CHECK((off0 = pGPool->alloc2(SZ_TESTBCKT, remap)) != 0);
    CHECK((off1 = pPool1->alloc2(SZ_TESTBCKT, remap)) != 0);
    CHECK((off2 = pPool1->alloc2(SZ_TESTBCKT, remap)) != 0);
    CHECK((off3 = pPool1->alloc2(SZ_TESTBCKT, remap)) != 0);
    if ((off0 == 0) || (off1 == 0) || (off2 == 0) || (off3 == 0))
        return;

    pPool2->release2(off1, SZ_TESTBCKT);
    pPool2->mvFreeBucket();
    CHECK((off0 = pGPool->alloc2(SZ_TESTBCKT, remap)) == off1);

    pPool2->release2(off0, SZ_TESTBCKT);
    pPool2->release2(off2, SZ_TESTBCKT);
    pPool2->mvFreeBucket();
    CHECK((off0 = pGPool->alloc2(SZ_TESTBCKT, remap)) == off2);

    pPool2->release2(off0, SZ_TESTBCKT);
    pPool2->release2(off3, SZ_TESTBCKT);
    pPool2->mvFreeBucket();
    CHECK((off0 = pGPool->alloc2(SZ_TESTBCKT, remap)) == off3);

    pPool1->mvFreeList();
    CHECK((off0 = pGPool->alloc2(SZ_TESTLIST, remap)) != 0);
    CHECK((off1 = pPool1->alloc2(SZ_TESTLIST, remap)) != 0);
    CHECK((off2 = pPool1->alloc2(SZ_TESTLIST, remap)) != 0);
    CHECK((off3 = pPool1->alloc2(SZ_TESTLIST, remap)) != 0);
    if ((off0 == 0) || (off1 == 0) || (off2 == 0) || (off3 == 0))
        return;

    pPool2->release2(off1, SZ_TESTLIST);
    pPool2->mvFreeList();

    CHECK(pGPool->alloc2(SZ_TESTLIST, remap) == off1);
    pPool2->release2(off2, SZ_TESTLIST);
    pPool2->release2(off3, SZ_TESTLIST);
    pPool2->mvFreeList();

    CHECK(pGPool->alloc2(SZ_TESTLIST, remap) == off3);

    CHECK(pShm->findReg(g_pPool1Name) != NULL);
    CHECK((off1 = pPool1->alloc2(SZ_TESTBCKT, remap)) != 0);
    CHECK(pShm->recoverOrphanShm() == 0);
    pPool1->destroy();
    CHECK(pShm->findReg(g_pPool1Name) == NULL);
    pPool1->release2(off1, SZ_TESTBCKT);
    pPool1->close();
    pPool2->close();
    CHECK(pShm->findReg(g_pPool2Name) == NULL);
    CHECK(pGPool->alloc2(SZ_TESTBCKT, remap) == off1);
    CHECK(pShm->recoverOrphanShm() == 0);

    // shm statistics
    int cnt;
    LsShmSize_t acnt;
    LsShmSize_t rcnt;
    off0 = pGPool->alloc2(1 * LSSHM_SHM_UNITSIZE, remap);
    off1 = pGPool->alloc2(2 * LSSHM_SHM_UNITSIZE + 1, remap);
    off2 = pGPool->alloc2(2 * LSSHM_SHM_UNITSIZE, remap);
    off3 = pGPool->alloc2(1 * LSSHM_SHM_UNITSIZE, remap);
    acnt = pGPool->roundSize2pages(1 * LSSHM_SHM_UNITSIZE)
           + pGPool->roundSize2pages(2 * LSSHM_SHM_UNITSIZE + 1)
           + pGPool->roundSize2pages(2 * LSSHM_SHM_UNITSIZE)
           + pGPool->roundSize2pages(1 * LSSHM_SHM_UNITSIZE);
    rcnt = 0;

    LsShmPoolMapStat *pStat =
        (LsShmPoolMapStat *)pShm->offset2ptr(pGPool->getPoolMapStatOffset());
    // in real life, should always use offset2ptr when accessing.
    // in this case, for simplicity, use same pointer, assume no remapping.

    cnt = pStat->m_iGpAllocated;
    pGPool->release2(off0, 1 * LSSHM_SHM_UNITSIZE);
    pGPool->release2(off2, 2 * LSSHM_SHM_UNITSIZE);
    rcnt += pGPool->roundSize2pages(3 * LSSHM_SHM_UNITSIZE);
    CHECK(pStat->m_iGpReleased == 3);       // 3 blocks
    CHECK(pStat->m_iGpFreeListCnt == 2);    // 2 entries
    CHECK(pStat->m_iPgAllocated == acnt);
    CHECK(pStat->m_iPgReleased == rcnt);
    pGPool->release2(off1, 2 * LSSHM_SHM_UNITSIZE + 1);
    rcnt += pGPool->roundSize2pages(2 * LSSHM_SHM_UNITSIZE + 1);
    CHECK(pStat->m_iGpReleased == 6);       // 6 blocks
    CHECK(pStat->m_iGpFreeListCnt == 1);    // 1 entry
    CHECK(pStat->m_iPgReleased == rcnt);
    pGPool->alloc2(2 * LSSHM_SHM_UNITSIZE,
                   remap); // alloc 2 blocks from global freelist
    acnt += pGPool->roundSize2pages(2 * LSSHM_SHM_UNITSIZE);
    cnt += 2;
    CHECK(pStat->m_iGpAllocated == (LsShmSize_t)cnt);
    CHECK(pStat->m_iGpFreeListCnt == 1);    // still 1 entry
    CHECK(pStat->m_iPgAllocated == acnt);

    // shmpool freelist
    acnt = pStat->m_iFlAllocated;       // bytes
    rcnt = pStat->m_iFlReleased;
    off0 = pGPool->alloc2(2 * SZ_TESTLIST, remap);
    acnt += (2 * SZ_TESTLIST);
    int diff = (int)(pStat->m_iFlAllocated - acnt);
    if ((diff > 0) && (diff < SZ_LISTMIN))  // might move residual to bucket
        acnt += diff;
    CHECK(pStat->m_iFlAllocated == acnt);
    cnt = pStat->m_iFlCnt;
    pGPool->release2(off0, 2 * SZ_TESTLIST);
    rcnt += (2 * SZ_TESTLIST);
    CHECK(pStat->m_iFlReleased == rcnt);
    CHECK(pStat->m_iFlCnt == (LsShmSize_t)(cnt + 1));
    pGPool->alloc2(SZ_TESTLIST, remap); // piece of a freelist block
    acnt += SZ_TESTLIST;
    CHECK(pStat->m_iFlAllocated == acnt);
    CHECK(pStat->m_iFlReleased == rcnt);
    CHECK(pStat->m_iFlCnt == (LsShmSize_t)(cnt + 1));
    pGPool->alloc2(SZ_TESTLIST, remap); // remainder of freelist block
    acnt += SZ_TESTLIST;
    CHECK(pStat->m_iFlAllocated == acnt);
    CHECK(pStat->m_iFlCnt == (LsShmSize_t)cnt);

    // shmpool bucket
    acnt = pStat->m_bckt[SZ_TESTBCKT / LSSHM_POOL_UNITSIZE].m_iBkAllocated;
    off0 = pGPool->alloc2(SZ_TESTBCKT, remap);
    ++acnt;
    CHECK(pStat->m_bckt[SZ_TESTBCKT / LSSHM_POOL_UNITSIZE].m_iBkAllocated ==
          acnt);
    rcnt = pStat->m_bckt[SZ_TESTBCKT / LSSHM_POOL_UNITSIZE].m_iBkReleased;
    pGPool->release2(off0, SZ_TESTBCKT);
    ++rcnt;
    CHECK(pStat->m_bckt[SZ_TESTBCKT / 8].m_iBkReleased == rcnt);
}

#endif
