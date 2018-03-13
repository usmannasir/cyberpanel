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
#include <http/httplog.h>

#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <shm/lsshm.h>
#include <shm/lsshmpool.h>
#include <shm/lsshmhash.h>
#include "lsshmdebug.h"

#define MY_MAXLOOP 0x8000
#define INITIAL_HASHSIZE 0x20
#define NUMTHREADS  8

typedef struct
{
    uint32_t    key;
    int         keyLen;
    char       *value;
    int         valueLen;
} hashNumItem_t;

static hashNumItem_t myHashNumItem[] =
{
    {0, 0, (char *)"TEST1", 0},
    {0, 0, (char *)"TEST2", 0},
    {0, 0, (char *)"TEST3", 0},
    {0, 0, (char *)"TEST4", 0},
    {0, 0, (char *)"TEST5", 0},
    {0, 0, (char *)"TEST6", 0}
};
#define NUM_HASHNUMITEM (int)(sizeof(myHashNumItem)/sizeof(hashNumItem_t))

typedef struct
{
    char       key[0x40];
    int        keyLen;
    char       value[0x40];
    int        valueLen;
} hashStrItem_t;

static hashStrItem_t myHashStrItem[] =
{
    {{'X', 'Y', 'Z', '1', 0}, 0, {'T', 'E', 'S', 'T', '1', 0}, 0},
    {{'A', 'Y', 'Z', '1', 0}, 0, {'T', 'E', 'S', 'T', '2', 0}, 0},
    {{'B', 'Y', 'Z', '1', 0}, 0, {'T', 'E', 'S', 'T', '3', 0}, 0},
    {{'C', 'Y', 'Z', '1', 0}, 0, {'T', 'E', 'S', 'T', '4', 0}, 0},
    {{'D', 'Y', 'Z', '1', 0}, 0, {'T', 'E', 'S', 'T', '5', 0}, 0},
    {{'E', 'Y', 'Z', '1', 0}, 0, {'T', 'E', 'S', 'T', '6', 0}, 0},
};
#define NUM_HASHSTRITEM (int)(sizeof(myHashStrItem)/sizeof(hashStrItem_t))

static void    setUpHashNumItem(hashNumItem_t *p, int num)
{
    int    counter = 0;
    while (--num >= 0)
    {
        p->key = ++counter;
        p->keyLen = sizeof(p->key);
        p->valueLen = strlen(p->value) + 1; /* include null */
        p++;
    }
}

static void    setUpHashStrItem(hashStrItem_t *p, int num)
{
    while (--num >= 0)
    {
        p->keyLen = strlen(p->key) + 1; /* include null */
        p->valueLen = strlen(p->value);
        p++;
    }
}

