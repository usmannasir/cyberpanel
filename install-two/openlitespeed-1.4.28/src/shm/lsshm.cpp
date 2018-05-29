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
#include <shm/lsshm.h>

#include <log4cxx/logger.h>
#include <lsr/ls_memcheck.h>
#include <shm/lsshmpool.h>
#include <shm/lsshmhash.h>
#include <util/gpath.h>

#include <fcntl.h>
#include <stdarg.h>
#include <string.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/time.h>


extern "C" {

/*
 *   ls_expandfile - expanding current file
 *   return 0 if file expanded
 *   otherwise return -1
 *
 *   if incrsize < 0 the file will be reduced.
 */
int ls_expandfile(int fd, LsShmOffset_t fromsize, LsShmXSize_t incrsize)
{
    LsShmOffset_t fromloc;
    int pagesize = getpagesize();
    LsShmOffset_t newsize = fromsize + incrsize;

    if (ftruncate(fd, (off_t)newsize) < 0)
        return LS_FAIL;

    if (newsize <= fromsize)
        return 0;

    fromloc = fromsize++;
    do
    {
        if (pwrite(fd, "", 1, fromsize) != 1)
        {
            ftruncate(fd, (off_t)fromloc);
            return LS_FAIL;
        }
        fromsize += pagesize;
    }
    while (fromsize < newsize);
    return 0;
}

};


typedef union
{
    struct
    {
        uint8_t     m_iMajor;
        uint8_t     m_iMinor;
        uint8_t     m_iRel;
        uint8_t     m_iType;
    } x;
    uint32_t    m_iVer;
} LsShmVersion;


struct ls_shmmap_s
{
    uint32_t          x_iMagic;
    LsShmVersion      x_version;
    uint64_t          x_id;
    LsShmOffset_t     x_iLockOffset;
    LsShmOffset_t     x_globalHashOff;
    LsShmMapStat      x_stat;               // map statistics
};



LsShmVersion s_version =
{
    { LSSHM_VER_MAJOR, LSSHM_VER_MINOR, LSSHM_VER_REL, LSSHM_VER_TYPE }
};
LsShmSize_t LsShm::s_iPageSize = LSSHM_PAGESIZE;
LsShmSize_t LsShm::s_iShmHdrSize = ((sizeof(LsShmMap) + 0xf) &
                                    ~0xf); // align 16
const char *LsShm::s_pDirBase[] = {NULL, NULL, NULL, NULL, NULL};
int LsShm::s_iNumBaseDir = 0;
LsShmStatus_t LsShm::s_errStat = LSSHM_OK;
int LsShm::s_iErrNo = 0;
char LsShm::s_aErrMsg[LSSHM_MAXERRMSG] = { 0 };


//
//  house keeping stuff
//
// LsShm *LsShm::s_pBase = NULL;
static HashStringMap< LsShm * > *s_pBase = NULL;


static inline HashStringMap< LsShm * > *getBase()
{
    if (s_pBase == NULL)
        s_pBase = new HashStringMap< LsShm * >();
    return s_pBase;
}


//
//  @brief setErrMsg - set the global static error message
//
LsShmStatus_t LsShm::setErrMsg(LsShmStatus_t stat, const char *fmt, ...)
{
    int ret;
    va_list va;

    s_errStat = stat;
    s_iErrNo = errno;
    va_start(va, fmt);
    ret = vsnprintf(s_aErrMsg, LSSHM_MAXERRMSG, fmt, va);
    va_end(va);
    if (ret >= LSSHM_MAXERRMSG)
        strcpy(&s_aErrMsg[LSSHM_MAXERRMSG - 4], "...");
    return LSSHM_OK;
}


void LsShm::logError(const char * pMsg)
{
    const char *pErrStr = getErrMsg();
    LOG4CXX_NS::Logger::getRootLogger()->error("[SHM] %s: %s",
                                               pMsg?pMsg:"", pErrStr);
    clrErrMsg();
}


