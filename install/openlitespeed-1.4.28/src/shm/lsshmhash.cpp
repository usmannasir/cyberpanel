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
#include <shm/lsshmhash.h>

#include <lsr/xxhash.h>
#include <shm/lsshmpool.h>
#include <shm/lsshmtidmgr.h>

#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>


// LruHash info
struct LsHashLruInfo_s
{
    LsShmHIterOff    linkFirst;
    LsShmHIterOff    linkLast;
    int              nvalset;    // number of keys currently set
    int              nvalexp;    // number of keys expired
    int              ndataset;   // number of value datas currently set
    int              ndatadel;   // number of datas deleted by mincnt
    int              ndataexp;   // number of datas expired
};


static int s_tidOffset[2] = { 
    sizeof(LsShmTidInfo), 
    sizeof(LsShmTidInfo) + sizeof(LsHashLruInfo_s)   
};


typedef struct ls_shmhtable_s
{
    uint32_t        x_iMagic;
    LsShmSize_t     x_iCapacity;
    LsShmSize_t     x_iSize;
    LsShmSize_t     x_iFullFactor;
    LsShmSize_t     x_iGrowFactor;
    LsShmOffset_t   x_iHIdx;
    LsShmOffset_t   x_iBitMap;
    LsShmOffset_t   x_iHIdxNew; // in rehash()
    LsShmSize_t     x_iCapacityNew;
    LsShmOffset_t   x_iWorkIterOff;
    LsShmOffset_t   x_iBitMapSz;
    LsShmOffset_t   x_iLockOffset;
    uint8_t         x_iMode;
    uint8_t         x_iFlags;
    uint8_t         x_unused[2];
    LsShmHTableStat x_stat;         // hash statistics
    uint8_t         x_reserved[256];
    
    LsHashLruInfo_s *getLruInfo()
    {   return (LsHashLruInfo_s *)&x_reserved[sizeof(x_reserved) 
                                             - sizeof(LsHashLruInfo_s)];    }
    
    LsShmTidInfo    *getTidInfo()
    {   return (LsShmTidInfo *)&x_reserved[sizeof(x_reserved) 
                          - s_tidOffset[x_iMode & LSSHM_FLAG_LRU]]; }
} LsShmHTable;


struct lsshmobsiter_s
{
    LsShmObserver  *observer;
    LsShmOffset_t   tableOff;
    LsShmOffset_t   iterOff;
};


const uint8_t s_bitMask[] =
{
    0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80
};
const size_t s_bitsPerChar =
    sizeof(s_bitMask) / sizeof(s_bitMask[0]);

// minimum element count for bloom bitmap (approx 1Mb table size)
#define MINSZ_FOR_BITMAP    (1024*1024/sizeof(LsShmHIterOff))

const size_t s_bitsPerLsShmHIdx =
    s_bitsPerChar * sizeof(LsShmHIterOff);


enum { prime_count = 31    };
static const LsShmSize_t s_primeList[prime_count] =
{
    7ul,          13ul,         29ul,
    53ul,         97ul,         193ul,       389ul,       769ul,
    1543ul,       3079ul,       6151ul,      12289ul,     24593ul,
    49157ul,      98317ul,      196613ul,    393241ul,    786433ul,
    1572869ul,    3145739ul,    6291469ul,   12582917ul,  25165843ul,
    50331653ul,   100663319ul,  201326611ul, 402653189ul, 805306457ul,
    1610612741ul, 3221225473ul, 4294967291ul
};


static int findRange(LsShmSize_t sz)
{
    int i = 1;
    for (; i < prime_count - 1; ++i)
    {
        if (sz <= s_primeList[i])
            break;
    }
    return i;
}

    static int sz2BitMapSz(LsShmSize_t sz)
    {
        return ((sz < MINSZ_FOR_BITMAP) ? 0 :
            (((sz + s_bitsPerLsShmHIdx - 1) / s_bitsPerLsShmHIdx)
            * sizeof(LsShmHIterOff)));
    }


LsShmSize_t LsShmHash::roundUp(LsShmSize_t sz)
{
    return s_primeList[findRange(sz)];
}


// Hash for 32bytes session id
LsShmHKey LsShmHash::hash32id(const void *__s, size_t len)
{
    const uint32_t *lp = (const uint32_t *)__s;
    LsShmHKey __h = 0;

    if (len >= 8)
        __h = *lp ^ *(lp + 1);
    else
    {
        while (len >= 4)
        {
            __h ^= *lp++;
            len -= 4;
        }
        // ignore the leftover!
        // if (len)
    }
    return __h;
}


LsShmHKey LsShmHash::hashBuf(const void *__s, size_t len)
{
    LsShmHKey __h = 0;
    const uint8_t *p = (const uint8_t *)__s;
    const uint8_t *pEnd = p + len;
    uint8_t ch;

    // we will need a better hash key generator for buf key
    while (p < pEnd)
    {
        ch = *(const uint8_t *)p++;
        __h = __h * 31 + (ch);
    }
    return __h;
}


LsShmHKey LsShmHash::hashXXH32(const void *__s, size_t len)
{
    return XXH32(__s, len, 0);
}


LsShmHKey LsShmHash::hashString(const void *__s, size_t len)
{
    LsShmHKey __h = 0;
    const char *p = (const char *)__s;
    char ch = *(const char *)p++;
    for (; ch ; ch = *((const char *)p++))
        __h = __h * 31 + (ch);

    return __h;
}


int LsShmHash::compString(const void *pVal1, const void *pVal2, size_t len)
{
    return strcmp((const char *)pVal1, (const char *)pVal2);
}


LsShmHKey LsShmHash::iHashString(const void *__s, size_t len)
{
    LsShmHKey __h = 0;
    const char *p = (const char *)__s;
    char ch = *(const char *)p++;
    for (; ch ; ch = *((const char *)p++))
    {
        if (ch >= 'A' && ch <= 'Z')
            ch += 'a' - 'A';
        __h = __h * 31 + (ch);
    }
    return __h;
}


int LsShmHash::iCompString(const void *pVal1, const void *pVal2, size_t len)
{
    return strncasecmp(
               (const char *)pVal1, (const char *)pVal2, strlen((const char *)pVal1));
}


LsShmHKey LsShmHash::hfIpv6(const void *pKey, size_t len)
{
    LsShmHKey key;
    if (sizeof(LsShmHKey) == 4)
    {
        key = *((const LsShmHKey *)pKey) +
              *(((const LsShmHKey *)pKey) + 1) +
              *(((const LsShmHKey *)pKey) + 2) +
              *(((const LsShmHKey *)pKey) + 3);
    }
    else
    {
        key = *((const LsShmHKey *)pKey) +
              *(((const LsShmHKey *)pKey) + 1);
    }
    return key;
}


int LsShmHash::cmpIpv6(const void *pVal1, const void *pVal2, size_t len)
{
    return memcmp(pVal1, pVal2, 16);
}


inline LsShmSize_t LsShmHash::fullFactor() const
{   return getHTable()->x_iFullFactor;   }


inline LsShmSize_t LsShmHash::growFactor() const
{   return getHTable()->x_iGrowFactor;   }


inline LsShmHIterOff *LsShmHash::getHIdx() const
{   return (LsShmHIterOff *)m_pPool->offset2ptr(getHTable()->x_iHIdx);   }


