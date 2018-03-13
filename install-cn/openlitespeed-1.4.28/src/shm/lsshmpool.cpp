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
#include <shm/lsshmpool.h>

#include <shm/lsshmhash.h>

#include <log4cxx/logger.h>

#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int s_pid = -1;

//
// Internal for free link
//
#define LSSHM_FREE_AMARKER 0x0123fedc
#define LSSHM_FREE_BMARKER 0xba984567

//
//  Two block to indicate a free block
//
struct ls_shmfreetop_s
{
    LsShmSize_t      x_iAMarker;
    LsShmSize_t      x_iFreeSize;           // size of the freeblock
    LsShmOffset_t    x_iFreeNext;
    LsShmOffset_t    x_iFreePrev;
};


struct ls_shmfreebot_s
{
    LsShmOffset_t    x_iFreeOffset;         // back to the begin
    LsShmSize_t      x_iBMarker;
};


// runtime free memory for the pool
struct ls_shmmapchunk_s
{
    LsShmOffset_t  x_iStart;
    LsShmOffset_t  x_iEnd;
};


struct ls_shmfreelist_s
{
    LsShmOffset_t  x_iNext;
    LsShmOffset_t  x_iPrev;
    LsShmSize_t    x_iSize;
};


struct ls_shmpoolmap_s
{
    ShmMapChunk     x_chunk;            // unused after alloc2
    LsShmOffset_t   x_iFreeList;        // the big free list
    LsShmOffset_t   x_iFreePageList;
    LsShmOffset_t   x_aFreeBucket[LSSHM_POOL_NUMBUCKET];
    LsShmPoolMapStat    x_stat;         // map statistics
};


struct ls_shmpoolmem_s
{
    uint32_t        x_iMagic;
    uint8_t         x_aName[LSSHM_MAXNAMELEN];
    LsShmSize_t     x_iSize;
    LsShmPoolMap    x_data;
    LsShmOffset_t   x_iLockOffset;
    pid_t           x_pid;
};


inline LsShmPoolMap *LsShmPool::getDataMap() const
{   return (LsShmPoolMap *)&(getPool()->x_data);    }


LsShmOffset_t LsShmPool::getPoolMapStatOffset() const
{ return (LsShmOffset_t)(long) & ((LsShmPoolMem *)(long)m_iOffset)->x_data.x_stat; }


inline  void LsShmPool::incrCheck(LsShmXSize_t *ptr, LsShmSize_t size)
{
    assert(ptr != NULL);
    LsShmSize_t prev = *ptr;
    *ptr += size;
    if (*ptr < prev)    // cnt wrapped
        *ptr = (LsShmSize_t) - 1;
    return;
}


LsShmStatus_t LsShmPool::createStaticData(const char *name)
{
    LsShmPoolMem *pPool = getPool();

    pPool->x_iMagic = LSSHM_POOL_MAGIC;
    strncpy((char *)pPool->x_aName, name, LSSHM_MAXNAMELEN);
    pPool->x_iSize = sizeof(LsShmPoolMem);

    pPool->x_iLockOffset = 0;
    pPool->x_pid = (m_pParent ? getpid() : 0); // only if using global pool

    // Data
    LsShmPoolMap *pDataMap = &pPool->x_data;
    pDataMap->x_chunk.x_iStart = 0;
    pDataMap->x_chunk.x_iEnd = 0;
    pDataMap->x_iFreeList = 0;
    pDataMap->x_iFreePageList = 0;
    ::memset(pDataMap->x_aFreeBucket, 0, sizeof(pDataMap->x_aFreeBucket));
    ::memset(&pDataMap->x_stat, 0, sizeof(LsShmPoolMapStat));

    return LSSHM_OK;
}


LsShmStatus_t LsShmPool::checkStaticData(const char *name)
{
    // check the file
    LsShmPoolMem *pPool = getPool();
    return ((pPool->x_iMagic == LSSHM_POOL_MAGIC)
            && (pPool->x_iSize == sizeof(LsShmPoolMem))
            && (strncmp((char *)pPool->x_aName, name, LSSHM_MAXNAMELEN) == 0)) ?
           LSSHM_OK : LSSHM_BADMAPFILE;
}


LsShmPool::LsShmPool()
    : m_iMagic(LSSHM_POOL_MAGIC)
    , m_pShm(NULL)
    , m_status(LSSHM_NOTREADY)
    , m_iOffset(0)
    , x_pPool(NULL)
    , m_pShmLock(NULL)
    , m_iAutoLock(1)
    , m_iShmOwner(0)
    , m_iRegNum(0)
    , m_pParent(NULL)
    , m_iRef(0)
{
}