LsShm::LsShm(const char *pMapName)
    : m_locks()
    , m_iMagic(LSSHM_MAGIC)
    , m_iMaxShmSize(0)
    , m_status(LSSHM_NOTREADY)
    , m_pFileName(NULL)
    , m_iFd(-1)
    , m_pShmLock(NULL)
    , x_pShmMap(NULL)
    , m_iMaxSizeO(0)
    , m_pGPool(NULL)
    , m_pGHash(NULL)
    , m_iRef(0)
{
    obj.m_pName = strdup(pMapName);
}


LsShm::~LsShm()
{
    if (m_pFileName != NULL)
    {
#ifdef DEBUG_RUN
        SHM_NOTICE("LsShm::~LsShm remove %s <%p>", m_pFileName, s_pBase);
#endif
        getBase()->remove(m_pFileName);
    }
    cleanup();
    if (m_pGPool)
        delete m_pGPool;
}


static void (*s_fatalErrorCb)() = NULL;

void LsShm::setFatalErrorHandler( void (*cb)() )
{
    s_fatalErrorCb = cb;
}


void LsShm::tryRecoverBadOffset(LsShmOffset_t offset)
{
    if (x_pShmMap->x_stat.m_iFileSize > offset)
    {
        remap();
        return;
    }
    deleteFile();
    if (s_fatalErrorCb)
        (*s_fatalErrorCb)();
    LsShmSize_t curMaxSize = x_pShmMap->x_stat.m_iFileSize; 
    if ( offset < curMaxSize)
    {
        assert(offset < curMaxSize);
    }
}


int LsShm::isOffsetValid(LsShmOffset_t offset)
{
    return (offset <= x_pShmMap->x_stat.m_iFileSize);
}


LsShmOffset_t LsShm::getMapStatOffset() const
{
    return (LsShmOffset_t)(long) & ((LsShmMap *)0)->x_stat;
}


static int lockFile(int fd, short lockType = F_WRLCK)
{
    int ret;
    struct flock lock;
    lock.l_type = lockType;
    lock.l_start = 0;
    lock.l_whence = SEEK_SET;
    lock.l_len = 0;
    while (1)
    {
        ret = fcntl(fd, F_SETLKW, &lock);
        if ((ret == -1) && (errno == EINTR))
            continue;
        return ret;
    }
}


const char *LsShm::detectDefaultRamdisk()
{
#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
    return "/dev/shm";
#else
    return NULL;
#endif
}


LsShmStatus_t LsShm::checkDirSpace(const char *dirName)
{
    struct statvfs st;
    off_t iDirBlocks, iMinBlocks;
    if (statvfs(dirName, &st) != 0)
        return LSSHM_BADPARAM;
    iMinBlocks = LSSHM_MINDIRSPACE / st.f_bsize;
    iDirBlocks = st.f_bfree;
    if (iDirBlocks < iMinBlocks)
        return LSSHM_BADPARAM;
    return LSSHM_OK;
}


LsShmStatus_t LsShm::addBaseDir(const char *dirName)
{
    if ((s_pDirBase[s_iNumBaseDir] = strdup(dirName)) == NULL)
        return LSSHM_SYSERROR;
    ++s_iNumBaseDir;
    return LSSHM_OK;
}


LsShm *LsShm::getExisting(const char *dirName)
{
    LsShm *pObj;
    GHash::iterator itor;
    itor = getBase()->find(dirName);
    if (itor == NULL)
        return NULL;
    pObj = (LsShm *)itor->second();
    ++pObj->m_iRef;
    return pObj;
}


