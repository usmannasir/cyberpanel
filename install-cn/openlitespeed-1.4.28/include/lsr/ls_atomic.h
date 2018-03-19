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

#ifndef LS_ATOMIC_H
#define LS_ATOMIC_H

#include <lsdef.h>

/**
 * @file
 */

#define ls_atomic_inline ls_always_inline

typedef volatile int32_t  ls_atom_32_t;
typedef volatile int64_t  ls_atom_64_t;
typedef volatile int      ls_atom_int_t;
typedef volatile long     ls_atom_long_t;
typedef volatile void    *ls_atom_ptr_t;

typedef volatile uint32_t ls_atom_u32_t;
typedef volatile uint64_t ls_atom_u64_t;
typedef volatile unsigned int    ls_atom_uint_t;
typedef volatile unsigned long   ls_atom_ulong_t;

typedef union
{
    struct
    {
        void *m_ptr;
        long   m_seq;
    };
#if defined( __i386__ )||defined( __arm__ )
    uint64_t   m_whole;
#elif defined( __x86_64 )||defined( __x86_64__ )
#if 0
    unsigned __int128 m_whole;
#else
    uint8_t    m_whole[16];
#endif
#endif
} __attribute__((__aligned__(
#if defined( __i386__ )||defined( __arm__ )
                     8
#elif defined( __x86_64 )||defined( __x86_64__ )
                     16
#endif
                 ))) ls_atom_xptr_t;

#define USE_GCC_ATOMIC
#ifdef USE_GCC_ATOMIC

#define ls_atomic_setint            __sync_lock_test_and_set
#define ls_atomic_setlong           __sync_lock_test_and_set
#define ls_atomic_setptr            __sync_lock_test_and_set

#define ls_atomic_clrint            __sync_lock_release
#define ls_atomic_clrlong           __sync_lock_release
#define ls_atomic_clrptr            __sync_lock_release
#define ls_atomic_clr32             __sync_lock_release

#define ls_atomic_casint            __sync_bool_compare_and_swap
#define ls_atomic_caslong           __sync_bool_compare_and_swap
#define ls_atomic_casptr            __sync_bool_compare_and_swap
#define ls_atomic_cas32             __sync_bool_compare_and_swap

#define ls_atomic_casvint           __sync_val_compare_and_swap
#define ls_atomic_casvlong          __sync_val_compare_and_swap
#define ls_atomic_casvptr           __sync_val_compare_and_swap
#define ls_atomic_casv32            __sync_val_compare_and_swap
#define ls_atomic_casv64            __sync_val_compare_and_swap

#define ls_barrier                  __sync_synchronize
#define ls_atomic_add               __sync_add_and_fetch
#define ls_atomic_sub               __sync_sub_and_fetch

#define ls_atomic_add_fetch         __sync_add_and_fetch
#define ls_atomic_sub_fetch         __sync_sub_and_fetch

#define ls_atomic_fetch_add         __sync_fetch_and_add
#define ls_atomic_fetch_sub         __sync_fetch_and_sub

#if defined( __i386__ )||defined( __arm__ )

ls_atomic_inline char ls_atomic_dcas(ls_atom_xptr_t *ptr,
                                     ls_atom_xptr_t *cmpptr, ls_atom_xptr_t *newptr)
{
    return __sync_bool_compare_and_swap(
               &ptr->m_whole, cmpptr->m_whole, newptr->m_whole);
}

ls_atomic_inline void ls_atomic_dcasv(ls_atom_xptr_t *ptr,
                                      ls_atom_xptr_t *cmpptr, ls_atom_xptr_t *newptr, ls_atom_xptr_t *oldptr)
{
    oldptr->m_whole = __sync_val_compare_and_swap(
                          &ptr->m_whole, cmpptr->m_whole, newptr->m_whole);
    return;
}

#endif

#else // USE_GCC_ATOMIC
#if defined( __arm__ )
#error "GCC atomics required on ARM (USE_GCC_ATOMIC)."
#endif

#if defined( __i386__ )