inline uint8_t *LsShmHash::getBitMap() const
{
    LsShmHTable *pTable = getHTable();
    if (pTable->x_iBitMapSz == 0)
        return NULL;
    return (uint8_t *)m_pPool->offset2ptr(pTable->x_iBitMap);
}


void LsShmHash::lockChkRehash()
{
    if ((lock() < 0) && (getHTable()->x_iHIdx != getHTable()->x_iHIdxNew))
        rehash();
}


void LsShmHash::autoLockChkRehash()
{
    if ((autoLock() < 0) && (getHTable()->x_iHIdx != getHTable()->x_iHIdxNew))
        rehash();
}


LsHashLruInfo *LsShmHash::getLru()
{   return getHTable()->getLruInfo();  }


LsShmHash::iteroffset LsShmHash::getLruTop()
{
    return getLru()->linkFirst;
}

LsShmHash::iteroffset LsShmHash::getLruBottom()
{
    return getLru()->linkLast;
}

int32_t LsShmHash::getLruTotal()
{   
    return getLru()->nvalset;       
}

int32_t LsShmHash::getLruTrimmed()
{
    return getLru()->nvalexp;
}


// For now assume only one observer.
// void *LsShmHash::getObsData(LsShmHElem *pElem, LsShmObserver *pObserver) const
void *LsShmHash::getObsData(LsShmHElem *pElem) const
{
    return pElem->x_aData + pElem->x_iValOff - m_pObservers->iterOff;
}


LsShmOffset_t LsShmHash::alloc2(LsShmSize_t size, int &remapped)
{
    LsShmOffset_t ret = m_pPool->alloc2(size, remapped);
    if (ret != 0)
        getHTable()->x_stat.m_iHashInUse += LsShmPool::size2roundSize(size);
    return ret;
}


void LsShmHash::release2(LsShmOffset_t offset, LsShmSize_t size)
{
    m_pPool->release2(offset, size);
    getHTable()->x_stat.m_iHashInUse -= LsShmPool::size2roundSize(size);
}


bool LsShmHash::empty() const
{
    return getHTable()->x_iSize == 0;
}


LsShmSize_t LsShmHash::size() const
{
    return getHTable()->x_iSize;
}


void LsShmHash::LsShmHash::incrTableSize()
{
    ++(getHTable()->x_iSize);
}


void LsShmHash::decrTableSize()
{
    --(getHTable()->x_iSize);
}


LsShmSize_t LsShmHash::capacity() const
{
    return getHTable()->x_iCapacity;
}


inline int LsShmHash::getBitMapEnt(uint32_t indx)
{
    uint8_t *pBitMap = getBitMap();
    return ((pBitMap == NULL) ? 1 :
        pBitMap[indx / s_bitsPerChar] & s_bitMask[indx % s_bitsPerChar]);
}


inline void LsShmHash::setBitMapEnt(uint32_t indx)
{
    uint8_t *pBitMap;
    if ((pBitMap = getBitMap()) != NULL)
        pBitMap[indx / s_bitsPerChar] |= s_bitMask[indx % s_bitsPerChar];
}


inline void LsShmHash::clrBitMapEnt(uint32_t indx)
{
    uint8_t *pBitMap;
    if ((pBitMap = getBitMap()) != NULL)
        pBitMap[indx / s_bitsPerChar] &= ~(s_bitMask[indx % s_bitsPerChar]);
}


LsShmOffset_t LsShmHash::getHTableStatOffset() const
{   return (LsShmOffset_t)(long) & ((LsShmHTable *)(long)m_iOffset)->x_stat; }


LsShmOffset_t LsShmHash::getHTableReservedOffset() const
{   return (LsShmOffset_t)(long) & ((LsShmHTable *)(long)m_iOffset)->x_reserved; }




int LsShmHash::chkHashTable(LsShm *pShm, LsShmReg *pReg, int *pMode, int *pFlags)
{
    if (pReg->x_iValue == 0)
        return -1;
    LsShmHTable *pTable = (LsShmHTable *)pShm->offset2ptr(pReg->x_iValue);
    if (pTable->x_iMagic != LSSHM_HASH_MAGIC)
        return -1;
    *pMode = pTable->x_iMode;
    *pFlags = pTable->x_iFlags;
    return 0;
}


LsShmHash::LsShmHash(LsShmPool *pool, const char *name,
                     LsShmHasher_fn hf, LsShmValComp_fn vc, int flags)
    : m_iMagic(LSSHM_HASH_MAGIC)
    , m_iOffset(0)
    , m_pPool(pool)
    , x_pTable(NULL)
    , m_hf(hf)
    , m_vc(vc)
    , m_iterExtraSpace(0)
    , m_dataExtraSpace(0)
    , m_iFlags(flags)
    , m_pLruAddon(NULL)
    , m_pObservers(NULL)
    , m_pTidMgr(NULL)
{
    obj.m_pName = strdup(name);
    m_iRef = 0;
    m_status = LSSHM_NOTREADY;
    m_pShmLock = NULL;
    m_iAutoLock = 1;      // enableLock()

    if (m_hf != NULL)
    {
        assert(m_vc);
        m_insert = insertPtr;
        m_update = updatePtr;
        m_set = setPtr;
        m_find = findPtr;
        m_get = getPtr;
        m_iMode = 1;
    }
    else
    {
        m_insert = insertNum;
        m_update = updateNum;
        m_set = setNum;
        m_find = findNum;
        m_get = getNum;
        m_iMode = 0;
    }
}


LsShmOffset_t LsShmHash::allocHTable(LsShmPool * pPool, int init_size,
                                     int iMode, int iFlags,
                                     LsShmOffset_t lockOffset)
{
    int remapped;
    // NOTE: system is not up yet... ignore remap here
    LsShmOffset_t offset = pPool->alloc2(sizeof(LsShmHTable), remapped);
    if (offset == 0)
    {
        return 0;
    }

    init_size = roundUp(init_size);
    int szTable = sz2TableSz(init_size);
    int szBitMap = sz2BitMapSz(init_size);
    LsShmOffset_t iBase = pPool->alloc2(szTable + szBitMap, remapped);

    if (iBase == 0)
    {
        pPool->release2(offset, sizeof(LsShmHTable));
        return 0;
    }
    LsShmHTable *pTable = (LsShmHTable *)pPool->offset2ptr(offset);

    ::memset(pTable, 0, sizeof(*pTable));
    ::memset(pPool->offset2ptr(iBase), 0, szTable + szBitMap);

    pTable->x_iMagic = LSSHM_HASH_MAGIC;
    pTable->x_iCapacity = init_size;
    pTable->x_iFullFactor = 2;
    pTable->x_iGrowFactor = 2;
    pTable->x_iBitMap = iBase;
    pTable->x_iHIdx = iBase + szBitMap;
    pTable->x_iHIdxNew = pTable->x_iHIdx;

    pTable->x_iBitMapSz = szBitMap;
    pTable->x_stat.m_iHashInUse = LsShmPool::size2roundSize(sizeof(LsShmHTable))
                                  + LsShmPool::size2roundSize(szTable + szBitMap);

    pTable->x_iLockOffset = lockOffset;

    pTable->x_iMode = iMode;
    pTable->x_iFlags = iFlags;

    return offset;

}


