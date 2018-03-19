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
#ifndef LSSHMLOCK_H
#define LSSHMLOCK_H

#include <shm/lsshmtypes.h>

#include <assert.h>
#include <stdint.h>

/**
 * @file
 * LsShm - LiteSpeed Shared Memory Lock
 */


class debugBase;

typedef struct ls_shmlock_map_s LsShmLockMap;
typedef union ls_shmlock_elem_s LsShmLockElem;

class LsShmLock
{
    friend class LsShm;

public:
    LsShmLock();
    ~LsShmLock();

    ls_shmlock_t *offset2pLock(LsShmOffset_t offset) const;
    void *offset2ptr(LsShmOffset_t offset) const;

    LsShmOffset_t ptr2offset(const void *ptr) const;

    LsShmOffset_t allocLock();
    int freeLock(ls_shmlock_t *pLock);

private:
    LsShmLock(const LsShmLock &other);
    LsShmLock &operator=(const LsShmLock &other);
    bool operator==(const LsShmLock &other);

private:
    // only use by physical mapping

    LsShmStatus_t       expand(LsShmXSize_t size);
    LsShmStatus_t       expandFile(LsShmOffset_t from, LsShmXSize_t incrSize);

    void                cleanup();
    LsShmStatus_t       checkMagic(LsShmLockMap *mp) const;
    LsShmStatus_t       init(const char *pFile, int fd,
                             LsShmXSize_t size, uint64_t id);
    int                 getfd() const   {   return m_iFd;   }
    uint64_t            getId() const;
    LsShmStatus_t       map(LsShmXSize_t size);
    void                unmap();
    void                setupFreeList(LsShmOffset_t to);

    uint32_t            m_iMagic;
    LsShmStatus_t       m_status;
    int                 m_iFd;
    LsShmLockMap       *m_pShmLockMap;
    LsShmLockElem      *m_pShmLockElem;
    LsShmXSize_t        m_iMaxSizeO;

    // for debug purpose
    friend class debugBase;
};

#endif