#define ls_atomic_setint(ptr, val) \
    (int)ls_atomic_set32((uint32_t *)ptr, (uint32_t)val)
#define ls_atomic_setlong(ptr, val) \
    (long)ls_atomic_set32((uint32_t *)ptr, (uint32_t)val)
#define ls_atomic_setptr(ptr, val) \
    (void *)ls_atomic_set32((uint32_t *)ptr, (uint32_t)val)

#define ls_atomic_clrint(ptr)       ls_atomic_clr32((uint32_t *)ptr)
#define ls_atomic_clrlong(ptr)      ls_atomic_clr32((uint32_t *)ptr)
#define ls_atomic_clrptr(ptr)       ls_atomic_clr32((uint32_t *)ptr)

#define ls_atomic_casint(ptr, cmpval, newval) \
    ls_atomic_cas32((uint32_t *)ptr, (uint32_t)cmpval, (uint32_t)newval)
#define ls_atomic_caslong(ptr, cmpval, newval) \
    ls_atomic_cas32((uint32_t *)ptr, (uint32_t)cmpval, (uint32_t)newval)
#define ls_atomic_casptr(ptr, cmpval, newval) \
    ls_atomic_cas32((uint32_t *)ptr, (uint32_t)cmpval, (uint32_t)newval)

#define ls_atomic_casvint(ptr, cmpval, newval) \
    (int)ls_atomic_casv32((uint32_t *)ptr, (uint32_t)cmpval, (uint32_t)newval)
#define ls_atomic_casvlong(ptr, cmpval, newval) \
    (long)ls_atomic_casv32((uint32_t *)ptr, (uint32_t)cmpval, (uint32_t)newval)
#define ls_atomic_casvptr(ptr, cmpval, newval) \
    (void *)ls_atomic_casv32((uint32_t *)ptr, (uint32_t)cmpval, (uint32_t)newval)

#elif defined( __x86_64 )||defined( __x86_64__ )

#define ls_atomic_setint(ptr, val) \
    (int)ls_atomic_set32((uint32_t *)ptr, (uint32_t)val)
#define ls_atomic_setlong(ptr, val) \
    (long)ls_atomic_set64((uint64_t *)ptr, (uint64_t)val)
#define ls_atomic_setptr(ptr, val) \
    (void *)ls_atomic_set64((uint64_t *)ptr, (uint64_t)val)

#define ls_atomic_clrint(ptr)       ls_atomic_clr32((uint32_t *)ptr)
#define ls_atomic_clrlong(ptr)      ls_atomic_clr64((uint64_t *)ptr)
#define ls_atomic_clrptr(ptr)       ls_atomic_clr64((uint64_t *)ptr)

#define ls_atomic_casint(ptr, cmpval, newval) \
    ls_atomic_cas32((uint32_t *)ptr, (uint32_t)cmpval, (uint32_t)newval)
#define ls_atomic_caslong(ptr, cmpval, newval) \
    ls_atomic_cas64((uint64_t *)ptr, (uint64_t)cmpval, (uint64_t)newval)
#define ls_atomic_casptr(ptr, cmpval, newval) \
    ls_atomic_cas64((uint64_t *)ptr, (uint64_t)cmpval, (uint64_t)newval)

#define ls_atomic_casvint(ptr, cmpval, newval) \
    (int)ls_atomic_casv32((uint32_t *)ptr, (uint32_t)cmpval, (uint32_t)newval)
#define ls_atomic_casvlong(ptr, cmpval, newval) \
    (long)ls_atomic_casv64((uint64_t *)ptr, (uint64_t)cmpval, (uint64_t)newval)
#define ls_atomic_casvptr(ptr, cmpval, newval) \
    (void *)ls_atomic_casv64((uint64_t *)ptr, (uint64_t)cmpval, (uint64_t)newval)

#endif

ls_atomic_inline void ls_atomic_add(ls_atom_32_t *ptr, int32_t val)
{
    __asm__ __volatile__(
        "lock; add{l} {%1,%0|%0,%1}"
        : "=m"(*ptr) : "ir"(val), "m"(*ptr));
}