int LsShmHash::init(LsShmOffset_t offset)
{
    m_iOffset = offset;
    x_pTable = (LsShmHTable *)m_pPool->offset2ptr(m_iOffset);
    LsShmHTable *pTable = getHTable();

    // check the magic and mode
    if ((m_iMagic != pTable->x_iMagic)
        || (m_iMode != pTable->x_iMode)
        || (m_iFlags != pTable->x_iFlags))
        return LS_FAIL;
    m_pShmLock = m_pPool->lockPool()->offset2pLock(pTable->x_iLockOffset);

    if (m_iFlags & LSSHM_FLAG_LRU)
        m_iterExtraSpace = sizeof(LsShmHElemLink);
    //if ((m_iFlags & LSSHM_FLAG_LRU_MODE2) || (m_iFlags & LSSHM_FLAG_LRU_MODE3))
    //    m_iLockEnable = 0;  // shmlru routines lock manually on higher level
    if (m_iFlags & LSSHM_FLAG_TID)
    {
        LsShmOffset_t iTidIterOff = addExtraSpace(sizeof(uint64_t), 0);
        if ((m_pTidMgr = new LsShmTidMgr(iTidIterOff)) == NULL)
            return LS_FAIL;
        LsShmOffset_t tidMgrOff = offset 
                + ((char *)pTable->getTidInfo() - (char *)pTable);
        m_pTidMgr->init(this, tidMgrOff, 0);
    }
    m_iRef = 1;
    m_status = LSSHM_READY;
    return LS_OK;
}


LsShmHash::~LsShmHash()
{
    if (obj.m_pName != NULL)
    {
        if (m_iRef == 0)
        {
#ifdef DEBUG_RUN
            SHM_NOTICE("LsShmHash::~LsShmHash remove %s <%p>",
                       m_pName, &m_objBase);
#endif
            m_pPool->getShm()->getObjBase().remove(obj.m_pName);
        }
        free(obj.m_pName);
        obj.m_pName = NULL;
    }
    if (m_pTidMgr != NULL)
        delete m_pTidMgr;
}


LsShmHash *LsShmHash::open(
    const char *pShmName, const char *pHashName, int init_size, int flags)
{
    LsShm *pShm;
    LsShmPool *pPool = NULL;
    LsShmHash *pHash = NULL;
    int attempts;

    for (attempts = 0; attempts < 2; ++attempts)
    {
        if ((pShm = LsShm::open(pShmName, 0)) == NULL)
        {
            if ((pShm = LsShm::open(pShmName, 0)) == NULL)
                return NULL;
        }
        if ((pPool = pShm->getGlobalPool()) == NULL)
        {
            pShm->deleteFile();
            pShm->close();
            continue;
        }

        if ((pHash = pPool->getNamedHash(pHashName, init_size,
            LsShmHash::hashXXH32, memcmp, flags)) == NULL)
        {
            pPool->close();
            pShm->deleteFile();
            pShm->close();
        }
        else
            break;
    }
    return pHash;
}


LsShmHash *LsShmHash::checkHTable(GHash::iterator itor, LsShmPool *pool,
                                  const char *name, LsShmHasher_fn hf, LsShmValComp_fn vc)
{
    LsShmHash *pObj;
    if (((pObj = (LsShmHash *)(ls_shmhash_t *)itor->second()) == NULL)
        || (pObj->m_iMagic != LSSHM_HASH_MAGIC)
        || (pObj->m_hf != hf)
        || (pObj->m_vc != vc))
        return NULL;    // bad: parameters not matching

    if (pObj->m_pPool != pool)
        return (LsShmHash *) - 1; // special case: different pools
    pObj->upRef();
    return pObj;
}


void LsShmHash::setFullFactor(int f)
{
    if (f > 0)
        getHTable()->x_iFullFactor = f;
}


void LsShmHash::setGrowFactor(int f)
{
    if (f > 0)
        getHTable()->x_iGrowFactor = f;
}


void LsShmHash::releaseHTableShm()
{
    if (m_iOffset != 0)
    {
        LsShmHTable *pTable = getHTable();
        if (pTable->x_iBitMap != 0)
        {
            m_pPool->release2(pTable->x_iBitMap,
                pTable->x_iBitMapSz + sz2TableSz(pTable->x_iCapacity));
        }
        if (m_pShmLock != NULL)
        {
            m_pPool->lockPool()->freeLock(m_pShmLock);
            m_pShmLock = NULL;
        }
        m_pPool->release2(m_iOffset, sizeof(LsShmHTable));
        m_iOffset = 0;
        x_pTable = NULL;
    }
}


void LsShmHash::close()
{
//     LsShmPool *p = NULL;
//     if (m_iPoolOwner != 0)
//     {
//         m_iPoolOwner = 0;
//         p = m_pPool;
//     }
    if (downRef() == 0)
        delete this;
//     if (p != NULL)
//         p->close();
}


//
//  The only way to remove the Shared Memory
//
void LsShmHash::destroy()
{
    if (m_iOffset != 0)
    {
        // remove from regMap
        m_pPool->getShm()->delReg(obj.m_pName);

        // all elements
        clear();

        releaseHTableShm();
    }
}


int LsShmHash::rehash()
{
    LsShmSize_t oldSize = capacity();
    LsShmSize_t newSize;
    LsShmOffset_t newIdxOff;
    LsShmOffset_t newBitOff;
    LsShmHIterOff *pIdxOld;
    LsShmHIterOff *pIdxNew;
    LsShmHIterOff *opIdx;
    LsShmHIterOff *npIdx;
    iterator iter;
    iteroffset iterOff;
    iteroffset iterNextOff;
    int szTable;
    int szBitMap;
#ifdef DEBUG_RUN
    SHM_NOTICE("LsShmHash::rehash %6d %X size %d cap %d NEW %d",
               getpid(), m_pPool->getShmMap(),
               size(),
               oldSize,
               s_primeList[findRange(oldSize) + growFactor()]
              );
#endif
    LsShmHTable *pTable = getHTable();
    pIdxOld = (LsShmHIterOff *)m_pPool->offset2ptr(pTable->x_iHIdx);
    if (pTable->x_iHIdx != pTable->x_iHIdxNew)          // rehash in progress
    {
        newSize = pTable->x_iCapacityNew;
        newIdxOff = pTable->x_iHIdxNew;
        pIdxNew = (LsShmHIterOff *)m_pPool->offset2ptr(newIdxOff);
        if ((iterOff.m_iOffset = pTable->x_iWorkIterOff) != 0)    // iter in progress
        {
            iter = offset2iterator(iterOff);
            npIdx = pIdxNew + getIndex(iter->x_hkey, newSize);
            if (npIdx->m_iOffset != iterOff.m_iOffset)            // not there yet
            {
                opIdx = pIdxOld + getIndex(iter->x_hkey, oldSize);
                if (opIdx->m_iOffset == iterOff.m_iOffset)
                    opIdx->m_iOffset = iter->x_iNext.m_iOffset;   // remove from old
                iter->x_iNext.m_iOffset = npIdx->m_iOffset;
                npIdx->m_iOffset = iterOff.m_iOffset;
            }

        }
    }
    else
    {
        int remapped;
        newSize = s_primeList[findRange(oldSize) + growFactor()];
        szTable = sz2TableSz(newSize);
        szBitMap = sz2BitMapSz(newSize);
        if ((newBitOff = alloc2(szTable + szBitMap, remapped)) == 0)
            return LS_FAIL;
        uint8_t *ptr = (uint8_t *)offset2ptr(newBitOff);
        ::memset(ptr, 0, szTable + szBitMap);
        newIdxOff = newBitOff + szBitMap;
        pIdxNew = (LsShmHIterOff *)(ptr + szBitMap);
        pTable = getHTable();
        pTable->x_iBitMap = newBitOff;
        pTable->x_iBitMapSz = szBitMap;
        pTable->x_iCapacityNew = newSize;
        pTable->x_iHIdxNew = newIdxOff;
        iterOff = begin();
    }

    pIdxOld = (LsShmHIterOff *)m_pPool->offset2ptr(pTable->x_iHIdx);
    while(iterOff.m_iOffset != 0)
    {
        uint32_t hashIndx;
        iter = offset2iterator(iterOff);
        iterNextOff = next(iterOff);
        hashIndx = getIndex(iter->x_hkey, newSize);
        npIdx = pIdxNew + hashIndx;
        setBitMapEnt(hashIndx);
        pTable->x_iWorkIterOff = iterOff.m_iOffset;
        (pIdxOld + getIndex(iter->x_hkey, oldSize))->m_iOffset = iter->x_iNext.m_iOffset;
        iter->x_iNext.m_iOffset = npIdx->m_iOffset;
        npIdx->m_iOffset = iterOff.m_iOffset;
        iterOff = iterNextOff;
    }
    pTable->x_iWorkIterOff = 0;

    szTable = sz2TableSz(oldSize);
    szBitMap = sz2BitMapSz(oldSize);
    release2(pTable->x_iHIdx - szBitMap, szTable + szBitMap);
    pTable->x_iCapacity = newSize;
    pTable->x_iHIdx = newIdxOff;
    return 0;
}


