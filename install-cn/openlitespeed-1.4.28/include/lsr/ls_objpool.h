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
#ifndef LS_OBJPOOL_H
#define LS_OBJPOOL_H

#include <lsr/ls_ptrlist.h>
#include <lsr/ls_types.h>

/**
 * @file
 */

#ifdef __cplusplus
extern "C" {
#endif

typedef struct ls_objpool_s ls_objpool_t;
/**
 * @typedef ls_objpool_objfn
 * @brief A function that the user wants to apply to every pointer in the object pool.
 * Also allows a user provided data for the function.
 *
 * @param[in] pObj - A pointer to the object to work on.
 * @param[in] param - A pointer to the user data passed into the function.
 * @return Should return 0 on success, not 0 on failure.
 */
typedef int (*ls_objpool_objfn)(void *pObj, void *param);

/**
 * @typedef ls_objpool_getnewfn
 * @brief \b USER \b IMPLEMENTED!
 * @details The user must implement a new object function for the object pool
 * to create pointers.
 *
 * @return A pointer to the new object.
 */
typedef void *(*ls_objpool_getnewfn)();

/**
 * @typedef ls_objpool_releaseobjfn
 * @brief \b USER \b IMPLEMENTED!
 * @details The user must implement a release object function for the object pool
 * to release objects.
 *
 * @param[in] pObj - A pointer to release.
 * @return Void.
 */
typedef void (*ls_objpool_releaseobjfn)(void *pObj);



/**
 * @typedef ls_objpool_t
 * @brief An object pool object.
 */
struct ls_objpool_s
{
    int                     chunksize;
    int                     poolsize;
    ls_ptrlist_t            freelist;
    ls_objpool_getnewfn     getnew_fn;
    ls_objpool_releaseobjfn releaseobj_fn;
};

/** @ls_objpool
 * @brief Initializes an object pool object.
 * @details Chunk size determines how many pointers should be allocated
 * each time an allocation is needed.  If chunkSize is 0, default is set
 * to 10.
 *
 * @param[in] pThis - A pointer to an allocated object pool object.
 * @param[in] chunkSize - The number of pointers to allocate.
 * @param[in] getNewFn - A user implemented get new function.
 * @param[in] releaseFn - A user implemented release object function.
 * @return Void.
 *
 * @see ls_objpool_d
 */
void ls_objpool(ls_objpool_t *pThis, int chunkSize,
                ls_objpool_getnewfn getNewFn, ls_objpool_releaseobjfn releaseFn);

/** @ls_objpool
 * @brief Destroys the contents of an initialized object pool object.
 *
 * @param[in] pThis - A pointer to an initialized object pool object.
 * @return Void.
 *
 * @see ls_objpool
 */
void ls_objpool_d(ls_objpool_t *pThis);

/** @ls_objpool_get
 * @brief Gets a pointer from the object pool.
 * @details Will allocate more if there are none left.
 *
 * @param[in] pThis - A pointer to an initialized object pool object.
 * @return The requested pointer if successful, NULL if not.
 */
void *ls_objpool_get(ls_objpool_t *pThis);

/** @ls_objpool_getmulti
 * @brief Gets an array of pointers from the object pool and stores
 * them in the provided structure.
 *
 * @param[in] pThis - A pointer to an initialized object pool object.
 * @param[out] pObj - The output array.
 * @param[in] n - The number of pointers to get.
 * @return The number of pointers gotten if successful, 0 if not.
 *
 */
int ls_objpool_getmulti(ls_objpool_t *pThis, void **pObj, int n);

/** @ls_objpool_recycle
 * @brief Returns the pointer to the pool.
 *
 * @param[in] pThis - A pointer to an initialized object pool object.
 * @param[in] pObj - A pointer to the pointer to recycle.
 * @return Void.
 */
ls_inline void ls_objpool_recycle(ls_objpool_t *pThis, void *pObj)
{
    if (pObj)
        ls_ptrlist_unsafepushback(&pThis->freelist, pObj);
}

/** @ls_objpool_recyclemulti
 * @brief Recycles an array of pointers to the object pool from the
 * provided pointer.
 *
 * @param[in] pThis - A pointer to an initialized object pool object.
 * @param[in] pObj - An array of pointers to return.
 * @param[in] n - The number of pointers to return.
 * @return Void.
 */
ls_inline void ls_objpool_recyclemulti(ls_objpool_t *pThis, void **pObj,
                                       int n)
{
    if (pObj)
        ls_ptrlist_unsafepushbackn(&pThis->freelist, pObj, n);
}

/** @ls_objpool_size
 * @brief Gets the current number of pointers \e available in the object pool.
 *
 * @param[in] pThis - A pointer to an initialized object pool object.
 * @return The size available.
 */
ls_inline int ls_objpool_size(const ls_objpool_t *pThis)
{   return ls_ptrlist_size(&pThis->freelist);  }

/** @ls_objpool_shrinkto
 * @brief Shrinks the pool to contain sz pointers.
 * @details If the current \link #ls_objpool_size size\endlink
 * is less than the size given, this function will do nothing.
 *
 * @param[in] pThis - A pointer to an initialized object pool object.
 * @param[in] sz - The size to shrink the pool to.
 * @return Void.
 */
ls_inline void ls_objpool_shrinkto(ls_objpool_t *pThis, int sz)
{
    int curSize = ls_ptrlist_size(&pThis->freelist);
    int i;
    for (i = 0; i < curSize - sz; ++i)
    {
        void *pObj = ls_ptrlist_popback(&pThis->freelist);
        pThis->releaseobj_fn(pObj);
        --pThis->poolsize;
    }
}

/** @ls_objpool_begin
 * @brief Gets the iterator beginning of a object pool object.
 *
 * @param[in] pThis - A pointer to an initialized object pool object.
 * @return The iterator beginning of a object pool object.
 */
ls_inline ls_ptrlist_iter ls_objpool_begin(ls_objpool_t *pThis)
{   return ls_ptrlist_begin(&pThis->freelist); }

/** @ls_objpool_end
 * @brief Gets the iterator end of a object pool object.
 *
 * @param[in] pThis - A pointer to an initialized object pool object.
 * @return The iterator end of a object pool object.
 */
ls_inline ls_ptrlist_iter ls_objpool_end(ls_objpool_t *pThis)
{   return ls_ptrlist_end(&pThis->freelist); }

/** @ls_objpool_applyall
 * @brief Applies fn to all the pointers in the object pool object.
 * @details Param may be used as a user data to give to the function if needed.
 *
 * @param[in] pThis - A pointer to an initialized object pool object.
 * @param[in] fn - A pointer to the \link ls_objpool_objfn function\endlink
 * to apply to the pointers.
 * @param[in] param - A pointer to the user data to pass into the function.
 * @return Void.
 *
 */
ls_inline void ls_objpool_applyall(ls_objpool_t *pThis,
                                   ls_objpool_objfn fn, void *param)
{
    ls_ptrlist_iter iter;
    for (iter = ls_objpool_begin(pThis); iter != ls_objpool_end(pThis); ++iter)
        (*fn)(*iter, param);
}

/** @ls_objpool_poolsize
 * @brief Gets the \e total number of pointers created by the object pool object.
 * @details This includes all pointers that the user may have gotten.
 *
 * @param[in] pThis - A pointer to an initialized object pool object.
 * @return The total number of pointers created.
 */
ls_inline int ls_objpool_poolsize(const ls_objpool_t *pThis)
{   return pThis->poolsize;   }

/** @ls_objpool_capacity
 * @brief Gets the storage capacity of an object pool object;
 *   \e i.e., how many pointers it may hold.
 *
 * @param[in] pThis - A pointer to an initialized object pool object.
 * @return The capacity in terms of number of pointers.
 */
ls_inline int ls_objpool_capacity(const ls_objpool_t *pThis)
{   return ls_ptrlist_capacity(&pThis->freelist);  }

#ifdef __cplusplus
}
#endif

#endif
