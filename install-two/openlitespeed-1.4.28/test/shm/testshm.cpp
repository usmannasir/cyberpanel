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


extern int testShmApi();
extern void testShmAlloc(LsShm *p);
extern void testShmPool(LsShm *p);
extern void testShmReg(LsShm *p);
extern void testShmHash(LsShm *p, LsShmPool *pool);

// #define LS_SHMSIZE  (0x800 * 2000)
// This will crash the system because of remapping.
#define LS_SHMSIZE  0x2000

//
//  Testing routines for SHM Page allocationextern void testShmAlloc(LsShm *p);

typedef struct
{
    LsShmOffset_t  offset;
    LsShmSize_t    size;
    LsShmOffset_t  expected;
    LsShmSize_t    roundsize;
} testShm_t;

testShm_t   tArray[] =
{
    {0, 0x400,  0x0400, 0}, // 1
    {0, 0x401,  0x0800, 0}, // 2
    {0, 0x400,  0x1000, 0}, // 1
    {0, 0x801,  0x1400, 0}, // 3
    {0, 0x400,  0x2000, 0}, // 1
    {0, 0x800,  0x2400, 0}, // 2
    {0, 0x1000, 0x2c00, 0}, // 4
    {0, 0x400,  0x3c00, 0}, // 1
    {0, 0x2001, 0x4000, 0}, // 1
    {0, 0x400,  0x6400, 0}, // 1
    {0, 0x400,  0x6800, 0}, // 1
    {0, 0x400,  0x6c00, 0}, // 1
    {0, 0x400,  0x7000, 0}, // 1
    {0, 0x4000, 0x7400, 0}, // 4
    {0, 0x400,  0xA400, 0}  // 4
    //            0xA800
};

void testPoolAlloc(LsShmPool *pool, testShm_t *p_table,
                   int num, int pageFlag)
{
    int        i;
    testShm_t *p;

    p = p_table;
    for (i = 0; i < num; i++, p++)
    {
        if (pageFlag)
            p->roundsize = debugBase::roundPageSize(pool, p->size);
        else
            p->roundsize = debugBase::roundDataSize(pool, p->size);

        int remapped = 0;
        if (!(p->offset = pool->alloc2(p->size, remapped)))
        {
            fprintf(debugBase::fp(), "ABORT: NO MEORY alloc2 [%8X %8X]\n",
                    p->size,
                    p->roundsize);
            abort();
        }
        fprintf(debugBase::fp(), "ALLOC %8X %8X -> %8X %8X %s\n",
                p->offset,
                p->size,
                p->expected,
                p->roundsize,
                (p->offset == p->expected) ? "GOOD" : "BAD "
               );
        fflush(debugBase::fp());
    }

    p = p_table;
    i = rand() % num;
    i = 0;
    while (i < num)
    {
        if (i & 0x1)
        {
            fprintf(debugBase::fp(), "\nFREE %d [%8X %8X] \n",
                    i, p->offset, p->roundsize);
            pool->release2(p->offset, p->size);

            if (pageFlag)
                debugBase::dumpShm(pool, 0, NULL);
            else
                debugBase::dumpShmPool(pool, 0, NULL);
            fflush(debugBase::fp());
        }
        p++;
        i++;
    }

    p = p_table;
    i = rand() % num;
    i = 0;
    while (i < num)
    {
        if (!(i & 0x1))
        {
            fprintf(debugBase::fp(), "\nFREE TEST %d [%8X %8X] \n",
                    i, p->offset, p->roundsize);
            pool->release2(p->offset, p->size);
            if (pageFlag)
                debugBase::dumpShm(pool, 0, NULL);
            else
                debugBase::dumpShmPool(pool, 0, NULL);
            fflush(debugBase::fp());
        }
        p++;
        i++;
    }

    fflush(debugBase::fp());
}

void    testShmAlloc(LsShm *shm)
{
    testShm_t    *p;
    int i;

    if (shm->status() != LSSHM_READY)
    {
        fprintf(debugBase::fp(), "LsShm %p NOTREADY %d\n",
                shm, shm->status());
        return;
    }

    LsShmPool   *pool = LsShmPool::open(shm, LSI_SHM_POOL_NAME);
    if (pool->status() != LSSHM_READY)
    {
        fprintf(debugBase::fp(), "LsShmPool %p NOTREADY %d\n",
                shm, shm->status());
        return;
    }

    p = tArray;
    for (i = 0; i < (int)(sizeof(tArray) / sizeof(testShm_t)); i++)
    {
        p->roundsize = debugBase::roundPageSize(pool, p->size),
           fprintf(debugBase::fp(), "\nALLOC TEST %d SIZE %X\n", i, p->roundsize);
        int remapped = 0;
        if (!(p->offset = pool->alloc2(p->size, remapped)))
        {
            fprintf(debugBase::fp(), "ABORT: NO MEORY alloc2 [%8X %8X]\n",
                    p->size,
                    p->roundsize);
            abort();
        }
        fprintf(debugBase::fp(), "ALLOC %8X %8X -> %8X %8X %s\n",
                p->offset,
                p->size,
                p->expected,
                p->roundsize,
                (p->offset == p->expected) ? "GOOD" : "BAD "
               );
        p++;
        debugBase::dumpShm(pool, 0, NULL);
        fflush(debugBase::fp());
    }

    p = tArray;
    i = rand() % (int)((sizeof(tArray) / sizeof(testShm_t)));
    for (; i < (int)(sizeof(tArray) / sizeof(testShm_t));)
    {
        if (i & 0x1)
        {
            fprintf(debugBase::fp(), "\nFREE TEST %d [%8X %8X] \n",
                    i, p->offset, p->roundsize);
            pool->release2(p->offset, p->size);
            debugBase::dumpShm(pool, 0, NULL);
            fflush(debugBase::fp());
        }
        p++;
        i++;
    }

    p = tArray;

    i = rand() % (int)((sizeof(tArray) / sizeof(testShm_t)));
    for (; i < (int)(sizeof(tArray) / sizeof(testShm_t));)
    {
        if (!(i & 0x1))
        {
            fprintf(debugBase::fp(), "\nFREE TEST %d [%8X %8X] \n",
                    i, p->offset, p->roundsize);
            pool->release2(p->offset, p->size);
            debugBase::dumpShm(pool, 0, NULL);
            fflush(debugBase::fp());
        }
        p++;
        i++;
    }

    fflush(debugBase::fp());
}

