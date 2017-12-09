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
#include <shm/lsshmlock.h>

#include <shm/lsshm.h>
#include <util/gpath.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/mman.h>
#include <sys/stat.h>


extern "C" {
    int ls_expandfile(int fd, LsShmOffset_t fromsize, LsShmXSize_t incrsize);
};

//
// LiteSpeed Shared Memory Lock Map
//
//  +------------------------------------------------
//  | HEADER
//  |    --> maxSize      --------------------------+
//  |    --> offset free  ----------------+         |
//  |                                     |         |
//  |----------------------------         |         |
//  |    --> Mutex                        |         |
//  |                        <------------+         |
//  |------------------------<----------------------+
//
struct ls_shmlock_map_s
{
    uint32_t            x_iMagic;
    LsShmCnt_t          x_iMaxElem;
    uint64_t            x_id;
    LsShmXSize_t        x_iMaxSize;      // the file size
    LsShmOffset_t       x_iFreeOffset;   // first free lock
};


union ls_shmlock_elem_s
{
    ls_shmlock_t        x_lock;
    LsShmOffset_t       x_iNext;
};


static LsShmSize_t s_iPageSize = LSSHM_PAGESIZE;
static LsShmSize_t s_iHdrSize  = ((sizeof(LsShmLockMap) + 0xf) &
                                      ~0xf); // align 16

static LsShmXSize_t  roundToPageSize(LsShmXSize_t size)
{   return ((size + s_iPageSize - 1) / s_iPageSize) * s_iPageSize; }


LsShmLock::LsShmLock()
    : m_iMagic(LSSHM_LOCK_MAGIC)
    , m_status(LSSHM_NOTREADY)
    , m_iFd(-1)
    , m_pShmLockMap(NULL)
    , m_pShmLockElem(NULL)
    , m_iMaxSizeO(0)
{
}


LsShmLock::~LsShmLock()
{
    cleanup();
}


ls_shmlock_t *LsShmLock::offset2pLock(LsShmOffset_t offset) const
{
    assert(offset < m_pShmLockMap->x_iMaxSize);
    return (ls_shmlock_t *)(((uint8_t *)m_pShmLockMap) + offset);
}

void *LsShmLock::offset2ptr(LsShmOffset_t offset) const
{
    assert(offset < m_pShmLockMap->x_iMaxSize);
    return (void *)(((uint8_t *)m_pShmLockMap) + offset);
}

LsShmOffset_t LsShmLock::ptr2offset(const void *ptr) const
{
    assert(ptr <
            ((uint8_t *)m_pShmLockMap) + m_pShmLockMap->x_iMaxSize);
    return (LsShmOffset_t)((uint8_t *)ptr - (uint8_t *)m_pShmLockMap);
}


LsShmOffset_t LsShmLock::allocLock()
{
    LsShmLockElem *pElem;
    LsShmOffset_t offset;
    ls_shmlock_lock(&m_pShmLockElem->x_lock);
    if ((offset = m_pShmLockMap->x_iFreeOffset) == 0)
    {
        ls_shmlock_unlock(&m_pShmLockElem->x_lock);
        return 0;
    }
    pElem = m_pShmLockElem + offset;
    m_pShmLockMap->x_iFreeOffset = pElem->x_iNext;
    ls_shmlock_unlock(&m_pShmLockElem->x_lock);
    if (sizeof(pElem->x_lock) == sizeof(int))   // optimized out by compiler
        *(int *)&pElem->x_lock = 0;
    else
        ::memset((void *)&pElem->x_lock, 0, sizeof(pElem->x_lock));
    return (LsShmOffset_t)((uint8_t *)&pElem->x_lock 
            - (uint8_t *)m_pShmLockMap);
}


int LsShmLock::freeLock(ls_shmlock_t *pLock)
{
    int num = ((LsShmLockElem *)pLock - m_pShmLockElem);
    LsShmLockElem *pElem = m_pShmLockElem + num;
    ls_shmlock_lock(&m_pShmLockElem->x_lock);
    pElem->x_iNext = m_pShmLockMap->x_iFreeOffset;
    m_pShmLockMap->x_iFreeOffset = num;
    ls_shmlock_unlock(&m_pShmLockElem->x_lock);
    return 0;
}


void LsShmLock::cleanup()
{
    unmap();
    if (m_iFd != -1)
    {
        close(m_iFd);
        m_iFd = -1;
    }
}


LsShmStatus_t LsShmLock::checkMagic(LsShmLockMap *mp) const
{
    return (mp->x_iMagic != m_iMagic) ? LSSHM_BADVERSION : LSSHM_OK;
}