int LsShmPool::init(LsShm *shm, const char *name, LsShmPool *gpool)
{
    LsShmOffset_t extraOffset = 0;
    LsShmSize_t extraSize = 0;


    if ((name == NULL) || (*name == '\0'))
    {
        m_status = LSSHM_BADPARAM;
        return LS_FAIL;
    }

    m_pShm = shm;
    m_pParent = gpool;
    obj.m_pName = NULL;


    if (strcmp(name, LSSHM_SYSPOOL) == 0)
    {
        m_iOffset = shm->xdataOffset();   // the system pool
    }
    else
    {
        if ((obj.m_pName = strdup(name)) == NULL)
        {
            m_status = LSSHM_ERROR;
            return LS_FAIL;
        }
        LsShmReg *p_reg;
        if ((p_reg = shm->findReg(name)) == NULL)
        {
            if ((p_reg = shm->addReg(name)) == NULL)
            {
                m_status = LSSHM_BADMAPFILE;
                return LS_FAIL;
            }
            if (m_pParent != NULL)
                p_reg->x_iFlag |= LSSHM_REGFLAG_PID;    // mark per process pool

            m_iRegNum = p_reg->x_iRegNum;
            p_reg->x_iValue = 0;    // not inited yet!
        }
        if ((m_iOffset = p_reg->x_iValue) == 0)
        {
            // create memory for new Pool
            // allocate header from SYS POOL
            LsShmOffset_t offset;
            int remapped;
            int rndPoolMemSz = roundDataSize(sizeof(LsShmPoolMem));
            offset = allocPage(LSSHM_SHM_UNITSIZE, remapped);
            if (offset == 0)
            {
                m_status = LSSHM_BADMAPFILE;
                return LS_FAIL;
            }
            ::memset(offset2ptr(offset), 0, rndPoolMemSz);
            m_iOffset = offset;
            p_reg->x_iValue = m_iOffset;

            extraOffset = offset + rndPoolMemSz;
            extraSize = LSSHM_SHM_UNITSIZE - rndPoolMemSz;
        }
    }
    x_pPool = (LsShmPoolMem *)offset2ptr(m_iOffset);

    if (getPool()->x_iSize != 0)
    {
        if ((m_status = checkStaticData(name)) != LSSHM_OK)
        {
            LsShm::setErrMsg(LSSHM_BADVERSION,
                             "Invalid SHM Pool [%s], magic=%08X(%08X), MapFile [%s].",
                             name, getPool()->x_iMagic, LSSHM_POOL_MAGIC, shm->fileName());
            return LS_FAIL;
        }
    }
    else
    {
        m_status = createStaticData(name);
        // NOTE release extra to freeList
        if ((extraOffset != 0) && (extraSize > LSSHM_POOL_MAXBCKTSIZE))
            releaseData(extraOffset, extraSize);
    }
    mapLock();

    if (m_status == LSSHM_OK)
    {
        m_status = LSSHM_READY;
        m_iRef = 1;
        if (obj.m_pName != NULL)
        {
#ifdef DEBUG_RUN
            SHM_NOTICE("LsShmPool::LsShmPool insert %s <%p>",
                       obj.m_pName, &m_objBase);
#endif
            m_pShm->getObjBase().insert(obj.m_pName, &this->obj);
        }
    }
    return LS_OK;
}


LsShmPool::~LsShmPool()
{
    if (m_pParent != NULL)
        destroy();
    if (obj.m_pName != NULL)
    {
#ifdef DEBUG_RUN
        SHM_NOTICE("LsShmPool::~LsShmPool remove %s <%p>",
                   obj.m_pName, &m_objBase);
#endif
        m_pShm->getObjBase().remove(obj.m_pName);
        ::free(obj.m_pName);
        obj.m_pName = NULL;
    }
}


LsShmOffset_t LsShmPool::getReg(const char *name)
{
    if (name == NULL)
        return 0;

    LsShmOffset_t offReg = m_pShm->findRegOff(name);
    if (offReg == 0)
    {
        if ((offReg = m_pShm->addRegOff(name)) == 0)
        {
            m_status = LSSHM_BADMAPFILE;
            return 0;
        }
    }
    return offReg;
}


LsShmHash *LsShmPool::getNamedHash(const char *name,
                                   LsShmSize_t init_size, LsShmHasher_fn hf,
                                   LsShmValComp_fn vc, int iFlags)
{
    LsShmHash *pObj;
    GHash::iterator itor;

    if (name == NULL)
        name = LSSHM_SYSHASH;

#ifdef DEBUG_RUN
    SHM_NOTICE("LsShmPool::getNamedHash find %s <%p>",
               name, &getObjBase());
#endif
    itor = getObjBase().find(name);
    if ((itor != NULL)
        && ((pObj = LsShmHash::checkHTable(itor, this, name, hf,
                                           vc)) != (LsShmHash *)-1))
        return pObj;

    LsShmOffset_t offReg = getReg(name);
    if (offReg == 0)
        return NULL;
    LsShmReg * pReg = (LsShmReg *)offset2ptr(offReg);
    if (!pReg)
        return NULL;

    if (pReg->x_iValue == 0)
    {
        LsShmOffset_t offset = allocateNewHash( init_size, hf != NULL, iFlags);
        if (offset != 0)
        {
            pReg = (LsShmReg *)offset2ptr(offReg);
            pReg->x_iValue = offset;
        }
    }
    if (!pReg->x_iValue)
        return NULL;

    return newHashByOffset(pReg->x_iValue, name, hf, vc, iFlags);
}


LsShmHash * LsShmPool::newHashByOffset(LsShmOffset_t offset,
                  const char *name, LsShmHasher_fn hf,
                  LsShmValComp_fn vc, int iFlags)
{
    LsShmHash *pObj;
//     if (iFlags & LSSHM_FLAG_LRU_MODE2)
//         pObj = new LsShmWLruHash(this, name, hf, vc);
//     else if (iFlags & LSSHM_FLAG_LRU_MODE3)
//         pObj = new LsShmXLruHash(this, name, hf, vc);
//     else
    pObj = new LsShmHash(this, name, hf, vc, iFlags);
    if ( pObj->init(offset) == LS_FAIL)
    {
        delete pObj;
        pObj = NULL;
    }
    else
        getObjBase().insert(pObj->name(), &pObj->obj);

    return pObj;
}


