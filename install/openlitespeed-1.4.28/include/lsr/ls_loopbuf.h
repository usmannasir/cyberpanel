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
#ifndef LS_LOOPBUF_H
#define LS_LOOPBUF_H

#include <lsr/ls_types.h>

#include <assert.h>
#include <stdlib.h>
#include <sys/uio.h>

/**
 * @file
 * @note
 * Loopbuf - A loopbuf is a mechanism which manages buffer allocation as long as
 *      the user ensures there is enough space (reserve, guarantee, append).\n
 *      It also loops around to the beginning of the allocation if there is space available
 *      in the front (pop front, pop front to).\n\n
 * The remainder of this document refers to the lsr implementation of loopbuf.\n\n
 * ls_loopbuf_t defines a loopbuf object.\n
 *      Functions prefixed with ls_loopbuf_* use a ls_loopbuf_t \* parameter.\n\n
 * ls_xloopbuf_t is a wrapper around ls_loopbuf_t, adding a pointer to the session pool (xpool).\n
 *      Functions prefixed with ls_xloopbuf_* use a ls_xloopbuf_t \* parameter.\n\n
 * If a user wants to use the session pool with loopbuf, there are two options:
 *      @li Use ls_loopbuf_x* functions with ls_loopbuf_t.
 *      This option should be used if the user can pass the xpool pointer every time a
 *      growing/shrinking function is called.
 *
 *      @li Use ls_xloopbuf_* functions with ls_xloopbuf_t.
 *      This structure takes in the session pool as a parameter during initialization and
 *      stores the pointer.  This should be used if the user cannot guarantee
 *      having the xpool pointer every time a function needs it.
 */

#define LSR_LOOPBUFUNIT 64