LsShmStatus_t LsShmLock::init(const char *pFileName, int fd,
                              LsShmXSize_t size, uint64_t id)
{
    struct stat mystat;
    bool needsetup;

    m_iFd = fd;
    size = ((size + s_iPageSize - 1) / s_iPageSize) * s_iPageSize;

    if (fstat(m_iFd, &mystat) < 0)
    {
        LsShm::setErrMsg(LSSHM_SYSERROR, "Unable to stat lock file, %s.",
                         strerror(errno));
        return LSSHM_BADMAPFILE;
    }

    needsetup = false;
    if (mystat.st_size == 0)
    {
        if (id == 0)
        {
            LsShm::setErrMsg(LSSHM_BADVERSION,
                             "Missing LockFile [%s]", pFileName);
            return LSSHM_BADVERSION;
        }
        // creating a new map
        if ((expandFile(0, roundToPageSize(size)) != LSSHM_OK)
            || (map(size) != LSSHM_OK))
            return LSSHM_ERROR;
        m_pShmLockMap->x_iMagic       = m_iMagic;
        m_pShmLockMap->x_id           = id;
        m_pShmLockMap->x_iMaxSize     = size;
        m_pShmLockMap->x_iFreeOffset  = 0;
        m_pShmLockMap->x_iMaxElem     = 0;
        needsetup = true;
    }
    else
    {
        if (mystat.st_size < s_iHdrSize)
        {
            LsShm::setErrMsg(LSSHM_BADMAPFILE, "Bad LockFile, size=%lld.",
                             (uint64_t)mystat.st_size);
            return LSSHM_BADMAPFILE;
        }

        // only map the header size to ensure the file is good.
        if (map(s_iHdrSize) != LSSHM_OK)
            return LSSHM_ERROR;

        if (checkMagic(m_pShmLockMap) != LSSHM_OK)
        {
            LsShm::setErrMsg(LSSHM_BADVERSION,
                             "Bad LockFile format, size=%lld, magic=%08X(%08X).",
                             (uint64_t)mystat.st_size,
                             m_pShmLockMap->x_iMagic, m_iMagic);
            return LSSHM_BADVERSION;
        }

        // expand the file if needed... won't shrink
        if (size > m_pShmLockMap->x_iMaxSize)
        {
            if (expandFile((LsShmOffset_t)m_pShmLockMap->x_iMaxSize,
                           (LsShmXSize_t)(size - m_pShmLockMap->x_iMaxSize)) != LSSHM_OK)
                return LSSHM_ERROR;
            m_pShmLockMap->x_iMaxSize = size;
            needsetup = true;
        }
        unmap();
        if (map(size) != LSSHM_OK)
            return LSSHM_ERROR;
    }
    if (needsetup)
        setupFreeList((LsShmOffset_t)size);
    return LSSHM_OK;
}


LsShmStatus_t LsShmLock::expand(LsShmXSize_t incrSize)
{
    LsShmXSize_t xsize = m_pShmLockMap->x_iMaxSize;

    if (expandFile((LsShmOffset_t)xsize, incrSize) != LSSHM_OK)
        return LSSHM_ERROR;
    unmap();
    xsize += incrSize;
    if (map(xsize) != LSSHM_OK)
    {
        xsize -= incrSize;
        if (xsize != 0)
            map(xsize);     // try to remap old size for cleanup
        return LSSHM_ERROR;
    }
    m_pShmLockMap->x_iMaxSize = xsize;

    return LSSHM_OK;
}


LsShmStatus_t LsShmLock::expandFile(LsShmOffset_t from,
                                    LsShmXSize_t incrSize)
{
    return (ls_expandfile(m_iFd, from,
                          incrSize) < 0) ?  LSSHM_ERROR : LSSHM_OK;
}


uint64_t  LsShmLock::getId() const
{
    return m_pShmLockMap->x_id;
}


LsShmStatus_t LsShmLock::map(LsShmXSize_t size)
{
    uint8_t *p = (uint8_t *)
        mmap(0, (size_t)size, PROT_READ | PROT_WRITE, MAP_SHARED, m_iFd, 0);
    if (p == MAP_FAILED)
    {
        LsShm::setErrMsg(LSSHM_SYSERROR, "Unable to mmap, size=%lu, %s.",
                         (unsigned long)size, strerror(errno));
        return LSSHM_SYSERROR;
    }

    m_pShmLockMap = (LsShmLockMap *)p;
    m_pShmLockElem = (LsShmLockElem *)((uint8_t *)p + s_iHdrSize);
    m_iMaxSizeO = size;
    return LSSHM_OK;
}


void LsShmLock::unmap()
{
    if (m_pShmLockMap != NULL)
    {
        munmap(m_pShmLockMap, m_iMaxSizeO);
        m_pShmLockMap = NULL;
        m_pShmLockElem = NULL;
        m_iMaxSizeO = 0;
    }
}


//
//  Note - LockNum 0 is for myself...
//
void LsShmLock::setupFreeList(LsShmOffset_t to)
{
    LsShmLockElem *p_elem =
        m_pShmLockElem + m_pShmLockMap->x_iMaxElem;
    LsShmOffset_t from = ptr2offset(p_elem);
    int numAdd = (to - from) / sizeof(LsShmLockElem);

    int curNum = m_pShmLockMap->x_iMaxElem;
    int lastNum = curNum + numAdd;
    int x_lastNum = lastNum;    // save it for later

    p_elem = m_pShmLockElem + --lastNum; // Can't call lockNum2pElem
    p_elem->x_iNext = m_pShmLockMap->x_iFreeOffset;
    while (--numAdd >= 1)
    {
        --p_elem;
        p_elem->x_iNext = lastNum--;
    }

    if (lastNum == 0)
    {
        ls_shmlock_setup(&m_pShmLockElem->x_lock); // lock for lockfile
        ++lastNum;      // keep this for myself
    }
    m_pShmLockMap->x_iFreeOffset = lastNum;
    m_pShmLockMap->x_iMaxElem = x_lastNum;
}