LsShmOffset_t LsShmPool::allocateNewHash(int init_size, int iMode, int iFlags)
{
    // Create new HASH Table
    ls_shmlock_t *pShmLock;
    LsShmOffset_t lockOffset = lockPool()->allocLock();
    if ((lockOffset == 0) 
        || (pShmLock = lockPool()->offset2pLock(lockOffset)) == NULL
        || (ls_shmlock_setup(pShmLock) != 0))
    {
        return 0;
    }

    // NOTE: system is not up yet... ignore remap here
    LsShmOffset_t offset =
            LsShmHash::allocHTable(this, init_size, iMode, iFlags,
                                   lockOffset);
    if (offset == 0)
    {
        lockPool()->freeLock(pShmLock);
    }
    return offset;
}


void LsShmPool::close()
{
    LsShm *p = NULL;
    if (m_iShmOwner != 0)
    {
        m_iShmOwner = 0;
        p = m_pShm; // delayed remove
    }
    if ((obj.m_pName != NULL) && (downRef() == 0))
        delete this;
    if (p != NULL)
        p->close();
}


void LsShmPool::destroy()
{
    if (m_iOffset == 0)
        return;

    int8_t owner;
    if (m_pParent != NULL)
        owner = 0;
    else
    {
        if ((m_pParent = m_pShm->getGlobalPool()) == NULL)
            return;
        owner = 1;
    }
    LsShmSize_t left;
    LsShmPoolMap *pDataMap = getDataMap();
    if ((left = pDataMap->x_chunk.x_iEnd - pDataMap->x_chunk.x_iStart) > 0)
        release2(pDataMap->x_chunk.x_iStart, left);
    mvFreeBucket();
    mvFreeList();
    if (obj.m_pName != NULL)
        m_pShm->delReg(obj.m_pName);
    m_pShm->freeLock(m_pShmLock);
    m_pParent->release2(m_iOffset, roundDataSize(sizeof(LsShmPoolMem)));
    m_iOffset = m_pParent->m_iOffset;   // let parent/global take over
    m_pShmLock = m_pShm->offset2pLock(getPool()->x_iLockOffset);
    m_iAutoLock = m_pParent->m_iAutoLock;
    if (owner != 0)
        m_pParent->close();
    m_pParent = NULL;
}


LsShmOffset_t LsShmPool::alloc2(LsShmSize_t size, int &remapped)
{
    LsShmOffset_t offset;

    if ((size == 0) || (size&0x80000000) || (size>LSSHM_MAXSIZE)) 
        return 0;

    remapped = 0;
    size = roundDataSize(size);
    autoLock();
    if (size >= LSSHM_SHM_UNITSIZE)
    {
        if ((offset = allocPage(size, remapped)) != 0)
        {
            incrCheck(&getDataMap()->x_stat.m_iPgAllocated, roundSize2pages(size));
        }
    }
    else
    {
        if (size >= LSSHM_POOL_MAXBCKTSIZE)
            // allocate from FreeList
            offset = allocFromDataFreeList(size);
        else
            // allocate from bucket
            offset = allocFromDataBucket(size);
        if (offset != 0)
            getDataMap()->x_stat.m_iPoolInUse += size;
    }
    autoUnlock();

    return offset;
}


void LsShmPool::addLeftOverPages(LsShmOffset_t offset, LsShmSize_t size)
{
    releasePageLocked(offset, size);
    incrCheck(&getDataMap()->x_stat.m_iGpAllocated,
            (size / LSSHM_SHM_UNITSIZE));
}


void LsShmPool::release2(LsShmOffset_t offset, LsShmSize_t size)
{
    size = roundDataSize(size);
    if (size >= LSSHM_SHM_UNITSIZE)
    {
        LsShmPool *pPagePool = ((m_pParent != NULL) ? m_pParent : this);
        pPagePool->autoLock();
        pPagePool->releasePageLocked(offset, size);
        if (m_pParent)
        {
            pPagePool->autoUnlock();
            autoLock();
        }
        incrCheck(&getDataMap()->x_stat.m_iPgReleased, roundSize2pages(size));
        autoUnlock();
    }
    else
    {
        autoLock();
        releaseData(offset, size);
        getDataMap()->x_stat.m_iPoolInUse -= size;
        autoUnlock();
    }
}


void LsShmPool::mvFreeList()
{
    if (m_pParent != NULL)
    {
        autoLock();
        m_pParent->addFreeList(getDataMap());
        autoUnlock();
    }
    return;
}