LsShm *LsShm::open(const char *mapName, LsShmXSize_t initsize,
                   const char *pBaseDir, int mode,
                   LsShmXSize_t addrMapSize)
{
    int i;
    LsShm *pObj;
    char buf[0x1000] = "";

    if (mapName == NULL)
        return NULL;

    if (pBaseDir != NULL)
    {
        snprintf(buf, sizeof(buf), "%s/%s.%s", pBaseDir, mapName,
                 LSSHM_SYSSHM_FILE_EXT);
        if ((pObj = getExisting(buf)) != NULL)
            return pObj;
    }
    else
    {
        for (i = 0; i < getBaseDirCount(); ++i)
        {
            snprintf(buf, sizeof(buf), "%s/%s.%s", s_pDirBase[i], mapName,
                     LSSHM_SYSSHM_FILE_EXT);
            if ((pObj = getExisting(buf)) != NULL)
                return pObj;
        }
    }

    LsShmStatus_t stat;
    pObj = new LsShm(mapName);
    if (pObj != NULL)
    {
        if (addrMapSize > 0)
            pObj->reserveAddrSpace(addrMapSize);
        stat = pObj->initShm(mapName, initsize, pBaseDir, mode);
        if (pObj->m_iFd != -1)
            lockFile(pObj->m_iFd, F_UNLCK);
        if (stat == LSSHM_OK)
            return pObj;

        if (stat == LSSHM_BADVERSION)
            pObj->deleteFile();
        delete pObj;
    }
    else
        stat = LSSHM_SYSERROR;
    if (*getErrMsg() == '\0')       // if no error message, set generic one
        setErrMsg(stat, "Unable to setup SHM MapFile [%s].", buf);

    return NULL;
}


LsShmStatus_t LsShm::checkMagic(LsShmMap *mp, const char *mName) const
{
    return ((mp->x_iMagic != m_iMagic)
            || (mp->x_version.m_iVer != s_version.m_iVer)) ?
           LSSHM_BADMAPFILE : LSSHM_OK;
}


void LsShm::deleteFile()
{
    if (m_pFileName != NULL)
        unlink(m_pFileName);
}


int LsShm::deleteFile(const char *pName, const char *pBaseDir)
{
    char buf[0x1000];
    struct stat st;
    if (pBaseDir != NULL)
    {
        snprintf(buf, sizeof(buf), "%s/%s.%s", pBaseDir, pName,
                 LSSHM_SYSSHM_FILE_EXT);
        if (stat(buf, &st) == 0)
        {
            unlink(buf);
            return 1;
        }
    }
    for (int i = 0; i < getBaseDirCount(); ++i)
    {
        snprintf(buf, sizeof(buf), "%s/%s.%s", s_pDirBase[i], pName,
                    LSSHM_SYSSHM_FILE_EXT);
        if (stat(buf, &st) == 0)
        {
            unlink(buf);
            return 1;
        }
    }
    return 0;
}


int LsShm::chperm(int uid, int gid, int mask)
{
    int ret = 0;
    if (mask > 0)
    {
        ret = fchmod(m_iFd, mask);
        fchmod( m_locks.getfd(), mask);
    }
    if (ret != -1 && uid > 0)
    {
        ret = fchown(m_iFd, uid, gid);
        fchown( m_locks.getfd(), uid, gid);
    }
    return ret;
}



void LsShm::close()
{
    if (--m_iRef == 0)
    {
        if (m_pGHash)
            delete m_pGHash;
        delete this;
    }
}


void LsShm::cleanup()
{
    unmap();
    if (m_iFd != -1)
    {
        ::close(m_iFd);
        m_iFd = -1;
    }
    if (m_pFileName != NULL)
    {
        free(m_pFileName);
        m_pFileName = NULL;
    }
    if (obj.m_pName != NULL)
    {
        free(obj.m_pName);
        obj.m_pName = NULL;
    }
}


//
// expand the file to a particular size
//
LsShmStatus_t LsShm::expandFile(LsShmOffset_t from, LsShmXSize_t incrSize)
{
    if (m_iMaxShmSize && ((from + incrSize) > m_iMaxShmSize))
        return LSSHM_BADMAXSPACE;

    if ((from + incrSize) < from)   // wrapped
    {
        setErrMsg(LSSHM_BADMAXSPACE,
                  "Unable to expand [%s], Exceeded internal data size [%lld].",
                  m_pFileName, (uint64_t)from + (uint64_t)incrSize);
        return LSSHM_BADMAXSPACE;
    }

    if (ls_expandfile(m_iFd, from, incrSize) < 0)
    {
        setErrMsg(LSSHM_BADNOSPACE, "Unable to expand [%s], incr=%lu, %s.",
                  m_pFileName, (unsigned long)incrSize, strerror(errno));
        return LSSHM_BADNOSPACE;
    }
    return LSSHM_OK;
}


