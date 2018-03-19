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
#ifndef LSSHMTYPES_H
#define LSSHMTYPES_H

#include <lsr/ls_lock.h>

#include <stdint.h>
#include <sys/types.h>

/**
 * @file
 * LsShm - LiteSpeed Shared Memory Types...
 */


#ifdef __cplusplus
extern "C"
{
#endif

// #define DEBUG_RUN               // dump a lot of msg and sleep
// #define DEBUG_TEST_SYS          // to exercise the system
// #define DEBUG_SHOW_MORE
// #define LSSHM_DEBUG_ENABLE
#define LSSHM_USE_SPINLOCK      // enable for spinlock otherwise mutex
#define USE_PIDSPINLOCK         // enable for pid based spinlock

// C to C++ wrapper
struct ls_shmobject_s 
{
    char * m_pName;
};
struct ls_shm_s 
{
    struct ls_shmobject_s obj;
};
struct ls_shmpool_s 
{
    struct ls_shmobject_s obj;
};
struct ls_shmhash_s 
{
    struct ls_shmobject_s obj;
} ;
typedef struct ls_shm_s         ls_shm_t;
typedef struct ls_shmpool_s     ls_shmpool_t;
typedef struct ls_shmhash_s     ls_shmhash_t;
typedef struct ls_shmobject_s   ls_shmobject_t;

#ifdef LSSHM_USE_SPINLOCK
typedef ls_spinlock_t           ls_shmlock_t;
#ifdef USE_PIDSPINLOCK
#define ls_shmlock_setup        ls_atomic_spin_setup
#define ls_shmlock_lock         ls_atomic_spin_pidlock
#define ls_shmlock_trylock      ls_atomic_pidspin_trylock
#define ls_shmlock_unlock       ls_atomic_spin_unlock
#define ls_shmlock_locked       ls_atomic_pidlocked
#else
#define ls_shmlock_setup        ls_spinlock_setup
#define ls_shmlock_lock         ls_spinlock_lock
#define ls_shmlock_trylock      ls_spinlock_trylock
#define ls_shmlock_unlock       ls_spinlock_unlock
#define ls_shmlock_locked       ls_spinlock_locked
#endif
#else
typedef ls_mutex_t              ls_shmlock_t;
#define ls_shmlock_setup        ls_mutex_setup
#define ls_shmlock_lock         ls_mutex_lock
#define ls_shmlock_trylock      ls_mutex_trylock
#define ls_shmlock_unlock       ls_mutex_unlock
#define ls_shmlock_locked       ls_mutex_locked
#endif


// shared memory types
typedef uint32_t                LsShmOffset_t;
typedef LsShmOffset_t           LsShmXSize_t;
typedef uint32_t                LsShmSize_t;
typedef uint32_t                LsShmCnt_t;

typedef h2_32_fn                LsShmHasher_fn;
typedef v2_comp                 LsShmValComp_fn;


#define LSSHM_MAGIC             0x20151012   // 32 bits
#define LSSHM_LOCK_MAGIC        0x20150505   // 32 bits
#define LSSHM_HASH_MAGIC        0x20150915   // 32 bits
#define LSSHM_POOL_MAGIC        0x20150930   // 32 bits

#define LSSHM_VER_MAJOR         0x0     // 8 bits
#define LSSHM_VER_MINOR         0x0     // 8 bits
#define LSSHM_VER_REL           0x1     // 8 bits
#define LSSHM_VER_TYPE          \
    (((sizeof(LsShmOffset_t)<<4) | sizeof(LsShmXSize_t)) & (0xff)) // 8 bits

#define LSSHM_PAGESIZE          0x2000  // min pagesize 8k
#define LSSHM_PAGEMASK          0xFFFFE000
#define LSSHM_MAXNAMELEN        12      // only 11 characters.

#define LSSHM_SYSSHM            "LsShm"     // default SHM name
#define LSSHM_SYSPOOL           "LsPool"    // default SHM POOL name
#define LSSHM_SYSHASH           "LsHash"    // default SHM HASH name

#define LSSHM_SYSSHM_FILENAME   LSSHM_SYSSHM
#define LSSHM_SYSSHM_FILE_EXT   "shm"
#define LSSHM_SYSLOCK_FILE_EXT  "lock"

#define LSSHM_MINDIRSPACE       0xA00000        // 10M minimum directory space
#define LSSHM_INITSIZE          LSSHM_PAGESIZE  // default SHM SIZE

#define LSSHM_SHM_UNITSIZE      0x400           // 1K byte increments
#define LSSHM_POOL_UNITSIZE     16              //  8 byte increments
#define LSSHM_POOL_BCKTINCR     16              // byte increment for buckets
#define LSSHM_MINHASH           0x400
#define LSSHM_MINLOCK           0x400
#define LSSHM_HASHINITSIZE      97

#define LSSHM_MINSPACE          0x2000          // minimum SHM SIZE

#define LSSHM_MAXSIZE           2000000000      // max size in memory allocation

#define LSSHM_MAXERRMSG         4096            // max error message len

// bit mask from ls.h
#define LSSHM_VAL_NONE          0x0000          // no flag values
#define LSSHM_VAL_INIT          0x0001          // used to indicate for memset
#define LSSHM_VAL_CREATED       0x0001          // return flag if SHM created

#define LSSHM_CHECKSIZE(x) { if ((x&0x80000000) || (x>LSSHM_MAXSIZE)) return end();}

enum LsShmStatus_t
{
    LSSHM_SYSERROR = -101,
    LSSHM_ERROR = -100,
    LSSHM_BADNOSPACE = -7,
    LSSHM_BADMAXSPACE = -6,
    LSSHM_NAMEINUSED = -5,
    LSSHM_BADNAMELEN = -4,
    LSSHM_BADMAPFILE = -3,
    LSSHM_BADVERSION = -2,
    LSSHM_BADPARAM = -1,
    LSSHM_NOTREADY = 0,
    LSSHM_OK = 0, // Tricky - for internal function to use
    LSSHM_READY = 1
};

enum LsShmMode_t { LSSHM_MODE_RDONLY = 1, LSSHM_MODE_RW = 2 };

// This will help to explain the key efficiency
struct LsHashStat_s
{
    int maxLink;        // max number in same key
    int numIdx;         // num of index key
    int numIdxOccupied; // num of key populated
    int num;            // total elements
    int numExpired;     // user supplied
    int numDup;         // num of duplicated keys
    int top[10];        // 1,2,3,4,5,10,20,50,100,100+
    void *userData;     // defined by user
};
typedef struct LsHashStat_s LsHashStat;

typedef struct LsHashLruInfo_s LsHashLruInfo;
typedef struct ls_shmhiteroff_s
{
    LsShmOffset_t   m_iOffset;   // offset location of hash element
} LsShmHIterOff;


/* status for shmlru_check */
#define SHMLRU_CHECKOK      (0)
#define SHMLRU_BADINIT      (-1)
#define SHMLRU_BADMAGIC     (-2)
#define SHMLRU_BADVALCNT    (-3)
#define SHMLRU_BADDATACNT   (-4)

#ifdef __cplusplus
}
#endif


#endif