testShm_t   dArray[] =
{
    /* offset size expected roundsize */
    {0,  0x0001,  0x0400, 0},
    {0,  0x0002,  0x0408, 0},
    {0,  0x0003,  0x0410, 0},
    {0,  0x0004,  0x0418, 0},
    {0,  0x0005,  0x0420, 0},
    {0,  0x0006,  0x0428, 0},
    {0,  0x0007,  0x0430, 0},
    {0,  0x0008,  0x0438, 0},

    {0,  0x0009,  0x0440, 0},
    {0,  0x000a,  0x0450, 0},
    {0,  0x000b,  0x0460, 0},
    {0,  0x000c,  0x0470, 0},
    {0,  0x000d,  0x0480, 0},
    {0,  0x000e,  0x0490, 0},
    {0,  0x000f,  0x04a0, 0},
    {0,  0x0010,  0x04b0, 0},

    {0,  0x0011,  0x04c0, 0},
    {0,  0x0012,  0x04d8, 0},
    {0,  0x0013,  0x04f0, 0},
    {0,  0x0014,  0x0508, 0},
    {0,  0x0015,  0x0520, 0},
    {0,  0x0016,  0x0538, 0},
    {0,  0x0017,  0x0550, 0},
    {0,  0x0018,  0x0568, 0},

    {0,  0x0019,  0x0580, 0},
    {0,  0x001a,  0x05a0, 0},
    {0,  0x001b,  0x05c0, 0},
    {0,  0x001c,  0x05e0, 0},
    {0,  0x001d,  0x0600, 0},
    {0,  0x001e,  0x0620, 0},
    {0,  0x001f,  0x0640, 0},
    {0,  0x0020,  0x0660, 0}
};

//
//  LiteSpeed SHM small memory tester!
//
void    testShmPool(LsShm *shm)
{
    if (shm->status() != LSSHM_READY)
    {
        fprintf(debugBase::fp(), "LsShm %p NOTREADY %d\n",
                shm, shm->status());
        return;
    }

    LsShmPool   *pool = LsShmPool::open(shm, LSI_SHM_POOL_NAME);
    if (pool->status() != LSSHM_READY)
    {
        fprintf(debugBase::fp(), "LsShmPool %p NOTREADY %d\n",
                shm, shm->status());
        return;
    }

    debugBase::dumpShm(pool, 0, NULL);
    debugBase::dumpShmPool(pool, 0, NULL);
    fflush(debugBase::fp());

    testPoolAlloc(pool, dArray, sizeof(dArray) / sizeof(testShm_t), 0);
}

//
//  testing the raw interface
//
int    genericTest()
{
    LsShm *p;
    const char *mapName = LSI_SHM_MAP_NAME;

    HttpLog::log(LSI_LOG_NOTICE, "Generic RAW LiterSpeed SHM TESTER\r\n");

    p = LsShm::open(mapName, LS_SHMSIZE);

    if (debugBase::checkStatus(mapName, mapName, p->status()))
        return LS_FAIL;

    LsShmPool *sysPool;
    sysPool = LsShmPool::open(p, LSSHM_SYSPOOL);

    if (debugBase::checkStatus(LSSHM_SYSPOOL, LSSHM_SYSPOOL,
                               sysPool->status()))
        return LS_FAIL;

#if 0
    // testShmAlloc(p);
    testShmPool(p);
    fflush(debugBase::fp());

    testShmReg(p);
    fflush(debugBase::fp());
#endif

    testShmHash(p, sysPool);
    fflush(debugBase::fp());

#if 0
    fprintf(debugBase::fp(), "===============  REG  ==========\n");
    debugBase::dumpShmReg(p);
    fprintf(debugBase::fp(), "================================\n");
    fflush(debugBase::fp());
#endif
    return 0;
}

//
//
//
int    testShm()
{
    debugBase::setup();
    HttpLog::log(LSI_LOG_NOTICE, "testShm START SIMPLE SHM TEST\r\n");
    HttpLog::log(LSI_LOG_NOTICE,  "PAGESIZE: %x\r\n", ::getpagesize());

#if 0
    if (genericTest())
        abort();
#endif

    //
    //  Api testing
    //
    if (testShmApi())
        abort();
    else
    {
        HttpLog::log(LSI_LOG_NOTICE, "testShm SIMPLE TEST DONE\r\nBye\r\n");
        return 0;
    }
}