LsShmStatus_t LsShm::openLockShmFile(int mode)
{
    if (mode & LSSHM_OPEN_NEW)
        unlink(m_pFileName);
    if ((m_iFd = ::open(m_pFileName, O_RDWR | O_CREAT, 0640)) < 0)
    {
        if ((GPath::createMissingPath(m_pFileName, 0755) < 0)
            || ((m_iFd = ::open(m_pFileName, O_RDWR | O_CREAT, 0640)) < 0))
        {
            setErrMsg(LSSHM_SYSERROR, "Unable to open/create [%s], %s.",
                      m_pFileName, strerror(errno));
            return LSSHM_BADMAPFILE;
        }
    }

    ::fcntl(m_iFd, F_SETFD, FD_CLOEXEC);
    lockFile(m_iFd);
    return LSSHM_OK;
}


LsShmStatus_t LsShm::newShmMap(LsShmSize_t size, uint64_t id)
{
    if (size < s_iPageSize)
        size = s_iPageSize;
    if ((expandFile(0, roundToPageSize(size)) != LSSHM_OK)
        || (mapAddrMap(size) != LSSHM_OK))
        return LSSHM_ERROR;
    x_pShmMap->x_id     = id;
    x_pShmMap->x_globalHashOff = 0;
    x_pShmMap->x_stat.m_iFileSize = size;               // x_iMaxSize
    x_pShmMap->x_stat.m_iUsedSize = LSSHM_SHM_UNITSIZE; // x_iCurSize

    if (((x_pShmMap->x_iLockOffset = allocLock()) == 0)
        || (m_pShmLock = offset2pLock(x_pShmMap->x_iLockOffset)) == NULL
        || (setupLocks() != LSSHM_OK))
        return LSSHM_ERROR;

    MEMCHK_UNPOISON(&(x_pShmMap->x_iMagic), 8);
    x_pShmMap->x_version.m_iVer = s_version.m_iVer;
    x_pShmMap->x_iMagic = m_iMagic;
    MEMCHK_POISON(&(x_pShmMap->x_iMagic), 8);

    return LSSHM_OK;
}