void LsShmPool::addFreeList(LsShmPoolMap *pSrcMap)
{
    LsShmOffset_t listOffset;
    if ((listOffset = pSrcMap->x_iFreeList) != 0)
    {
        autoLock();
        LsShmFreeList *pFree;
        LsShmFreeList *pFreeList;
        LsShmOffset_t freeOffset;
        if ((freeOffset = getDataMap()->x_iFreeList) != 0)
        {
            pFreeList = (LsShmFreeList *)offset2ptr(freeOffset);
            LsShmOffset_t next = listOffset;
            LsShmOffset_t last;
            do
            {
                last = next;
                pFree = (LsShmFreeList *)offset2ptr(last);
                next = pFree->x_iNext;
            }
            while (next != 0);
            pFree->x_iNext = freeOffset;
            pFreeList->x_iPrev = last;
        }
        LsShmSize_t cnt = pSrcMap->x_stat.m_iFlReleased
                          - pSrcMap->x_stat.m_iFlAllocated;
        getDataMap()->x_iFreeList = listOffset;
        incrCheck(&getDataMap()->x_stat.m_iFlReleased, cnt);
        getDataMap()->x_stat.m_iFlCnt += pSrcMap->x_stat.m_iFlCnt;
        autoUnlock();
        pSrcMap->x_iFreeList = 0;
        incrCheck(&pSrcMap->x_stat.m_iFlAllocated, cnt);
        pSrcMap->x_stat.m_iFlCnt = 0;
    }
    return;
}


void LsShmPool::mvFreeBucket()
{
    if (m_pParent != NULL)
    {
        autoLock();
        m_pParent->addFreeBucket(getDataMap());
        autoUnlock();
    }
    return;
}


void LsShmPool::addFreeBucket(LsShmPoolMap *pSrcMap)
{
    int num = 1;     // skip zero slot
    LsShmOffset_t *pSrc = &pSrcMap->x_aFreeBucket[1];
    LsShmOffset_t *pDst = &getDataMap()->x_aFreeBucket[1];
    autoLock();
    while (num < LSSHM_POOL_NUMBUCKET)
    {
        LsShmOffset_t bcktOffset;
        if ((bcktOffset = *pSrc) != 0)
        {
            LsShmOffset_t freeOffset;
            LsShmOffset_t *pFree;
            if ((freeOffset = *pDst) != 0)
            {
                LsShmOffset_t next = bcktOffset;
                do
                {
                    pFree = (LsShmOffset_t *)offset2ptr(next);
                }
                while ((next = *pFree) != 0);
                *pFree = freeOffset;
            }
            *pDst = bcktOffset;
            *pSrc = 0;
            LsShmSize_t cnt = pSrcMap->x_stat.m_bckt[num].m_iBkReleased
                              - pSrcMap->x_stat.m_bckt[num].m_iBkAllocated;
            incrCheck(&pSrcMap->x_stat.m_bckt[num].m_iBkAllocated, cnt);
            incrCheck(&getDataMap()->x_stat.m_bckt[num].m_iBkReleased, cnt);
        }
        ++pSrc;
        ++pDst;
        ++num;
    }
    autoUnlock();
    return;
}

static unsigned int s_debug_free_bucket = 0;


//
// Internal release2
//
void LsShmPool::releaseData(LsShmOffset_t offset, LsShmSize_t size)
{
    LsShmPoolMap *pDataMap = getDataMap();
    if (size >= LSSHM_POOL_MAXBCKTSIZE)
    {
        // release to FreeList
        LsShmFreeList *pFree;
        LsShmFreeList *pFreeList;
        LsShmOffset_t freeOffset;

        // setup FreeList block
        pFree = (LsShmFreeList *)offset2ptr(offset);
        pFree->x_iSize = size;

        if ((freeOffset = pDataMap->x_iFreeList) != 0)
        {
            pFreeList = (LsShmFreeList *)offset2ptr(freeOffset);
            pFree->x_iNext = freeOffset;
            pFree->x_iPrev = 0;
            pFreeList->x_iPrev = offset;
        }
        else
        {
            pFree->x_iNext = 0;
            pFree->x_iPrev = 0;
        }
        pDataMap->x_iFreeList = offset;
        incrCheck(&pDataMap->x_stat.m_iFlReleased, size);
        ++pDataMap->x_stat.m_iFlCnt;
    }
    else
    {
        // release to DataBucket
        LsShmSize_t bucketNum = dataSize2Bucket(size);
        LsShmOffset_t *pBucket;
        LsShmOffset_t *pData;

        pData = (LsShmOffset_t *)offset2ptr(offset);
        pBucket = &pDataMap->x_aFreeBucket[bucketNum];
        assert(m_pShm->isOffsetValid(offset));
        if (s_debug_free_bucket == bucketNum)
            LS_LOGRAW("[DEBUG] [SHM] [%d-%d:%p] release to freebucket, "
                      "offset: %d, size: %d, next: %d\n",
                      s_pid, m_pShm->getfd(), this, offset, size, *pBucket);
        if (!m_pShm->isOffsetValid(*pBucket))
        {    
            LS_ERROR("[SHM] [%d-%d:%p] freebucket corruption, "
                     "offset: %d, bucket: %d\n", s_pid, m_pShm->getfd(), 
                     this, *pBucket, bucketNum);
            *pData = 0;
        }
        else
            *pData = *pBucket;
        *pBucket = offset;
        incrCheck(&pDataMap->x_stat.m_bckt[bucketNum].m_iBkReleased, 1);
    }
}