int LsShmHash::release_hash_elem(LsShmHash::iteroffset iterOff,
                                 void *pUData)
{
    LsShmHash *pThis = (LsShmHash *)pUData;
    LsShmHash::iterator iter = pThis->offset2iterator(iterOff);
    pThis->release2(iterOff.m_iOffset, (LsShmSize_t)iter->x_iLen);
    return 0;
}


void LsShmHash::clear()
{
    LsShmHTable *pTable = getHTable();
    int n = for_each2(begin(), end(), release_hash_elem, this);
    assert(n == (int)size());

    ::memset(offset2ptr(pTable->x_iBitMap), 0,
        pTable->x_iBitMapSz + sz2TableSz(pTable->x_iCapacity));
    pTable->x_iSize = 0;
    if (m_iFlags & LSSHM_FLAG_LRU)
    {
        LsHashLruInfo *pLru = getLru();
        pLru->linkFirst.m_iOffset = 0;
        pLru->linkLast.m_iOffset = 0;
        pLru->nvalset = 0;
        pLru->ndataset = 0;
    }
    if (m_pTidMgr != NULL)
        m_pTidMgr->clearCb();
}


LsShmHash::iteroffset LsShmHash::doGet(
    iteroffset iterOff, LsShmHKey key, ls_strpair_t *pParms,
    int *pFlag)
{
    if (iterOff.m_iOffset != 0)
    {
        iterator iter = offset2iterator(iterOff);
        if (m_iFlags & LSSHM_FLAG_LRU)
            linkSetTop(iter, iterOff);
        *pFlag = LSSHM_VAL_NONE;
        return iterOff;
    }
    LSSHM_CHECKSIZE(ls_str_len(&pParms->val));
    iterOff = insert2(key, pParms);
    if (iterOff.m_iOffset != 0)
    {
        if (*pFlag & LSSHM_VAL_INIT)
        {
            // initialize the memory
            ::memset(offset2iteratorData(iterOff),
                        0, ls_str_len(&pParms->val));
        }
        // some special lru initialization
//         if (m_iFlags & LSSHM_FLAG_LRU_MODE2)
//         {
//             shmlru_data_t *pData = (shmlru_data_t *)offset2iteratorData(
//                                         iterOff);
//             pData->maxsize = 0;
//             pData->offiter = iterOff;
//         }
//         else if (m_iFlags & LSSHM_FLAG_LRU_MODE3)
//             ((shmlru_val_t *)offset2iteratorData(iterOff))->offdata = 0;
        *pFlag = LSSHM_VAL_CREATED;
    }
    return iterOff;
}


LsShmHash::iteroffset LsShmHash::doInsert(
            iteroffset iterOff, LsShmHKey key, ls_strpair_t *pParms)
{
    if (iterOff.m_iOffset != 0)
        return end();
    LSSHM_CHECKSIZE(ls_str_len(&pParms->val));
    return insert2(key, pParms);
}

LsShmHash::iteroffset LsShmHash::doSet(
            iteroffset iterOff, LsShmHKey key, ls_strpair_t *pParms)
{
    LSSHM_CHECKSIZE(ls_str_len(&pParms->val));
    if (iterOff.m_iOffset != 0)
    {
        iterator iter = offset2iterator(iterOff);
        if (iter->realValLen() >= (LsShmSize_t)ls_str_len(&pParms->val))
        {
            iter->setValLen(ls_str_len(&pParms->val));
            setIterData(iter, ls_str_buf(&pParms->val));
            if (m_iFlags & LSSHM_FLAG_LRU)
                linkSetTop(iter, iterOff);
            if (m_pTidMgr != NULL)
                m_pTidMgr->updateIterCb(iter, iterOff);
            return iterOff;
        }
        else
        {
            // remove the iter and install new one
            eraseIteratorHelper(iterOff);
        }
    }
    return insert2(key, pParms);
}

LsShmHash::iteroffset LsShmHash::doUpdate(iteroffset iterOff, LsShmHKey key, ls_strpair_t *pParms)
{
    if (iterOff.m_iOffset == 0)
        return end();
    return doSet(iterOff, key, pParms);
}


//
// @brief erase - remove iter from the SHM pool.
// @brief will destroy the link to itself if any!
//
void LsShmHash::eraseIteratorHelper(iteroffset iterOff)
{
    if (iterOff.m_iOffset == 0)
        return;

    iterator iter = offset2iterator(iterOff);
    uint32_t hashIndx = getIndex(iter->x_hkey, capacity());
    LsShmHIterOff *pIdx = getHIdx() + hashIndx;
    LsShmOffset_t offset = pIdx->m_iOffset;
    LsShmHElem *pElem;
    LsShmOffset_t next = iter->x_iNext.m_iOffset;     // in case of remap in tid list
    LsShmSize_t size = iter->x_iLen;

    if (m_iFlags & LSSHM_FLAG_LRU)
        unlinkHElem(iter);

    //NOTE:race condition, two process release the object at the same time. 
    //     ShmHash was not properly locked. 
    assert(offset != 0);
#ifdef DEBUG_RUN
    if (offset == 0)
    {
        SHM_NOTICE(
            "LsShmHash::eraseIteratorHelper %6d %X size %d cap %d",
            getpid(), m_pPool->getShmMap(),
            size(),
            capacity()
        );
        sleep(10);
    }
#endif

    if (m_pTidMgr != NULL)
    {
        m_pTidMgr->eraseIterCb(iter);
        pIdx = getHIdx() + hashIndx;
    }
    if (offset == iterOff.m_iOffset)
    {
        if ((pIdx->m_iOffset = next) == 0) // last one
            clrBitMapEnt(hashIndx);
    }
    else
    {
        while (offset != 0)
        {
            pElem = (LsShmHElem *)m_pPool->offset2ptr(offset);
            if (pElem->x_iNext.m_iOffset == iterOff.m_iOffset)
            {
                pElem->x_iNext.m_iOffset = next;
                break;
            }
            // next offset...
            offset = pElem->x_iNext.m_iOffset;
        }
    }

    release2(iterOff.m_iOffset, size);
    decrTableSize();
}