LsShmStatus_t LsShm::initShm(const char *mapName, LsShmXSize_t size,
                             const char *pBaseDir, int mode)
{
    int i = 0;
    struct stat     mystat;
    char            buf[0x1000];
    struct timeval  tv;
    uint64_t        id = 0;

    // m_status = LSSHM_NOTREADY;

    if (pBaseDir != NULL)
    {
        snprintf(buf, sizeof(buf), "%s/%s.%s", pBaseDir, mapName,
                 LSSHM_SYSSHM_FILE_EXT);
        m_pFileName = buf;
        if (openLockShmFile(mode) != LSSHM_OK)
        {
            m_pFileName = NULL;
            return LSSHM_BADMAPFILE;
        }
    }
    else
    {
        for (i = 0; i < getBaseDirCount(); ++i)
        {
            snprintf(buf, sizeof(buf), "%s/%s.%s", s_pDirBase[i], mapName,
                     LSSHM_SYSSHM_FILE_EXT);
            m_pFileName = buf;
            if (openLockShmFile(mode) == LSSHM_OK)
                break;
        }
        if (i == getBaseDirCount())
        {
            m_pFileName = NULL;
            return LSSHM_BADMAPFILE;
        }
    }

    if ((m_pFileName = strdup(buf)) == NULL)
    {
        m_status = LSSHM_ERROR;
        return m_status;
    }

    size = ((size + s_iPageSize - 1) / s_iPageSize) * s_iPageSize;

    if (fstat(m_iFd, &mystat) < 0)
    {
        setErrMsg(LSSHM_SYSERROR, "Unable to stat [%s], %s.",
                  m_pFileName, strerror(errno));
        return LSSHM_BADMAPFILE;
    }

    snprintf(buf, sizeof(buf), "%s/%s.%s",
             (pBaseDir != NULL) ? pBaseDir : s_pDirBase[i],
             mapName, LSSHM_SYSLOCK_FILE_EXT);

    if (mystat.st_size == 0)
    {
        gettimeofday(&tv, NULL);
        id = tv.tv_sec * 1000000 + tv.tv_usec;
        unlink(buf);
    }

    int fdLock = ::open(buf, O_RDWR | O_CREAT, 0640);
    if (fdLock == -1
        || (m_status = m_locks.init(buf, fdLock, LSSHM_MINLOCK, id)) != LSSHM_OK)
    {
        if (*getErrMsg() == '\0')       // if no error message, set generic one
            setErrMsg(LSSHM_BADMAPFILE, "Unable to set SHM LockFile for [%s].", buf);
        return m_status;
    }
    ::fcntl(fdLock, F_SETFD, FD_CLOEXEC);

    if (mystat.st_size == 0)
    {
        LsShmStatus_t ret = newShmMap(size, id);
        if (ret != LSSHM_OK)
            return ret;
    }
    else
    {
        // Old File
        if (mystat.st_size < s_iShmHdrSize)
        {
            setErrMsg(LSSHM_BADMAPFILE, "Bad SHM file format [%s], size=%lld.",
                      m_pFileName, (uint64_t)mystat.st_size);
            return LSSHM_BADMAPFILE;
        }

        // only map the header size to ensure the file is good.
        LsShmMap * pShmMap = (LsShmMap *)mmap(0, (size_t)s_iShmHdrSize, 
                                              PROT_READ | PROT_WRITE, 
                                              MAP_SHARED, m_iFd, 0);
        if (pShmMap == MAP_FAILED)
        {
            setErrMsg(LSSHM_SYSERROR, "Unable to mmap [%s], size=%lu, %s.",
                    m_pFileName, (unsigned long)size, strerror(errno));
            return LSSHM_SYSERROR;
        }

        if (checkMagic(pShmMap, obj.m_pName) != LSSHM_OK)
        {
            setErrMsg(LSSHM_BADVERSION,
                      "Bad SHM file format [%s], size=%lld, magic=%08X(%08X).",
                      m_pFileName, (uint64_t)mystat.st_size,
                      pShmMap->x_iMagic, m_iMagic);
            return LSSHM_BADVERSION;
        }

        i = pShmMap->x_iMagic;
        
        if (pShmMap->x_id != m_locks.getId())
        {
            setErrMsg(LSSHM_BADVERSION,
                      "SHM file [%s] ID=%lld, LOCK file ID=%lld.",
                      m_pFileName, pShmMap->x_id, m_locks.getId());
            return LSSHM_BADVERSION;
        }

        if (pShmMap->x_stat.m_iFileSize != mystat.st_size)
        {
            SHM_WARN("SHM file [%s] size: %lld, does not match x_stat.m_iFileSize: %ld, correct it",
                     m_pFileName, mystat.st_size, pShmMap->x_stat.m_iFileSize);
            pShmMap->x_stat.m_iFileSize = mystat.st_size;
        }
        
        // expand the file if needed... won't shrink
        if (size > pShmMap->x_stat.m_iFileSize)
        {
            if (expandFile((LsShmOffset_t)pShmMap->x_stat.m_iFileSize,
                           (LsShmXSize_t)(size - pShmMap->x_stat.m_iFileSize)) != LSSHM_OK)
                return LSSHM_ERROR;
            pShmMap->x_stat.m_iFileSize = size;
        }
        else
            size = mystat.st_size;
        munmap(pShmMap, (size_t)s_iShmHdrSize);

        if (mapAddrMap(size) != LSSHM_OK)
            return LSSHM_ERROR;

        if (x_pShmMap->x_iLockOffset == 0)
            x_pShmMap->x_iLockOffset = allocLock();
        if (x_pShmMap->x_iLockOffset != 36)
        {
            SHM_WARN("SHM file [%s] bad lock offset: %lld, it should be always 36, correct it",
                     m_pFileName, x_pShmMap->x_iLockOffset);
            x_pShmMap->x_iLockOffset = 36;
        }
        
        m_pShmLock = offset2pLock(x_pShmMap->x_iLockOffset);
    }

    getGlobalPool();
    m_status = LSSHM_READY;
    m_iRef = 1;
    getBase()->insert(m_pFileName, this);

    return LSSHM_OK;
}