//
// @brief map the lock into Object space
//
void LsShmPool::mapLock()
{
    LsShmPoolMem *pPool = getPool();
    if (pPool->x_iLockOffset == 0)
    {
        pPool->x_iLockOffset = m_pShm->allocLock();
        if ( pPool->x_iLockOffset == 0)
        {
            m_status = LSSHM_ERROR;
            return;
        }
        m_pShmLock = m_pShm->offset2pLock(pPool->x_iLockOffset);
        ls_shmlock_setup(m_pShmLock);

    }
    else
        m_pShmLock = m_pShm->offset2pLock(pPool->x_iLockOffset);
    //BUG: reset lock for existing lock, could be locked by another process.
    //setupLock();
}


//
//  @brief allocFromDataFreeList - only for size >= LSSHM_POOL_MAXBCKTSIZE
//  @brief linear search the FreeList for it.
//  @brief if no match from FreeList then allocate from data.x_chunk
//
LsShmOffset_t LsShmPool::allocFromDataFreeList(LsShmSize_t size)
{
    LsShmOffset_t offset;
    LsShmFreeList *pFree;
    int left;
    offset = getDataMap()->x_iFreeList;
    while (offset != 0)
    {
        pFree = (LsShmFreeList *)offset2ptr(offset);
        if ((left = (int)(pFree->x_iSize - size)) >= 0)
        {
            pFree->x_iSize = (LsShmSize_t)left;
            incrCheck(&getDataMap()->x_stat.m_iFlAllocated, size);
            if ((LsShmSize_t)left < LSSHM_POOL_MAXBCKTSIZE)
                mvDataFreeListToBucket(pFree, offset);
            return offset + left;
        }
        offset = pFree->x_iNext;
    }
    LsShmSize_t num = 1;
    if ((offset = allocFromDataChunk(size, num)) != 0)
    {
        incrCheck(&getDataMap()->x_stat.m_iFlReleased, size);
        incrCheck(&getDataMap()->x_stat.m_iFlAllocated, size);
    }
    return offset;
}


LsShmOffset_t LsShmPool::allocFromDataBucket(LsShmSize_t size)
{
    LsShmOffset_t offset;
    LsShmOffset_t *np, *pBucket;

    LsShmSize_t num = dataSize2Bucket(size);
    pBucket = &getDataMap()->x_aFreeBucket[num];
    if ((offset = *pBucket) != 0)
    {
        np = (LsShmOffset_t *)offset2ptr(offset);
        if (!m_pShm->isOffsetValid(*np))
        {
            LS_ERROR("[SHM] [%d-%d:%p] pool free bucket [%d] corruption, at "
                     "offset: %d, invalid value: %d, usage: alloc %d, free %d\n",
                     s_pid, m_pShm->getfd(), this, num, offset, *np, 
                     getDataMap()->x_stat.m_bckt[num].m_iBkAllocated,
                     getDataMap()->x_stat.m_bckt[num].m_iBkReleased );
            *pBucket = (LsShmOffset_t)0;
        }
        else
            *pBucket = *np;
    }
    else 
    {
        if (s_debug_free_bucket == num)
            LS_LOGRAW("[DEBUG] [SHM] [%d-%d:%p] freebucket %d is empty for size: %d\n", 
                    s_pid, m_pShm->getfd(), this, num, size);
        if ((offset = fillDataBucket(num, size)) == 0)
            return 0;
        }
    incrCheck(&getDataMap()->x_stat.m_bckt[num].m_iBkAllocated, 1);
    if (s_debug_free_bucket == num)
        LS_LOGRAW("[DEBUG] [SHM] [%d-%d:%p] allocate from freebucket, "
                  "offset: %d, size: %d, next: %d\n", 
                  s_pid, m_pShm->getfd(), this, offset, size, getDataMap()->x_aFreeBucket[num]);
    return offset;
}


LsShmOffset_t LsShmPool::allocFromGlobalBucket(
    LsShmSize_t bucketNum, LsShmSize_t &num)
{
    LsShmOffset_t first;
    LsShmOffset_t next;
    LsShmOffset_t *np;

    if (getDataMap()->x_aFreeBucket[bucketNum] == 0)
        return 0;

    LsShmSize_t cnt = 0;
    autoLock();
    np = &getDataMap()->x_aFreeBucket[bucketNum];
    next = first = *np;
    while (next != 0)
    {
        assert(m_pShm->isOffsetValid(next));
        np = (LsShmOffset_t *)offset2ptr(next);
        next = *np;
        if (++cnt >= num)
            break;
    }
    getDataMap()->x_aFreeBucket[bucketNum] = next;
    *np = 0;
    incrCheck(&getDataMap()->x_stat.m_bckt[bucketNum].m_iBkAllocated, cnt);
    autoUnlock();
    num = cnt;
    return first;
}