static void    testShmHashSmall(LsShm *shm, LsShmPool *pool)
{
    if (shm->status() != LSSHM_READY)
    {
        fprintf(debugBase::fp(), "LsShm %p NOTREADY %d\n",
                shm, shm->status());
        return;
    }

    LsShmHash *myHashNum = LsShmHash::open(pool
                                           , "SHMHASH-NUM"
                                           , 0x10, NULL, NULL);
    LsShmHash *myHashStr = LsShmHash::open(pool
                                           , "SHMHASH-STR"
                                           , 0x10
                                           , LsShmHash::hashString
                                           , LsShmHash::compString);

    assert(myHashNum && myHashStr);

    setUpHashNumItem(myHashNumItem, NUM_HASHNUMITEM);
    setUpHashStrItem(myHashStrItem, NUM_HASHSTRITEM);
    LsShmHash::iterator iter;

    fprintf(debugBase::fp(), "\nTESTING NUM HASH\n");
    hashNumItem_t *p_hashNumItem;
    p_hashNumItem = myHashNumItem;
    for (int i = 0; i < NUM_HASHNUMITEM; i++, p_hashNumItem++)
    {
        iter = myHashNum->findIterator((void *)(long)p_hashNumItem->key,
                                       p_hashNumItem->keyLen);
        if (!iter)
        {
            fprintf(debugBase::fp(), "GOOD HASH MISSING KEY %d\n",
                    p_hashNumItem->key);

            iter = myHashNum->insertIterator((void *)(long)p_hashNumItem->key,
                                             p_hashNumItem->keyLen,
                                             p_hashNumItem->value, p_hashNumItem->valueLen);
            if (!iter)
            {
                fprintf(debugBase::fp(), "ERROR HASH FAILED TO INSERT KEY %d\n",
                        p_hashNumItem->key);
            }

            iter = myHashNum->findIterator((void *)(long)p_hashNumItem->key,
                                           p_hashNumItem->keyLen);
            if (!iter)
            {
                fprintf(debugBase::fp(), "ERROR HASH MISSING KEY %d\n",
                        p_hashNumItem->key);
                fflush(debugBase::fp());
                continue;
            }
            fflush(debugBase::fp());
        }
        char *cp;
        long *lp;
        lp = (long *)iter->getKey();
        cp = (char *)myHashNum->getIterDataPtr(iter);
        fprintf(debugBase::fp(),
                "HASH KEY %d -> LEN %d KEY %X rkeylen %d valuelen %d [%s %d]\n",
                p_hashNumItem->key,
                iter->x_iLen,
                (int)iter->x_hkey,
                iter->getKeyLen(),
                iter->getValLen(),
                cp, (int)*lp);

    }
    fflush(debugBase::fp());

    fprintf(debugBase::fp(), "\nTESTING STR HASH\n");
    hashStrItem_t *p_hashStrItem;
    p_hashStrItem = myHashStrItem;
    for (int i = 0; i < NUM_HASHSTRITEM; i++, p_hashStrItem++)
    {
        iter = myHashStr->findIterator((void *)p_hashStrItem->key,
                                       p_hashStrItem->keyLen);
        if (!iter)
        {
            fprintf(debugBase::fp(), "GOOD HASH MISSING KEY STR %s\n",
                    p_hashStrItem->key);

            iter = myHashStr->insertIterator((void *)p_hashStrItem->key,
                                             p_hashStrItem->keyLen,
                                             p_hashStrItem->value, p_hashStrItem->valueLen);
            if (!iter)
            {
                fprintf(debugBase::fp(), "ERROR HASH FAILED TO INSERT KEY STR %s\n",
                        p_hashStrItem->key);
            }

            iter = myHashStr->findIterator((void *)p_hashStrItem->key,
                                           p_hashStrItem->keyLen);
            if (!iter)
            {
                fprintf(debugBase::fp(), "ERROR HASH MISSING KEY STR %s\n",
                        p_hashStrItem->key);
                fflush(debugBase::fp());
                continue;
            }
            fflush(debugBase::fp());
        }
        char *cp;
        char *kp;
        kp = (char *)iter->getKey();
        cp = (char *)myHashStr->getIterDataPtr(iter);

        fprintf(debugBase::fp(),
                "HASH KEY %s -> LEN %d KEY %X rkeylen %d valuelen %d [%s %s]\n",
                p_hashStrItem->key,
                iter->x_iLen,
                (unsigned int)iter->x_hkey,
                iter->getKeyLen(),
                iter->getValLen(),
                cp, kp);
        fflush(debugBase::fp());
    }
    fflush(debugBase::fp());
}

/*
 * Create big testcase here
 */
LsShmHash *xHashStr;
LsShmHash *xHashNum;
static int setupHashFunc(LsShmPool *pool)
{
    const char *funcName = "testShmHash";
    const char *hashName = "SHMHASH-STR";
    xHashStr = LsShmHash::open(pool
                               , hashName
                               , INITIAL_HASHSIZE
                               , LsShmHash::hashString
                               , LsShmHash::compString);
    assert(xHashStr);
    if (debugBase::checkStatus(funcName, hashName, xHashStr->status()))
        return LS_FAIL;

    hashName = "SHMHASH-NUM";
    xHashNum = LsShmHash::open(pool
                               , hashName
                               , INITIAL_HASHSIZE
                               , NULL
                               , NULL);
    assert(xHashNum);
    if (debugBase::checkStatus(funcName, hashName, xHashNum->status()))
        return LS_FAIL;
    return 0;
}

