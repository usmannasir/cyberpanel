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
#ifndef LS_XPOOL_H
#define LS_XPOOL_H

/* define to handle all allocs/frees as separate `big' blocks */
//#define LS_VG_DEBUG

/* define for miscellaneous debug status */
//#define LS_XPOOL_INTERNAL_DEBUG

#include <inttypes.h>
#include <lsr/ls_types.h>

/**
 * @file
 */


#ifdef __cplusplus
extern "C" {
#endif


/**
 * @ls_xpool_new
 * @brief Creates a new session memory pool object.
 * @details The routine allocates and initializes an object
 *   to manage a memory pool which is expected
 *   to exist only for the life of a session, at which time it
 *   may be efficiently cleaned up.
 *
 * @return A pointer to an initialized session memory pool object.
 *
 * @see ls_xpool_delete
 */
ls_xpool_t *ls_xpool_new();


/**
 * @ls_xpool_reset
 * @brief Destroys then re-initializes a session memory pool object.
 * @details The previously allocated memory and data are released,
 *   and the pool is set empty to be used again.
 *
 * @param[in] pool - A pointer to an initialized session pool object.
 * @return Void.
 */
void    ls_xpool_reset(ls_xpool_t *pool);

/**
 * @ls_xpool_alloc
 * @brief Allocates memory from the session memory pool.
 * @details The allocated memory is not initialized.
 *
 * @param[in] pool - A pointer to an initialized session pool object.
 * @param[in] size - The size (number of bytes) to allocate.
 * @return A pointer to the allocated memory, else NULL on error.
 *
 * @see ls_xpool_free
 */
void   *ls_xpool_alloc(ls_xpool_t *pool, uint32_t size);

/**
 * @ls_xpool_calloc
 * @brief Allocates memory from the session memory pool
 *   for an array of fixed size items.
 * @details The allocated memory is set to zero (unlike ls_xpool_alloc).
 *
 * @param[in] pool - A pointer to an initialized session pool object.
 * @param[in] items - The number of items to allocate.
 * @param[in] size - The size in bytes of each item.
 * @return A pointer to the allocated memory, else NULL on error.
 *
 * @see ls_xpool_alloc
 */
void   *ls_xpool_calloc(ls_xpool_t *pool, uint32_t items, uint32_t size);

/**
 * @ls_xpool_realloc
 * @brief Changes the size of a block of memory allocated
 *   from the session memory pool.
 * @details The new memory contents will be unchanged
 *   for the minimum of the old and new sizes.
 *   If the memory size is increasing, the additional memory is uninitialized.
 *
 * @param[in] pool - A pointer to an initialized session pool object.
 * @param[in] pOld - A pointer to the current allocated memory.
 * @param[in] new_sz - The new size in bytes.
 * @return A pointer to the new allocated memory, else NULL on error.
 * @note If the current pointer \e pOld argument is NULL,
 *   ls_xpool_realloc effectively becomes ls_xpool_alloc to allocate new memory.
 *
 * @see ls_xpool_alloc
 */
void   *ls_xpool_realloc(ls_xpool_t *pool, void *pOld, uint32_t new_sz);

/**
 * @ls_xpool_free
 * @brief Frees (releases) memory back to the session memory pool.
 * @details The memory pointer must be one returned from a previous
 *   successful call to ls_xpool_alloc.
 *
 * @param[in] pool - A pointer to an initialized session pool object.
 * @param[in] data - A pointer to the allocated memory.
 * @return Void.
 *
 * @see ls_xpool_alloc
 */
void    ls_xpool_free(ls_xpool_t *pool, void *data);

/**
 * @ls_xpool_isempty
 * @brief Specifies whether or not a session memory pool object is empty.
 *
 * @param[in] pool - A pointer to an initialized session pool object.
 * @return Non-zero if empty, else 0 if not.
 */
int     ls_xpool_isempty(ls_xpool_t *pool);

/**
 * @ls_xpool_skipfree
 * @brief Sets the mode of the session memory pool to \e not free memory
 *   blocks individually at this time.
 * @details This call may be used as an optimization when the pool
 *   is going to be reset or destroyed.
 *
 * @param[in] pool - A pointer to an initialized session pool object.
 * @return Void.
 */
void    ls_xpool_skipfree(ls_xpool_t *pool);

/**
 * @ls_xpool_delete
 * @brief Destroys then deletes a session memory pool object.
 * @details The object should have been created with a previous
 *   successful call to ls_xpool_new.
 *
 * @param[in] pool - A pointer to an initialized session pool object.
 * @return Void.
 *
 * @see ls_xpool_new
 */
void    ls_xpool_delete(ls_xpool_t *pool);

#ifdef __cplusplus
}
#endif

#endif //LS_XPOOL_H