#ifdef __cplusplus
extern "C" {
#endif

typedef struct ls_loopbuf_s ls_loopbuf_t;
typedef struct ls_xloopbuf_s ls_xloopbuf_t;

/**
 * @typedef ls_loopbuf_t
 * @brief An auto allocation buffer that allows looping if the front is popped off.
 */
struct ls_loopbuf_s
{
    char           *pbuf;
    char           *pbufend;
    char           *phead;
    char           *pend;
    int             sizemax;
};

/**
 * @typedef ls_xloopbuf_t
 * @brief A struct that contains a session pool pointer as well as ls_loopbuf_t
 * @details This structure can be useful for when the user knows that the
 * structure will only last an HTTP Session and the user cannot guarantee that
 * he/she will have a pointer to the session pool every time it is needed.
 */
struct ls_xloopbuf_s
{
    ls_loopbuf_t   loopbuf;
    ls_xpool_t    *pool;
};

/** @ls_loopbuf_xnew
 * @brief Create a new loopbuf structure with an initial capacity from
 * a session pool.
 *
 * @param[in] size - The initial capacity for the loopbuf (bytes).
 * @param[in] pool - A pointer to the session pool to allocate from.
 * @return A loopbuf structure if successful, NULL if not.
 *
 * @see ls_loopbuf_xdelete
 */
ls_loopbuf_t *ls_loopbuf_xnew(int size, ls_xpool_t *pool);

/** @ls_loopbuf_x
 * @brief Initializes a given loopbuf to an initial capacity from
 * a session pool.
 *
 * @param[in] pThis - A pointer to an allocated loopbuf object.
 * @param[in] size - The initial capacity for the loopbuf (bytes).
 * @param[in] pool - A pointer to the session pool to allocate from.
 * @return The loopbuf structure if successful, NULL if not.
 *
 * @see ls_loopbuf_xd
 */
ls_loopbuf_t *ls_loopbuf_x(ls_loopbuf_t *pThis, int size,
                           ls_xpool_t *pool);

/** @ls_loopbuf_xd
 * @brief Destroys the loopbuf.  DOES NOT FREE pThis!
 * @details Use with ls_loopbuf_x.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] pool - A pointer to the session pool.
 * @return Void.
 *
 * @see ls_loopbuf_x
 */
void ls_loopbuf_xd(ls_loopbuf_t *pThis, ls_xpool_t *pool);

/** @ls_loopbuf_xdelete
 * @brief Deletes the loopbuf, opposite of \link #ls_loopbuf_xnew loopbuf xnew \endlink
 * @details If a loopbuf was created with \link #ls_loopbuf_xnew loopbuf xnew, \endlink
 * it must be deleted with \link #ls_loopbuf_xdelete loopbuf xdelete. \endlink
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] pool - A pointer to the session pool to delete from.
 * @return Void.
 *
 * @see ls_loopbuf_xnew
 */
void ls_loopbuf_xdelete(ls_loopbuf_t *pThis, ls_xpool_t *pool);

/** @ls_loopbuf_new
 * @brief Create a new loopbuf structure with an initial capacity.
 *
 * @param[in] size - The initial capacity for the loopbuf (bytes).
 * @return A loopbuf structure if successful, NULL if not.
 *
 * @see ls_loopbuf_delete
 */
ls_loopbuf_t *ls_loopbuf_new(int size);

/** @ls_loopbuf
 * @brief Initializes a given loopbuf to an initial capacity.
 *
 * @param[in] pThis - A pointer to an allocated loopbuf object.
 * @param[in] size - The initial capacity for the loopbuf (bytes).
 * @return The loopbuf object if successful, NULL if not.
 *
 * @see ls_loopbuf_d
 */
ls_loopbuf_t *ls_loopbuf(ls_loopbuf_t *pThis, int size);

/** @ls_loopbuf_d
 * @brief Destroys the loopbuf.  DOES NOT FREE pThis!
 * @details Use with ls_loopbuf.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @return Void.
 *
 * @see ls_loopbuf
 */
ls_inline void ls_loopbuf_d(ls_loopbuf_t *pThis)
{   ls_loopbuf_xd(pThis, NULL);  }

/** @ls_loopbuf_delete
 * @brief Deletes the loopbuf, opposite of \link #ls_loopbuf_new loopbuf new \endlink
 * @details If a loopbuf was created with \link #ls_loopbuf_new loopbuf new. \endlink
 * it must be deleted with \link #ls_loopbuf_delete loopbuf delete; \endlink
 * otherwise, there will be a memory leak.  This function does garbage collection
 * for the internal constructs and will free pThis.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @return Void.
 *
 * @see ls_loopbuf_new
 */
void ls_loopbuf_delete(ls_loopbuf_t *pThis);

/** @ls_loopbuf_xreserve
 * @brief Reserves size total bytes for the loopbuf from the session pool.
 * If size is lower than the current size, it will not shrink.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] size - The total number of bytes to reserve.
 * @param[in] pool - A pointer to the session pool to allocate from.
 * @return 0 on success, -1 on failure.
 */
int ls_loopbuf_xreserve(ls_loopbuf_t *pThis, int size, ls_xpool_t *pool);

/** @ls_loopbuf_xappend
 * @brief Appends the loopbuf with the specified buffer.
 * @details This function appends the loopbuf with the specified buffer.  It will check
 * if there is enough space in the loopbuf and will grow the loopbuf from the
 * session pool if there is not enough space.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] pBuf - A pointer to the buffer to append.
 * @param[in] size - The size of pBuf.
 * @param[in] pool - A pointer to the session pool to allocate from.
 * @return The size appended or -1 if it failed.
 */
int ls_loopbuf_xappend(
    ls_loopbuf_t *pThis, const char *pBuf, int size, ls_xpool_t *pool);

/** @ls_loopbuf_xguarantee
 * @brief Guarantees size more bytes for the loopbuf.  If size is lower than the
 * available amount, it will not allocate any more.  Allocates from the given session pool.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] size - The number of bytes to guarantee.
 * @param[in] pool - A pointer to the session pool to allocate from.
 * @return 0 on success, -1 on failure.
 */
int ls_loopbuf_xguarantee(ls_loopbuf_t *pThis, int size, ls_xpool_t *pool);

/** @ls_loopbuf_xstraight
 * @brief Straighten the loopbuf.
 * @details If the loopbuf is split in two parts due to looping, this function
 * makes it one whole again.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] pool - A pointer to the pool to allocate from.
 * @return Void.
 */
void ls_loopbuf_xstraight(ls_loopbuf_t *pThis, ls_xpool_t *pool);

/** @ls_loopbuf_available
 * @brief Gets the number of bytes left in the loopbuf.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @return The number of bytes left.
 */
int ls_loopbuf_available(const ls_loopbuf_t *pThis);

/** @ls_loopbuf_contiguous
 * @brief Gets the number of contiguous bytes left in the loopbuf.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @return The number of contiguous bytes left.
 */
int ls_loopbuf_contiguous(const ls_loopbuf_t *pThis);

/** @ls_loopbuf_used
 * @brief Tells the loopbuf that the user used size more bytes from
 * the end of the loopbuf.
 * @details Do not call this after the calls
 * \link #ls_loopbuf_append loopbuf append,\endlink
 * \link #ls_loopbuf_xappend loopbuf xappend.\endlink
 * It will be updated within those functions.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] size - The size to add.
 * @return Void.
 */
void ls_loopbuf_used(ls_loopbuf_t *pThis, int size);

/** @ls_loopbuf_reserve
 * @brief Reserves size total bytes for the loopbuf.  If size is lower than the current
 * size, it will not shrink.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] size - The total number of bytes to reserve.
 * @return 0 on success, -1 on failure.
 */
ls_inline int ls_loopbuf_reserve(ls_loopbuf_t *pThis, int size)
{   return ls_loopbuf_xreserve(pThis, size, NULL);   }

/** @ls_loopbuf_append
 * @brief Appends the loopbuf with the specified buffer.
 * @details This function appends the loopbuf with the specified buffer.  It will check
 * if there is enough space in the loopbuf and will grow the loopbuf if there
 * is not enough space.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] pBuf - A pointer to the given buffer to append.
 * @param[in] size - The size of pBuf.
 * @return The size appended or -1 if it failed.
 */
ls_inline int ls_loopbuf_append(ls_loopbuf_t *pThis, const char *pBuf,
                                int size)
{   return ls_loopbuf_xappend(pThis, pBuf, size, NULL);  }

/** @ls_loopbuf_guarantee
 * @brief Guarantees size more bytes for the loopbuf.  If size is lower than the
 * available amount, it will not allocate any more.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] size - The number of bytes to guarantee.
 * @return 0 on success, -1 on failure.
 */
ls_inline int ls_loopbuf_guarantee(ls_loopbuf_t *pThis, int size)
{   return ls_loopbuf_xguarantee(pThis, size, NULL); }

/** @ls_loopbuf_straight
 * @brief Straighten the loopbuf.
 * @details If the loopbuf is split in two parts due to looping, this function
 * makes it one whole again.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @return Void.
 */
ls_inline void ls_loopbuf_straight(ls_loopbuf_t *pThis)
{   return ls_loopbuf_xstraight(pThis, NULL);    }

/** @ls_loopbuf_moveto
 * @brief Moves the front size bytes from pThis to pBuf.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[out] pBuf - A pointer to the allocated buffer to copy to.
 * @param[in] size - The number of bytes to attempt to copy.
 * @return The number of bytes copied.
 */
int ls_loopbuf_moveto(ls_loopbuf_t *pThis, char *pBuf, int size);

/** @ls_loopbuf_popfront
 * @brief Pops the front size bytes from pThis.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] size - The number of bytes to pop.
 * @return The number of bytes popped.
 */
int ls_loopbuf_popfront(ls_loopbuf_t *pThis, int size);

/** @ls_loopbuf_popback
 * @brief Pops the ending size bytes from pThis.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] size - The number of bytes to pop.
 * @return The number of bytes popped.
 */
int ls_loopbuf_popback(ls_loopbuf_t *pThis, int size);

/** @ls_loopbuf_swap
 * @brief Swaps the contents of the two loopbufs.
 * @param[in,out] lhs - A pointer to an initialized loopbuf object.
 * @param[in,out] rhs - A pointer to another initialized loopbuf object.
 * @return Void.
 */
void ls_loopbuf_swap(ls_loopbuf_t *lhs, ls_loopbuf_t *rhs);

/** @ls_loopbuf_update
 * @brief Update the loopbuf at the offset to the contents of pBuf.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] offset - The starting offset to update in the loopbuf.
 * @param[in] pBuf - A pointer to the buffer.
 * @param[in] size - The amount of bytes to copy.
 * @return Void.
 */
void ls_loopbuf_update(
    ls_loopbuf_t *pThis, int offset, const char *pBuf, int size);

/** @ls_loopbuf_search
 * @brief Searches the loopbuf starting at the offset for the pattern.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] offset - The offset to start the search at.
 * @param[in] accept - A pointer to the pattern to match.
 * @param[in] acceptLen - The length of the pattern to match.
 * @return The pointer to the pattern in the loopbuf if found, NULL if not.
 */
char *ls_loopbuf_search(
    ls_loopbuf_t *pThis, int offset, const char *accept, int acceptLen);

/** @ls_loopbuf_blksize
 * @brief Gets the front block size.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @return The front block size.
 */
ls_inline int ls_loopbuf_blksize(const ls_loopbuf_t *pThis)
{
    if (pThis->phead > pThis->pend)
        return pThis->pbufend - pThis->phead;
    return pThis->pend - pThis->phead;
}

/** @ls_loopbuf_size
 * @brief Gets the size used in the loopbuf so far.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @return The size used.
 */
ls_inline int ls_loopbuf_size(const ls_loopbuf_t *pThis)
{
    int ret = pThis->pend - pThis->phead;
    if (ret >= 0)
        return ret;
    return ret + pThis->sizemax;
}

/** @ls_loopbuf_capacity
 * @brief Gets the total capacity of the loopbuf.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @return The total capacity in terms of bytes.
 */
ls_inline int ls_loopbuf_capacity(const ls_loopbuf_t *pThis)
{   return pThis->sizemax;  }

/** @ls_loopbuf_empty
 * @brief Specifies whether or not the loopbuf is empty.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @return Non-zero if empty, 0 if not.
 */
ls_inline int ls_loopbuf_empty(const ls_loopbuf_t *pThis)
{   return (pThis->phead == pThis->pend);  }

/** @ls_loopbuf_full
 * @brief Specifies whether or not the loopbuf is full.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @return Non-zero if full, 0 if not.
 */
ls_inline int ls_loopbuf_full(const ls_loopbuf_t *pThis)
{   return  ls_loopbuf_size(pThis) == pThis->sizemax - 1; }

/** @ls_loopbuf_begin
 * @brief Gets a pointer to the beginning of the used data.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @return A pointer to the beginning.
 */
ls_inline char *ls_loopbuf_begin(const ls_loopbuf_t *pThis)
{   return pThis->phead;  }

/** @ls_loopbuf_end
 * @brief Gets a pointer to the end of the used data.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @return A pointer to the end.
 */
ls_inline char *ls_loopbuf_end(const ls_loopbuf_t *pThis)
{   return pThis->pend;  }

/** @ls_loopbuf_getptr
 * @brief Gets a pointer of a given offset from the loopbuf.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] offset - The offset from the beginning of the used data.
 * @return The pointer associated with the offset.
 */
ls_inline char *ls_loopbuf_getptr(const ls_loopbuf_t *pThis, int offset)
{
    return pThis->pbuf
           + (pThis->phead - pThis->pbuf + offset)
           % pThis->sizemax;
}

/** @ls_loopbuf_getoffset
 * @brief Given a pointer, calculates the offset relative to the start of
 * the used data.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] p - The pointer to compare.
 * @return The offset.
 */
ls_inline int ls_loopbuf_getoffset(const ls_loopbuf_t *pThis,
                                   const char *p)
{
    if (p < pThis->pbuf || p >= pThis->pbufend)
        return -1;
    return (p - pThis->phead + pThis->sizemax) % pThis->sizemax;
}

/** @ls_loopbuf_clear
 * @brief Clears the loopbuf to 0 bytes used.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @return Void.
 */
ls_inline void ls_loopbuf_clear(ls_loopbuf_t *pThis)
{   pThis->phead = pThis->pend = pThis->pbuf;    }

/** @ls_loopbuf_unsafeapp
 * @brief Appends the loopbuf with a character.
 * @details This function is unsafe in that it will not check if there is enough space
 * allocated.  This function exists to speed up the append process if the user can
 * guarantee that the loopbuf is large enough.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] ch - The character to append to the loopbuf.
 * @return Void.
 */
ls_inline void ls_loopbuf_unsafeapp(ls_loopbuf_t *pThis, char ch)
{
    *((pThis->pend)++) = ch;
    if (pThis->pend == pThis->pbufend)
        pThis->pend = pThis->pbuf;
}

/** @ls_loopbuf_inc
 * @brief Increments the pointer.  If it is currently pointing to the end of the loopbuf,
 * then the increment will point to the beginning of the loopbuf.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in,out] pPos - A pointer to the pointer to increment.
 * @return The incremented pointer.
 */
ls_inline char *ls_loopbuf_inc(ls_loopbuf_t *pThis, char **pPos)
{
    assert(pPos);
    if (++*pPos == pThis->pbufend)
        *pPos = pThis->pbuf ;
    return *pPos ;
}

//NOTICE: The number of segments must match the count of iovec structs in order to use iov_insert.
/** @ls_loopbuf_getnumseg
 * @brief Gets the number of segments the data is stored as.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @return The number of segments the data is stored as.
 */
ls_inline int ls_loopbuf_getnumseg(ls_loopbuf_t *pThis)
{   return pThis->pend > pThis->phead ? 1 : 2;  }

/** @ls_loopbuf_insiov
 * @brief Inserts the contents of the loopbuf into the vector.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @param[in] vect - The vector to copy the content pointer to.
 * @param[in] count - The number of segments the data is stored as.
 * @return 0 on success, -1 on failure.
 */
int ls_loopbuf_insiov(ls_loopbuf_t *pThis, struct iovec *vect, int count);





/** @ls_xloopbuf_new
 * @brief Create a new xloopbuf structure with an initial capacity from
 * a session pool.
 *
 * @param[in] size - The initial capacity for the xloopbuf (bytes).
 * @param[in] pool - A pointer to the session pool to allocate from.
 * @return An xloopbuf structure if successful, NULL if not.
 *
 * @see ls_xloopbuf_delete
 */
ls_xloopbuf_t *ls_xloopbuf_new(int size, ls_xpool_t *pool);

/** @ls_xloopbuf
 * @brief Initializes a given xloopbuf to an initial capacity from
 * a session pool.
 *
 * @param[in] pThis - A pointer to an allocated xloopbuf object.
 * @param[in] size - The initial capacity for the xloopbuf (bytes).
 * @param[in] pool - A pointer to the session pool to allocate from.
 * @return The xloopbuf structure if successful, NULL if not.
 *
 * @see ls_xloopbuf_d
 */
ls_xloopbuf_t *ls_xloopbuf(ls_xloopbuf_t *pThis, int size,
                           ls_xpool_t *pool);

/** @ls_xloopbuf_d
 * @brief Destroys the xloopbuf.  DOES NOT FREE pThis!
 * @details Use with ls_xloopbuf.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @return Void.
 *
 * @see ls_xloopbuf
 */
void ls_xloopbuf_d(ls_xloopbuf_t *pThis);

/** @ls_xloopbuf_delete
 * @brief Deletes the xloopbuf, opposite of \link #ls_xloopbuf_new xloopbuf new \endlink
 * @details If a xloopbuf was created with \link #ls_xloopbuf_new xloopbuf new, \endlink
 * it must be deleted with \link #ls_xloopbuf_delete xloopbuf delete. \endlink
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @return Void.
 *
 * @see ls_xloopbuf_new
 */
void ls_xloopbuf_delete(ls_xloopbuf_t *pThis);

/** @ls_xloopbuf_reserve
 * @brief Reserves size total bytes for the xloopbuf.  If size is lower than the current
 * size, it will not shrink.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @param[in] size - The total number of bytes to reserve.
 * @return 0 on success, -1 on failure.
 */
ls_inline int ls_xloopbuf_reserve(ls_xloopbuf_t *pThis, int size)
{   return ls_loopbuf_xreserve(&pThis->loopbuf, size, pThis->pool); }

/** @ls_xloopbuf_append
 * @brief Appends the xloopbuf with the specified buffer.
 * @details This function appends the xloopbuf with the specified buffer.  It will check
 * if there is enough space in the xloopbuf and will grow the xloopbuf if there
 * is not enough space.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @param[in] pBuf - A pointer to the given buffer to append.
 * @param[in] size - The size of pBuf.
 * @return The size appended or -1 if it failed.
 */
ls_inline int ls_xloopbuf_append(ls_xloopbuf_t *pThis, const char *pBuf,
                                 int size)
{   return ls_loopbuf_xappend(&pThis->loopbuf, pBuf, size, pThis->pool);    }

/** @ls_xloopbuf_guarantee
 * @brief Guarantees size more bytes for the xloopbuf.  If size is lower than the
 * available amount, it will not allocate any more.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @param[in] size - The number of bytes to guarantee.
 * @return 0 on success, -1 on failure.
 */
ls_inline int ls_xloopbuf_guarantee(ls_xloopbuf_t *pThis, int size)
{   return ls_loopbuf_xguarantee(&pThis->loopbuf, size, pThis->pool);   }

/** @ls_xloopbuf_swap
 * @brief Swaps the contents of the two xloopbufs.
 *
 * @param[in,out] lhs - A pointer to an initialized xloopbuf object.
 * @param[in,out] rhs - A pointer to another initialized xloopbuf object.
 * @return Void.
 */
void ls_xloopbuf_swap(ls_xloopbuf_t *lhs, ls_xloopbuf_t *rhs);

/** @ls_xloopbuf_straight
 * @brief Straighten the xloopbuf.
 * @details If the xloopbuf is split in two parts due to looping, this function
 * makes it one whole again.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @return Void.
 */
ls_inline void ls_xloopbuf_straight(ls_xloopbuf_t *pThis)
{   ls_loopbuf_xstraight(&pThis->loopbuf, pThis->pool); }

/** @ls_xloopbuf_available
 * @brief Gets the number of bytes left in the xloopbuf.
 *
 * @param[in] pThis - A pointer to an initialized loopbuf object.
 * @return The number of bytes left.
 */
ls_inline int ls_xloopbuf_available(const ls_xloopbuf_t *pThis)
{   return ls_loopbuf_available(&pThis->loopbuf);  }

/** @ls_xloopbuf_contiguous
 * @brief Gets the number of contiguous bytes left in the xloopbuf.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @return The number of contiguous bytes left.
 */
ls_inline int ls_xloopbuf_contiguous(const ls_xloopbuf_t *pThis)
{   return ls_loopbuf_contiguous(&pThis->loopbuf); }

/** @ls_xloopbuf_used
 * @brief Tells the xloopbuf that the user used size more bytes from
 * the end of the xloopbuf.
 * @details Do not call this after the call
 * \link #ls_xloopbuf_append xloopbuf append.\endlink
 * It will be updated within that function.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @param[in] size - The size to add.
 * @return Void.
 */
ls_inline void ls_xloopbuf_used(ls_xloopbuf_t *pThis, int size)
{   ls_loopbuf_used(&pThis->loopbuf, size);    }

/** @ls_xloopbuf_update
 * @brief Update the xloopbuf at the offset to the contents of pBuf.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @param[in] offset - The starting offset to update in the loopbuf.
 * @param[in] pBuf - A pointer to the buffer to copy.
 * @param[in] size - The amount of bytes to copy.
 * @return Void.
 */
ls_inline void ls_xloopbuf_update(
    ls_xloopbuf_t *pThis, int offset, const char *pBuf, int size)
{   ls_loopbuf_update(&pThis->loopbuf, offset, pBuf, size);    }

/** @ls_xloopbuf_search
 * @brief Searches the xloopbuf starting at the offset for the pattern.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @param[in] offset - The offset to start the search at.
 * @param[in] accept - A pointer to the pattern to match.
 * @param[in] acceptLen - The length of the pattern to match.
 * @return The pointer to the pattern in the xloopbuf if found, NULL if not.
 */
ls_inline char *ls_xloopbuf_search(
    ls_xloopbuf_t *pThis, int offset, const char *accept, int acceptLen)
{   return ls_loopbuf_search(&pThis->loopbuf, offset, accept, acceptLen);  }

/** @ls_xloopbuf_moveto
 * @brief Moves the front size bytes from pThis to pBuf.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @param[out] pBuf - A pointer to the allocated buffer to copy to.
 * @param[in] size - The number of bytes to attempt to copy.
 * @return The number of bytes copied.
 */
ls_inline int ls_xloopbuf_moveto(ls_xloopbuf_t *pThis, char *pBuf,
                                 int size)
{   return ls_loopbuf_moveto(&pThis->loopbuf, pBuf, size);    }

/** @ls_xloopbuf_popfront
 * @brief Pops the front size bytes from pThis.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @param[in] size - The number of bytes to pop.
 * @return The number of bytes popped.
 */
ls_inline int ls_xloopbuf_popfront(ls_xloopbuf_t *pThis, int size)
{   return ls_loopbuf_popfront(&pThis->loopbuf, size);    }

/** @ls_xloopbuf_popback
 * @brief Pops the ending size bytes from pThis.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @param[in] size - The number of bytes to pop.
 * @return The number of bytes popped.
 */
ls_inline int ls_xloopbuf_popback(ls_xloopbuf_t *pThis, int size)
{   return ls_loopbuf_popback(&pThis->loopbuf, size); }

/** @ls_xloopbuf_blksize
 * @brief Gets the front block size.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @return The front block size.
 */
ls_inline int ls_xloopbuf_blksize(const ls_xloopbuf_t *pThis)
{   return ls_loopbuf_blksize(&pThis->loopbuf); }

/** @ls_xloopbuf_size
 * @brief Gets the size used in the xloopbuf so far.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @return The size used.
 */
ls_inline int ls_xloopbuf_size(const ls_xloopbuf_t *pThis)
{   return ls_loopbuf_size(&pThis->loopbuf);   }

/** @ls_xloopbuf_capacity
 * @brief Gets the total capacity of the xloopbuf.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @return The total capacity in terms of bytes.
 */
ls_inline int ls_xloopbuf_capacity(const ls_xloopbuf_t *pThis)
{   return pThis->loopbuf.sizemax;    }

/** @ls_xloopbuf_empty
 * @brief Specifies whether or not the xloopbuf is empty.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @return 0 for false, true otherwise.
 */
ls_inline int ls_xloopbuf_empty(const ls_xloopbuf_t *pThis)
{   return (pThis->loopbuf.phead == pThis->loopbuf.pend); }

/** @ls_xloopbuf_full
 * @brief Specifies whether or not the xloopbuf is full.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @return 0 for false, true otherwise.
 */
ls_inline int ls_xloopbuf_full(const ls_xloopbuf_t *pThis)
{   return ls_xloopbuf_size(pThis) == pThis->loopbuf.sizemax - 1;  }

/** @ls_xloopbuf_begin
 * @brief Gets a pointer to the beginning of the used data.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @return A pointer to the beginning.
 */
ls_inline char *ls_xloopbuf_begin(const ls_xloopbuf_t *pThis)
{   return pThis->loopbuf.phead;    }

/** @ls_xloopbuf_end
 * @brief Gets a pointer to the end of the used data.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @return A pointer to the end.
 */
ls_inline char *ls_xloopbuf_end(const ls_xloopbuf_t *pThis)
{   return pThis->loopbuf.pend; }

/** @ls_xloopbuf_getptr
 * @brief Gets a pointer of a given offset from the xloopbuf.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @param[in] size - The offset from the beginning of the used data.
 * @return The pointer associated with the offset.
 */
ls_inline char *ls_xloopbuf_getptr(const ls_xloopbuf_t *pThis, int size)
{   return ls_loopbuf_getptr(&pThis->loopbuf, size);  }

/** @ls_xloopbuf_getoffset
 * @brief Given a pointer, calculates the offset relative to the start of
 * the used data.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @param[in] p - The pointer to compare.
 * @return The offset.
 */
ls_inline int ls_xloopbuf_getoffset(const ls_xloopbuf_t *pThis,
                                    const char *p)
{   return ls_loopbuf_getoffset(&pThis->loopbuf, p);  }

/** @ls_xloopbuf_clear
 * @brief Clears the xloopbuf to 0 bytes used.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @return Void.
 */
ls_inline void ls_xloopbuf_clear(ls_xloopbuf_t *pThis)
{   pThis->loopbuf.phead = pThis->loopbuf.pend = pThis->loopbuf.pbuf;    }

/** @ls_xloopbuf_unsafeapp
 * @brief Appends the xloopbuf with a character.
 * @details This function is unsafe in that it will not check if there is enough space
 * allocated.  This function exists to speed up the append process if the user can
 * guarantee that the xloopbuf is large enough.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @param[in] ch - The character to append to the xloopbuf.
 * @return Void.
 */
ls_inline void ls_xloopbuf_unsafeapp(ls_xloopbuf_t *pThis, char ch)
{   ls_loopbuf_unsafeapp(&pThis->loopbuf, ch); }

/** @ls_xloopbuf_inc
 * @brief Increments the pointer.  If it is currently pointing to the end of the xloopbuf,
 * then the increment will point to the beginning of the xloopbuf.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @param[in,out] pPos - A pointer to the pointer to increment.
 * @return The incremented pointer.
 */
ls_inline char *ls_xloopbuf_inc(ls_xloopbuf_t *pThis, char **pPos)
{   return ls_loopbuf_inc(&pThis->loopbuf, pPos);   }

//NOTICE: The number of segments must match the count of iovec structs in order to use iov_insert.
/** @ls_xloopbuf_getnumseg
 * @brief Gets the number of segments the data is stored as.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @return The number of segments the data is stored as.
 */
ls_inline int ls_xloopbuf_getnumseg(ls_xloopbuf_t *pThis)
{   return pThis->loopbuf.pend > pThis->loopbuf.phead ? 1 : 2;  }

/** @ls_xloopbuf_insiov
 * @brief Inserts the contents of the xloopbuf into the vector.
 *
 * @param[in] pThis - A pointer to an initialized xloopbuf object.
 * @param[in] vect - The vector to copy the content pointer to.
 * @param[in] count - The number of segments the data is stored as.
 * @return 0 on success, -1 on failure.
 */
ls_inline int ls_xloopbuf_insiov(
    ls_xloopbuf_t *pThis, struct iovec *vect, int count)
{   return ls_loopbuf_insiov(&pThis->loopbuf, vect, count);    }


#ifdef __cplusplus
}
#endif
#endif //LS_LOOPBUF_H