LsShmHash::iteroffset LsShmHash::find2(LsShmHKey key,
                                       ls_strpair_t *pParms)
{
    uint32_t hashIndx = getIndex(key, capacity());
    if (getBitMapEnt(hashIndx) == 0)     // quick check
        return end();
    LsShmHIterOff *pIdx = getHIdx() + hashIndx;

#ifdef DEBUG_RUN
    SHM_NOTICE("LsShmHash::find %6d %X size %d cap %d <%p> %d",
               getpid(), m_pPool->getShmMap(),
               size(),
               capacity(),
               pIdx,
               hashIndx
              );
#endif
    LsShmHIterOff offset = *pIdx;
    LsShmHElem *pElem;

    while (offset.m_iOffset != 0)
    {
        pElem = (LsShmHElem *)m_pPool->offset2ptr(offset.m_iOffset);
        if ((pElem->x_hkey == key)
            && (pElem->getKeyLen() == (int)ls_str_len(&pParms->key))
            && ((*m_vc)(ls_str_buf(&pParms->key), pElem->getKey(),
                        ls_str_len(&pParms->key)) == 0))
            break;
        offset.m_iOffset = pElem->x_iNext.m_iOffset;
    }
    return offset;
}


LsShmHash::iteroffset LsShmHash::allocIter(int keyLen, int realValLen)
{
    LsShmHElemOffs_t valueOff = sizeof(ls_vardata_t) + round4(keyLen)
                                + m_iterExtraSpace;
    int valLen = realValLen + m_dataExtraSpace;
    LsShmHElemLen_t elementSize = sizeof(LsShmHElem) + valueOff
                      + sizeof(ls_vardata_t) + round4(valLen);
    int remapped;
    iteroffset offset;
    offset.m_iOffset = alloc2(elementSize, remapped);
    if (offset.m_iOffset == 0)
        return offset;
    LsShmHElem *pNew = (LsShmHElem *)m_pPool->offset2ptr(offset.m_iOffset);

    pNew->x_iLen = elementSize;
    pNew->x_iValOff = valueOff;
    // pNew->x_iNext.m_iOffset = 0;
    pNew->setKeyLen(keyLen);
    pNew->setValLen(valLen);
    return offset;
}


LsShmHash::iteroffset LsShmHash::insert2(
    LsShmHKey key, ls_strpair_t *pParms)
{
    LsShmHash::iteroffset offset = insertCopy2(key, pParms);
    if (m_pTidMgr != NULL)
        m_pTidMgr->insertIterCb(offset);
    return offset;
}


LsShmHash::iteroffset LsShmHash::insertCopy2(LsShmHKey key,
        ls_strpair_t *pParms)
{
    LsShmHash::iteroffset offset;

    if (size() * fullFactor() > capacity())
    {
        if (rehash() < 0)
        {
            if (size() == capacity())
                return end();
        }
    }

    offset = allocIter(ls_str_len(&pParms->key),
                                     ls_str_len(&pParms->val));
    if (offset.m_iOffset == 0)
        return offset;
    LsShmHElem *pNew = (LsShmHElem *)m_pPool->offset2ptr(offset.m_iOffset);

    // pNew->x_iNext.m_iOffset = 0;
    pNew->x_hkey = key;

    setIterKey(pNew, ls_str_buf(&pParms->key));
    setIterData(pNew, ls_str_buf(&pParms->val));
    if (m_iFlags & LSSHM_FLAG_LRU)
        linkHElem(pNew, offset);

    uint32_t hashIndx = getIndex(key, capacity());
    LsShmHIterOff *pIdx = getHIdx() + hashIndx;
    pNew->x_iNext.m_iOffset = pIdx->m_iOffset;
    pIdx->m_iOffset = offset.m_iOffset;
    setBitMapEnt(hashIndx);

#ifdef DEBUG_RUN
    SHM_NOTICE("LsShmHash::insert %6d %X size %d cap %d <%p> %d",
               getpid(), m_pPool->getShmMap(),
               size(),
               capacity(),
               pIdx,
               hashIndx
              );
#endif
    incrTableSize();

    return offset;
}


LsShmHash::iteroffset LsShmHash::iterGrowValue(iteroffset iterOff,
                                               int size_to_grow, int front)
{
    LsShmHElem *pOld = (LsShmHElem *)m_pPool->offset2ptr(iterOff.m_iOffset);
    int keyLen = pOld->getKeyLen();
    int valLen = pOld->getValLen();
    int valOff = pOld->x_iValOff;
    int newTotalSize = pOld->x_iLen + round4(size_to_grow);
    int remapped;
    iteroffset offset;
    offset.m_iOffset = alloc2(newTotalSize, remapped);
    if (offset.m_iOffset == 0)
        return offset;
    LsShmHElem *pNew = offset2iterator(offset);

    pNew->x_iLen = newTotalSize;
    pNew->x_iValOff = valOff;
    // pNew->x_iNext.m_iOffset = 0;
    pNew->setKeyLen(keyLen);
    pNew->setValLen(valLen + size_to_grow);

    pOld = (LsShmHElem *)m_pPool->offset2ptr(iterOff.m_iOffset);
        // pNew->x_iNext.m_iOffset = 0;
    pNew->x_hkey = pOld->x_hkey;

    setIterKey(pNew, pOld->getKey());
    if (front)
        front = size_to_grow;
    ::memcpy(pNew->getVal() + front, pOld->getVal(), pOld->getValLen());

    eraseIteratorHelper(iterOff);
    if (m_iFlags & LSSHM_FLAG_LRU)
        linkHElem(pNew, offset);
    if (m_pTidMgr != NULL)
    {
        m_pTidMgr->insertIterCb(offset);
        pNew = offset2iterator(offset);
    }

    uint32_t hashIndx = getIndex(pNew->x_hkey, capacity());
    LsShmHIterOff *pIdx = getHIdx() + hashIndx;
    pNew->x_iNext.m_iOffset = pIdx->m_iOffset;
    pIdx->m_iOffset = offset.m_iOffset;
    setBitMapEnt(hashIndx);

    incrTableSize();
    return offset;
}





LsShmHash::iteroffset LsShmHash::findNum(LsShmHash *pThis, ls_strpair_t *pParms)
{
    LsShmHash::iteroffset offset = {0};
    LsShmHKey key = (LsShmHKey)(long)ls_str_buf(&pParms->key);
    uint32_t hashIndx = pThis->getIndex(key, pThis->capacity());
    if (pThis->getBitMapEnt(hashIndx) == 0)     // quick check
        return offset;
    LsShmHIterOff *pIdx = pThis->getHIdx() + hashIndx;
    offset = *pIdx;
    LsShmHElem *pElem;

    while (offset.m_iOffset != 0)
    {
        pElem = pThis->offset2iterator(offset);
        // check to see if the key is the same
        if ((pElem->x_hkey == key) && ((*(LsShmHKey *)pElem->getKey()) == key))
            break;
        offset.m_iOffset = pElem->x_iNext.m_iOffset;
    }
    return offset;
}


LsShmHash::iteroffset LsShmHash::getNum(LsShmHash *pThis,
                                        ls_strpair_t *pParms, int *pFlag)
{
    iteroffset iterOff = findNum(pThis, pParms);
    char *keyptr = ls_str_buf(&pParms->key);
    ls_strpair_t nparms;
    ls_str_set(&nparms.key, (char *)&keyptr, sizeof(LsShmHKey));
    nparms.val = pParms->val;

    return pThis->doGet(iterOff, (LsShmHKey)(long)keyptr, &nparms, pFlag);
}