// will not shrink at the current moment
LsShmStatus_t LsShm::expand(LsShmXSize_t incrSize)
{
    LsShmXSize_t xsize = x_pShmMap->x_stat.m_iFileSize;

    if (expandFile((LsShmOffset_t)xsize, incrSize) != LSSHM_OK)
        return LSSHM_ERROR;

    //unmap();
    xsize += incrSize;
    x_pShmMap->x_stat.m_iFileSize = xsize;
    
    if (mapAddrMap(xsize) != LSSHM_OK)
    {
        return LSSHM_ERROR;
    }

    return LSSHM_OK;
}


LsShmStatus_t LsShm::mapAddrMap(LsShmXSize_t size)
{
    if (m_addrMap.remap(m_iFd, m_iMaxSizeO, size) == LS_FAIL)
    {
        setErrMsg(LSSHM_SYSERROR, "Unable to mmap [%s], old map size = %lu, size=%lu, %s.",
                  m_pFileName, (unsigned long)m_iMaxSizeO, (unsigned long)size, strerror(errno));
        return LSSHM_SYSERROR;
        
    }
    if (m_iMaxSizeO == 0)
    {
        x_pShmMap = (LsShmMap *)m_addrMap.offset2ptr(0);
        x_pStats = &x_pShmMap->x_stat;
        MEMCHK_POISON(&(x_pShmMap->x_iMagic), 8);
    }
    m_iMaxSizeO = size;
    return LSSHM_OK;
}


LsShmStatus_t LsShm::remap()
{
#ifdef DEBUG_RUN
    SHM_NOTICE("LsShm::remap %6d %X %X %X",
               getpid(), x_pShmMap, x_pShmMap->x_stat.m_iFileSize, m_iMaxSizeO);
#endif
    struct stat mystat;
    if (fstat(m_iFd, &mystat) < 0)
        return LSSHM_BADMAPFILE;
    if (mystat.st_size != x_pShmMap->x_stat.m_iFileSize)
    {
        setErrMsg(LSSHM_SYSERROR, "%s: real file size: %lu, SHM stats file size: %lu.",
                  m_pFileName, (unsigned long)mystat.st_size, 
                  (unsigned long)x_pShmMap->x_stat.m_iFileSize);
        if ( x_pShmMap->x_stat.m_iFileSize - mystat.st_size > 100 * 1024 * 1024)
        {
            LsShmMap mapCopy = *x_pShmMap;
            deleteFile();
            if (s_fatalErrorCb)
                (*s_fatalErrorCb)();
            
            assert( "bad file size." == (char *)&mapCopy);
        }
    }
    LsShmXSize_t size = x_pShmMap->x_stat.m_iFileSize;
    //unmap();
    return mapAddrMap(size);
}


void LsShm::unmap()
{
    if (x_pShmMap != NULL)
    {
        m_addrMap.unmap();
        x_pShmMap = NULL;
        x_pStats = NULL;
        m_iMaxSizeO = 0;
    }
}


