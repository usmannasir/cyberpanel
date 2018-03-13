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
#ifndef LS_MAP_H
#define LS_MAP_H

#include <lsr/ls_types.h>

#include <stddef.h>

/**
 * @file
 */


#ifdef __cplusplus
extern "C" {
#endif

// #define LSR_MAP_DEBUG


typedef struct ls_mapnode_s ls_mapnode_t;
typedef struct ls_map_s ls_map_t;


typedef ls_mapnode_t *ls_map_iter;

/**
 * @typedef ls_map_value_compare
 * @brief The user must provide a comparison function for the key structure.
 * It will be used whenever comparisons need to be made.
 *
 * @param[in] pVal1 - The first key to compare.
 * @param[in] pVal2 - The key to compare pVal1 against.
 * @return < 0 for pVal1 before pVal2, 0 for equal,
 * \> 0 for pVal1 after pVal2.
 */
typedef int (*ls_map_value_compare)(const void *pVal1, const void *pVal2);

/**
 * @typedef ls_map_foreach_fn
 * @brief A function that the user wants to apply to every node in the map.
 *
 * @param[in] pKey - The key from the current node.
 * @param[in] pValue - The value from the same node.
 * @return Should return 0 on success, not 0 on failure.
 */
typedef int (*ls_map_foreach_fn)(const void *pKey, void *pValue);

/**
 * @typedef ls_map_foreach2_fn
 * @brief A function that the user wants to apply to every node in the map.
 * Also allows a user provided data for the function.
 *
 * @param[in] pKey - The key from the current node.
 * @param[in] pValue - The value from the same node.
 * @param[in] pUData - The user data passed into the function.
 * @return Should return 0 on success, not 0 on failure.
 */
typedef int (*ls_map_foreach2_fn)(const void *pKey, void *pValue,
                                  void *pUData);

typedef int (*ls_map_insert_fn)(ls_map_t *pThis, const void *pKey,
                                void *pValue);
typedef void *(*ls_map_update_fn)(ls_map_t *pThis, const void *pKey,
                                  void *pValue, ls_map_iter node);
typedef ls_map_iter(*ls_map_find_fn)(ls_map_t *pThis, const void *pKey);

/**
 * @typedef ls_map_t
 * @brief A tree structure that follows the Red Black Tree structure.
 */
struct ls_map_s
{
    size_t                  sizenow;
    ls_mapnode_t           *root;
    ls_mapnode_t           *detached;
    ls_map_value_compare    vc_fn;
    ls_xpool_t             *xpool;
    ls_map_insert_fn        insert_fn;
    // Use either key/value or node, node can be null if key/value put in.
    ls_map_update_fn        update_fn;
    ls_map_find_fn          find_fn;
};


/** @ls_map_new
 * @brief Creates a new map.  Allocates from the global pool unless the pool parameter specifies a session pool.
 * Initializes the map according to the parameters.
 * @details The user may create his/her own val comp associated with his/her key structure,
 * but some sample ones for char * and ipv6 values are provided in ls_hash.h.
 * @note If the user knows the map will only last for a session, a pointer to a
 * session pool may be passed in the pool parameter.
 *
 * @param[in] vc - A pointer to the comparison function to use for the keys.
 * @param[in] pool - A session pool pointer, else NULL to specify the global pool.
 * @return A pointer to a new initialized map on success, NULL on failure.
 *
 * @see ls_map_delete, ls_hash_cmp_string, ls_hash_cmp_ci_string,
 * ls_hash_cmp_ipv6, ls_map_val_comp
 */
ls_map_t  *ls_map_new(ls_map_value_compare vc, ls_xpool_t *pool);

/** @ls_map
 * @brief Initializes the map.  Allocates from the global pool unless the pool parameter specifies a session pool.
 * @details The user may create his/her own val comp associated with his/her key structure,
 * but some sample ones for char * and ipv6 values are provided in ls_hash.h.
 * @note If the user knows the map will only last for a session, a pointer to a
 * session pool may be passed in the pool parameter.
 *
 * @param[in] pThis - A pointer to an allocated map.
 * @param[in] vc - A pointer to the comparison function to use for the keys.
 * @param[in] pool - A session pool pointer, else NULL to specify the global pool.
 * @return A pointer to the initialized map on success, NULL on failure.
 *
 * @see ls_map_d, ls_hash_cmp_string, ls_hash_cmp_ci_string, ls_hash_cmp_ipv6, ls_map_val_comp
 */
ls_map_t  *ls_map(ls_map_t *pThis, ls_map_value_compare vc,
                  ls_xpool_t *pool);

/** @ls_map_d
 * @brief Destroys the map.  Does not free the map structure itself, only the internals.
 * @note This function should be used in conjunction with ls_map.
 * The user is responsible for freeing the data itself.  This function only frees structures
 * it allocated.
 *
 * @param[in] pThis - A pointer to an initialized map.
 * @return Void.
 *
 * @see ls_map
 */
void ls_map_d(ls_map_t *pThis);

/** @ls_map_delete
 * @brief Deletes the map.  Frees the map internals and the map structure itself.
 * @note This function should be used in conjunction with ls_map_new.
 * The user is responsible for freeing the data itself.  This function only frees structures
 * it allocated.
 *
 * @param[in] pThis - A pointer to an initialized map.
 * @return Void.
 *
 * @see ls_map_new
 */
void ls_map_delete(ls_map_t *pThis);

/** @ls_map_getnodekey
 * @brief Gets the node's key.
 *
 * @param[in] node - The node to extract the key from.
 * @return The key.
 */
const void *ls_map_getnodekey(ls_map_iter node);

/** @ls_map_getnodeval
 * @brief Gets the node's value.
 *
 * @param[in] node - The node to extract the value from.
 * @return The value.
 */
void *ls_map_getnodeval(ls_map_iter node);


/** @ls_map_clear
 * @brief Empties the map of and frees the nodes and resets the size.
 * @note The values will not be freed in this function.  It is the user's
 * responsibility to free them.
 *
 * @param[in] pThis - A pointer to an initialized map.
 * @return Void.
 */
void ls_map_clear(ls_map_t *pThis);

/** @ls_map_releasenodes
 * @brief Releases node and any children it may have.
 * @note The values will not be freed in this function.  It is the user's
 * responsibility to free them.
 *
 * @param[in] pThis - A pointer to an initialized map.
 * @param[in] node - A pointer to the source node to release.
 * @return Void.
 */
void ls_map_releasenodes(ls_map_t *pThis, ls_map_iter node);

/** @ls_map_swap
 * @brief Swaps the lhs and rhs maps.
 *
 * @param[in,out] lhs - A pointer to an initialized map.
 * @param[in,out] rhs - A pointer to another initialized map.
 * @return Void.
 */
void ls_map_swap(ls_map_t *lhs, ls_map_t *rhs);

/** @ls_map_insert
 * @brief Inserts a node with the given key and value in the map.
 * @note \b IMPORTANT: The key \b MUST \b BE a part of the value structure.
 *
 * @param[in] pThis - A pointer to an initialized map.
 * @param[in] pKey - A pointer to the key of the new node.
 * @param[in] pValue - A pointer to the value of the new node.
 * @return 0 if added or -1 if not.
 */
int ls_map_insert(ls_map_t *pThis, const void *pKey, void *pValue);

/** @ls_map_find
 * @brief Finds the node with the given key in the map.
 *
 * @param[in] pThis - A pointer to an initialized map.
 * @param[in] pKey - The key to search for.
 * @return A pointer to the node if found or NULL if not found.
 */
ls_map_iter ls_map_find(ls_map_t *pThis, const void *pKey);

/** @ls_map_update
 * @brief Updates a node with the given key in the map.  Can use
 * the key or the node parameter to search with.
 * @note \b IMPORTANT: The key \b MUST \b BE a part of the value structure.
 *
 * @param[in] pThis - A pointer to an initialized map.
 * @param[in] pKey - The key of the node.
 * @param[in] pValue - The new value of the node.
 * @param[in] node - The node with the key/value to update.  The key must match
 * pKey.
 * @return The old value if updated or NULL if something went wrong.
 */
void *ls_map_update(ls_map_t *pThis, const void *pKey, void *pValue,
                    ls_map_iter node);

/** @ls_map_detachnode
 * @brief Detaches the node from the tree, but does \b NOT delete it.
 * @details These routines allow the user to remove a node from the tree,
 * then reattach with an updated key.
 *
 * @param[in] pThis - A pointer to an initialized map.
 * @param[in] node - A pointer to the node to detach.
 * @return The value of the node or NULL upon error.
 *
 * @see ls_map_attachnode
 */
void *ls_map_detachnode(ls_map_t *pThis, ls_map_iter node);

/** @ls_map_attachnode
 * @brief Attaches the node to the tree.
 * @note \b IMPORTANT: The node must be detached first.
 * @details These routines allow the user to remove a node from the tree,
 * then reattach with an updated key.
 *
 * @param[in] pThis - A pointer to an initialized map.
 * @param[in] pKey - The key of the node.
 * @param[in] pValue - The new value of the node.
 * @return 0 on success, -1 on failure.
 *
 * @see ls_map_detachnode
 */
int ls_map_attachnode(ls_map_t *pThis, const void *pKey, void *pVal);

/** @ls_map_deletenode
 * @brief Deletes the node from the map.
 *
 * @param[in] pThis - A pointer to an initialized map.
 * @param[in] node - A pointer to the node to delete.
 * @return The value from the node.
 */
void *ls_map_deletenode(ls_map_t *pThis, ls_map_iter node);

/** @ls_map_begin
 * @brief Gets the first node of the map.
 *
 * @param[in] pThis - A pointer to an initialized source map.
 * @return The first node of the map.
 */
ls_map_iter ls_map_begin(ls_map_t *pThis);

/** @ls_map_end
 * @brief Gets the end node of the map.
 *
 * @param[in] pThis - A pointer to an initialized map.
 * @return The end node of the map.
 */
ls_map_iter ls_map_end(ls_map_t *pThis);

/** @ls_map_next
 * @brief Gets the next node of the map.
 *
 * @param[in] pThis - A pointer to an initialized map.
 * @param[in] node - A pointer to the current node.
 * @return A pointer to the next node of the map, NULL if it's the end.
 */
ls_map_iter ls_map_next(ls_map_t *pThis, ls_map_iter node);

/** @ls_map_foreach
 * @brief Runs a function for each node in the map.  The function must
 * follow the #ls_map_foreach_fn format.
 *
 * @param[in] pThis - A pointer to an initialized map.
 * @param[in] beg - A pointer to the first node to apply the function to.
 * @param[in] end - A pointer to the last node to apply the function to.
 * @param[in] fun - A pointer to the \link #ls_map_foreach_fn function\endlink
 * to apply to nodes.
 * @return The number of nodes that the function applied to.
 */
int ls_map_foreach(ls_map_t *pThis, ls_map_iter beg,
                   ls_map_iter end, ls_map_foreach_fn fun);

/** @ls_map_foreach2
 * @brief Runs a function for each node in the map.  The function must
 * follow the #ls_map_foreach2_fn format.
 *
 * @param[in] pThis - A pointer to an initialized map.
 * @param[in] beg - A pointer to the first node to apply the function to.
 * @param[in] end - A pointer to the last node to apply the function to.
 * @param[in] fun - A pointer to the \link #ls_map_foreach2_fn function\endlink
 * to apply to nodes.
 * @param[in] pUData - A pointer to the user data to pass into the function.
 * @return The number of nodes that the function applied to.
 */
int ls_map_foreach2(ls_map_t *pThis, ls_map_iter beg,
                    ls_map_iter end, ls_map_foreach2_fn fun, void *pUData);

/** @ls_map_empty
 * @brief Specifies whether or not the map is empty.
 *
 * @param[in] pThis - A pointer to an initialized map.
 * @return Non-zero if empty, 0 if not.
 */
ls_inline int ls_map_empty(const ls_map_t *pThis)
{    return pThis->sizenow == 0;  }

/** @ls_map_size
 * @brief Gets the current size of the map.
 *
 * @param[in] pThis - A pointer to an initialized map.
 * @return The size of the map.
 */
ls_inline size_t ls_map_size(const ls_map_t *pThis)
{    return pThis->sizenow;       }

/** @ls_map_val_comp
 * @brief Gets the comparison function of the map.
 *
 * @param[in] pThis - A pointer to an initialized source map.
 * @return A pointer to the comparison function.
 */
ls_inline ls_map_value_compare ls_map_val_comp(ls_map_t *pThis)
{    return pThis->vc_fn;         }


#ifdef LSR_MAP_DEBUG
void ls_map_print(ls_map_iter node, int layer);
ls_inline void ls_map_printTree(ls_map_t *pThis)
{    ls_map_print(pThis->root, 0);    }
#endif

#ifdef __cplusplus
}
#endif


#endif //LS_MAP_H