LsShmHash::iteroffset LsShmHash::insertNum(LsShmHash *pThis,
        ls_strpair_t *pParms)
{
    iteroffset iterOff = findNum(pThis, pParms);
    char *keyptr = ls_str_buf(&pParms->key);
    ls_strpair_t nparms;
    ls_str_set(&nparms.key, (char *)&keyptr, sizeof(LsShmHKey));
    nparms.val = pParms->val;

    return pThis->doInsert(iterOff, (LsShmHKey)(long)keyptr, &nparms);
}


LsShmHash::iteroffset LsShmHash::setNum(LsShmHash *pThis, ls_strpair_t *pParms)
{
    iteroffset iterOff = findNum(pThis, pParms);
    char *keyptr = ls_str_buf(&pParms->key);
    ls_strpair_t nparms;
    ls_str_set(&nparms.key, (char *)&keyptr, sizeof(LsShmHKey));
    nparms.val = pParms->val;

    return pThis->doSet(iterOff, (LsShmHKey)(long)keyptr, &nparms);
}


LsShmHash::iteroffset LsShmHash::updateNum(LsShmHash *pThis,
        ls_strpair_t *pParms)
{
    iteroffset iterOff = findNum(pThis, pParms);
    char *keyptr = ls_str_buf(&pParms->key);
    ls_strpair_t nparms;
    ls_str_set(&nparms.key, (char *)&keyptr, sizeof(LsShmHKey));
    nparms.val = pParms->val;

    return pThis->doUpdate(iterOff, (LsShmHKey)(long)keyptr, &nparms);
}


LsShmHash::iteroffset LsShmHash::findPtr(LsShmHash *pThis,
        ls_strpair_t *pParms)
{
    return pThis->find2((*pThis->m_hf)(
                            ls_str_buf(&pParms->key), ls_str_len(&pParms->key)), pParms);
}


LsShmHash::iteroffset LsShmHash::getPtr(LsShmHash *pThis,
                                        ls_strpair_t *pParms, int *pFlag)
{
    LsShmHKey key = (*pThis->m_hf)(
                        ls_str_buf(&pParms->key), ls_str_len(&pParms->key));
    iteroffset iterOff = pThis->find2(key, pParms);

    return pThis->doGet(iterOff, key, pParms, pFlag);
}


LsShmHash::iteroffset LsShmHash::insertPtr(LsShmHash *pThis,
        ls_strpair_t *pParms)
{
    LsShmHKey key = (*pThis->m_hf)(
                        ls_str_buf(&pParms->key), ls_str_len(&pParms->key));
    iteroffset iterOff = pThis->find2(key, pParms);

    return pThis->doInsert(iterOff, key, pParms);
}


LsShmHash::iteroffset LsShmHash::setPtr(LsShmHash *pThis,
                                        ls_strpair_t *pParms)
{
    LsShmHKey key = (*pThis->m_hf)(
                        ls_str_buf(&pParms->key), ls_str_len(&pParms->key));
    iteroffset iterOff = pThis->find2(key, pParms);

    return pThis->doSet(iterOff, key, pParms);
}


LsShmHash::iteroffset LsShmHash::updatePtr(LsShmHash *pThis,
        ls_strpair_t *pParms)
{
    LsShmHKey key = (*pThis->m_hf)(
                        ls_str_buf(&pParms->key), ls_str_len(&pParms->key));
    iteroffset iterOff = pThis->find2(key, pParms);

    return pThis->doUpdate(iterOff, key, pParms);
}


#ifdef notdef
LsShmHash::iteroffset LsShmHash::doExpand(LsShmHash *pThis,
        iteroffset iterOff, LsShmHKey key, ls_strpair_t *pParms, uint16_t flags)
{
    iterator iter = pThis->offset2iterator(iterOff.m_iOffset);
    int32_t lenExp = ls_str_len(&pParms->value);
    int32_t lenNew = iter->getValLen() + lenExp;
    LSSHM_CHECKSIZE(lenNew);
    if (iter->realValLen() >= (LsShmSize_t)lenNew)
    {
        iter->setValLen(lenNew);
        if (pThis->m_iFlags & LSSHM_FLAG_LRU)
            pThis->linkSetTop(iter);
    }
    else
    {
        // allocate a new iter, copy data, and remove the old
        ls_strpair_t parmsNew;
        iteroffset iterOffNew;
        iterator iterNew;
        iterOffNew = pThis->insert2(key,
                                    pThis->setParms(&parmsNew,
                                            ls_str_buf(&pParms->key), ls_str_len(&pParms->key),
                                            NULL, lenNew));
        iter = pThis->offset2iterator(iterOff.m_iOffset);     // in case of insert remap
        iterNew = pThis->offset2iterator(iterOffNew);
        ::memcpy(iterNew->getVal(), iter->getVal(), iter->getValLen());
        pThis->eraseIteratorHelper(iterOff);
        iterOff = iterOffNew;
        iter = iterNew;
    }
    return iterOff;
}
#endif


LsShmHash::iteroffset LsShmHash::begin()
{
    if (size() == 0)
        return end();

    LsShmHIterOff *p = getHIdx();
    LsShmHIterOff *pIdxEnd = p + capacity();
    while (p < pIdxEnd)
    {
        if (p->m_iOffset != 0)
            return *p;
        ++p;
    }
    return end();
}


LsShmHash::iteroffset LsShmHash::next(iteroffset iterOff)
{
    if (iterOff.m_iOffset == 0)
        return iterOff;
    iterator iter = offset2iterator(iterOff);
    if (iter->x_iNext.m_iOffset != 0)
    {
        if (iter->x_iNext.m_iOffset == iterOff.m_iOffset)
        {
            iter->x_iNext.m_iOffset = 0;
            //assert("looping next offset detected" == 0);
        }
        else
            return iter->x_iNext;
    }
    LsShmHIterOff *p = getHIdx();
    LsShmHIterOff *pIdxEnd = p + capacity();
    p += (getIndex(iter->x_hkey, capacity()) + 1);
    while (p < pIdxEnd)
    {
        if (p->m_iOffset != 0)
        {
#ifdef DEBUG_RUN
            iterator xiter = (iterator)m_pPool->offset2ptr(p->m_iOffset);
            if (xiter != NULL)
            {
                if ((xiter->getKeyLen() == 0)
                    || (xiter->x_hkey == 0)
                    || (xiter->x_iLen == 0))
                {
                    SHM_NOTICE(
                        "LsShmHash::next PROBLEM %6d %X SLEEPING",
                        getpid(), m_pPool->getShmMap());
                    sleep(10);
                }
            }
#endif
            if ((*p).m_iOffset == iterOff.m_iOffset)
            {
                (*p).m_iOffset = 0;
                //assert("looping next offset detected" == 0);
            }
            else
                return *p;
        }
        ++p;
    }
    return end();
}


int LsShmHash::for_each(iteroffset beg, iteroffset end, for_each_fn fun)
{
    if (fun == NULL)
    {
        errno = EINVAL;
        return LS_FAIL;
    }
    int n = 0;
    iteroffset iterNext = beg;
    iteroffset iterOff;
    while (iterNext.m_iOffset != 0)
    {
        iterOff = iterNext;
        iterNext = next(iterNext);      // get next before fun
        if (fun(iterOff) != 0)
            break;
        ++n;
    }
    return n;
}


