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
#ifndef LSSHMPOOL_H
#define LSSHMPOOL_H
#include <shm/lsshm.h>

#ifdef LSSHM_DEBUG_ENABLE
class debugBase;
#endif

/**
 * @file
 * replicated the gpool idea.
 *  lsShmPool
 *  (0) Page memory is handled by LsShm.
 *  (1) Maintain fixed size bucket for fast allocation (4-1024, 16 byte interval).
 *  (2) Anything bigger than max bucket will get from the freelist allocation.
 *
 *  LsShmPoolMem -> the physical map structure
 *
 *  all map members start with x_
 */


// runtime free memory for the pool
typedef struct ls_shmmapchunk_s ShmMapChunk;
typedef struct ls_shmfreelist_s LsShmFreeList;
typedef struct ls_shmpoolmap_s LsShmPoolMap;
typedef struct ls_shmpoolmem_s LsShmPoolMem;
typedef struct ls_shmfreetop_s LShmFreeTop;
typedef struct ls_shmfreebot_s LShmFreeBot;


#define LSSHM_POOL_NUMBUCKET    0x40
#define LSSHM_MAX_BUCKET_SLOT   0x8 // max bucket slot allocation


#define LSSHM_POOL_MAXBCKTSIZE  (LSSHM_POOL_NUMBUCKET * LSSHM_POOL_BCKTINCR)

typedef struct
{
    LsShmXSize_t     m_iPgAllocated;    // allocated by pages (blocks)
    LsShmXSize_t     m_iPgReleased;     // released by pages (blocks)
    LsShmXSize_t     m_iPoolInUse;      // currently allocated from pool (bytes)
    LsShmXSize_t     m_iFreeChunk;      // chunk to be allocated (bytes)
    LsShmXSize_t     m_iFlAllocated;    // allocated from free list (bytes)
    LsShmXSize_t     m_iFlReleased;     // released to free list (bytes)
    LsShmXSize_t     m_iFlCnt;          // entries on free list (count)
    LsShmXSize_t     m_iGpAllocated;    // global pool allocated (blocks)
    LsShmXSize_t     m_iGpReleased;     // global pool released (blocks)
    LsShmXSize_t     m_iGpFreeListCnt;  // global pool free block list cnt
    struct bcktstat
    {
        LsShmXSize_t m_iBkAllocated;    // total allocations from bucket (count)
        LsShmXSize_t m_iBkReleased;     // total releases to bucket (count)
    } m_bckt[LSSHM_POOL_NUMBUCKET];
} LsShmPoolMapStat;


class LsShmPool : public ls_shmpool_s
{
public:
    LsShmPool();
    ~LsShmPool();

public:
    LsShmHash *getNamedHash(const char *name, LsShmSize_t init_size,
                            LsShmHasher_fn hf, LsShmValComp_fn vc, int flags);
    int init(LsShm *shm, const char *name, LsShmPool *gpool);
    void close();
    void destroy();

    uint32_t getMagic() const
    {   return m_iMagic;    }

    ls_attr_inline LsShm *getShm() const
    {   return m_pShm;      }

    LsShmStatus_t status() const
    {   return m_status; };

    ls_attr_inline void *offset2ptr(LsShmOffset_t offset) const
    {   return (void *)m_pShm->offset2ptr(offset); }

    ls_attr_inline LsShmOffset_t ptr2offset(const void *ptr) const
    {   return m_pShm->ptr2offset(ptr); }

    ls_attr_inline LsShmStatus_t chkRemap()
    {   return m_pShm->chkRemap(); }

    static inline LsShmSize_t roundDataSize(LsShmSize_t size)
    {
        return ((size + (LSSHM_POOL_UNITSIZE - 1))
                / LSSHM_POOL_UNITSIZE) * LSSHM_POOL_UNITSIZE;
    };

    static inline  LsShmSize_t roundPageSize(LsShmSize_t size)
    {
        return ((size + (LSSHM_SHM_UNITSIZE - 1))
                / LSSHM_SHM_UNITSIZE) * LSSHM_SHM_UNITSIZE;
    };

    static inline  LsShmSize_t size2roundSize(LsShmSize_t size)
    {
        return ((size >= LSSHM_SHM_UNITSIZE) ?
                roundPageSize(size) : roundDataSize(size));
    }

    static inline  LsShmSize_t roundSize2pages(LsShmSize_t size)
    {
        return ((size + (LSSHM_SHM_UNITSIZE - 1)) / LSSHM_SHM_UNITSIZE);
    };

    LsShmOffset_t  alloc2(LsShmSize_t size, int &remapped);
    void  release2(LsShmOffset_t offset, LsShmSize_t size);
    void  mvFreeList();
    void  mvFreeBucket();


    void enableAutoLock()
    {   m_iAutoLock = 1; }

    void disableAutoLock()
    {   m_iAutoLock = 0; }

    ls_attr_inline LsShmSize_t getShmMapMaxSize() const
    {   return m_pShm->maxSize(); }

    LsShmOffset_t getPoolMapStatOffset() const;

    LsShmLock *lockPool()
    {   return m_pShm->getLocks(); }

#ifdef notdef
    void setMapOwner(int o)
    {   m_iShmOwner = o; }
#endif

