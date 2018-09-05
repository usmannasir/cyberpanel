/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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
#ifndef _LS_MEMCHECK_H_
#define _LS_MEMCHECK_H_

//this file is not available under gcc 
//#include <sanitizer/asan_interface.h>

//add our own
#if !defined(__has_feature)
# define __has_feature(x) 0
#endif

#ifdef __cplusplus
extern "C" {
#endif
  void __asan_poison_memory_region(void const volatile *addr, size_t size);
  void __asan_unpoison_memory_region(void const volatile *addr, size_t size);
#ifdef __cplusplus
}  // extern "C"
#endif

// User code should use macros instead of functions.
#if  __has_feature(address_sanitizer) || defined(__SANITIZE_ADDRESS__)
#define ASAN_POISON_MEMORY_REGION(addr, size) \
  __asan_poison_memory_region((addr), (size))
#define ASAN_UNPOISON_MEMORY_REGION(addr, size) \
  __asan_unpoison_memory_region((addr), (size))
#else
#define ASAN_POISON_MEMORY_REGION(addr, size) 
#define ASAN_UNPOISON_MEMORY_REGION(addr, size)
#endif


#ifdef USE_VALGRIND
#include <valgrind/memcheck.h>
#define VG_NEW_POOL(a, b, c)    VALGRIND_CREATE_MEMPOOL(a, b, c)
#define VG_DEL_POOL(pool)       VALGRIND_DESTROY_MEMPOOL(pool)
#define VG_POISON(a, b)         VALGRIND_MAKE_MEM_NOACCESS(a, b)
#define VG_UNPOISON(a, b)       VALGRIND_MAKE_MEM_DEFINED(a, b)
#define VG_POOL_ALLOC(a, b, c)  VALGRIND_MEMPOOL_ALLOC(a, b, c)
#define VG_POOL_FREE(a, b)      VALGRIND_MEMPOOL_FREE(a, b)

#else /* USE_VALGRIND */

#define VG_NEW_POOL(a, b, c)
#define VG_DEL_POOL(a)
#define VG_POOL_ALLOC(a, b, c)
#define VG_POOL_FREE(a, b)
#define VG_POISON(a, b) 
#define VG_UNPOISON(a, b) 
#endif /* USE_VALGRIND */
        
#define ASAN_POISON(p, s)       ASAN_POISON_MEMORY_REGION(p, s)
#define ASAN_UNPOISON(p, s)     ASAN_UNPOISON_MEMORY_REGION(p, s)    

#define MEMCHK_NEWPOOL(pool, b, c)  VG_NEW_POOL(pool, b, c) 
#define MEMCHK_DESTROY_POOL(pool)   VG_DEL_POOL(pool)

#define MEMCHK_POISON_CHKNUL(p, s) \
    do { if (p != NULL) {VG_POISON(p, s); ASAN_POISON(p, s); } } while(0)
#define MEMCHK_POISON(p, s) \
    do { VG_POISON(p, s); ASAN_POISON(p, s); } while(0)
        
#define MEMCHK_UNPOISON_CHKNUL(p, s) \
    do { if (p != NULL) {VG_UNPOISON(p, s); ASAN_UNPOISON(p, s); } } while(0)
#define MEMCHK_UNPOISON(p, s) \
    do { VG_UNPOISON(p, s); ASAN_UNPOISON(p, s); } while(0)

#define MEMCHK_ALLOC(pool, p, s) \
    do { VG_POOL_ALLOC(pool, p, s); ASAN_UNPOISON(p, s); } while(0)
    
#define MEMCHK_ALLOC_CHKNUL(pool, p, s) \
    do { if (p != NULL) {VG_POOL_ALLOC(pool, p, s); ASAN_UNPOISON(p, s); } } while(0)

#define MEMCHK_FREE(pool, p, s) \
    do { VG_POOL_FREE(pool, p); ASAN_POISON(p, s); } while(0)
    
        
#endif      //_LS_MEMCEHCK_H_