int LsShmHash::for_each2(
    iteroffset beg, iteroffset end, for_each_fn2 fun, void *pUData)
{
    if (fun == NULL)
    {
        errno = EINVAL;
        return LS_FAIL;
    }
    int n = 0;
    iteroffset iterNext = beg;
    iteroffset iterOff;
    while (iterNext.m_iOffset != 0)
    {
        iterOff = iterNext;
        iterNext = next(iterNext);      // get next before fun
        if (fun(iterOff, pUData) != 0)
            break;
        ++n;
    }
    return n;
}


int LsShmHash::trim(time_t tmCutoff, LsShmHash::TrimCb func, void *arg)
{
    if ((m_iFlags & LSSHM_FLAG_LRU) == 0)
        return LS_FAIL;
    int del = 0;
    LsShmHElem *pElem;
    iteroffset next;
    autoLockChkRehash();
    LsHashLruInfo *pLru = getLru();
    iteroffset offElem = pLru->linkLast;
    while (offElem.m_iOffset != 0)
    {
        int ret = 1;
        if ((m_pTidMgr != NULL) && (m_pTidMgr->checkTidTbl() != 0))
            pLru = getLru();
        pElem = offset2iterator(offElem);
        if (pElem->getLruLasttime() >= tmCutoff)
            break;
        next = pElem->getLruLinkNext();

        if (func != NULL)
        {
            ret = (*func)(pElem, arg);
            if (ret < 0) //Error quit
                break;
        }

        //int ret = clrdata(pElem->getVal());
        if (ret == 1)
        {
            eraseIteratorHelper(offElem);
            ++del;
            pLru->ndataexp += ret;
            pLru->ndataset -= ret;
        }
        else
        {
            linkSetTop(offset2iterator(offElem), offElem);
        }

        offElem = next;
    }
    pLru->nvalexp += del;
    autoUnlock();
    return del;
}

int LsShmHash::trimsize(int need, LsShmHash::TrimCb func, void *arg)
{
    if ((m_iFlags & LSSHM_FLAG_LRU) == 0)
        return LS_FAIL;
    int del = 0;
    LsShmHElem *pElem;
    iteroffset next;
    autoLockChkRehash();
    LsHashLruInfo *pLru = getLru();
    iteroffset offElem = pLru->linkLast;
    while ((offElem.m_iOffset != 0) && (need > 0))
    {
        int ret = 1;
        if ((m_pTidMgr != NULL) && (m_pTidMgr->checkTidTbl() != 0))
            pLru = getLru();
        pElem = offset2iterator(offElem);
        need -= pElem->x_iLen;
        next = pElem->getLruLinkNext();

        if (func != NULL)
            ret = (*func)(pElem, arg);
//         int ret = clrdata(pElem->getVal());
        eraseIteratorHelper(offElem);
        ++del;
        pLru->ndataexp += ret;
        pLru->ndataset -= ret;
        offElem = next;
    }
    pLru->nvalexp += del;
    autoUnlock();
    return del;
}


int LsShmHash::trimByCb(int maxCnt, LsShmHash::TrimCb func, void *arg)
{
    if ((m_iFlags & LSSHM_FLAG_LRU) == 0)
        return LS_FAIL;
    int del = 0;
    LsShmHElem *pElem;
    iteroffset next;
    autoLockChkRehash();
    LsHashLruInfo *pLru = getLru();
    iteroffset offElem = pLru->linkLast;
    while ((offElem.m_iOffset != 0) && (maxCnt > 0))
    {
        int ret = 1;
        if ((m_pTidMgr != NULL) && (m_pTidMgr->checkTidTbl() != 0))
            pLru = getLru();
        pElem = offset2iterator(offElem);
        maxCnt--;
        next = pElem->getLruLinkNext();
        if (func != NULL)
        {
            ret = (*func)(pElem, arg);
            if (ret < 0)
                break;
            if (ret == 0)
            {
                offElem = next;
                continue;
            }
        }
        eraseIteratorHelper(offElem);
        ++del;
        pLru->ndataexp += ret;
        pLru->ndataset -= ret;
        offElem = next;
    }
    pLru->nvalexp += del;
    autoUnlock();
    return del;
}


int LsShmHash::touchLru(iteroffset iterOff)
{
    if ((m_iFlags & LSSHM_FLAG_LRU) == 0)
        return 0;

    autoLockChkRehash();
    linkSetTop(offset2iterator(iterOff), iterOff);
    autoUnlock();

    return 0;
}


void LsShmHash::linkHElem(LsShmHElem *pElem, iteroffset offElem)
{
    assert(m_pPool->getShm()->isLocked(m_pShmLock));
    LsHashLruInfo *pLru = getLru();
    LsShmHElemLink *pLink = pElem->getLruLinkPtr();
    if (pLru->linkFirst.m_iOffset)
    {
        set_linkNext(pLru->linkFirst, offElem);
        pLink->x_iLinkPrev = pLru->linkFirst;
    }
    else
    {
        pLink->x_iLinkPrev.m_iOffset = 0;
        pLru->linkLast = offElem;
    }
    pLink->x_iLinkNext.m_iOffset = 0;
    pLink->x_lasttime = time((time_t *)NULL);
    pLru->linkFirst = offElem;
    ++pLru->nvalset;
}


void LsShmHash::unlinkHElem(LsShmHElem *pElem)
{
    assert(m_pPool->getShm()->isLocked(m_pShmLock));
    LsHashLruInfo *pLru = getLru();
    LsShmHElemLink *pLink = pElem->getLruLinkPtr();
    if (pLink->x_iLinkNext.m_iOffset)
        set_linkPrev(pLink->x_iLinkNext, pLink->x_iLinkPrev);
    else
        pLru->linkFirst = pLink->x_iLinkPrev;
    if (pLink->x_iLinkPrev.m_iOffset)
        set_linkNext(pLink->x_iLinkPrev, pLink->x_iLinkNext);
    else
        pLru->linkLast = pLink->x_iLinkNext;
    --pLru->nvalset;
}

void LsShmHash::linkSetTop(LsShmHElem *pElem, iteroffset offElem)
{
    assert(m_pPool->getShm()->isLocked(m_pShmLock));
    LsShmHElemLink *pLink = pElem->getLruLinkPtr();
    iteroffset next = pLink->x_iLinkNext;
    if (next.m_iOffset != 0)      // not top of list already
    {
        LsHashLruInfo *pLru = getLru();
        iteroffset prev = pLink->x_iLinkPrev;
        if (prev.m_iOffset == 0)  // last one
            pLru->linkLast = next;
        else
            set_linkNext(prev, next);
        set_linkPrev(next, prev);
        pLink->x_iLinkNext.m_iOffset = 0;
        pLink->x_iLinkPrev = pLru->linkFirst;
        set_linkNext(pLru->linkFirst, offElem);
        pLru->linkFirst = offElem;
    }
    pLink->x_lasttime = time((time_t *)NULL);
}