    HashStringMap< ls_shmobject_t *> &getObjBase()
    {   return m_pShm->getObjBase(); }

    int lock()
    {
        return m_iAutoLock ? 0 : getShm()->lockRemap(m_pShmLock);
    }

    int unlock()
    {   return m_iAutoLock ? 0 : ls_shmlock_unlock(m_pShmLock); }

    int getRef()  { return m_iRef; }
    int upRef()   { return ++m_iRef; }
    int downRef() { return --m_iRef; }

    LsShmHash * newHashByOffset(LsShmOffset_t x_globalHashOff,
                  const char *name, LsShmHasher_fn hf,
                  LsShmValComp_fn vc, int flags);
    LsShmOffset_t allocateNewHash(int initSize, int iMode, int iFlags);
    int mergeDeadPool(LsShmPoolMem* pPool);
    
    void addLeftOverPages(LsShmOffset_t offset, LsShmSize_t size);


    static void setPid( int pid );

private:
    ls_attr_inline LsShmPoolMem *getPool() const
    {   return x_pPool;     }
    //x_pPool = (LsShmPoolMem *)offset2ptr(m_iOffset));   }

    LsShmPoolMap *getDataMap() const;

    void mapLock();
    
    int autoLock()
    {   return m_iAutoLock ? getShm()->lockRemap(m_pShmLock) 
                           : (assert(!m_pParent || getShm()->isLocked(m_pShmLock)), 0);   }

    int autoUnlock()
    {   assert(!m_pParent || getShm()->isLocked(m_pShmLock));
        return m_iAutoLock ? ls_shmlock_unlock(m_pShmLock) : 0;     }
    
    LsShmOffset_t getReg(const char *name);

    LsShmOffset_t allocPage(LsShmSize_t pagesize, int &remapped);
    void releasePageLocked(LsShmOffset_t offset, LsShmSize_t pagesize);
    void releasePageNoJoinLocked(LsShmOffset_t offset, LsShmSize_t pagesize);

    // for internal purpose
    void  releaseData(LsShmOffset_t offset, LsShmSize_t size);

    LsShmStatus_t checkStaticData(const char *name);
    LsShmStatus_t createStaticData(const char *name);

    //
    // data related
    //
    LsShmOffset_t allocFromDataFreeList(LsShmSize_t size);
    LsShmOffset_t allocFromDataBucket(LsShmSize_t size);
    LsShmOffset_t allocFromGlobalBucket(LsShmSize_t bucketNum,
                                        LsShmSize_t &num);
    LsShmOffset_t fillDataBucket(LsShmSize_t bucketNum, LsShmSize_t size);
    LsShmOffset_t allocFromDataChunk(LsShmSize_t size, LsShmSize_t &num);
    void mvDataFreeListToBucket(LsShmFreeList *pFree, LsShmOffset_t offset);
    void rmFromDataFreeList(LsShmFreeList *pFree);

    void  addFreeList(LsShmPoolMap *pSrcMap);
    void  addFreeBucket(LsShmPoolMap *pSrcMap);

    LsShmSize_t dataSize2Bucket(LsShmSize_t size) const
    {   return (size / LSSHM_POOL_BCKTINCR); }

    bool isFreeBlockAbove(LsShmOffset_t offset, LsShmSize_t size, int joinFlag);
    bool isFreeBlockBelow(LsShmOffset_t offset, LsShmSize_t size, int joinFlag);
    void joinFreeList(LsShmOffset_t offset, LsShmSize_t size);

    LsShmOffset_t getFromFreeList(LsShmSize_t pagesize);
    void reduceFreeFromBot(LShmFreeTop *ap,
                           LsShmOffset_t offset, LsShmSize_t newsize);
    void disconnectFromFree(LShmFreeTop *ap, LShmFreeBot *bp);

    void incrCheck(LsShmXSize_t *ptr, LsShmSize_t size);

    LsShmOffset_t  alloc2Ex(LsShmSize_t size, int &remapped);
    void releasePageLockParent(LsShmOffset_t offset, LsShmSize_t size);
    void release2Ex(LsShmOffset_t offset, LsShmSize_t size);
    void release2NoJoin(LsShmOffset_t offset, LsShmSize_t size);

private:
    LsShmPool(const LsShmPool &other);
    LsShmPool &operator=(const LsShmPool &other);
    bool operator==(const LsShmPool &other);

    uint32_t            m_iMagic;
    LsShm              *m_pShm;         // SHM handle
    LsShmStatus_t       m_status;       // Ready ...
    LsShmOffset_t       m_iOffset;      // find from SHM registry
    LsShmPoolMem       *x_pPool;
    ls_shmlock_t       *m_pShmLock;
    int8_t              m_iAutoLock;
    int8_t              m_iShmOwner;    // indicated if I own the SHM
    uint16_t            m_iRegNum;      // registry number
    LsShmPool          *m_pParent;      // parent global pool
    int                 m_iRef;
#ifdef LSSHM_DEBUG_ENABLE
    friend class debugBase;
#endif
};

#endif // LSSHMPOOL_H
