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

#include <shm/lsshmhash.h>

#include <stdio.h>
#include <string.h>
#include "unittest-cpp/UnitTest++.h"

static const char *g_pShmDirName = "/dev/shm/ols";
static const char *g_pShmName = "SHMLRUTEST";
static const char *g_pHashName = "SHMLRUHASH";

static void doit(LsShm *pShm);

TEST(ls_ShmBaseLru_test)
{
    char shmfilename[255];
    char lockfilename[255];
    LsShm *pShm;
    snprintf(shmfilename, sizeof(shmfilename), "%s/%s.shm",
             g_pShmDirName, g_pShmName);
    snprintf(lockfilename, sizeof(lockfilename), "%s/%s.lock",
             g_pShmDirName, g_pShmName);
    unlink(shmfilename);
    unlink(lockfilename);

    fprintf(stdout, "shmbaselrutest: [%s/%s]\n", g_pShmName, g_pHashName);
    CHECK((pShm = LsShm::open(g_pShmName, 0, g_pShmDirName)) != NULL);
    if (unlink(shmfilename) != 0)
        perror(shmfilename);
    if (unlink(lockfilename) != 0)
        perror(lockfilename);

    if (pShm == NULL)
    {
        printf("Msg: [%s], stat=%d, errno=%d.\n",
               LsShm::getErrMsg(), LsShm::getErrStat(), LsShm::getErrNo());
        LsShm::clrErrMsg();
        return;
    }

    doit(pShm);
}


static int trimfunc(LsShmHash::iterator iter, void *arg)
{
    LsShmHash *pHash = (LsShmHash *)arg;
    fprintf(stdout, "trim: [%.*s][%.*s] size=%d\n",
            iter->getKeyLen(), iter->getKey(),
            iter->getValLen(), iter->getVal(),
            (int)pHash->size());
    return 0;
}


static void doit(LsShm *pShm)
{
    const char key0[] = "KEY0";
    const char key1[] = "KEY1";
    const char keyX[] = "KEYX5678901234567";
    const char valX[] = "VALX56789012345678901";
    LsShmPool *pGPool;
    LsShmHash *pHash;
    LsShmHElem *pTop;
    LsShmHash::iterator iter = NULL;
    LsShmHash::iteroffset iterOff0 = {0};
    LsShmHash::iteroffset iterOff1 = {0};
    LsShmHash::iteroffset iterOffX = {0};
    LsShmHash::iteroffset offTop = {0};
    ls_strpair_t parms;
    int flags;
    int cnt = 0;
    int num;

    CHECK((pGPool = pShm->getGlobalPool()) != NULL);
    if (pGPool == NULL)
        return;
    CHECK((pHash = pGPool->getNamedHash(
                       g_pHashName, 0, LsShmHash::hashXXH32, memcmp,
                       LSSHM_FLAG_LRU)) != NULL);
    if (pHash == NULL)
        return;
    ls_str_set(&parms.key, (char *)key0, sizeof(key0) - 1);
    ls_str_set(&parms.val, NULL, 0);
    flags = LSSHM_FLAG_NONE;
    CHECK((iterOff0 = pHash->getIterator(&parms, &flags)).m_iOffset != 0);
    CHECK(flags == LSSHM_VAL_CREATED);

    ls_str_set(&parms.key, (char *)key1, sizeof(key1) - 1);
    CHECK((iterOff1 = pHash->findIterator(&parms)).m_iOffset == 0);
    CHECK((iterOff1 = pHash->updateIterator(&parms)).m_iOffset == 0);

    CHECK((iterOff1 = pHash->insertIterator(&parms)).m_iOffset != 0);
    CHECK(pHash->findIterator(&parms).m_iOffset == iterOff1.m_iOffset);
    ls_str_set(&parms.val, (char *)valX, sizeof(valX) - 1);
    CHECK((iterOff1 = pHash->updateIterator(&parms)).m_iOffset !=
          0);  // may change
    if (iterOff1.m_iOffset != 0)
    {
        iter = pHash->offset2iterator(iterOff1);
        CHECK(iter->getValLen() == sizeof(valX) - 1);
        CHECK(memcmp(iter->getVal(), valX, iter->getValLen()) == 0);
    }
    ls_str_set(&parms.val, (char *)valX, 5);
    CHECK(pHash->setIterator(&parms).m_iOffset ==
          iterOff1.m_iOffset);  // should use same memory
    CHECK(iter->getValLen() == 5);

    ls_str_set(&parms.key, (char *)keyX, sizeof(keyX) - 1);
    flags = LSSHM_VAL_NONE;
    CHECK((iterOffX = pHash->getIterator(&parms, &flags)).m_iOffset != 0);
    CHECK(flags == LSSHM_VAL_CREATED);

    CHECK(pHash->check() == SHMLRU_CHECKOK);
    CHECK(pHash->size() == 3);
    CHECK(pHash->getLruTop().m_iOffset == iterOffX.m_iOffset);

    ls_str_set(&parms.key, (char *)key0, sizeof(key0) - 1);
    flags = LSSHM_VAL_NONE;
    CHECK(pHash->getIterator(&parms, &flags).m_iOffset == iterOff0.m_iOffset);
    CHECK(flags == LSSHM_VAL_NONE);

    offTop = pHash->getLruTop();
    CHECK(offTop.m_iOffset == iterOff0.m_iOffset);
    if ((int)offTop.m_iOffset > 0)
    {
        pTop = pHash->offset2iterator(offTop);
        time_t tmval = pTop->getLruLasttime();
        fprintf(stdout, "[%.*s] %s",
                pTop->getKeyLen(), pTop->getKey(), ctime(&tmval));
        num = pHash->size();
        CHECK((cnt = pHash->trim(tmval, trimfunc, (void *)pHash)) < num);
        num -= cnt;
        CHECK(pHash->size() == (size_t)num);
        CHECK(pHash->trim(tmval + 1, trimfunc, (void *)pHash) == num);
        CHECK(pHash->size() == (size_t)0);
        CHECK(pHash->getLruTop().m_iOffset == 0);
    }

    // large hash test
    char keyBuf[16];
    char valBuf[16];
    LsShmOffset_t off;
    int i;
    int valLen;
    num = 80000;
    for (i = 0; i < num; ++i)
    {
        sprintf(keyBuf, "KEY%06d", i);
        sprintf(valBuf, "VAL%06d", i);
        if ((off = pHash->insert(keyBuf, 9, valBuf, 9)) == 0)
        {
            printf("Insert [%.*s] failed: [%s], stat=%d, errno=%d.\n",
                   9, keyBuf,
                   LsShm::getErrMsg(), LsShm::getErrStat(), LsShm::getErrNo());
            LsShm::clrErrMsg();
            break;
        }
        if (pHash->find(keyBuf, 9, &valLen) != off)
            break;
        if (strncmp((const char *)pHash->offset2ptr(off), valBuf, 9) != 0)
            break;
    }
    CHECK(pHash->size() == (size_t)num);
    offTop = pHash->getLruTop();
    pTop = pHash->offset2iterator(offTop);
    time_t tmval = pTop->getLruLasttime();
    CHECK(pHash->trim(tmval + 1, NULL, NULL) == num);
    CHECK(pHash->size() == (size_t)0);

    pHash->close();

    return;
}

#endif

