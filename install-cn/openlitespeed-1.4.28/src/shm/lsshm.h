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
#ifndef LSSHM_H
#define LSSHM_H

#include <lsdef.h>
#include <shm/lsshmlock.h>
#include <shm/lsshmtypes.h>
#include "addrmap.h"
#include <util/hashstringmap.h>

#include <assert.h>
#include <stdint.h>
#include <sys/types.h>

/**
 * @file
 * LsShm - LiteSpeed Shared Memory
 */

#define SHM_DBG(format, ...) \
    LOG4CXX_NS::Logger::getRootLogger()->debug(format, ##__VA_ARGS__ )

#define SHM_NOTICE(format, ...) \
    LOG4CXX_NS::Logger::getRootLogger()->notice(format, ##__VA_ARGS__ )

#define SHM_WARN(format, ...) \
    LOG4CXX_NS::Logger::getRootLogger()->warn(format, ##__VA_ARGS__ )

    
#ifdef LSSHM_DEBUG_ENABLE
class debugBase;// These two should be the same size...
#endif
class LsShmPool;
class LsShmHash;

#define LSSHM_OPEN_STD      0x00
#define LSSHM_OPEN_NEW      0x01


//
// LiteSpeed Shared Memory Map
//
//  +------------------------------------------------
//  | HEADER
//  |    --> maxSize      --------------------------+
//  |    --> offset free  ----------------+         |
//  |    --> offset xdata ------+         |         |
//  |           size of xdata   |         |         |
//  |-------------------------- |         |         |
//  | xdata area          <-----+         |         |
//  |-------------------------            |         |
//  | Free area           <---------------+         |
//  |-------------------------  <-------------------+
//

typedef struct
{
    uint16_t          x_iRegNum;   // max 64k registry
    uint16_t          x_iFlag;     // 0x1 - assigned
    LsShmOffset_t     x_iValue;    // offset
} LsShmReg;

#define LSSHM_REGFLAG_CLR       0x0000
#define LSSHM_REGFLAG_SET       0x0001
#define LSSHM_REGFLAG_PID       0x0002

typedef struct
{
    LsShmXSize_t      m_iFileSize;          // file size (bytes)
    LsShmXSize_t      m_iUsedSize;          // file size allocated (bytes)
} LsShmMapStat;

typedef struct ls_shmmap_s LsShmMap;

/*
 *   data struct all the library routines to access the map
 */
class LsShm : public ls_shm_s
{
public:
    static LsShm *open(const char *mapName, LsShmXSize_t initSize,
                       const char *pBaseDir = NULL, 
                       int mode = LSSHM_OPEN_STD, LsShmXSize_t addrMapSize = 0);
    
    int chperm(int uid, int gid, int mask);
    
    void close();

    void deleteFile();


private:
    LsShm(const char *pMapName);
    ~LsShm();

public:

    static const char *detectDefaultRamdisk();
    static LsShmStatus_t checkDirSpace(const char *dirName);
    static LsShmStatus_t addBaseDir(const char *dirName);
    static int getBaseDirCount()        {   return s_iNumBaseDir;   }
    static int deleteFile(const char *pName, const char *pBaseDir);
    
    static LsShmStatus_t setErrMsg(LsShmStatus_t stat, const char *fmt, ...);
    static LsShmStatus_t getErrStat()   {   return s_errStat;   }
    static int getErrNo()               {   return s_iErrNo;    }
    static const char *getErrMsg()      {   return s_aErrMsg;   }
    static void clrErrMsg()
    {
        s_errStat = LSSHM_OK;
        s_iErrNo = 0;
        s_aErrMsg[0] = '\0';
    }

    static void logError(const char * pMsg);
    static void setFatalErrorHandler( void (*cb)() );

    void setShmMaxSize(LsShmXSize_t size)
    {
        m_iMaxShmSize = size > LSSHM_MINSPACE ? size : LSSHM_MINSPACE;
    }

    LsShmXSize_t shmMaxSize() const {   return m_iMaxShmSize;   }
    LsShmXSize_t maxSize() const    {   return x_pStats->m_iFileSize;   }
    LsShmXSize_t oldMaxSize() const {   return m_iMaxSizeO;     }
    const char *fileName() const    {   return m_pFileName;     }
    const char *mapName() const     {   return obj.m_pName;      }

    ls_attr_inline LsShmMap *getShmMap() const
    {
        return x_pShmMap;
    }

    int getfd() const   {   return m_iFd;   }
    
    LsShmMapStat *getMapStat() const    {   return x_pStats;    }

    LsShmOffset_t getMapStatOffset() const;

    LsShmOffset_t allocPage(LsShmSize_t pagesize, int &remapped);
    int reserveAddrSpace(LsShmSize_t total)
    {   return m_addrMap.mapAddrSpace(total);  }

    LsShmPool *getGlobalPool();
    LsShmPool *getNamedPool(const char *pName);

    LsShmHash *getGlobalHash(int initSize);

    void *offset2ptr(LsShmOffset_t offset)
    {
        if (offset < 32)    //sizeof(LsShmMap)
            return NULL;
        if (offset > m_iMaxSizeO)
        {
            tryRecoverBadOffset(offset);
        }
        return (void *)m_addrMap.offset2ptr(offset);
    }  // map size

    int isOffsetValid(LsShmOffset_t offset);

    LsShmOffset_t ptr2offset(const void *ptr) const
    {
        if (ptr == NULL)
            return 0;
        return m_addrMap.ptr2offset(ptr);
    }

    LsShmXSize_t avail() const
    {   return x_pStats->m_iFileSize - x_pStats->m_iUsedSize;   }

    LsShmStatus_t status() const        {   return m_status;    }

    LsShmOffset_t xdataOffset() const   {   return (LsShmOffset_t)s_iShmHdrSize;    }

    LsShmLock *getLocks()               {   return &m_locks;    }

    LsShmOffset_t allocLock()           {   return m_locks.allocLock();     }
    int freeLock(ls_shmlock_t *pLock)   {   return m_locks.freeLock(pLock); }

    ls_shmlock_t *offset2pLock(LsShmOffset_t offset) const
    {   return m_locks.offset2pLock(offset);    }

    ls_attr_inline int lockRemap(ls_shmlock_t *pLock)
    {
        int ret = ls_shmlock_lock(pLock);
        chkRemap();
        return ret;
    }

    ls_attr_inline int isLocked(ls_shmlock_t *pLock)
    {
        return ls_shmlock_locked(pLock);
    }
    
    ls_attr_inline LsShmStatus_t chkRemap()
    {
        return (x_pStats->m_iFileSize == m_iMaxSizeO) ? LSSHM_OK : remap();
    }

    LsShmStatus_t remap();

    //
    //   registry
    //
    LsShmOffset_t  findRegOff(const char *name);
    LsShmOffset_t  addRegOff(const char *name);
    LsShmReg      *findReg(const char *name);
    LsShmReg      *addReg(const char *name);
    void           delReg(const char *name);

    int            recoverOrphanShm();

    HashStringMap < ls_shmobject_t *> &getObjBase()
    {
        return m_objBase;
    }

#ifdef LSSHM_DEBUG_ENABLE
    // for debug purpose
    friend class debugBase;
#endif

private:
    LsShm(const LsShm &other);
    LsShm &operator=(const LsShm &other);
    bool operator==(const LsShm &other);

    LsShmStatus_t   expand(LsShmXSize_t incrSize);

    ls_attr_inline int lock()
    {
        return lockRemap(m_pShmLock);
    }

    int unlock()
    {
        return ls_shmlock_unlock(m_pShmLock);
    }

    LsShmStatus_t setupLocks()
    {
        return (ls_shmlock_setup(m_pShmLock)) ? LSSHM_ERROR : LSSHM_OK;
    }

    void tryRecoverBadOffset(LsShmOffset_t offset);

    // only use by physical mapping
    LsShmXSize_t roundToPageSize(LsShmXSize_t size) const
    {
        return ((size + s_iPageSize - 1) / s_iPageSize) * s_iPageSize;
    }

    LsShmSize_t roundUnitSize(LsShmSize_t pagesize) const
    {
        return ((pagesize + (LSSHM_SHM_UNITSIZE - 1))
                / LSSHM_SHM_UNITSIZE) * LSSHM_SHM_UNITSIZE;
    }

    void used(LsShmSize_t size)
    {
        x_pStats->m_iUsedSize += size;
    }

    LsShmStatus_t   mapAddrMap(LsShmXSize_t size);

    void            cleanup();
    LsShmStatus_t   checkMagic(LsShmMap *mp, const char *mName) const;
    LsShmStatus_t   initShm(const char *mapName, LsShmXSize_t initialSize,
                            const char *pBaseDir, int mode);
    LsShmStatus_t   openLockShmFile(int mode);

    LsShmStatus_t   expandFile(LsShmOffset_t from, LsShmXSize_t incrSize);
    void            unmap();
    static LsShm   *getExisting(const char *dirName);

    LsShmStatus_t newShmMap(LsShmSize_t size, uint64_t id);

    static int chkReg(LsShmHIterOff iterOff, void *pUData);

    // various objects within the SHM
    HashStringMap < ls_shmobject_t *> m_objBase;

    LsShmLock               m_locks;
    uint32_t                m_iMagic;
    static LsShmSize_t      s_iPageSize;
    static LsShmSize_t      s_iShmHdrSize;
    static const char      *s_pDirBase[5];
    static int              s_iNumBaseDir;
    static LsShmStatus_t    s_errStat;
    static int              s_iErrNo;
    static char             s_aErrMsg[];
    LsShmXSize_t            m_iMaxShmSize;

    LsShmStatus_t           m_status;
    char                   *m_pFileName;    // dir + mapName + ext
    int                     m_iFd;
    ls_shmlock_t           *m_pShmLock;

    LsShmMap               *x_pShmMap;
    LsShmXSize_t            m_iMaxSizeO;
    LsShmMapStat           *x_pStats;

    LsShmPool              *m_pGPool;
    LsShmHash              *m_pGHash;
    int                     m_iRef;
    AddrMap                 m_addrMap;
};

#endif