//
// @brief fillDataBucket allocates memory from a Global pool else Chunk storage.
// @brief This may cause a remap; only use offset...
// @brief bucketNum and size should be logically connected.
// @brief passing both to avoid an extra calulation.
// @brief freeBucket[bucketNum] will be set to the new allocated pool.
// @brief return the offset of the newly allocated memory.
//
LsShmOffset_t LsShmPool::fillDataBucket(LsShmSize_t bucketNum, LsShmSize_t size)
{
    LsShmSize_t num;
    // allocated according to data size
    num = (LSSHM_POOL_MAXBCKTSIZE << 2) / size;
    if (num > LSSHM_MAX_BUCKET_SLOT)
        num = LSSHM_MAX_BUCKET_SLOT;

    LsShmOffset_t xoffset, offset;
    if ((m_pParent != NULL)
        && ((offset = m_pParent->allocFromGlobalBucket(bucketNum, num)) != 0))
    {
        if (num > 1)
        {
            xoffset = *((LsShmOffset_t *)m_pShm->offset2ptr(offset));
            assert(m_pShm->isOffsetValid(xoffset));
            getDataMap()->x_aFreeBucket[bucketNum] = xoffset;
            if (s_debug_free_bucket == bucketNum)
                LS_LOGRAW("[DEBUG] [SHM] [%d-%d:%p] allocFromGlobalBucket(), %d objects, "
                          "first offset: %d, second offset: %d\n", s_pid,
                          m_pShm->getfd(), this, num, offset, xoffset);

        }
        incrCheck(&getDataMap()->x_stat.m_bckt[bucketNum].m_iBkReleased, num);
        return offset;
    }
    xoffset = offset = allocFromDataChunk(size, num);   // might remap
    if (num == 0)
        return offset;  // big problem, no more memory
    incrCheck(&getDataMap()->x_stat.m_bckt[bucketNum].m_iBkReleased, num);

    // take the first one - save the rest
    xoffset += size;
    if (s_debug_free_bucket == bucketNum)
        LS_LOGRAW("[DEBUG] [SHM] [%d-%d:%p] allocFromDataChunk(), %d objects, "
                  "first offset: %d, push offset: %d\n", s_pid, m_pShm->getfd(),
                  this, num, offset, xoffset);
    if (--num != 0)
    {
        assert(m_pShm->isOffsetValid(xoffset));
        getDataMap()->x_aFreeBucket[bucketNum] = xoffset;
    }
    uint8_t *xp;
    xp = (uint8_t *)offset2ptr(offset);
    while (num-- != 0)
    {
        xp += size;
        xoffset += size;
        assert(m_pShm->isOffsetValid(xoffset));
        *((LsShmOffset_t *)xp) = num ? xoffset : 0;
        if (s_debug_free_bucket == bucketNum)
            LS_LOGRAW("[DEBUG] [SHM] [%d-%d:%p] allocFromDataChunk(), append #%d offset: %d, \n",
                      s_pid, m_pShm->getfd(), this, num , *((LsShmOffset_t *)xp));
        }
    return offset;
}


//
// @brief allocFromDataChunk
// @brief num suggested the number of buckets to allocate.
//
// @brief could reduce the number if it is too many,
//  currently it set max to 0x20 regardless.
// @brief fill the bucket will all available space.
// @brief return offset and num of buckets.
// @brief could cause remap.
// @brief always check return num and offset.
//
LsShmOffset_t LsShmPool::allocFromDataChunk(LsShmSize_t size,
        LsShmSize_t &num)
{
    LsShmOffset_t offset;
    LsShmSize_t numAvail;
    LsShmSize_t avail;
    LsShmPoolMap *pDataMap = getDataMap();

    avail = pDataMap->x_chunk.x_iEnd - pDataMap->x_chunk.x_iStart;
    numAvail = avail / size;
    if (numAvail)
    {
        if (numAvail < num) // shrink the num
            num = numAvail;
        size *= num;
        offset = pDataMap->x_chunk.x_iStart;
        pDataMap->x_chunk.x_iStart += size;
        pDataMap->x_stat.m_iFreeChunk -= size;
        return offset;
    }

    LsShmOffset_t releaseOffset;
    LsShmSize_t releaseSize;
    if (avail != 0)
    {
        offset = pDataMap->x_chunk.x_iStart;
        pDataMap->x_chunk.x_iStart += avail;
        // release all Chunk memory
        // releaseData(offset, avail);
        releaseOffset = offset;
        releaseSize = avail;
    }
    else
    {
        releaseOffset = 0;
        releaseSize = 0;
    }

    // figure pagesize needed - round to SHM page unit to avoid waste
    LsShmSize_t needed = roundPageSize(size * num);
    if (needed < LSSHM_SHM_UNITSIZE)
        needed = LSSHM_SHM_UNITSIZE;

    int remapped = 0;
    if ((offset = allocPage(needed, remapped)) == 0)
    {
        num = 0;
        return 0;
    }
    if (remapped != 0)
        pDataMap = getDataMap();
    pDataMap->x_stat.m_iFreeChunk += needed;

    if (releaseOffset != 0)
    {
        // merging leftover and newly allocated memory
        if (releaseOffset + releaseSize == offset)
        {
            offset = releaseOffset;
            needed += releaseSize;
        }
        else
        {
            releaseData(releaseOffset, releaseSize);
            pDataMap->x_stat.m_iFreeChunk -= releaseSize;
        }
    }
    pDataMap->x_chunk.x_iStart = offset;
    pDataMap->x_chunk.x_iEnd = offset + needed;
    return allocFromDataChunk(size, num);
}


void LsShmPool::mvDataFreeListToBucket(LsShmFreeList *pFree,
                                       LsShmOffset_t offset)
{
    rmFromDataFreeList(pFree);
    if (pFree->x_iSize > 0)
    {
        incrCheck(&getDataMap()->x_stat.m_iFlAllocated, pFree->x_iSize);
        LsShmSize_t bucketNum = dataSize2Bucket(pFree->x_iSize);
        LsShmOffset_t *np;
        np = (LsShmOffset_t *)pFree; // cast to offset
        *np = getDataMap()->x_aFreeBucket[bucketNum];
        
        assert(m_pShm->isOffsetValid(offset));
        getDataMap()->x_aFreeBucket[bucketNum] = offset;
        incrCheck(&getDataMap()->x_stat.m_bckt[bucketNum].m_iBkReleased, 1);
    }
}


