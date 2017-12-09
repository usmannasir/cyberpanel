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
#ifndef LS_HASH_H
#define LS_HASH_H


#include <ctype.h>
#include <stddef.h>
#include <lsr/ls_types.h>
#include <lsr/xxhash.h>

/**
 * @file
 * @note \b IMPORTANT: For every hash element, the key
 * \b MUST \b BE a part of the value structure.
 */

#ifdef __cplusplus
extern "C" {
#endif


typedef struct ls_hash_s ls_hash_t;
typedef struct ls_hashelem_s ls_hashelem_t;


typedef ls_hashelem_t *ls_hash_iter;

/**
 * @typedef ls_hash_hasher
 * @brief The user must provide a hash function for the key structure.
 *  It will be used to calculate where the hash element belongs.
 *
 * @param[in] p - A pointer to the key.
 * @return A ls_hash_key_t value.
 */
typedef ls_hash_key_t (*ls_hash_hasher)(const void *p);

/**
 * @typedef ls_hash_value_compare
 * @brief The user must provide a comparison function for the key structure.
 *  It will be used whenever comparisons need to be made.
 *
 * @param[in] pVal1 - A pointer to the first key to compare.
 * @param[in] pVal2 - A pointer to the second key to compare.
 * @return < 0 for pVal1 before pVal2, 0 for equal,
 *  \> 0 for pVal1 after pVal2.
 */
typedef int (*ls_hash_value_compare)(const void *pVal1, const void *pVal2);

/**
 * @typedef ls_hash_foreach_fn
 * @brief A function that the user wants to apply to every element
 *  in the hash table.
 *
 * @param[in] pKey - A pointer to the key from the current hash element.
 * @param[in] pData - A pointer to the value from the same hash element.
 * @return Should return 0 on success, not 0 on failure.
 */
typedef int (*ls_hash_foreach_fn)(const void *pKey, void *pData);

/**
 * @typedef ls_hash_foreach2_fn
 * @brief A function that the user wants to apply to every element
 *  in the hash table.
 *  Also allows a user provided data for the function.
 *
 * @param[in] pKey - A pointer to the key from the current hash element.
 * @param[in] pData - A pointer to the value from the same hash element.
 * @param[in] pUData - A pointer to the user data passed into the function.
 * @return Should return 0 on success, not 0 on failure.
 */
typedef int (*ls_hash_foreach2_fn)(
    const void *pKey, void *pData, void *pUData);

typedef ls_hash_iter(*ls_hash_insert_fn)(
    ls_hash_t *pThis, const void *pKey, void *pValue);
typedef ls_hash_iter(*ls_hash_update_fn)(
    ls_hash_t *pThis, const void *pKey, void *pValue);
typedef ls_hash_iter(*ls_hash_find_fn)(ls_hash_t *pThis, const void *pKey);



/**
 * @typedef ls_hash_t
 * @brief A hash table structure.
 */
struct ls_hash_s
{
    ls_hashelem_t     **htable;
    ls_hashelem_t     **htable_end;
    size_t              sizemax;
    size_t              sizenow;
    int                 load_factor;
    ls_hash_hasher      hf_fn;
    ls_hash_value_compare vc_fn;
    int                 grow_factor;
    ls_xpool_t         *xpool;

    ls_hash_insert_fn   insert_fn;
    ls_hash_update_fn   update_fn;
    ls_hash_find_fn     find_fn;
};

/** @ls_hash_new
 * @brief Creates a new hash table.  Allocates from the global pool
 *  unless the pool parameter specifies a session pool.
 *  Initializes the table according to the parameters.
 * @details The user may create his/her own hash function and val comp
 *  associated with his/her key structure,
 *  but some sample ones for char * and ipv6 values are provided below.
 * @note If the user knows the table will only last for a session,
 *  a pointer to a session pool may be passed in the pool parameter.
 *
 * @param[in] init_size - Initial capacity to allocate.
 * @param[in] hf - A pointer to the hash function to use for the keys.
 * @param[in] vc - A pointer to the comparison function to use for the keys.
 * @param[in] pool - A session pool pointer,
 *  else NULL to specify the global pool.
 * @return A pointer to a new initialized hash table on success,
 *  NULL on failure.
 *
 * @see ls_hash_delete, ls_hash_hf_string, ls_hash_hf_ci_string,
 *  ls_hash_hf_ipv6, ls_hash_hash_fn, ls_hash_cmp_string,
 *  ls_hash_cmp_ci_string, ls_hash_cmp_ipv6, ls_hash_val_comp
 */
ls_hash_t *ls_hash_new(size_t init_size,
                       ls_hash_hasher hf, ls_hash_value_compare vc, ls_xpool_t *pool);

/** @ls_hash
 * @brief Initializes the hash table.  Allocates from the global pool
 *  unless the pool parameter specifies a session pool.
 * @details The user may create his/her own hash function and val comp
 *  associated with his/her key structure,
 *  but some sample ones for char * and ipv6 values are provided below.
 * @note If the user knows the table will only last for a session,
 *  a pointer to a session pool may be passed in the pool parameter.
 *
 * @param[in] pThis - A pointer to an allocated hash table object.
 * @param[in] init_size - Initial capacity to allocate.
 * @param[in] hf - A pointer to the hash function to use for the keys.
 * @param[in] vc - A pointer to the comparison function to use for the keys.
 * @param[in] pool - A session pool pointer,
 *  else NULL to specify the global pool.
 * @return A pointer to the initialized hash table on success, NULL on failure.
 *
 * @see ls_hash_d, ls_hash_hfstring, ls_hash_hfcistring,
 *  ls_hash_hfipv6, ls_hash_hashfn, ls_hash_cmpstring,
 *  ls_hash_cmpcistring, ls_hash_cmpipv6, ls_hash_val_comp
 */
ls_hash_t *ls_hash(ls_hash_t *pThis, size_t init_size,
                   ls_hash_hasher hf, ls_hash_value_compare vc, ls_xpool_t *pool);

/** @ls_hash_d
 * @brief Destroys the table.
 *  Does not free the hash structure itself, only the internals.
 * @note This function should be used in conjunction with ls_hash.
 *  The user is responsible for freeing the data itself.
 *  This function only frees structures allocated by lsr hash functions.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @return Void.
 *
 * @see ls_hash
 */
void ls_hash_d(ls_hash_t *pThis);

/** @ls_hash_delete
 * @brief Deletes the table.  Frees the table and the hash structure itself.
 * @note This function should be used in conjunction with ls_hash_new.
 *  The user is responsible for freeing the data itself.
 *  This function only frees structures allocated by lsr hash functions.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @return Void.
 *
 * @see ls_hash_new
 */
void ls_hash_delete(ls_hash_t *pThis);

/** @ls_hash_getkey
 * @brief Given a hash element, returns the key.
 *
 * @param[in] pElem - A pointer to the hash element to get the key from.
 * @return The key.
 */
const void *ls_hash_getkey(ls_hashelem_t *pElem);

/** @ls_hash_getdata
 * @brief Given a hash element, returns the data/value.
 *
 * @param[in] pElem - A pointer to the hash element to get the data from.
 * @return The data.
 */
void *ls_hash_getdata(ls_hashelem_t *pElem);

/** @ls_hash_gethkey
 * @brief Given a hash element, returns the hash key.
 *
 * @param[in] pElem - A pointer to the hash element to get the hash key from.
 * @return The hash key.
 */
ls_hash_key_t ls_hash_gethkey(ls_hashelem_t *pElem);

/** @ls_hash_getnext
 * @brief Given a hash element, returns the next hash element in the same
 *  array slot.
 *
 * @param[in] pElem - A pointer to the current hash element.
 * @return The next hash element, or NULL if there are no more in the slot.
 */
ls_hashelem_t *ls_hash_getnext(ls_hashelem_t *pElem);

/** @ls_hash_hfstring
 * @brief A provided hash function for strings.  Case sensitive.
 *
 * @param[in] __s - The string to calculate.
 * @return The hash key.
 */
ls_hash_key_t ls_hash_hfstring(const void *__s);

/** @ls_hash_cmpstring
 * @brief A provided comparison function for strings.  Case sensitive.
 *
 * @param[in] pVal1 - The first string to compare.
 * @param[in] pVal2 - The second string to compare.
 * @return Result according to #ls_hash_val_comp.
 */
int ls_hash_cmpstring(const void *pVal1, const void *pVal2);

/** @ls_hash_hfcistring
 * @brief A provided hash function for strings.  Case insensitive.
 *
 * @param[in] __s - The string to calculate.
 * @return The hash key.
 */
ls_hash_key_t ls_hash_hfcistring(const void *__s);

/** @ls_hash_cmpcistring
 * @brief A provided comparison function for strings.  Case insensitive.
 *
 * @param[in] pVal1 - The first string to compare.
 * @param[in] pVal2 - The second string to compare.
 * @return Result according to #ls_hash_val_comp.
 */
int ls_hash_cmpcistring(const void *pVal1, const void *pVal2);

/** @ls_hash_hfipv6
 * @brief A provided hash function for ipv6 values (unsigned long).
 *
 * @param[in] pKey - A pointer to the value to calculate.
 * @return The hash key.
 */
ls_hash_key_t ls_hash_hfipv6(const void *pKey);

/** @ls_hash_cmpipv6
 * @brief A provided comparison function for ipv6 values (unsigned long).
 *
 * @param[in] pVal1 - The first value to compare.
 * @param[in] pVal2 - The second value to compare.
 * @return Result according to #ls_hash_val_comp.
 */
int ls_hash_cmpipv6(const void *pVal1, const void *pVal2);

/** @ls_hash_clear
 * @brief Empties the table of and frees the elements and resets the size.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @return Void.
 */
void ls_hash_clear(ls_hash_t *pThis);

/** @ls_hash_erase
 * @brief Erases the element from the table.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @param[in] iter - A pointer to the element to remove from the table.
 *  This will be freed within the function.
 * @return Void.
 */
void ls_hash_erase(ls_hash_t *pThis, ls_hash_iter iter);

/** @ls_hash_swap
 * @brief Swaps the lhs and rhs hash tables.
 *
 * @param[in,out] lhs - A pointer to an initialized hash table object.
 * @param[in,out] rhs - A pointer to another initialized hash table object.
 * @return Void.
 */
void ls_hash_swap(ls_hash_t *lhs, ls_hash_t *rhs);

/** @ls_hash_find
 * @brief Finds the element with the given key in the hash table.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @param[in] pKey - The key to search for.
 * @return A pointer to the hash element if found or NULL if not found.
 */
ls_inline ls_hash_iter ls_hash_find(ls_hash_t *pThis, const void *pKey)
{   return (pThis->find_fn)(pThis, pKey);             }

/** @ls_hash_insert
 * @brief Inserts an element with the given key and value in the hash table.
 * @note \b IMPORTANT: The key \b MUST \b BE a part of the value structure.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @param[in] pKey - The key of the new hash element.
 * @param[in] pValue - The value of the new hash element.
 * @return A pointer to the hash element if added or NULL if not.
 */
ls_inline ls_hash_iter ls_hash_insert(
    ls_hash_t *pThis, const void *pKey, void *pValue)
{   return (pThis->insert_fn)(pThis, pKey, pValue);   }

/** @ls_hash_update
 * @brief Updates an element with the given key in the hash table.
 *  Inserts if it doesn't exist.
 * @note \b IMPORTANT: The key \b MUST \b BE a part of the value structure.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @param[in] pKey - The key of the hash element.
 * @param[in] pValue - The value of the hash element.
 * @return A pointer to the hash element if updated
 *  or NULL if something went wrong.
 */
ls_inline ls_hash_iter ls_hash_update(
    ls_hash_t *pThis, const void *pKey, void *pValue)
{   return (pThis->update_fn)(pThis, pKey, pValue);   }

/** @ls_hash_hash_function
 * @brief Gets the hash function of the hash table.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @return A pointer to the hash function.
 */
ls_inline ls_hash_hasher ls_hash_hash_function(ls_hash_t *pThis)
{   return pThis->hf_fn;    }

/** @ls_hash_val_comp
 * @brief Gets the comparison function of the hash table.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @return A pointer to the comparison function.
 */
ls_inline ls_hash_value_compare ls_hash_val_comp(ls_hash_t *pThis)
{   return pThis->vc_fn;    }

/** @ls_hash_setloadfactor
 * @brief Sets the load factor of the hash table.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @param[in] f - The load factor to update the table to.
 * @return Void.
 */
ls_inline void ls_hash_setloadfactor(ls_hash_t *pThis, int f)
{    if (f > 0)    pThis->load_factor = f;  }

/** @ls_hash_getgrowfactor
 * @brief Sets the grow factor of the hash table.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @param[in] f - The grow factor to update the table to.
 * @return Void.
 */
ls_inline void ls_hash_getgrowfactor(ls_hash_t *pThis, int f)
{    if (f > 0)    pThis->grow_factor = f;  }

/** @ls_hash_empty
 * @brief Specifies whether or not the hash table is empty.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @return Non-zero if empty, 0 if not.
 */
ls_inline int ls_hash_empty(const ls_hash_t *pThis)
{   return pThis->sizenow == 0; }

/** @ls_hash_size
 * @brief Gets the current size of the hash table.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @return The size of the table.
 */
ls_inline size_t ls_hash_size(const ls_hash_t *pThis)
{   return pThis->sizenow;      }

/** @ls_hash_capacity
 * @brief Gets the current capacity of the hash table.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @return The capacity of the table.
 */
ls_inline size_t ls_hash_capacity(const ls_hash_t *pThis)
{   return pThis->sizemax;  }

/** @ls_hash_begin
 * @brief Gets the first element of the hash table.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @return A pointer to the first element of the table.
 */
ls_hash_iter ls_hash_begin(ls_hash_t *pThis);

/** @ls_hash_end
 * @brief Gets the end element of the hash table.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @return A pointer to the end element of the table.
 */
ls_inline ls_hash_iter ls_hash_end(ls_hash_t *pThis)
{   return NULL;  }

/** @ls_hash_next
 * @brief Gets the next element of the hash table.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @param[in] iter - A pointer to the current hash element.
 * @return A pointer to the next element of the table, NULL if it's the end.
 */
ls_hash_iter ls_hash_next(ls_hash_t *pThis, ls_hash_iter iter);

/** @ls_hash_foreach
 * @brief Runs a function for each element in the hash table.
 *  The function must follow the #ls_hash_foreach_fn format.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @param[in] beg - A pointer to the first hash element
 *  to apply the function to.
 * @param[in] end - A pointer to the last hash element
 *  to apply the function to.
 * @param[in] fun - A pointer to the
 *  \link #ls_hash_foreach_fn function\endlink to apply to hash elements.
 * @return The number of hash elements that the function applied to.
 */
int ls_hash_foreach(ls_hash_t *pThis,
                    ls_hash_iter beg, ls_hash_iter end, ls_hash_foreach_fn fun);

/** @ls_hash_foreach2
 * @brief Runs a function for each element in the hash table.
 *  The function must follow the #ls_hash_foreach2_fn format.
 *
 * @param[in] pThis - A pointer to an initialized hash table object.
 * @param[in] beg - A pointer to the first hash element
 *  to apply the function to.
 * @param[in] end - A pointer to the last hash element
 *  to apply the function to.
 * @param[in] fun - A pointer to the
 *  \link #ls_hash_foreach2_fn function\endlink to apply to hash elements.
 * @param[in] pUData - A pointer to the user data to pass into the function.
 * @return The number of hash elements that the function applied to.
 */
int ls_hash_foreach2(ls_hash_t *pThis,
                     ls_hash_iter beg, ls_hash_iter end, ls_hash_foreach2_fn fun,
                     void *pUData);


#if defined( __x86_64 )||defined( __x86_64__ )
#define XXH   XXH64
#else
#define XXH   XXH32
#endif

#ifdef __cplusplus
}
#endif


#endif //LS_HASH_H
