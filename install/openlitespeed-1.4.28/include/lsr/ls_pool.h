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
#ifndef LS_POOL_H
#define LS_POOL_H


#include <stddef.h>


/**
 * @file
 */


#ifdef __cplusplus
extern "C" {
#endif


/**
 * @ls_pinit
 * @brief Initializes the global memory pool.
 *   This routine must be called before the memory pool is used.
 *
 * @return Void.
 */
void ls_pinit();

/**
 * @ls_palloc
 * @brief Allocates memory from the global memory pool.
 * @details The allocated memory is not initialized.
 *
 * @param[in] size - The size (number of bytes) to allocate.
 * @return A pointer to the allocated memory, else NULL on error.
 *
 * @see ls_pfree
 */
void *ls_palloc(size_t size);

/**
 * @ls_pfree
 * @brief Frees (releases) memory back to the global memory pool.
 * @details The memory pointer must be one returned from a previous
 *   successful call to ls_palloc.
 *
 * @param[in] p - A pointer to the allocated memory.
 * @return Void.
 *
 * @see ls_palloc
 */
void   ls_pfree(void *p);

/**
 * @ls_prealloc
 * @brief Changes the size of a block of memory allocated
 *   from the global memory pool.
 * @details The new memory contents will be unchanged
 *   for the minimum of the old and new sizes.
 *   If the memory size is increasing, the additional memory is uninitialized.
 *   If the current pointer \e p argument is NULL, ls_prealloc effectively
 *   becomes ls_palloc to allocate new memory.
 *
 * @param[in] p - A pointer to the current allocated memory.
 * @param[in] new_sz - The new size in bytes.
 * @return A pointer to the new allocated memory, else NULL on error.
 *
 * @see ls_palloc
 */
void *ls_prealloc(void *p, size_t new_sz);

/**
 * @ls_dupstr2
 * @brief Duplicates a buffer (or string).
 * @details The new memory for the duplication is allocated from the
 *   global memory pool.
 *
 * @param[in] p - A pointer to the buffer to duplicate.
 * @param[in] len - The size (length) in bytes of the buffer.
 * @return A pointer to the duplicated buffer, else NULL on error.
 */
char *ls_pdupstr2(const char *p, int len);

/**
 * @ls_dupstr
 * @brief Duplicates a null-terminated string.
 * @details The new memory for the duplication is allocated from the
 *   global memory pool.
 *
 * @param[in] p - A pointer to the string to duplicate.
 * @return A pointer to the duplicated string (including null-termination),
 *   else NULL on error.
 */
char *ls_pdupstr(const char *p);

/**
 * @ls_preserve
 * @brief Changes the size of a block of memory allocated
 *   from the global memory pool.
 * @details If new_sz is equal or smaller than the current 
 *   memory block size, the old memory block wont be changed.
 *   If the memory size is increasing, the contents will NOT be copied to new
 *   memory block, if need to keep old content unchanged, use ls_prealloc 
 *   instead. 
 *   If the current pointer \e pOld argument is NULL, ls_preserve effectively
 *   becomes ls_palloc to allocate new memory.
 *
 * @param[in] pOld - A pointer to the current allocated memory.
 * @param[in] new_sz - The new size in bytes.
 * @return A pointer to the new allocated memory, else NULL on error.
 *
 * @see ls_prealloc
 */
void *ls_preserve(void *pOld, size_t new_sz);


/**
 * @ls_palloc_slab
 * @brief Allocates memory from the global memory pool.
 * @details The allocated memory is not initialized.
 *
 * @param[in] size - The size (number of bytes) to allocate.
 * @return A pointer to the allocated memory, else NULL on error.
 *
 * @see ls_pfree_slab
 */
void *ls_palloc_slab(size_t size);

/**
 * @ls_pfree
 * @brief Frees (releases) memory back to the global memory pool.
 * @details The memory pointer must be one returned from a previous
 *   successful call to ls_palloc.
 *
 * @param[in] p - A pointer to the allocated memory.
 * @param[in] size - The size (number of bytes) to be freed, must match ls_palloc_slab
 * @return Void.
 *
 * @see ls_palloc_slab
 */
void   ls_pfree_slab(void *p, size_t size);

/**
 * @ls_prealloc_slab
 * @brief Changes the size of a block of memory allocated
 *   from the global memory pool.
 * @details The new memory contents will be unchanged
 *   for the minimum of the old and new sizes.
 *   If the memory size is increasing, the additional memory is uninitialized.
 *   If the current pointer \e p argument is NULL, ls_prealloc effectively
 *   becomes ls_palloc to allocate new memory.
 *
 * @param[in] p - A pointer to the current allocated memory.
 * @param[in] old_sz - The old size in bytes.
 * @param[in] new_sz - The new size in bytes.
 * @return A pointer to the new allocated memory, else NULL on error.
 *
 * @see ls_palloc_slab ls_free_slab
 */
void *ls_prealloc_slab(void *p, size_t old_sz, size_t new_sz);



#ifdef __cplusplus
}
#endif

#endif  /* LS_POOL_H */

