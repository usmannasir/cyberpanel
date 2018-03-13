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
#ifndef LS_PTRLIST_H
#define LS_PTRLIST_H


#include <stddef.h>
#include <string.h>
#include <sys/types.h>
#include <stdbool.h>
#include <lsr/ls_types.h>


/**
 * @file
 * @note
 * Pointer List -
 *   The pointer list object manages a list of objects through
 *   a list of pointers (void *) to them.
 *   The objects pointed to may be of any defined type.
 *   Functions are available to allocate, add, and remove elements
 *   to/from the list in a variety of ways, get information about the list,
 *   and also perform functions such as sorting the list.
 */


#ifdef __cplusplus
extern "C" {
#endif

/**
 * @typedef gpl_for_each_fn
 * @brief Function pointer when iterating through a pointer list object.
 */
typedef int (*gpl_for_each_fn)(void *);
/**
 * @typedef ls_ptrlist_iter
 * @brief Iterator for the pointer list object.
 */
typedef void **ls_ptrlist_iter;
/**
 * @typedef ls_const_ptrlist_iter
 * @brief Const iterator for the pointer list object.
 */
typedef void *const *ls_const_ptrlist_iter;

/**
 * @typedef ls_ptrlist_t
 */
struct ls_ptrlist_s
{
    /**
     * @brief The beginning of storage.
     */
    void **pstore;
    /**
     * @brief The end of storage.
     */
    void **pstoreend;
    /**
     * @brief The current end of data.
     */
    void **pend;
};

/**
 * @ls_ptrlist
 * @brief Initializes a pointer list object.
 * @details This object manages pointers to generic (void *) objects.
 *   An initial size is specified, but the size may change with other
 *   ls_ptrlist_* routines.
 *
 * @param[in] pThis - A pointer to an allocated pointer list object.
 * @param[in] initSize - The initial size to allocate for the list elements,
 *    which may be 0 specifying an empty initialized pointer list.
 * @return Void.
 *
 * @see ls_ptrlist_new, ls_ptrlist_d
 */
void ls_ptrlist(ls_ptrlist_t *pThis, size_t initSize);

/**
 * @ls_ptrlist_copy
 * @brief Copies a pointer list object.
 *
 * @param[in] pThis - A pointer to an allocated pointer list object (destination).
 * @param[in] pRhs - A pointer to the pointer list object to be copied (source).
 * @return Void.
 */
void ls_ptrlist_copy(ls_ptrlist_t *pThis, const ls_ptrlist_t *pRhs);

/**
 * @ls_ptrlist_new
 * @brief Creates a new pointer list object.
 * @details The routine allocates and initializes an object
 *   which manages pointers to generic (void *) objects.
 *   An initial size is specified, but the size may change with other
 *   ls_ptrlist_* routines.
 *
 * @param[in] initSize - The initial size to allocate for the list elements,
 *    which may be 0 specifying an empty initialized pointer list.
 * @return A pointer to an initialized pointer list object.
 *
 * @see ls_ptrlist, ls_ptrlist_delete
 */
ls_ptrlist_t *ls_ptrlist_new(size_t initSize);

/**
 * @ls_ptrlist_d
 * @brief Destroys the contents of a pointer list object.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @return Void.
 *
 * @see ls_ptrlist
 */
void ls_ptrlist_d(ls_ptrlist_t *pThis);

/**
 * @ls_ptrlist_delete
 * @brief Destroys then deletes a pointer list object.
 * @details The object should have been created with a previous
 *   successful call to ls_ptrlist_new.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @return Void.
 *
 * @see ls_ptrlist_new
 */
void ls_ptrlist_delete(ls_ptrlist_t *pThis);

/**
 * @ls_ptrlist_resize
 * @brief Changes the total storage or list size in a pointer list object.
 * @details If the new size is greater than the current capacity,
 *   the storage is extended with the existing data remaining intact.
 *   If the new size is less, the list size is truncated.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @param[in] sz - The new size in terms of number of elements (pointers).
 * @return 0 on success, else -1 on error.
 */
int ls_ptrlist_resize(ls_ptrlist_t *pThis, size_t sz);

/**
 * @ls_ptrlist_size
 * @brief Gets the current size of a pointer list object.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @return The size in terms of number of elements (pointers).
 */
ls_inline ssize_t ls_ptrlist_size(const ls_ptrlist_t *pThis)
{   return pThis->pend - pThis->pstore;   }

/**
 * @ls_ptrlist_empty
 * @brief Specifies whether or not a pointer list object contains any elements.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @return True if empty, else false.
 */
ls_inline bool ls_ptrlist_empty(const ls_ptrlist_t *pThis)
{   return pThis->pend == pThis->pstore;   }

/**
 * @ls_ptrlist_full
 * @brief Specifies whether or not a pointer list object is at full capacity.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @return True if full, else false.
 */
ls_inline bool ls_ptrlist_full(const ls_ptrlist_t *pThis)
{   return pThis->pend == pThis->pstoreend;   }

/**
 * @ls_ptrlist_capacity
 * @brief Gets the storage capacity of a pointer list object;
 *   \e i.e., how many elements it may hold.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @return The capacity in terms of number of elements (pointers).
 */
ls_inline size_t ls_ptrlist_capacity(const ls_ptrlist_t *pThis)
{   return pThis->pstoreend - pThis->pstore;   }

/**
 * @ls_ptrlist_clear
 * @brief Clears (empties, deletes) a pointer list object of all its elements.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @return Void.
 */
ls_inline void ls_ptrlist_clear(ls_ptrlist_t *pThis)
{   pThis->pend = pThis->pstore;   }

/**
 * @ls_ptrlist_begin
 * @brief Gets the iterator beginning of a pointer list object.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @return The iterator beginning of a pointer list object.
 */
ls_inline ls_ptrlist_iter ls_ptrlist_begin(ls_ptrlist_t *pThis)
{   return pThis->pstore;   }

/**
 * @ls_ptrlist_end
 * @brief Gets the iterator end of a pointer list object.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @return The iterator end of a pointer list object.
 */
ls_inline ls_ptrlist_iter ls_ptrlist_end(ls_ptrlist_t *pThis)
{   return pThis->pend;   }

/**
 * @ls_ptrlist_back
 * @brief Gets the last element (pointer) in a pointer list object.
 * @details The routine does \e not change anything in the object.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @return The last element (pointer) in a pointer list object.
 */
ls_inline void *ls_ptrlist_back(const ls_ptrlist_t *pThis)
{   return *(pThis->pend - 1);   }

/**
 * @ls_ptrlist_reserve
 * @brief Reserves storage in a pointer list object.
 * @details If the object currently contains data elements,
 *   the storage is extended with the existing data remaining intact.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @param[in] sz - The new size in terms of number of elements (pointers).
 * @return 0 on success, else -1 on error.
 */
int ls_ptrlist_reserve(ls_ptrlist_t *pThis, size_t sz);

/**
 * @ls_ptrlist_grow
 * @brief Extends (increases) the storage capacity of a pointer list object.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @param[in] sz - The size increment in terms of number of elements (pointers).
 * @return 0 on success, else -1 on error.
 */
int ls_ptrlist_grow(ls_ptrlist_t *pThis, size_t sz);

/**
 * @ls_ptrlist_erase
 * @brief Erases (deletes) an element from a pointer list object.
 * @details This decreases the size of the pointer list object by one.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @param[in,out] iter - Iterator specifying the element to erase.
 * @return The same iterator which now specifies the previous last element in
 *   the pointer list object.
 * @note The order of the elements in the pointer list object
 *   may have been changed.
 *   This may be significant if the elements were expected to be in a
 *   specific order.
 * @note Note also that when erasing the last (\e i.e., end) element
 *   in the list, upon return the iterator specifies the newly erased
 *   element, which is thus invalid.
 */
ls_inline ls_ptrlist_iter ls_ptrlist_erase(
    ls_ptrlist_t *pThis, ls_ptrlist_iter iter)
{
    /** Do not use *(-- to avoid trigger compiler bug */
    --pThis->pend;
    *iter = *(pThis->pend);
    return iter;
}

/**
 * @ls_ptrlist_unsafepushback
 * @brief Adds (pushes) an element to the end of a pointer list object.
 * @details This function is unsafe in that it will not check if there
 * is enough space allocated.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @param[in] pPointer - The element (pointer) to add.
 * @return Void.
 * @warning It is the responsibility of the user to ensure that
 *   there is sufficient allocated storage for the request.
 */
ls_inline void ls_ptrlist_unsafepushback(
    ls_ptrlist_t *pThis, void *pPointer)
{   *pThis->pend++ = pPointer;   }

/**
 * @ls_ptrlist_unsafepushbackn
 * @brief Adds (pushes) a number of elements to the end
 *   of a pointer list object.
 * @details This function is unsafe in that it will not check if there
 * is enough space allocated.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @param[in] pPointer - A pointer to the elements (pointers) to add.
 * @param[in] n - The number of elements to add.
 * @return Void.
 * @warning It is the responsibility of the user to ensure that
 *   there is sufficient allocated storage for the request.
 */
void ls_ptrlist_unsafepushbackn(
    ls_ptrlist_t *pThis, void **pPointer, int n);

/**
 * @ls_ptrlist_unsafepopbackn
 * @brief Pops a number of elements from the end
 *   of a pointer list object.
 * @details This function is unsafe in that it will not check if there
 * is enough space allocated.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @param[out] pPointer - A pointer where the elements (pointers) are returned.
 * @param[in] n - The number of elements to return.
 * @return Void.
 * @warning It is the responsibility of the user to ensure that
 *   there is sufficient allocated storage for the request.
 */
void ls_ptrlist_unsafepopbackn(
    ls_ptrlist_t *pThis, void **pPointer, int n);

/**
 * @ls_ptrlist_pushback
 * @brief Adds an element to the end of a pointer list object.
 * @details If the pointer list object is at capacity, the storage is extended.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @param[in] pPointer - The element (pointer) to add.
 * @return 0 on success, else -1 on error.
 */
int  ls_ptrlist_pushback(ls_ptrlist_t *pThis, void *pPointer);

/**
 * @ls_ptrlist_pushback2
 * @brief Adds a list of elements to the end of a pointer list object.
 * @details If the pointer list object is at capacity, the storage is extended.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @param[in] plist - A pointer to the pointer list object
 *   containing the elements (pointers) to add.
 * @return 0 on success, else -1 on error.
 */
int  ls_ptrlist_pushback2(ls_ptrlist_t *pThis, const ls_ptrlist_t *plist);

/**
 * @ls_ptrlist_popback
 * @brief Pops an element from the end of a pointer list object.
 * @details This decreases the size of the pointer list object by one.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @return The element (pointer).
 * @warning It is expected that the pointer list object is \e not empty.
 */
ls_inline void *ls_ptrlist_popback(ls_ptrlist_t *pThis)
{   --pThis->pend;     return *pThis->pend;   }

/**
 * @ls_ptrlist_popfront
 * @brief Pops a number of elements from the beginning (front)
 *   of a pointer list object.
 * @details The number of elements returned cannot be greater
 *   than the current size of the pointer list object.
 *   The remaining elements, if any, are then moved to the front.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @param[out] pPointer - A pointer where the elements (pointers) are returned.
 * @param[in] n - The number of elements to return.
 * @return The number of elements returned.
 */
ls_inline int ls_ptrlist_popfront(
    ls_ptrlist_t *pThis, void **pPointer, int n)
{
    if (n > ls_ptrlist_size(pThis))
        n = ls_ptrlist_size(pThis);
    memmove(pPointer, pThis->pstore, n * sizeof(void *));
    if (n >= ls_ptrlist_size(pThis))
        ls_ptrlist_clear(pThis);
    else
    {
        memmove(pThis->pstore, pThis->pstore + n,
                sizeof(void *) * (pThis->pend - pThis->pstore - n));
        pThis->pend -= n;
    }
    return n;
}

/**
 * @ls_ptrlist_sort
 * @brief Sorts the elements in a pointer list object.
 * @details The routine uses qsort(3).
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @param[in] compare - The compare function used to sort.
 * @return Void.
 */
void ls_ptrlist_sort(
    ls_ptrlist_t *pThis, int (*compare)(const void *, const void *));

/**
 * @ls_ptrlist_swap
 * @brief Exchanges (swaps) the contents of two pointer list objects.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @param[in] pRhs - A pointer to the initialized object to swap with.
 * @return Void.
 */
void ls_ptrlist_swap(
    ls_ptrlist_t *pThis, ls_ptrlist_t *pRhs);

/**
 * @ls_ptrlist_lowerbound
 * @brief Gets an element or the lower bound in a sorted pointer list object.
 * @details The pointer list object elements must be sorted,
 *   as the routine uses a binary search algorithm.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @param[in] pKey - A pointer to the key to match.
 * @param[in] compare - The compare function used to match.
 * @return The iterator to the element if found,
 *   else the lower bound.
 *
 * @see ls_ptrlist_sort
 */
ls_const_ptrlist_iter ls_ptrlist_lowerbound(
    const ls_ptrlist_t *pThis,
    const void *pKey, int (*compare)(const void *, const void *));

/**
 * @ls_ptrlist_bfind
 * @brief Finds an element in a sorted pointer list object.
 * @details The pointer list object elements must be sorted,
 *   as the routine uses a binary search algorithm.
 *
 * @param[in] pThis - A pointer to an initialized pointer list object.
 * @param[in] pKey - A pointer to the key to match.
 * @param[in] compare - The compare function used to match.
 * @return The iterator to the element if found,
 *   else ls_ptrlist_end if not found.
 *
 * @see ls_ptrlist_sort
 */
ls_const_ptrlist_iter ls_ptrlist_bfind(
    const ls_ptrlist_t *pThis,
    const void *pKey, int (*compare)(const void *, const void *));

/**
 * @ls_ptrlist_foreach
 * @brief Iterates through a list of elements
 *   calling the specified function for each.
 *
 * @param[in] beg - The beginning pointer list object iterator.
 * @param[in] end - The end iterator.
 * @param[in] fn - The function to be called for each element.
 * @return The number of elements processed.
 */
int ls_ptrlist_foreach(
    ls_ptrlist_iter beg, ls_ptrlist_iter end, gpl_for_each_fn fn);


#ifdef __cplusplus
}
#endif

#endif  /* LS_PTRLIST_H */

