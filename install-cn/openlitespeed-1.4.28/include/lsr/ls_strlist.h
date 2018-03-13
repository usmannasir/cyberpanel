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
#ifndef LS_STRLIST_H
#define LS_STRLIST_H


#include <lsr/ls_ptrlist.h>
#include <lsr/ls_types.h>


/**
 * @file
 * @note
 * String List -
 *   The string list object manages a list of ls_str_t objects through
 *   a list of pointers to them.
 *   Functions are available to allocate, add, and remove elements
 *   to/from the list in a variety of ways, get information about the list,
 *   and also perform functions such as sorting the list.
 *
 * @warning Note the difference between
 *   ls_strlist_{push,pop,insert,erase} and ls_strlist_{add,remove,clear,_d}.\n
 *   {push,pop,...} expect user allocated (constructed) ls_str_t objects.\n
 *   {add,remove,...} allocate ls_str_t objects given char \*s,
 *   and deallocate the objects when called to.\n
 *   Do \*NOT\* mix these mechanisms.
 */


#ifdef __cplusplus
extern "C" {
#endif

/**
 * @typedef ls_strlist_iter
 * @brief Iterator for the string list object.
 */
typedef ls_str_t   **ls_strlist_iter;

/**
 * @typedef ls_const_strlist_iter
 * @brief Const iterator for the string list object.
 */
typedef ls_str_t *const  *ls_const_strlist_iter;


/**
 * @ls_strlist
 * @brief Initializes a string list object.
 * @details This object manages pointers to ls_str_t objects.
 *   An initial size is specified, but the size may change with other
 *   ls_strlist_* routines.
 *
 * @param[in] pThis - A pointer to an allocated string list object.
 * @param[in] initSize - The initial size to allocate for the list elements,
 *    which may be 0 specifying an empty initialized string list.
 * @return Void.
 *
 * @see ls_strlist_new, ls_strlist_d, ls_str
 */
ls_inline void ls_strlist(ls_strlist_t *pThis, size_t initSize)
{   ls_ptrlist(pThis, initSize);   }

/**
 * @ls_strlist_copy
 * @brief Copies a string list object.
 *
 * @param[in] pThis - A pointer to an allocated string list object (destination).
 * @param[in] pRhs - A pointer to the string list object to be copied (source).
 * @return Void.
 */
void ls_strlist_copy(ls_strlist_t *pThis, const ls_strlist_t *pRhs);

/**
 * @ls_strlist_new
 * @brief Creates a new string list object.
 * @details The routine allocates and initializes an object
 *   which manages pointers to ls_str_t objects.
 *   An initial size is specified, but the size may change with other
 *   ls_strlist_* routines.
 *
 * @param[in] initSize - The initial size to allocate for the list elements,
 *    which may be 0 specifying an empty initialized string list.
 * @return A pointer to an initialized string list object.
 *
 * @see ls_strlist, ls_strlist_delete
 */
ls_strlist_t *ls_strlist_new(size_t initSize);

/**
 * @ls_strlist_d
 * @brief Deletes the elements and destroys the contents of a string list object.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @return Void.
 *
 * @see ls_strlist
 */
void ls_strlist_d(ls_strlist_t *pThis);

/**
 * @ls_strlist_delete
 * @brief Deletes the elements and destroys the contents of a string list object,
 *   then deletes the object.
 * @details The object should have been created with a previous
 *   successful call to ls_strlist_new.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @return Void.
 *
 * @see ls_strlist_new
 */
void ls_strlist_delete(ls_strlist_t *pThis);

/* derived from ls_ptrlist */

/**
 * @ls_strlist_resize
 * @brief Changes the storage or data size in a string list object.
 * @details If the new size is greater than the current capacity,
 *   the storage is extended with the existing data remaining intact.
 *   If the new size is less, the data size is truncated.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[in] sz - The new size in terms of number of elements.
 * @return 0 on success, else -1 on error.
 */
ls_inline int ls_strlist_resize(ls_strlist_t *pThis, size_t sz)
{   return ls_ptrlist_resize(pThis, sz);   }

/**
 * @ls_strlist_size
 * @brief Gets the current size of a string list object.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @return The size in terms of number of elements.
 */
ls_inline ssize_t ls_strlist_size(const ls_strlist_t *pThis)
{   return ls_ptrlist_size(pThis);   }

/**
 * @ls_strlist_empty
 * @brief Specifies whether or not a string list object contains any elements.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @return True if empty, else false.
 */
ls_inline bool ls_strlist_empty(const ls_strlist_t *pThis)
{   return ls_ptrlist_empty(pThis);   }

/**
 * @ls_strlist_full
 * @brief Specifies whether or not a string list object is at full capacity.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @return True if full, else false.
 */
ls_inline bool ls_strlist_full(const ls_strlist_t *pThis)
{   return ls_ptrlist_full(pThis);   }

/**
 * @ls_strlist_capacity
 * @brief Gets the storage capacity of a string list object;
 *   \e i.e., how many elements it may hold.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @return The capacity in terms of number of elements.
 */
ls_inline size_t ls_strlist_capacity(const ls_strlist_t *pThis)
{   return ls_ptrlist_capacity(pThis);   }

/**
 * @ls_strlist_begin
 * @brief Gets the iterator beginning of a string list object.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @return The iterator beginning of a string list object.
 */
ls_inline ls_strlist_iter ls_strlist_begin(ls_strlist_t *pThis)
{   return (ls_strlist_iter)ls_ptrlist_begin(pThis);   }

/**
 * @ls_strlist_end
 * @brief Gets the iterator end of a string list object.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @return The iterator end of a string list object.
 */
ls_inline ls_strlist_iter ls_strlist_end(ls_strlist_t *pThis)
{   return (ls_strlist_iter)ls_ptrlist_end(pThis);   }

/**
 * @ls_strlist_back
 * @brief Gets the last element in a string list object.
 * @details The routine does \e not change anything in the object.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @return The last element in a string list object.
 */
ls_inline ls_str_t *ls_strlist_back(const ls_strlist_t *pThis)
{   return (ls_str_t *)ls_ptrlist_back(pThis);   }

/**
 * @ls_strlist_reserve
 * @brief Reserves (allocates) storage in a string list object.
 * @details If the object currently contains data elements,
 *   the storage is extended with the existing data remaining intact.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[in] sz - The new size in terms of number of elements.
 * @return 0 on success, else -1 on error.
 */
ls_inline int ls_strlist_reserve(ls_strlist_t *pThis, size_t sz)
{   return ls_ptrlist_reserve(pThis, sz);   }

/**
 * @ls_strlist_grow
 * @brief Extends (increases) the storage capacity of a string list object.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[in] sz - The size increment in terms of number of elements.
 * @return 0 on success, else -1 on error.
 */
ls_inline int ls_strlist_grow(ls_strlist_t *pThis, size_t sz)
{   return ls_ptrlist_grow(pThis, sz);   }

/**
 * @ls_strlist_erase
 * @brief Erases (deletes) an element from a string list object.
 * @details This decreases the size of the string list object by one.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[in,out] iter - Iterator specifying the element to erase.
 * @return The same iterator which now specifies the previous last element in
 *   the string list object.
 * @note The order of the elements in the string list object
 *   may have been changed.
 *   This may be significant if the elements were expected to be in a
 *   specific order.
 * @note Note also that when erasing the last (\e i.e., end) element
 *   in the list, upon return the iterator specifies the newly erased
 *   element, which is thus invalid.
 */
ls_inline ls_strlist_iter ls_strlist_erase(
    ls_strlist_t *pThis, ls_strlist_iter iter)
{
    return (ls_strlist_iter)ls_ptrlist_erase(pThis, (ls_ptrlist_iter)iter);
}

/**
 * @ls_strlist_unsafepushback
 * @brief Adds (pushes) an element to the end of a string list object.
 * @details This function is unsafe in that it will not check if there is enough space
 * allocated.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[in] pPointer - The element to add.
 * @return Void.
 * @warning It is the responsibility of the user to ensure that
 *   there is sufficient allocated storage for the request.
 */
ls_inline void ls_strlist_unsafepushback(
    ls_strlist_t *pThis, ls_str_t *pPointer)
{   ls_ptrlist_unsafepushback(pThis, (void *)pPointer);   }

/**
 * @ls_strlist_unsafepushbackn
 * @brief Adds (pushes) a number of elements to the end of a string list object.
 * @details This function is unsafe in that it will not check if there is enough space
 * allocated.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[in] pPointer - A pointer to the elements to add.
 * @param[in] n - The number of elements to add.
 * @return Void.
 * @warning It is the responsibility of the user to ensure that
 *   there is sufficient allocated storage for the request.
 */
ls_inline void ls_strlist_unsafepushbackn(
    ls_strlist_t *pThis, ls_str_t **pPointer, int n)
{   ls_ptrlist_unsafepushbackn(pThis, (void **)pPointer, n);   }

/**
 * @ls_strlist_unsafepopbackn
 * @brief Pops a number of elements from the end of a string list object.
 * @details This function is unsafe in that it will not check if there is enough space
 * allocated.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[out] pPointer - A pointer where the elements are returned.
 * @param[in] n - The number of elements to return.
 * @return Void.
 * @warning It is the responsibility of the user to ensure that
 *   there is sufficient allocated storage for the request.
 */
ls_inline void ls_strlist_unsafepopbackn(
    ls_strlist_t *pThis, ls_str_t **pPointer, int n)
{   ls_ptrlist_unsafepopbackn(pThis, (void **)pPointer, n);   }

/**
 * @ls_strlist_pushback
 * @brief Adds an element to the end of a string list object.
 * @details If the string list object is at capacity, the storage is extended.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[in] pPointer - The element to add.
 * @return 0 on success, else -1 on error.
 */
ls_inline int ls_strlist_pushback(
    ls_strlist_t *pThis, ls_str_t *pPointer)
{   return ls_ptrlist_pushback(pThis, (void *)pPointer);   }

/**
 * @ls_strlist_pushback2
 * @brief Adds a list of elements to the end of a string list object.
 * @details If the string list object is at capacity, the storage is extended.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[in] plist - A pointer to the string list object
 *   containing the elements to add.
 * @return 0 on success, else -1 on error.
 */
ls_inline int ls_strlist_pushback2(
    ls_strlist_t *pThis, const ls_strlist_t *plist)
{   return ls_ptrlist_pushback2(pThis, plist);   }

/**
 * @ls_strlist_popback
 * @brief Pops an element from the end of a string list object.
 * @details This decreases the size of the string list object by one.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @return The element.
 * @warning It is expected that the string list object is \e not empty.
 */
ls_inline ls_str_t *ls_strlist_popback(ls_strlist_t *pThis)
{   return (ls_str_t *)ls_ptrlist_popback(pThis);   }

/**
 * @ls_strlist_popfront
 * @brief Pops a number of elements from the beginning (front)
 *   of a string list object.
 * @details The number of elements returned cannot be greater
 *   than the current size of the string list object.
 *   After popping,
 *   the remaining elements, if any, are moved to the front.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[out] pPointer - A pointer where the elements are returned.
 * @param[in] n - The number of elements to return.
 * @return The number of elements returned.
 */
ls_inline int ls_strlist_popfront(
    ls_strlist_t *pThis, ls_str_t **pPointer, int n)
{   return ls_ptrlist_popfront(pThis, (void **)pPointer, n);   }

/* specialized ls_strlist */

/**
 * @ls_strlist_releaseobjs
 * @brief Deletes all elements from a string list object, and empties the object.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @return Void.
 * @warning The elements of the string list object must have been allocated
 *   and added through previous successful calls to ls_strlist_add.
 *
 * @see ls_strlist_add, ls_strlist_remove, ls_strlist_clear
 */
void ls_strlist_releaseobjs(ls_strlist_t *pThis);

/**
 * @ls_strlist_foreach
 * @brief Iterates through a list of elements
 *   calling the specified function for each.
 *
 * @param[in] beg - The beginning string list object iterator.
 * @param[in] end - The end iterator.
 * @param[in] fn - The function to be called for each element.
 * @return The number of elements processed.
 */
ls_inline int ls_strlist_foreach(
    ls_strlist_iter beg, ls_strlist_iter end, gpl_for_each_fn fn)
{   return ls_ptrlist_foreach((void **)beg, (void **)end, fn);   }

/**
 * @ls_strlist_add
 * @brief Creates and adds an element to the end of a string list object.
 * @details If the string list object is at capacity, the storage is extended.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[in] pStr - A char \* used to create the ls_str_t element.
 * @param[in] len - The length of characters at \e pStr.
 * @return A pointer to the created ls_str_t element on success,
 *   else NULL on error.
 * @note ls_strlist_add and ls_strlist_remove should be used together.
 *
 * @see ls_strlist_remove
 */
const ls_str_t *ls_strlist_add(
    ls_strlist_t *pThis, const char *pStr, int len);

/**
 * @ls_strlist_remove
 * @brief Removes and deletes an element from a string list object.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[in] pStr - A char \* used to find the ls_str_t element.
 * @return Void.
 * @note ls_strlist_add and ls_strlist_remove should be used together.
 *
 * @see ls_strlist_add
 */
void ls_strlist_remove(ls_strlist_t *pThis, const char *pStr);

/**
 * @ls_strlist_clear
 * @brief Deletes all elements from a string list object, and empties the object.
 * @details It is identical to ls_strlist_releaseobjs.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @return Void.
 * @warning The elements of the string list object must have been allocated
 *   and added through previous successful calls to ls_strlist_add.
 *
 * @see ls_strlist_add, ls_strlist_remove, ls_strlist_releaseobjs
 */
void ls_strlist_clear(ls_strlist_t *pThis);

/**
 * @ls_strlist_sort
 * @brief Sorts the elements in a string list object.
 * @details The routine uses qsort(3) with strcmp(3) as the compare function.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @return Void.
 */
void ls_strlist_sort(ls_strlist_t *pThis);

/**
 * @ls_strlist_insert
 * @brief Adds an element to a string list object, then sorts the object.
 * @details If the string list object is at capacity, the storage is extended.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[in] pDir - The element to add.
 * @return Void.
 * @note Note that the \e pDir parameter to ls_strlist_insert
 *   must be a previously allocated ls_str_t element.
 *   In contrast, ls_strlist_add takes a char \*, and creates a new
 *   ls_str_t element to add.
 *
 * @see ls_strlist_sort, ls_strlist_add
 */
void ls_strlist_insert(ls_strlist_t *pThis, ls_str_t *pDir);

/**
 * @ls_strlist_find
 * @brief Finds an element in a string list object.
 * @details The routine uses a linear search algorithm and strcmp(3).
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[in] pStr - The key to match.
 * @return The element if found, else NULL if not found.
 *
 * @see ls_strlist_bfind
 * @note If the string list object is sorted,
 *   ls_strlist_bfind may be more efficient.
 */
const ls_str_t *ls_strlist_find(const ls_strlist_t *pThis,
                                const char *pStr);

/**
 * @ls_strlist_lowerbound
 * @brief Gets an element or the lower bound in a sorted string list object.
 * @details The string list object elements must be sorted,
 *   as the routine uses a binary search algorithm.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[in] pStr - The key to match.
 * @return The element if found, else the lower bound.
 *
 * @see ls_strlist_sort
 */
ls_const_strlist_iter ls_strlist_lowerbound(
    const ls_strlist_t *pThis, const char *pStr);

/**
 * @ls_strlist_bfind
 * @brief Finds an element in a sorted string list object.
 * @details The string list object elements must be sorted,
 *   as the routine uses a binary search algorithm.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[in] pStr - The key to match.
 * @return The element if found, else NULL if not found.
 *
 * @see ls_strlist_find, ls_strlist_sort
 * @note If the string list object is not sorted,
 *   ls_strlist_find may be used instead.
 */
ls_str_t *ls_strlist_bfind(const ls_strlist_t *pThis, const char *pStr);

/**
 * @ls_strlist_split
 * @brief Parses (splits) a buffer into tokens which are added to the specified
 *   string list object.
 *
 * @param[in] pThis - A pointer to an initialized string list object.
 * @param[in] pBegin - A pointer to the beginning of the string to parse.
 * @param[in] pEnd - A pointer to the end of the string.
 * @param[in] delim - The field delimiters (cannot be an empty string).
 * @return The new size of the string list object
 *   in terms of number of elements.
 */
int ls_strlist_split(
    ls_strlist_t *pThis, const char *pBegin, const char *pEnd,
    const char *delim);


#ifdef __cplusplus
}
#endif

#endif  /* LS_STRLIST_H */