typedef struct
{
    int             keyLen;
    int             valueLen;
    LsShmHKey    key;
    uint8_t         value[0x20];
} myHashItem_t;

static void    setHashNumItem(myHashItem_t *p_item, int num, int myId)
{
    char       n;

    n = snprintf((char *)p_item->value, 0x20, "%d %d", num, myId);
    p_item->key = num;
    p_item->keyLen = sizeof(int);
    p_item->valueLen = n;
}

#if 0
/*
 */
static void dumpIter(LsShmHash *p_hash, LsShmHash::iterator iter)
{
    fprintf(debugBase::fp(),
            "ITER %X LEN %d VOFF %d NEXT %d KEY %X KLEN %d VLEN %d\n",
            p_hash->ptr2offset(iter),
            iter->x_iLen,
            iter->x_valueOff,
            iter->x_iNext,
            iter->x_hkey,
            iter->getKeyLen(),
            iter->x_iValueLen
           );
    debugBase::dumpIter("IterKey", iter);
}
#endif

static int verifyNumKey(LsShmHash *p_hash, int num , int id,
                        LsShmHash::iterator iter,
                        int dumpFlag
                       )
{
    if (!iter)
        return -2; // not find

    myHashItem_t x;
    setHashNumItem(&x, num, id);
    if (
        (!memcmp((char *)iter->getVal(), (char *)x.value, x.valueLen))
        && ((*(int *) iter->getKey()) == num)
    )
        return 0;
    if (dumpFlag)
    {
        debugBase::dumpBuf("NE-Key", (char *)&x.key, x.keyLen);
        debugBase::dumpBuf("NE-Val", (char *)x.value, x.valueLen);
        debugBase::dumpBuf("NR-Key", (char *)iter->getKey(), iter->getKeyLen());
        debugBase::dumpBuf("NR-Val", (char *)iter->getVal(), iter->getValLen());
    }
    return LS_FAIL;
}

static int  findNumKey(LsShmHash *p_hash, int num , int id)
{
    LsShmHash::iterator iter;
    myHashItem_t x;
    setHashNumItem(&x, num, id);

    iter = p_hash->findIterator((void *)(long)x.key, x.keyLen);
    if (!iter)
    {
        fprintf(debugBase::fp(), "ERROR FIND HASH-NUM %d %d\n", num, id);
        return LS_FAIL;
    }
    else
    {
        if (!verifyNumKey(p_hash, num, id, iter, 1))
        {
            fprintf(debugBase::fp(), "GOOD MATCHED-NUM %08X %8d %8d\n",
                    p_hash->ptr2offset(iter), num, id);
        }
        fflush(debugBase::fp());
    }
    return 0;
}

static int  saveNumKey(LsShmHash *p_hash, int num , int id)
{
    LsShmHash::iterator iter;
    myHashItem_t x;
    setHashNumItem(&x, num, id);
    iter = p_hash->setIterator((void *)(long)x.key, x.keyLen, x.value,
                               x.valueLen);
    if (!iter)
    {
        fprintf(debugBase::fp(), "ERROR SAVE HASH-NUM %d %d\n", num, id);
        return LS_FAIL;
    }
    // return verifyNumKey(p_hash, num, id, iter, 1);
    return 0;
}