LsShmOffset_t LsShm::allocPage(LsShmSize_t pagesize, int &remap)
{
    LsShmOffset_t offset;
    LsShmSize_t availSize;

    remap = 0;

    //
    //  MUTEX SHOULD BE HERE for multi process/thread environment
    // Only use lock when m_status is Ready.
    if (m_status == LSSHM_READY)
        if (lock() > 0)
            return 0; // no lock acquired...

    // Allocate from heap space
    availSize = avail();
    if (pagesize > availSize)
    {
        LsShmXSize_t needSize;
        // min 16 unit at a time

        LsShmSize_t availAddrSize = m_addrMap.getAvailAddrSpace(
            x_pShmMap->x_stat.m_iUsedSize, pagesize);
        LS_DBG("[SHM] [PID:%d] To alloc page: %d bytes at offset: %ld, availAddr: %d\n",
                getpid(), pagesize, (long)x_pShmMap->x_stat.m_iUsedSize, availAddrSize);
        needSize = (pagesize - availSize);
        if (pagesize > availAddrSize)
        {
            needSize += availAddrSize; 
        }
        LsShmXSize_t targetSize = x_pShmMap->x_stat.m_iFileSize + needSize;
        targetSize = (targetSize + (16 * LSSHM_SHM_UNITSIZE - 1)) &
                        ~(16 * LSSHM_SHM_UNITSIZE - 1);
        
        if (expand(targetSize - x_pShmMap->x_stat.m_iFileSize) != LSSHM_OK)
        {
            offset = 0;
            goto out;
        }
        if (pagesize > availAddrSize)
        {
            m_pGPool->addLeftOverPages(x_pShmMap->x_stat.m_iUsedSize, 
                                       availAddrSize);
            used(availAddrSize);
        }
    }
    offset = x_pShmMap->x_stat.m_iUsedSize;
    used(pagesize);
out:
    if (m_status == LSSHM_READY)
        unlock();
    return offset;
}


int LsShm::recoverOrphanShm()
{
    if ((getGlobalPool() == NULL) || (m_pGHash == NULL))
        return 0;

    m_pGHash->disableAutoLock();
    m_pGHash->lockChkRehash();
    LsShmSize_t size = m_pGHash->size();
    m_pGHash->for_each2(m_pGHash->begin(), m_pGHash->end(), chkReg, this);
    size -= m_pGHash->size();
    m_pGHash->unlock();
    m_pGHash->enableAutoLock();
    return (int)size;
}


int LsShm::chkReg(LsShmHIterOff iterOff, void *pUData)
{
    LsShmReg *pReg =
        (LsShmReg *)((LsShm *)pUData)->m_pGHash->offset2iteratorData(iterOff);
    if (pReg->x_iFlag & LSSHM_REGFLAG_PID)
    {
        LsShmPoolMem *pPool =
            (LsShmPoolMem *)((LsShm *)pUData)->offset2ptr(pReg->x_iValue);
        LsShmPool *pGPool = ((LsShm *)pUData)->m_pGPool;
        if (pGPool->mergeDeadPool(pPool))
            ((LsShm *)pUData)->m_pGHash->eraseIterator(iterOff);
    }
    return 0;
}


LsShmPool *LsShm::getGlobalPool()
{
    if ((m_pGPool != NULL) && (m_pGPool->getMagic() == LSSHM_POOL_MAGIC))
        return m_pGPool;

    const char *name = LSSHM_SYSPOOL;
    m_pGPool = new LsShmPool();
    if (m_pGPool != NULL)
    {
        if (m_pGPool->init(this, name, NULL) == LS_OK
            && m_pGPool->getRef() != 0)
            return m_pGPool;

        delete m_pGPool;
        m_pGPool = NULL;
    }
    if (*getErrMsg() == '\0')       // if no error message, set generic one
    {
        setErrMsg(LSSHM_ERROR, "Unable to get Global Pool, MapFile [%s].",
                  m_pFileName);
    }
    return NULL;
}