void LsShmPool::rmFromDataFreeList(LsShmFreeList *pFree)
{
    LsShmFreeList *xp;
    if (pFree->x_iPrev == 0)
        getDataMap()->x_iFreeList = pFree->x_iNext;
    else
    {
        xp = (LsShmFreeList *) offset2ptr(pFree->x_iPrev);
        xp->x_iNext = pFree->x_iNext;
    }
    if (pFree->x_iNext != 0)
    {
        xp = (LsShmFreeList *)offset2ptr(pFree->x_iNext);
        xp->x_iPrev = pFree->x_iPrev;
    }
    --getDataMap()->x_stat.m_iFlCnt;
}


LsShmOffset_t LsShmPool::getFromFreeList(LsShmSize_t size)
{
    LsShmOffset_t offset;
    LShmFreeTop *ap;

    offset = getDataMap()->x_iFreePageList;
    while (offset != 0)
    {
        ap = (LShmFreeTop *)offset2ptr(offset);
        if (ap->x_iFreeSize >= size)
        {
            LsShmSize_t left = ap->x_iFreeSize - size;
            reduceFreeFromBot(ap, offset, left);
            return offset + left;
        }
        offset = ap->x_iFreeNext;
    }
    return 0; // no match
}

static void markTopUsed(LShmFreeTop *ap)
{
    ap->x_iAMarker = 0;
}


//
//  reduceFreeFromBot - reduce to size or unlink myself from FreeList
//
void LsShmPool::reduceFreeFromBot(
    LShmFreeTop *ap, LsShmOffset_t offset, LsShmSize_t newsize)
{
    if (newsize == 0)
    {
        // remove myself from freelist
        markTopUsed(ap);
        disconnectFromFree(ap,
            (LShmFreeBot *)offset2ptr(ap->x_iFreeSize - sizeof(LShmFreeBot)));
        return;
    }

    //
    // NOTE: reduce size from bottom
    //
    LShmFreeBot *bp =
        (LShmFreeBot *)offset2ptr(offset + newsize - sizeof(LShmFreeBot));

    bp->x_iFreeOffset = offset;
    bp->x_iBMarker = LSSHM_FREE_BMARKER;
    ap->x_iFreeSize = newsize;
}


void LsShmPool::disconnectFromFree(LShmFreeTop *ap, LShmFreeBot *bp)
{
    LsShmOffset_t myNext, myPrev;
    myNext = ap->x_iFreeNext;
    myPrev = ap->x_iFreePrev;
    LShmFreeTop *xp;

    LsShmPoolMap *pDataMap = getDataMap();
    if (myPrev != 0)
    {
        xp = (LShmFreeTop *)offset2ptr(myPrev);
        xp->x_iFreeNext = myNext;
    }
    else
        pDataMap->x_iFreePageList = myNext;
    if (myNext != 0)
    {
        xp = (LShmFreeTop *)offset2ptr(myNext);
        xp->x_iFreePrev = myPrev;
    }
    --pDataMap->x_stat.m_iGpFreeListCnt;
}


//
//  @brief isFreeBlockAbove - is the space above this block "freespace".
//  @return true if the block above is free otherwise false
//
bool LsShmPool::isFreeBlockAbove(
    LsShmOffset_t offset, LsShmSize_t size, int joinFlag)
{
    LsShmSize_t aboveOffset = offset - sizeof(LShmFreeBot);
    if (aboveOffset < LSSHM_SHM_UNITSIZE)
        return false;

    LShmFreeBot *bp = (LShmFreeBot *)offset2ptr(aboveOffset);
    if ((bp->x_iBMarker == LSSHM_FREE_BMARKER)
        && (bp->x_iFreeOffset >= LSSHM_SHM_UNITSIZE)
        && (bp->x_iFreeOffset < aboveOffset))
    {
        LShmFreeTop *ap = (LShmFreeTop *)offset2ptr(bp->x_iFreeOffset);
        if ((ap->x_iAMarker == LSSHM_FREE_AMARKER)
            && ((ap->x_iFreeSize + bp->x_iFreeOffset) == offset))
        {
            if (joinFlag != 0)
            {
                // join above block
                ap->x_iFreeSize += size;

                LShmFreeBot *xp =
                    (LShmFreeBot *)offset2ptr(offset + size - sizeof(LShmFreeBot));
                xp->x_iBMarker = LSSHM_FREE_BMARKER;
                xp->x_iFreeOffset = bp->x_iFreeOffset;

                markTopUsed((LShmFreeTop *)offset2ptr(offset));
            }
            return true;
        }
    }
    return false;
}