static int    testLargeNumHash(LsShm *shm,
                               LsShmPool *pool,
                               LsShmHash *hash,
                               int id)
{
    int    from_num;

    for (from_num = 0; from_num < MY_MAXLOOP;)
    {
        if ((from_num & 0x3) == id)
        {
            if (findNumKey(hash, from_num , id))
            {
                fprintf(debugBase::fp(), "SAVE KEY %d %d", from_num, id);
                if (saveNumKey(hash, from_num , id))
                {
                    fprintf(debugBase::fp(), "ERROR CREATE HASH-NUM %d %d\n", from_num, id);
                    return LS_FAIL;
                }
                fprintf(debugBase::fp(), "\n");
            }
        }
        from_num++;
    }
    return 0;
}

static void    setHashStrItem(hashStrItem_t *p_item, int num, int myId)
{
    char       n;

    n = snprintf((char *)p_item->key, 0x20, "KEY%d+%d", num, myId);
    p_item->keyLen = n + 1; /* key including null */
    n = snprintf((char *)p_item->value, 0x20, "VALUE%d-%d", num, myId);
    p_item->valueLen = n; /* no null */
}

static int verifyStrKey(LsShmHash *p_hash, int num , int id,
                        LsShmHash::iterator iter, int dumpFlag)
{
    if (!iter)
        return -2; // not find

    hashStrItem_t x;
    setHashStrItem(&x, num, id);
    if (
        (!memcmp((char *)iter->getVal(), (char *)x.value, x.valueLen))
        &&
        (!memcmp((char *)iter->getKey(), (char *)x.key, x.keyLen))
    )
        return 0;
    if (dumpFlag)
    {
        debugBase::dumpBuf("SE-Key", (char *)x.key, x.keyLen);
        debugBase::dumpBuf("SE-Val", (char *)x.value, x.valueLen);
        debugBase::dumpBuf("SR-Key", (char *)iter->getKey(), iter->getKeyLen());
        debugBase::dumpBuf("SR-Val", (char *)iter->getVal(), iter->getValLen());
    }
    return LS_FAIL;
}

static int  findStrKey(LsShmHash *p_hash, int num , int id)
{
    LsShmHash::iterator iter;
    hashStrItem_t x;
    setHashStrItem(&x, num, id);

    iter = p_hash->findIterator((void *)x.key, x.keyLen);
    if (!iter)
    {
        fprintf(debugBase::fp(), "ERROR FIND HASH-STR %d %d\n", num, id);
        return LS_FAIL;
    }
    else
    {
        if (!verifyStrKey(p_hash, num, id, iter, 1))
        {
            fprintf(debugBase::fp(),
                    "GOOD MATCHED-STR %08X %8d %8d\n",
                    p_hash->ptr2offset(iter), num, id);
        }
        fflush(debugBase::fp());
    }
    return 0;
}

static int  saveStrKey(LsShmHash *p_hash, int num , int id)
{
    LsShmHash::iterator iter;
    hashStrItem_t x;
    setHashStrItem(&x, num, id);

    iter = p_hash->setIterator((void *)x.key, x.keyLen, (void *)x.value,
                               x.valueLen);
    if (!iter)
    {
        fprintf(debugBase::fp(), "ERROR SAVE HASH-STR %d %d\n", num, id);
        return LS_FAIL;
    }
    // return verifyStrKey(p_hash, num, id, iter, 1);
    return 0;
}

static int testSingleStrHash(LsShm *shm,
                             LsShmPool *pool,
                             LsShmHash *hash,
                             int num, int id)
{
    if (findStrKey(hash, num , id))
    {
        fprintf(debugBase::fp(), "SAVE KEY %d ", num);
        if (saveStrKey(hash, num , id))
        {
            fprintf(debugBase::fp(), "ERROR CREATE HASH-STR %d %d\n", num, id);
            return LS_FAIL;
        }
        fprintf(debugBase::fp(), "\n");
    }
    return 0;
}