ls_atomic_inline void ls_atomic_sub(ls_atom_32_t *ptr, int32_t val)
{
    ls_atomic_add(ptr, -val);
}


ls_atomic_inline int32_t ls_atomic_fetch_add(ls_atom_32_t *ptr,
        int32_t val)
{
    register int32_t result;
    __asm__ __volatile__(
        "lock; xadd{l} {%0,%1|%1,%0}"
        : "=r"(result), "=m"(*ptr)
        : "0"(val), "m"(*ptr));
    return result;
}

ls_atomic_inline int32_t ls_atomic_add_fetch2(ls_atom_32_t *ptr,
        int32_t val)
{
    return ls_atomic_fetch_add(ptr, val) + val;
}

ls_atomic_inline int32_t ls_atomic_fetch_sub(ls_atom_32_t *ptr,
        int32_t val)
{
    return ls_atomic_fetch_add(ptr, -val);
}

ls_atomic_inline int32_t ls_atomic_sub_fetch2(ls_atom_32_t *ptr,
        int32_t val)
{
    return ls_atomic_fetch_add(ptr, -val) - val;
}


ls_atomic_inline int32_t ls_atomic_add_fetch(ls_atom_32_t *ptr,
        int32_t val)
{
    int32_t save = 0;
    __asm__ __volatile__(
        "mov %0,%2\n\t"
        "lock xadd %0,%1\n"
        : "+r"(val)
        , "+m"(*ptr)
        , "+r"(save)
    );
    return val + save;
}

ls_atomic_inline int32_t ls_atomic_sub_fetch(ls_atom_32_t *ptr,
        int32_t val)
{
    int32_t save = 0;
    __asm__ __volatile__(
        "neg %0\n\t"
        "mov %0,%2\n\t"
        "lock xadd %0,%1\n"
        : "+r"(val)
        , "+m"(*ptr)
        , "+r"(save)
    );
    return val + save;
}

ls_atomic_inline uint32_t ls_atomic_set32(uint32_t *ptr, uint32_t val)
{
    __asm__ __volatile__(
        "xchg %0,%1\n"
        : "+r"(val)
        , "+m"(*ptr)
    );
    return val;
}

ls_atomic_inline void ls_atomic_clr32(uint32_t *ptr)
{
    __asm__ __volatile__(
        "movl $0x0,%0\n"
        : "=m"(*ptr)
        :
        : "memory"
    );
}

ls_atomic_inline unsigned char ls_atomic_cas32(
    uint32_t *ptr, uint32_t cmpval, uint32_t newval)
{
    unsigned char result;
    __asm__ __volatile__(
        "lock cmpxchg %3,%1\n\t"
        "sete %0\n"
        : "=q"(result)
        , "+m"(*ptr)
        : "a"(cmpval)
        , "r"(newval)
        : "cc"
    );
    return result;
}

ls_atomic_inline uint32_t ls_atomic_casv32(
    uint32_t *ptr, uint32_t cmpval, uint32_t newval)
{
    uint32_t result;
    __asm__ __volatile__(
        "lock cmpxchg %3,%1\n"
        : "=a"(result)
        , "+m"(*ptr)
        : "a"(cmpval)
        , "r"(newval)
    );
    return result;
}

#if defined( __i386__ )

#define ls_barrier()   __asm__ __volatile__("lock orl $0x0,(%esp)\n");

ls_atomic_inline unsigned char ls_atomic_dcas(volatile ls_atom_xptr_t *ptr,
        ls_atom_xptr_t *cmpptr, ls_atom_xptr_t *newptr)
{
    unsigned char result;
    __asm__ __volatile__(
        "lock cmpxchg8b %1\n\t"
        "setz %0\n"
        : "=q"(result)
        , "+m"(*ptr)
        : "a"(cmpptr->m_ptr), "d"(cmpptr->m_seq)
        , "b"(newptr->m_ptr), "c"(newptr->m_seq)
        : "cc"
    );
    return result;

}