//
// Check if this is a good free block
//
bool LsShmPool::isFreeBlockBelow(
    LsShmOffset_t offset, LsShmSize_t size, int joinFlag)
{
    LsShmOffset_t belowOffset = offset + size;
    if (belowOffset >= m_pShm->maxSize())
        return false;

    LShmFreeTop *ap = (LShmFreeTop *)offset2ptr(belowOffset);
    if (ap->x_iAMarker == LSSHM_FREE_AMARKER)
    {
        // the bottom free offset
        LsShmOffset_t e_offset = belowOffset + ap->x_iFreeSize;
        if ((e_offset < LSSHM_SHM_UNITSIZE) || (e_offset > getShmMapMaxSize()))
            return false;

        e_offset -= sizeof(LShmFreeBot);
        LShmFreeBot *bp = (LShmFreeBot *)offset2ptr(e_offset);
        if ((bp->x_iBMarker == LSSHM_FREE_BMARKER)
            && (bp->x_iFreeOffset == belowOffset))
        {
            if (joinFlag != 0)
            {
                markTopUsed(ap);
                if (joinFlag == 2)
                {
                    disconnectFromFree(ap, bp);
                    // merge to top
                    LShmFreeTop *xp = (LShmFreeTop *)offset2ptr(offset);
                    xp->x_iFreeSize += ap->x_iFreeSize;
                    bp->x_iFreeOffset = offset;
                    return true;
                }

                // setup myself as free block
                LShmFreeTop *np = (LShmFreeTop *)offset2ptr(offset);
                np->x_iAMarker = LSSHM_FREE_AMARKER;
                np->x_iFreeSize = size + ap->x_iFreeSize;
                np->x_iFreeNext = ap->x_iFreeNext;
                np->x_iFreePrev = ap->x_iFreePrev;

                bp->x_iFreeOffset = offset;

                LShmFreeTop *xp;
                if (np->x_iFreeNext != 0)
                {
                    xp = (LShmFreeTop *)offset2ptr(np->x_iFreeNext);
                    xp->x_iFreePrev = offset;
                }
                if (np->x_iFreePrev != 0)
                {
                    xp = (LShmFreeTop *)offset2ptr(np->x_iFreePrev);
                    xp->x_iFreeNext = offset;
                }
                else
                    getDataMap()->x_iFreePageList = offset;
            }
            return true;
        }
    }
    return false;
}


LsShmOffset_t LsShmPool::allocPage(LsShmSize_t pagesize, int &remap)
{
    LsShmOffset_t offset;

    if ((pagesize&0x80000000) || (pagesize>LSSHM_MAXSIZE))
        return 0;
    pagesize = roundPageSize(pagesize);
    remap = 0;

    LsShmPool *pPagePool = ((m_pParent != NULL) ? m_pParent : this);
    if (m_pParent != NULL)
        pPagePool->autoLock();
    if ((offset = pPagePool->getFromFreeList(pagesize)) == 0)
    {
        if ((offset = m_pShm->allocPage(pagesize, remap)) == 0)
        {
            goto out;
        }
        markTopUsed((LShmFreeTop *)offset2ptr(offset));
    }
    incrCheck(&pPagePool->getDataMap()->x_stat.m_iGpAllocated,
        (pagesize / LSSHM_SHM_UNITSIZE));
out:
    if (m_pParent != NULL)
        pPagePool->autoUnlock();

    return offset;
}


void LsShmPool::releasePageLocked(LsShmOffset_t offset, LsShmSize_t pagesize)
{
    pagesize = roundPageSize(pagesize);

    incrCheck(&getDataMap()->x_stat.m_iGpReleased,
        (pagesize / LSSHM_SHM_UNITSIZE));
    if (isFreeBlockAbove(offset, pagesize, 1))
    {
        LShmFreeTop *ap;
        offset = ((LShmFreeBot *)offset2ptr(
                      offset + pagesize - sizeof(LShmFreeBot)))->x_iFreeOffset;
        ap = (LShmFreeTop *)offset2ptr(offset);
        isFreeBlockBelow(offset, ap->x_iFreeSize, 2);
        return;
    }
    if (isFreeBlockBelow(offset, pagesize, 1))
        return;
    joinFreeList(offset, pagesize);
}


void LsShmPool::joinFreeList(LsShmOffset_t offset, LsShmSize_t size)
{
    LsShmPoolMap *pDataMap = getDataMap();
    // setup myself as free block
    LShmFreeTop *np = (LShmFreeTop *)offset2ptr(offset);
    np->x_iAMarker = LSSHM_FREE_AMARKER;
    np->x_iFreeSize = size;
    np->x_iFreeNext = pDataMap->x_iFreePageList;
    np->x_iFreePrev = 0;

    // join myself to freeList
    pDataMap->x_iFreePageList = offset;

    if (np->x_iFreeNext != 0)
    {
        LShmFreeTop *xp = (LShmFreeTop *)offset2ptr(np->x_iFreeNext);
        xp->x_iFreePrev = offset;
    }

    LShmFreeBot *bp =
        (LShmFreeBot *)offset2ptr(offset + size - sizeof(LShmFreeBot));
    bp->x_iFreeOffset = offset;
    bp->x_iBMarker = LSSHM_FREE_BMARKER;
    ++pDataMap->x_stat.m_iGpFreeListCnt;
}


int LsShmPool::mergeDeadPool(LsShmPoolMem* pPool)
{
    if ((kill(pPool->x_pid, 0) < 0) && (errno == ESRCH))
    {
        addFreeBucket(&pPool->x_data);
        addFreeList(&pPool->x_data);
        release2( ptr2offset(pPool), roundDataSize(sizeof(LsShmPoolMem)));
        return 1;
    }
    return 0;
}


void LsShmPool::setPid(int pid)
{
    s_pid = pid;
}
