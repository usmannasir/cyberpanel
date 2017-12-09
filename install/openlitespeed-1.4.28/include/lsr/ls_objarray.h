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
#ifndef LS_OBJARRAY_H
#define LS_OBJARRAY_H

#include <lsr/ls_types.h>

#include <string.h>

/**
 * @file
 * This structure can be used for a more efficient object allocation.
 *
 * Essentially, a block of objects is allocated at once, so when the user
 * anticipates needing to allocate something in a loop, it will be faster
 * to do fewer large allocations rather than many small allocations.
 *
 * @warning To avoid any issues, be consistent with the usage of the session pool.
 * If one call uses the pool, any and all other calls with a pool parameter must
 * have the same pool.
 * @see ls_objarray_setcapacity, ls_objarray_guarantee
 */

#ifdef __cplusplus
extern "C" {
#endif

typedef struct ls_objarray_s ls_objarray_t;

/**
 * @typedef ls_objarray_t
 * @brief An array of objects.
 */
struct ls_objarray_s
{
    int     sizemax;
    int     sizenow;
    int     objsize;
    void   *parray;
};

/** @ls_objarray_init
 * @brief Initializes the given array.  User must give the object size.
 * @details This function does not allocate for the array.  To begin allocation,
 * user should call \link #ls_objarray_setcapacity setcapacity \endlink
 * or \link #ls_objarray_guarantee guarantee. \endlink
 *
 * @param[in] pThis - A pointer to an allocated objarray object.
 * @param[in] objSize - The size of the object the user intends to allocate.
 * @return Void.
 *
 * @see ls_objarray_setcapacity, ls_objarray_guarantee
 */
ls_inline void ls_objarray_init(ls_objarray_t *pThis, int objSize)
{
    pThis->sizemax = pThis->sizenow = 0;
    pThis->objsize = objSize;
    pThis->parray = NULL;
}

/** @ls_objarray_release
 * @brief Releases the internals of the array.
 * DOES NOT RELEASE THE OBJARRAY STRUCTURE ITSELF.
 *
 * @param[in] pThis - A pointer to an initalized objarray object.
 * @param[in] pool - If the array was allocated from the session pool in
 * setcapacity or guarantee, the user must pass in the pointer of that pool.
 * Otherwise, this should be NULL.
 * @return Void.
 *
 * @see ls_objarray_setcapacity, ls_objarray_guarantee
 */
void ls_objarray_release(ls_objarray_t *pThis, ls_xpool_t *pool);

/** @ls_objarray_clear
 * @brief Resets the objarray to size 0, but DOES NOT DEALLOCATE THE ARRAY.
 * @details This could be useful if the user needs to reset the array, but plans on
 * reusing it.  The user should take care when using the session pool and making
 * sure that the array will only be used within a session.
 *
 * @param[in] pThis - A pointer to an initalized objarray object.
 * @return Void.
 */
ls_inline void ls_objarray_clear(ls_objarray_t *pThis)
{   pThis->sizenow = 0;  }

/** @ls_objarray_getcapacity
 * @brief Gets the capacity of the objarray.
 *
 * @param[in] pThis - A pointer to an initalized objarray object.
 * @return The capacity of the objarray in terms of number of objects.
 */
ls_inline int ls_objarray_getcapacity(const ls_objarray_t *pThis)
{   return pThis->sizemax;   }

/** @ls_objarray_getsize
 * @brief Gets the size of the objarray.
 *
 * @param[in] pThis - A pointer to an initalized objarray object.
 * @return The size of the objarray in terms of number of objects.
 */
ls_inline int ls_objarray_getsize(const ls_objarray_t *pThis)
{   return pThis->sizenow;   }

/** @ls_objarray_getobjsize
 * @brief Gets the object size of the objarray.
 *
 * @param[in] pThis - A pointer to an initalized objarray object.
 * @return The object size of the objarray.
 */
ls_inline int ls_objarray_getobjsize(const ls_objarray_t *pThis)
{   return pThis->objsize;   }

/** @ls_objarray_getarray
 * @brief Gets the array pointer from the objarray.
 *
 * @param[in] pThis - A pointer to an initalized objarray object.
 * @return The array of the objarray.
 */
ls_inline void *ls_objarray_getarray(ls_objarray_t *pThis)
{   return pThis->parray;   }

/** @ls_objarray_setsize
 * @brief Sets the size of the objarray.  Must be less than the capacity.
 *
 * @param[in] pThis - A pointer to an initalized objarray object.
 * @param[in] size - The number of objects to update to.
 * @return Void.
 */
ls_inline void ls_objarray_setsize(ls_objarray_t *pThis, int size)
{   pThis->sizenow = (size > pThis->sizemax ? pThis->sizemax : size);   }

/** @ls_objarray_setcapacity
 * @brief Sets the capacity of the object array to the given number of objects.
 * @details If the user wishes to use a session pool and can guarantee that the
 * objects will only be used within a session, a session pool pointer may
 * be specified; otherwise, it should be NULL.
 *
 * @param[in] pThis - A pointer to an initalized objarray object.
 * @param[in] pool - A pointer to the session pool if the user wishes to use one.  NULL if not.
 * @param[in] numObj - The number of objects to set the capacity to.
 * @return Void.
 */
void ls_objarray_setcapacity(ls_objarray_t *pThis, ls_xpool_t *pool,
                             int numObj);

/** @ls_objarray_guarantee
 * @brief Guarantees the capacity of the object array to be the given number of objects.
 * @details If the user wishes to use a session pool and can guarantee that the
 * objects will only be used within a session, a session pool pointer may
 * be specified; otherwise, it should be NULL.
 *
 * @param[in] pThis - A pointer to an initalized objarray object.
 * @param[in] pool - A pointer to the session pool if the user wishes to use one.  NULL if not.
 * @param[in] numObj - The number of objects to guarantee.
 * @return Void.
 */
ls_inline void ls_objarray_guarantee(ls_objarray_t *pThis,
                                     ls_xpool_t *pool, int numObj)
{   ls_objarray_setcapacity(pThis, pool, numObj /*+ pThis->sizenow*/);    }

/** @ls_objarray_getobj
 * @brief Gets the object at a given index in the array.  The index must be
 * less than the size of the array.
 *
 * @param[in] pThis - A pointer to an initialized object array.
 * @param[in] index - The index of the object.
 * @return A pointer to the requested object.
 */
ls_inline void *ls_objarray_getobj(const ls_objarray_t *pThis, int index)
{
    if (index < 0 || index >= pThis->sizenow)
        return NULL;
    char *ptr = (char *)pThis->parray;
    return (void *)(ptr + (index * pThis->objsize));
}

/** @ls_objarray_getnew
 * @brief Gets a new object pointer from the array.  If there is no
 * more space, this will return NULL.
 * @details To avoid any issues, the user should check to make sure
 * that the array has enough space before calling this function.
 *
 * @param[in] pThis - A pointer to an initialized object array to get the object from.
 * @return A pointer to the new object, or NULL if there
 * was not enough space.
 *
 * @see ls_objarray_setcapacity, ls_objarray_guarantee
 */
ls_inline void *ls_objarray_getnew(ls_objarray_t *pThis)
{
    if (pThis->sizenow >= pThis->sizemax)
        return NULL;
    char *ptr = (char *)pThis->parray;
    return (void *)(ptr + (pThis->sizenow++ * pThis->objsize));
}






#ifdef __cplusplus
}
#endif

#endif //LS_OBJARRAY_H