static int    testLargeStrHash(LsShm *shm,
                               LsShmPool *pool,
                               LsShmHash *hash,
                               int id)
{
    int    from_num;
    for (from_num = 0; from_num < MY_MAXLOOP;)
    {
        if ((from_num & 0x3) == id)
        {
            if (findStrKey(hash, from_num , id))
            {
                fprintf(debugBase::fp(), "SAVE KEY %d ", from_num);
                if (saveStrKey(hash, from_num , id))
                {
                    fprintf(debugBase::fp(), "ERROR CREATE HASH-STR %d %d\n", from_num, id);
                    return LS_FAIL;
                }
                fprintf(debugBase::fp(), "\n");
            }
        }
        from_num++;
    }
    return 0;
}

typedef struct
{
    LsShm      *shm;
    LsShmPool *pool;
    LsShmHash *hash;
    int         id;
    int         numMode;
    pthread_t   tid;
    int         exit;
} myThread_t;

void *runThread(void *uData)
{
    myThread_t *p;
    p = (myThread_t *)uData;
    fprintf(debugBase::fp(), "runThread %d-%d\n", p->id, p->numMode);
    // sleep(5 - p->id);
    fprintf(debugBase::fp(), "exitThread %d-%d\n", p->id, p->numMode);
    fflush(debugBase::fp());

    int exitCode = p->id;
    if (p->numMode)
    {
        if (testLargeNumHash(p->shm, p->pool, p->hash, p->id))
            exitCode = -p->id;
    }
    else
    {
        if (testLargeStrHash(p->shm, p->pool, p->hash, p->id))
            exitCode = -p->id;
    }
    pthread_exit((void *)(long)exitCode);
}

myThread_t  myThread[8] =
{
    {NULL, NULL, NULL, 0, 0, 0, 0},
    {NULL, NULL, NULL, 1, 0, 0, 0},
    {NULL, NULL, NULL, 2, 0, 0, 0},
    {NULL, NULL, NULL, 3, 0, 0, 0},
    {NULL, NULL, NULL, 0, 1, 0, 0},
    {NULL, NULL, NULL, 1, 1, 0, 0},
    {NULL, NULL, NULL, 2, 1, 0, 0},
    {NULL, NULL, NULL, 3, 1, 0, 0}
};


static int testHashWithThread(LsShm *shm, LsShmPool *pool)
{
    myThread_t *p;
    int i;

    p = myThread;
    for (i = 0; i < NUMTHREADS ; i++, p++)
    {
        p->shm = shm;
        p->pool = pool;
        if (p->numMode)
            p->hash = xHashNum;
        else
            p->hash = xHashStr;

        pthread_create(&p->tid, NULL, runThread, (void *) p);
        fprintf(debugBase::fp(), "DISPATCHED %d-%d\n",
                p->id, p->numMode);
    }
    p = myThread;
    for (i = 0; i < NUMTHREADS ; i++, p++)
    {
        pthread_join(p->tid, (void **)&p->exit);
        fprintf(debugBase::fp(), "JOINED %d-%d-%d\n",
                p->id, p->numMode, p->exit);
        fflush(debugBase::fp());
    }
    return 0;
}

//
//  The Hash Tester entry pointr
//
void    testSimple(LsShm *shm, LsShmPool *pool)
{
    int i ;
    testShmHashSmall(shm, pool);

    fprintf(debugBase::fp(), "\nVERIFING DATA\n");
    for (i = 0; i < 4; i++)
    {
        if (testLargeNumHash(shm, pool, xHashNum, i))
            return;
        if (testLargeStrHash(shm, pool, xHashStr, i))
            return;
    }

    for (i = 0; i < 4; i++)
    {
        testSingleStrHash(shm, pool, xHashStr, 100, 0);
        testSingleStrHash(shm, pool, xHashStr, 101, 1);
        testSingleStrHash(shm, pool, xHashStr, 102, 2);
        testSingleStrHash(shm, pool, xHashStr, 103, 3);
    }
}

void    testShmHash(LsShm *shm, LsShmPool *pool)
{
    if (setupHashFunc(pool))
        abort() ;

    testHashWithThread(shm, pool);
//    testSimple(shm, pool);
}