int LsShmHash::linkSetTopTime(iteroffset offset, time_t lasttime)
{
    if (m_iFlags & LSSHM_FLAG_LRU)
    {
        autoLockChkRehash();
        LsShmHElemLink *pLink = offset2iterator(offset)->getLruLinkPtr();
        if ((pLink->x_iLinkNext.m_iOffset != 0) || (lasttime > time((time_t *)NULL)))
        {
            autoUnlock();
            return LS_FAIL;
        }
        iteroffset prev = pLink->x_iLinkPrev;
        if (prev.m_iOffset != 0)
        {
            LsShmHElemLink *pPrev = offset2iterator(prev)->getLruLinkPtr();
            if (lasttime < pPrev->x_lasttime)
                lasttime = pPrev->x_lasttime;
        }
        pLink->x_lasttime = lasttime;
        autoUnlock();
    }
    return LS_OK;
}

int LsShmHash::linkMvTopTime(iteroffset offset, time_t lasttime)
{
    if (m_iFlags & LSSHM_FLAG_LRU)
    {
        autoLockChkRehash();
        LsShmHElemLink *pLink = offset2iterator(offset)->getLruLinkPtr();
        if ((pLink->x_iLinkNext.m_iOffset != 0) || (lasttime <= 0))
            return LS_FAIL;
        pLink->x_lasttime = lasttime;
        iteroffset prev = pLink->x_iLinkPrev;
        if (prev.m_iOffset == 0)  // only one
        {
            autoUnlock();
            return LS_OK;
        }
        LsShmHElemLink *pPrev = offset2iterator(prev)->getLruLinkPtr();
        if (pPrev->x_lasttime <= lasttime)  // prev is older or same time
        {
            autoUnlock();
            return LS_OK;
        }
        LsHashLruInfo *pLru = getLru();
        pPrev->x_iLinkNext.m_iOffset = 0;
        pLru->linkFirst = prev;     // prev is now top
        while (1)
        {
            if (pPrev->x_iLinkPrev.m_iOffset == 0)
            {
                pPrev->x_iLinkPrev = offset;
                pLink->x_iLinkNext = prev;
                pLink->x_iLinkPrev.m_iOffset = 0;
                pLru->linkLast = offset;
                break;
            }
            prev = pPrev->x_iLinkPrev;
            pPrev = offset2iterator(prev)->getLruLinkPtr();
            if (pPrev->x_lasttime <= lasttime)
            {
                pLink->x_iLinkNext = pPrev->x_iLinkNext;
                pLink->x_iLinkPrev = prev;
                pPrev->x_iLinkNext = offset;
                set_linkPrev(pLink->x_iLinkNext, offset);
                break;
            }
        }
        autoUnlock();
    }
    return LS_OK;
}


LsShmHash::iteroffset LsShmHash::nextTmLruIterOff(time_t tmCutoff)
{
    if ((m_iFlags & LSSHM_FLAG_LRU) == 0)
        return end();
    iterator iter;
    iteroffset iterOff = getLru()->linkLast;
    if (tmCutoff > 0)
    {
        while (iterOff.m_iOffset != 0)
        {
            iter = offset2iterator(iterOff);
            if (iter->getLruLasttime() > tmCutoff)
                break;
            iterOff = iter->getLruLinkNext();
        }
    }
    return iterOff;
}


LsShmHash::iteroffset LsShmHash::prevTmLruIterOff(time_t tmCutoff)
{
    if ((m_iFlags & LSSHM_FLAG_LRU) == 0)
        return end();
    iterator iter;
    iteroffset iterOff = getLru()->linkFirst;
    if (tmCutoff > 0)
    {
        while (iterOff.m_iOffset != 0)
        {
            iter = offset2iterator(iterOff);
            if (iter->getLruLasttime() < tmCutoff)
                break;
            iterOff = iter->getLruLinkPrev();
        }
    }
    return iterOff;
}


int LsShmHash::check()
{
    if ((m_iFlags & LSSHM_FLAG_LRU) == 0)
        return SHMLRU_BADINIT;

    int valcnt = 0;
    int datacnt = 0;
    int ret;
    LsShmHElem *pElem;
    autoLockChkRehash();
    LsHashLruInfo *pLru = getLru();
    iteroffset offElem = pLru->linkLast;
    while (offElem.m_iOffset != 0)
    {
        ret = 1;
        pElem = offset2iterator(offElem);
        if (m_pLruAddon && (ret = m_pLruAddon->chkdata(pElem->getVal())) < 0)
        {
            autoUnlock();
            return ret;
        }
        ++valcnt;
        if (m_pLruAddon)
            datacnt += ret;
        offElem = pElem->getLruLinkNext();
    }
    if (valcnt != pLru->nvalset)
        ret = SHMLRU_BADVALCNT;
    else if (datacnt != pLru->ndataset)
        ret = SHMLRU_BADDATACNT;
    else
        ret = SHMLRU_CHECKOK;
    autoUnlock();
    return ret;
}



//
//  @brief statIdx - helper function which return num of elements in this link
//
int LsShmHash::statIdx(iteroffset iterOff, for_each_fn2 fun, void *pUdata)
{
    LsHashStat *pHashStat = (LsHashStat *)pUdata;
#define NUM_SAMPLE  0x20
    typedef struct statKey_s
    {
        LsShmHKey    key;
        int          numDup;
    } statKey_t;
    statKey_t keyTable[NUM_SAMPLE];
    statKey_t *p_keyTable;
    int numKey = 0;
    int curDup = 0; // keep track the number of dup!

    int numInIdx = 0;
    while (iterOff.m_iOffset != 0)
    {
        iterator iter = offset2iterator(iterOff);
        int i;
        p_keyTable = keyTable;
        for (i = 0; i < numKey; ++i, ++p_keyTable)
        {
            if (p_keyTable->key == iter->x_hkey)
            {
                ++p_keyTable->numDup;
                ++curDup;
                break;
            }
        }
        if ((i == numKey) && (i < NUM_SAMPLE))
        {
            p_keyTable->key = iter->x_hkey;
            p_keyTable->numDup = 0;
            ++numKey;
        }

        ++numInIdx;
        if (fun != NULL)
            fun(iterOff, pUdata);
        iterOff = iter->x_iNext;
    }

    pHashStat->numDup += curDup;
    return numInIdx;
}


//
//  @brief stat - populate the statistic of the hash table
//  @brief return num of elements searched.
//  @brief populate the pHashStat.
//
int LsShmHash::stat(LsHashStat *pHashStat, for_each_fn2 fun, void *pData)
{
    if (pHashStat == NULL)
    {
        errno = EINVAL;
        return LS_FAIL;
    }
    ::memset(pHashStat, 0, sizeof(LsHashStat));
    pHashStat->userData = pData;

    autoLockChkRehash();
    // search each idx
    LsShmHIterOff *p = getHIdx();
    LsShmHIterOff *pIdxEnd = p + capacity();
    while (p < pIdxEnd)
    {
        ++pHashStat->numIdx;
        if (p->m_iOffset != 0)
        {
            ++pHashStat->numIdxOccupied;
            int num;
            if ((num = statIdx(*p, fun, (void *)pHashStat)) != 0)
            {
                pHashStat->num += num;
                if (num > pHashStat->maxLink)
                    pHashStat->maxLink = num;

                // top 10 listing
                int topidx;
                if (num <= 5)
                    topidx = num - 1;
                else if (num <= 10)
                    topidx = 5;
                else if (num <= 20)
                    topidx = 6;
                else if (num <= 50)
                    topidx = 7;
                else if (num <= 100)
                    topidx = 8;
                else
                    topidx = 9;
                ++pHashStat->top[topidx];
            }
        }
        ++p;
    }
    autoUnlock();
    return pHashStat->num;
}

