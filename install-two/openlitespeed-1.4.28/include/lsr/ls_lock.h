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
#ifndef LS_LOCK_H
#define LS_LOCK_H

#include <lsr/ls_atomic.h>
#include <lsr/ls_types.h>

#include <assert.h>
#include <stdint.h>
#include <pthread.h>
#include <sys/types.h>
#include <unistd.h>
#include <errno.h>
#include <signal.h>

#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
#include <linux/futex.h>
#include <sys/syscall.h>
#endif


/**
 * @file
 * There are a number of locking mechanisms available to the user,
 * selectable through conditional compilation.
 *
 * \li USE_F_MUTEX - Support futex (fast user-space mutex) instead of pthread_mutex.
 * \li USE_ATOMIC_SPIN - Support atomic spin instead of pthread_spin_lock.
 * \li USE_MUTEX_LOCK - Use mutex/futex locks rather than spin locks.
 *
 * Note that certain hardware and operating systems handle implementation differently.
 */


#ifdef __cplusplus
extern "C" {
#endif

#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__) \
    || defined(__FreeBSD__ ) || defined(__NetBSD__) || defined(__OpenBSD__)
#define USE_F_MUTEX
#define USE_MUTEX_ADAPTIVE

#else
#undef USE_F_MUTEX
#define USE_MUTEX_LOCK

#endif
#define USE_ATOMIC_SPIN

#define MAX_FUTEX_SPINCNT      10

/* LiteSpeed general purpose lock/unlock/trylock
 */
#ifdef USE_F_MUTEX
typedef int32_t             ls_mutex_t;
#else
typedef pthread_mutex_t     ls_mutex_t;
#endif

#if defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)
#include <libkern/OSAtomic.h>
typedef OSSpinLock ls_pspinlock_t;
#define ls_pspinlock_lock          OSSpinLockLock
#define ls_pspinlock_trylock       OSSpinLockTry
#define ls_pspinlock_unlock        OSSpinLockUnlock
#else
typedef pthread_spinlock_t ls_pspinlock_t;
#define ls_pspinlock_lock          pthread_spin_lock
#define ls_pspinlock_trylock       pthread_spin_trylock
#define ls_pspinlock_unlock        pthread_spin_unlock
#endif

#if defined(__i386__) || defined(__ia64__) || defined(__x86_64) || defined(__x86_64__)
//#define cpu_relax()         asm volatile("pause\n": : :"memory")
// ron - the PAUSE approach is order of magnitude slower in MT with contention
#define cpu_relax()         usleep(1);
#else
#define cpu_relax()         usleep(1);
//#define cpu_relax()         ;
#endif
typedef int32_t             ls_atom_spinlock_t;

#ifdef USE_ATOMIC_SPIN
typedef ls_atom_spinlock_t   ls_spinlock_t;

extern int ls_spin_pid;    /* process id used with ls_atomic_pidspin */
void ls_atomic_pidspin_init();
#else
typedef ls_pspinlock_t  ls_spinlock_t;
#endif

#ifdef USE_MUTEX_LOCK
typedef ls_mutex_t         ls_lock_t;
#else
typedef ls_spinlock_t      ls_lock_t;
#endif


#ifdef USE_F_MUTEX
#define ls_mutex_setup             ls_futex_setup
#define ls_mutex_lock              ls_futex_safe_lock
#define ls_mutex_trylock           ls_futex_trylock
#define ls_mutex_unlock            ls_futex_safe_unlock
#else
#define ls_mutex_setup             ls_pthread_mutex_setup
#define ls_mutex_lock              pthread_mutex_lock
#define ls_mutex_trylock           pthread_mutex_trylock
#define ls_mutex_unlock            pthread_mutex_unlock
#endif

#ifdef USE_ATOMIC_SPIN
#define ls_spinlock_setup         ls_atomic_spin_setup
#define ls_spinlock_lock          ls_atomic_spin_lock
#define ls_spinlock_trylock       ls_atomic_spin_trylock
#define ls_spinlock_unlock        ls_atomic_spin_unlock
#else
#define ls_spinlock_setup         ls_pspinlock_setup
#define ls_spinlock_lock          ls_pspinlock_lock
#define ls_spinlock_trylock       ls_pspinlock_trylock
#define ls_spinlock_unlock        ls_pspinlock_unlock
#endif

#ifdef USE_MUTEX_LOCK
#define ls_lock_setup             ls_mutex_setup
#define ls_lock_lock              ls_mutex_lock
#define ls_lock_trylock           ls_mutex_trylock
#define ls_lock_unlock            ls_mutex_unlock
#else
#define ls_lock_setup             ls_spinlock_setup
#define ls_lock_lock              ls_spinlock_lock
#define ls_lock_trylock           ls_spinlock_trylock
#define ls_lock_unlock            ls_spinlock_unlock
#endif

#define LS_LOCK_AVAIL 0
#define LS_LOCK_INUSE 456

#if defined(__FreeBSD__ ) || defined(__NetBSD__) || defined(__OpenBSD__)
#include <errno.h>
#include <machine/atomic.h>
#include <sys/umtx.h>
ls_inline int ls_futex_wake(int *futex)
{
    return _umtx_op(futex, UMTX_OP_WAKE, 1, 0, 0);
}

ls_inline int ls_futex_wait(int *futex, int val, struct timespec *timeout)
{
    int err = _umtx_op(futex, UMTX_OP_WAIT_UINT, val, 0, (void *)timeout);
    return err;
}

#endif


#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)

ls_inline int ls_futex_wake(int *futex)
{
    return syscall(SYS_futex, futex, FUTEX_WAKE, 1, NULL, NULL, 0);
}


ls_inline int ls_futex_wait(int *futex, int val, struct timespec *timeout)
{
    return syscall(SYS_futex, futex, FUTEX_WAIT, val, timeout, NULL, 0);
}

#endif


#ifdef USE_F_MUTEX

#define LS_FUTEX_LOCKED1    (1)
#define LS_FUTEX_LOCKED2    (2)     /* locked with waiters */

/**
 * @ls_futex_lock
 * @brief Locks
 *   a lock set up using futexes.
 *
 * @param[in] p - A pointer to the lock.
 * @return 0 when able to acquire the lock.
 *
 * @see ls_futex_setup, ls_futex_trylock, ls_futex_unlock
 */
ls_inline int ls_futex_lock(ls_mutex_t *p)
{
    int val;

#if defined( USE_MUTEX_ADAPTIVE )
    int i;
    for (i = 0; i < MAX_FUTEX_SPINCNT; ++i)
    {
        if ((val = ls_atomic_casvint(p, LS_LOCK_AVAIL, LS_FUTEX_LOCKED1))
            == LS_LOCK_AVAIL)
            return 0;
        if (val == LS_FUTEX_LOCKED2)   /* do not spin if other waiters exist */
            break;
    }
#endif

    if ((val = ls_atomic_casvint(p, LS_LOCK_AVAIL, LS_FUTEX_LOCKED1))
        != LS_LOCK_AVAIL)
    {
        do
        {
            if ((val == LS_FUTEX_LOCKED2)
                || (ls_atomic_casvint(p, LS_FUTEX_LOCKED1, LS_FUTEX_LOCKED2)
                    != LS_LOCK_AVAIL))
                ls_futex_wait(p, LS_FUTEX_LOCKED2, NULL); /* blocking */
        }
        while ((val = ls_atomic_casvint(p, LS_LOCK_AVAIL, LS_FUTEX_LOCKED2))
               != LS_LOCK_AVAIL);
    }
    return 0;
}

#define LS_FUTEX_HAS_WAITER     (0x80000000)
#define LS_FUTEX_PID_MASK       (0x7fffffff)

/**
 * @ls_futex_safe_lock
 * @brief Locks
 *   a lock set up using futexes.
 *
 * @param[in] p - A pointer to the lock.
 * @return 0 when able to acquire the lock normally,
 *   or a negative process id number if the lock was acquired from
 *   a non-running process.
 *
 * @see ls_futex_setup, ls_futex_trylock, ls_futex_unlock
 */
ls_inline int ls_futex_safe_lock(ls_mutex_t *p)
{
    uint lockpid;
    struct timespec x_time = { 1, 0 }; // 1 sec wait
    if (ls_spin_pid == 0)
        ls_atomic_pidspin_init();

    lockpid = ls_atomic_casvint(p, LS_LOCK_AVAIL, ls_spin_pid);
    if (lockpid == LS_LOCK_AVAIL)
        return 0;
    do
    {
        if ((kill(lockpid & LS_FUTEX_PID_MASK, 0) < 0) && (errno == ESRCH)
            && ls_atomic_casint(p, lockpid, ls_spin_pid | LS_FUTEX_HAS_WAITER))
            return -(lockpid & LS_FUTEX_PID_MASK);
        if ((lockpid & LS_FUTEX_HAS_WAITER)
            || ls_atomic_casint(p, lockpid, lockpid | LS_FUTEX_HAS_WAITER) != 0)
            ls_futex_wait(p, lockpid | LS_FUTEX_HAS_WAITER, &x_time);
    }
    while ((lockpid = ls_atomic_casvint(p, LS_LOCK_AVAIL,
                                        ls_spin_pid | LS_FUTEX_HAS_WAITER)) != LS_LOCK_AVAIL);

    return 0;
}


/**
 * @ls_futex_safe_unlock
 * @brief Unlocks
 *   a lock set up using futexes.
 *
 * @param[in] p - A pointer to the lock.
 * @return 0, or 1 if there was a process waiting, else -1 on error.
 *
 * @see ls_futex_setup, ls_futex_lock, ls_futex_trylock
 */
ls_inline int ls_futex_safe_unlock(ls_mutex_t *p)
{

    int old = ls_atomic_setint(p, 0);
    assert((old & LS_FUTEX_PID_MASK) == ls_spin_pid);
    if ((old & LS_FUTEX_HAS_WAITER) == 0)
        return 0;

    //return syscall(SYS_futex, p, FUTEX_WAKE, 1, NULL, NULL, 0);
    return ls_futex_wake(p);
}

/**
 * @ls_futex_trylock
 * @brief Tries to lock
 *   a lock set up using futexes.
 * @details The routine actually uses the built-in functions for
 *   atomic memory access.
 *
 * @param[in] p - A pointer to the lock.
 * @return 0 on success, else 1 if unable to acquire the lock.
 *
 * @see ls_futex_setup, ls_futex_lock, ls_futex_unlock
 */
ls_inline int ls_futex_trylock(ls_mutex_t *p)
{
    return !ls_atomic_casint(p, 0, 1);
}

/**
 * @ls_futex_unlock
 * @brief Unlocks
 *   a lock set up using futexes.
 *
 * @param[in] p - A pointer to the lock.
 * @return 0, or 1 if there was a process waiting, else -1 on error.
 *
 * @see ls_futex_setup, ls_futex_lock, ls_futex_trylock
 */
ls_inline int ls_futex_unlock(ls_mutex_t *p)
{
    assert(*(int *)p != 0);
    return (ls_atomic_setint(p, LS_LOCK_AVAIL) == LS_FUTEX_LOCKED2) ?
           ls_futex_wake(p) : 0;
}

/**
 * @ls_futex_setup
 * @brief Initializes a locking mechanism
 *   using futexes (fast user-space mutexes).
 *
 * @param[in] p - A pointer to the lock.
 * @return 0.
 *
 * @see ls_futex_lock, ls_futex_unlock, ls_futex_trylock
 */
int ls_futex_setup(ls_mutex_t *p);

#endif //USE_F_MUTEX

//#ifdef USE_ATOMIC_SPIN


/**
 * @ls_atomic_spin_lock
 * @brief Locks
 *   a spinlock set up with built-in functions for atomic memory access.
 * @details The routine \e spins until it is able to acquire the lock.
 *
 * @param[in] p - A pointer to the lock.
 * @return 0 when able to acquire the lock.
 *
 * @see ls_atomic_spin_setup, ls_atomic_spin_trylock, ls_atomic_spin_unlock,
 *   ls_atomic_spin_pidlock
 */
ls_inline int ls_atomic_spin_lock(ls_atom_spinlock_t *p)
{
    while (!ls_atomic_casint(p, LS_LOCK_AVAIL, LS_LOCK_INUSE))
    {
        cpu_relax();
    }
    return 0;
}

/**
 * @ls_atomic_spin_pidlock
 * @brief Locks
 *   a spinlock set up with built-in functions for atomic memory access
 *   using a Process Id lock.
 * @details The routine \e spins until it is able to acquire the lock.
 *   This version additionally attempts to determine if the process
 *   owning the lock is still in execution.
 *
 * @param[in] p - A pointer to the lock.
 * @return 0 when able to acquire the lock normally,
 *   or a negative process id number if the lock was acquired from
 *   a non-running process.
 *
 * @see ls_atomic_spin_lock
 */

int ls_atomic_spin_pidwait(ls_atom_spinlock_t *p);

ls_inline int ls_atomic_spin_pidlock(ls_atom_spinlock_t *p)
{
    int waitpid;
    if (ls_spin_pid == 0)
        ls_atomic_pidspin_init();
    waitpid = ls_atomic_casvint(p, LS_LOCK_AVAIL, ls_spin_pid);
    if (waitpid == LS_LOCK_AVAIL)
    {
        return 0;
    }
    return ls_atomic_spin_pidwait(p);
}


/**
 * @ls_atomic_spin_trylock
 * @brief Tries to lock
 *   a spinlock set up with built-in functions for atomic memory access.
 *
 * @param[in] p - A pointer to the lock.
 * @return 0 on success, else 1 if unable to acquire the lock.
 *
 * @see ls_atomic_spin_setup, ls_atomic_spin_lock, ls_atomic_spin_unlock,
 *   ls_atomic_pidspin_trylock
 */
ls_inline int ls_atomic_spin_trylock(ls_atom_spinlock_t *p)
{
    return !ls_atomic_casint(p, LS_LOCK_AVAIL, LS_LOCK_INUSE);
}

/**
 * @ls_atomic_pidspin_trylock
 * @brief Tries to lock
 *   a spinlock set up with built-in functions for atomic memory access
 *   using a Process Id lock.
 *
 * @param[in] p - A pointer to the lock.
 * @return 0 on success, else 1 if unable to acquire the lock.
 *
 * @see ls_atomic_spin_trylock
 */
ls_inline int ls_atomic_pidspin_trylock(ls_atom_spinlock_t *p)
{
    if (ls_spin_pid == 0)
        ls_atomic_pidspin_init();
    return !ls_atomic_casint(p, LS_LOCK_AVAIL, ls_spin_pid);
}

/**
 * @ls_atomic_spin_unlock
 * @brief Unlocks
 *   a spinlock set up with built-in functions for atomic memory access.
 *
 * @param[in] p - A pointer to the lock.
 * @return 0.
 *
 * @see ls_atomic_spin_setup, ls_atomic_spin_lock, ls_atomic_spin_trylock
 */
ls_inline int ls_atomic_spin_unlock(ls_atom_spinlock_t *p)
{
    ls_atomic_clrint(p);
    return 0;
}

/**
 * @ls_atomic_spin_locked
 * @brief Test if a spinlock is currently in locked state.
 *
 * @param[in] p - A pointer to the lock.
 * @return 1 - locked, 0 - not locked.
 *
 * @see ls_atomic_spin_setup, ls_atomic_spin_lock, ls_atomic_spin_trylock 
 *      ls_atomic_spin_unlock
 */
ls_inline int ls_atomic_spin_locked(ls_atom_spinlock_t *p)
{
    return *p != 0;
}

/**
 * @ls_atomic_spin_pidunlock
 * @brief Unlocks
 *   a spinlock set up with built-in functions for atomic memory access.
 *
 * @param[in] p - A pointer to the lock.
 * @return 0.
 *
 * @see ls_atomic_spin_setup, ls_atomic_spin_lock, ls_atomic_spin_trylock
 */
ls_inline int ls_atomic_spin_pidunlock(ls_atom_spinlock_t *p)
{
    assert(*p == ls_spin_pid);
    ls_atomic_clrint(p);
    return 0;
}


/**
 * @ls_atomic_pidlocked
 * @brief Test if a spinlock is currently is locked with current pid.
 *
 * @param[in] p - A pointer to the lock.
 * @return 1 - locked, 0 - not locked.
 *
 * @see ls_atomic_spin_setup, ls_atomic_spin_lock, ls_atomic_spin_trylock 
 *      ls_atomic_spin_unlock
 */
ls_inline int ls_atomic_pidlocked(ls_atom_spinlock_t *p)
{
    if (ls_spin_pid == 0)
        ls_atomic_pidspin_init();
    return *p == ls_spin_pid;
}


/**
 * @ls_atomic_spin_setup
 * @brief Initializes a locking mechanism
 *   using spinlocks with built-in functions for atomic memory access.
 *
 * @param[in] p - A pointer to the lock.
 * @return 0.
 *
 * @see ls_atomic_spin_lock, ls_atomic_spin_unlock, ls_atomic_spin_trylock
 */
int ls_atomic_spin_setup(ls_atom_spinlock_t *p);

//#endif

int ls_pthread_mutex_setup(pthread_mutex_t *);

int ls_pspinlock_setup(ls_pspinlock_t *p);

#ifdef __cplusplus
}
#endif

#endif //LS_LOCK_H

