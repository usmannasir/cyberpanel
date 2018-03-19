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
#ifndef LSR_INTERNAL_H
#define LSR_INTERNAL_H

#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>

#include <lsr/ls_types.h>
#include <lsr/ls_atomic.h>
#include <lsr/ls_node.h>


/**
 * @file
 */


#ifdef __cplusplus
extern "C" {
#endif


typedef struct __link_s
{
    struct __link_s *next;
} __link_t;


typedef enum { RED, BLACK } ls_map_color;

struct ls_mapnode_s
{
    ls_map_color    color;
    const void     *pkey;
    void           *pvalue;
    struct ls_mapnode_s    *left;
    struct ls_mapnode_s    *right;
    struct ls_mapnode_s    *parent;
};

struct ls_hashelem_s
{
    struct ls_hashelem_s   *next;
    const void             *pkey;
    void                   *pdata;
    ls_hash_key_t           hkey;
};

#define HW_CACHE_SIZE  64
/**
 * @struct ls_lfqueue_s
 * @brief Lock free node based fifo queue.
 */
struct ls_lfqueue_s
{
    volatile ls_lfnodei_t   *volatile *phead;
    char                               pad[HW_CACHE_SIZE];
    volatile ls_atom_xptr_t            tail;
};

/**
 * @struct ls_lfstack_s
 * @brief Lock free node based stack.
 */
struct ls_lfstack_s
{
    volatile ls_atom_xptr_t  head;
};

/**
 * @struct ls_pool_header_s
 * @brief Global memory pool header.
 */
struct ls_pool_header_s
{
    uint32_t        size;
    uint32_t        magic;
};


#if defined( __x86_64 )||defined( __x86_64__ )
#define LSR_POOL_DATA_ALIGN              16
#else
#define LSR_POOL_DATA_ALIGN              8
#endif

/**
 * @struct ls_pool_blk_s
 * @brief Global memory pool block definition.
 */
struct ls_pool_blk_s
{
    union
    {
        struct ls_pool_blk_s           *next;
        struct ls_pool_header_s         header;
        char align[LSR_POOL_DATA_ALIGN];
    };
};
typedef struct ls_pool_blk_s       ls_pool_blk_t;

/**
 * @struct ls_xpool_header_s
 * @brief Session memory pool header.
 */
typedef union
{
    struct
    {
        uint32_t    size;
        uint32_t    magic;
    };
    char align[LSR_POOL_DATA_ALIGN];
} ls_xpool_header_t;

/**
 * @struct ls_xpool_bblk_s
 * @brief Session memory pool `big' block definition.
 */
struct ls_xpool_bblk_s
{
    struct ls_xpool_bblk_s   *prev;
    struct ls_xpool_bblk_s   *next;
    ls_xpool_header_t         header;
    char     data[];
};
typedef struct ls_xpool_bblk_s     ls_xpool_bblk_t;

/**
 * @ls_plistfree
 * @brief Frees (releases) a linked list of allocated memory blocks
 *   back to the global memory pool.
 * @details The list of memory blocks must have the same size,
 *   and must be linked as provided by the ls_pool_blk_t structure.
 *
 * @param[in] plist - A pointer to the linked list of allocated memory blocks.
 * @param[in] size - The size in bytes of each block.
 * @return Void.
 * @note This routine provides an efficient way to free a list of allocated
 *   blocks back to the global memory pool, such as in the case of releasing
 *   the \e superblocks from the session memory pool.
 */
void   ls_plistfree(ls_pool_blk_t *plist, size_t size);

/**
 * @ls_psavepending
 * @brief Saves a linked list of allocated memory blocks
 *   to be freed to the global memory pool at a later time.
 * @details The list of memory blocks may have various sizes.
 *   They must be linked as provided by the ls_xpool_bblk_t structure.
 *
 * @param[in] plist - A pointer to the linked list of allocated memory blocks.
 * @return Void.
 * @note This routine provides a way to delay the freeing of allocated memory
 *   until a more appropriate or convenient time.
 *
 * @see ls_pfreepending
 */
void   ls_psavepending(ls_xpool_bblk_t *plist);

/**
 * @ls_pfreepending
 * @brief Frees (releases) the list of previously \e saved allocated
 *   memory blocks back to the global memory pool.
 * @details The linked list must have been created with previous
 *   successful call(s) to ls_psavepending.

 * @return Void.
 *
 * @see ls_psavepending
 */
void   ls_pfreepending();

#ifdef __cplusplus
}
#endif


#endif //LSR_INTERNAL_H