ls_atomic_inline void ls_atomic_dcasv(volatile ls_atom_xptr_t *ptr,
                                      ls_atom_xptr_t *cmpptr, ls_atom_xptr_t *newptr, ls_atom_xptr_t *oldptr)
{
    __asm__ __volatile__(
        "lock cmpxchg8b %0\n\t"
        : "+m"(*ptr)
        , "=a"(oldptr->m_ptr)
        , "=d"(oldptr->m_seq)
        : "a"(cmpptr->m_ptr), "d"(cmpptr->m_seq)
        , "b"(newptr->m_ptr), "c"(newptr->m_seq)
    );
    return;

}

ls_atomic_inline uint64_t ls_atomic_casv64(
    uint64_t *ptr, uint64_t cmpval, uint64_t newval)
{
    ls_atom_xptr_t result;
    ls_atomic_dcasv((ls_atom_xptr_t *)ptr,
                    (ls_atom_xptr_t *)&cmpval, (ls_atom_xptr_t *)&newval, &result);
    return result.m_whole;
}

#elif defined( __x86_64 )||defined( __x86_64__ )

#define ls_barrier() __asm__ __volatile__("mfence\n");

ls_atomic_inline uint64_t ls_atomic_set64(uint64_t *ptr, uint64_t val)
{
    __asm__ __volatile__(
        "xchg %0,%1\n"
        : "+r"(val)
        , "+m"(*ptr)
    );
    return val;
}

ls_atomic_inline void ls_atomic_clr64(uint64_t *ptr)
{
    __asm__ __volatile__(
        "movq $0x0,%0\n"
        : "=m"(*ptr)
        :
        : "memory"
    );
}

ls_atomic_inline unsigned char ls_atomic_cas64(
    uint64_t *ptr, uint64_t cmpval, uint64_t newval)
{
    unsigned char result;
    __asm__ __volatile__(
        "lock cmpxchg %3,%1\n\t"
        "sete %0\n"
        : "=q"(result)
        , "+m"(*ptr)
        : "a"(cmpval)
        , "r"(newval)
        : "cc"
    );
    return result;
}

ls_atomic_inline uint64_t ls_atomic_casv64(
    uint64_t *ptr, uint64_t cmpval, uint64_t newval)
{
    uint64_t result;
    __asm__ __volatile__(
        "lock cmpxchg %3,%1\n"
        : "=a"(result)
        , "+m"(*ptr)
        : "a"(cmpval)
        , "r"(newval)
    );
    return result;
}

#endif // assembly

#endif // USE_GCC_ATOMIC

#if defined( __x86_64 )||defined( __x86_64__ )

ls_atomic_inline char ls_atomic_dcas(volatile ls_atom_xptr_t *ptr,
                                     ls_atom_xptr_t *cmpptr, ls_atom_xptr_t *newptr)
{
    char result;
    __asm__ __volatile__(
        "lock cmpxchg16b %1\n\t"
        "setz %0\n"
        : "=q"(result)
        , "+m"(*ptr)
        : "a"(cmpptr->m_ptr), "d"(cmpptr->m_seq)
        , "b"(newptr->m_ptr), "c"(newptr->m_seq)
        : "cc"
    );
    return result;

}

ls_atomic_inline void ls_atomic_dcasv(volatile ls_atom_xptr_t *ptr,
                                      ls_atom_xptr_t *cmpptr, ls_atom_xptr_t *newptr, ls_atom_xptr_t *oldptr)
{
    __asm__ __volatile__(
        "lock cmpxchg16b %0\n\t"
        : "+m"(*ptr)
        , "=a"(oldptr->m_ptr)
        , "=d"(oldptr->m_seq)
        : "a"(cmpptr->m_ptr), "d"(cmpptr->m_seq)
        , "b"(newptr->m_ptr), "c"(newptr->m_seq)
    );
    return;

}

#endif // 64

#define ls_atomic_load( v, px )  {   v = *px; ls_barrier();     }
#define ls_atomic_store( pv, x ) {   ls_barrier(); *pv = x;     }

#endif // LS_ATOMIC_H

