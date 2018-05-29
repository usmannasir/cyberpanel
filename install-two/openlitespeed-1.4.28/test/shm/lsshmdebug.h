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
#ifndef LSSHMDEBUG_H

#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <shm/lsshmtypes.h>
#include <shm/lsshm.h>
#include <shm/lsshmpool.h>
#include <shm/lsshmhash.h>

#define LSI_SHM_DEBUGFILE    "/dev/shm/LiteSpeed/simon.debug"
#define LSI_SHM_MAP_FILENAME "/dev/shm/LiteSpeed/ls_0.shm"
#define LSI_SHM_MAP_NAME     "dumbo"
#define LSI_SHM_POOL_NAME    "shmpool"
#define LSI_SHM_HASH_NAME    "shmhash"

class debugBase
{
    static FILE *m_fp;
    static char *m_outfile;

    static void dumpFreeBlock(LsShm *pShm, LsShmOffset_t offset);
    static void dumpMapFreeList(LsShm *pShm);
    static void dumpMapCheckFree(LsShm *pShm);
    static void dumpMapHeader(LsShm *pShm);
    static void dumpHeader(LsShm *pShm);

    static void dumpPoolDataCheck(LsShmPool *pool);
    static void dumpPoolDataFreeList(LsShmPool *pool);
    static void dumpPoolDataFreeBucket(LsShmPool *pool);
    static void dumpPoolPage(LsShmPool *pool);
    static void dumpPoolData(LsShmPool *pool);
    static void dumpPoolHeader(LsShmPool *pool);

public:
    static void dumpShmReg(LsShm *pShm);

    static FILE *fp() { return m_fp; };
    static void setup(const char *filename = LSI_SHM_DEBUGFILE);
    static void done();
    static void dumpShm(LsShmPool *pool, int mode, void *udata);

    inline static LsShmSize_t roundPageSize(LsShmPool *pool, LsShmSize_t size)
    { return pool->roundPageSize(size); };
    inline static LsShmSize_t roundDataSize(LsShmPool *pool, LsShmSize_t size)
    { return pool->roundDataSize(size); };
    static LsShm *pool2shm(LsShmPool *pool)
    { return pool->m_pShm ; }

    static void dumpShmPool(LsShmPool *pool, int mode, void *udata);

    static int checkStatus(const char *tag, const char *mapName,
                           LsShmStatus_t status);
    static void dumpRegistry(const char *tag, const LsShmReg *p_reg);

    static const char *decode(const char *p, int len);
    static void dumpBuf(const char *tag, const char *buf, int size);
    static void dumpIter(const char *tag, LsShmHash::iterator iter);
    static void dumpIterKey(LsShmHash::iterator iter);
    static void dumpIterValue(LsShmHash::iterator iter);

};

#endif