LsShmPool *LsShm::getNamedPool(const char *name)
{
    LsShmPool *pObj;
    GHash::iterator iter;

    if (name == NULL)
        return getGlobalPool();

#ifdef DEBUG_RUN
    SHM_NOTICE("LsShm::getNamedPool find %s <%p>",
               name, &getObjBase());
#endif
    iter = getObjBase().find(name);
    if (iter != NULL)
    {
#ifdef DEBUG_RUN
        SHM_NOTICE("LsShm::getNamedPool %s <%p> return %p ",
                   name, &getObjBase(), iter);
#endif
        pObj = (LsShmPool *)(ls_shmpool_t *)iter->second();
        if (pObj->getMagic() != LSSHM_POOL_MAGIC)
            return NULL;
        pObj->upRef();
        return pObj;
    }
    LsShmPool *gpool;
    if ((gpool = getGlobalPool()) == NULL)
        return NULL;
    pObj = new LsShmPool();
    if (pObj != NULL)
    {
        if (pObj->init(this, name, gpool) == LS_OK
            && pObj->getRef() != 0)
            return pObj;
        delete pObj;
    }
    if (*getErrMsg() == '\0')       // if no error message, set generic one
    {
        setErrMsg(LSSHM_ERROR, "Unable to get SHM Pool [%s], MapFile [%s].",
                  name, m_pFileName);
    }
    return NULL;
}


LsShmHash *LsShm::getGlobalHash(int initSize)
{
    if (m_pGHash)
        return m_pGHash;
    LsShmPool *gpool = getGlobalPool();
    if (!x_pShmMap->x_globalHashOff)
    {
        x_pShmMap->x_globalHashOff = gpool->allocateNewHash(initSize, 1,
                                                            LSSHM_FLAG_NONE);
        if (!x_pShmMap->x_globalHashOff)
            return NULL;
    }
    m_pGHash = gpool->newHashByOffset(x_pShmMap->x_globalHashOff, "_G",
            LsShmHash::hashXXH32, memcmp, LSSHM_FLAG_NONE);
    return m_pGHash;

}


#define LSSHM_REG_DEFAULT_SIZE 10

LsShmOffset_t LsShm::findRegOff(const char *name)
{
    if ((name == NULL) || (*name == '\0'))
        return 0;

    LsShmHash * pGlobal = getGlobalHash(LSSHM_REG_DEFAULT_SIZE);
    if (!pGlobal)
        return 0;
    int valLen;
    LsShmOffset_t offset = pGlobal->find(name, strlen(name), &valLen);
    if (offset == 0 || valLen != sizeof(LsShmReg))
        return 0;
    return offset;
}


LsShmReg *LsShm::findReg(const char *name)
{
    LsShmOffset_t offset = findRegOff(name);
    if (offset == 0 )
        return NULL;
    return (LsShmReg *)offset2ptr(offset);
}


//
// @brief - addReg add the given name into Registry.
// @brief   return the offset of the registry
//
LsShmOffset_t LsShm::addRegOff(const char *name)
{
    if ((name == NULL) || (*name == '\0'))
        return 0;

    LsShmHash * pGlobal = getGlobalHash(LSSHM_REG_DEFAULT_SIZE);
    if (!pGlobal)
        return 0;
    int valLen = sizeof(LsShmReg);
    int flag = LSSHM_VAL_INIT;
    return pGlobal->get(name, strlen(name), &valLen, &flag);
}


//
// @brief - addReg add the given name into Registry.
// @brief   return the ptr of the registry
//
LsShmReg *LsShm::addReg(const char *name)
{
    LsShmOffset_t offset = addRegOff( name );
    if (offset != 0)
        return (LsShmReg *)offset2ptr(offset);
    return NULL;
}


//
// @brief - delReg delete the given name from Registry.
//
void LsShm::delReg(const char *name)
{
    LsShmHash * pGlobal;
    if ((name != NULL) && (*name != '\0')
        && ((pGlobal = getGlobalHash(LSSHM_REG_DEFAULT_SIZE)) != NULL))
    {
        pGlobal->remove(name, strlen(name));
    }
    return;
}
