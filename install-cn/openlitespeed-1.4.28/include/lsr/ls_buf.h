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
#ifndef LS_BUF_H
#define LS_BUF_H

#include <assert.h>
#include <string.h>
#include <lsr/ls_types.h>

/**
 * @file
 * @note
 *  Auto Buffer - An auto buffer is a mechanism which manages buffer allocation
 *  as long as the user ensures there is enough space
 *  (reserve, guarantee, grow, append).\n\n
 *  From hereafter, lsr buf refers to the lsr implementation of auto buffer.\n\n
 *  ls_buf_t defines an auto buffer object.\n
 *      Functions prefixed with ls_buf_* use a ls_buf_t \* parameter.\n\n
 *  ls_xbuf_t is a wrapper around ls_buf_t,
 *  adding a pointer to the session pool (xpool).\n
 *      Functions prefixed with ls_xbuf_* use a ls_xbuf_t \* parameter.\n\n
 *  If a user wants to use the session pool with lsr buf, there are two options:
 *      @li Use ls_buf_x* functions with ls_buf_t.
 *      This option should be used if the user can pass the xpool pointer
 *      every time a growing/shrinking function is called.
 *
 *      @li Use ls_xbuf_x* functions with ls_xbuf_t.
 *      This structure takes in the session pool as a parameter
 *      during initialization and stores the pointer.
 *      This should be used if the user cannot guarantee
 *      having the xpool pointer every time a function needs it.
 */


#ifdef __cplusplus
extern "C" {
#endif

/**
 * @typedef ls_buf_t
 * @brief A buffer that will grow as needed.
 */
typedef struct ls_buf_s
{
    char   *pbuf;
    char   *pend;
    char   *pbufend;
} ls_buf_t;

/**
 * @typedef ls_xbuf_t
 * @brief A struct that contains a session pool pointer as well as ls_buf_t
 * @details This structure can be useful for when the user knows that the
 *  structure will only last an HTTP Session and the user cannot guarantee that
 *  he/she will have a pointer to the session pool every time it is needed.
 */
typedef struct ls_xbuf_s
{
    ls_buf_t       buf;
    ls_xpool_t    *pool;
} ls_xbuf_t;

/** @ls_buf_xnew
 * @brief Creates and initializes a new buffer from the session pool.
 *
 * @param[in] size - The initial size to set the buffer to.
 * @param[in] pool - A pointer to the session pool to allocate from.
 * @return A pointer to the created buffer if successful, NULL if not.
 *
 * @see ls_buf_xdelete
 */
ls_buf_t *ls_buf_xnew(int size, ls_xpool_t *pool);

/** @ls_buf_x
 * @brief Initializes the buffer to a given size from a given
 *  session pool.
 *
 * @param[in] pThis - A pointer to an allocated lsr buf object.
 * @param[in] size - The initial size to set the buffer to.
 * @param[in] pool - A pointer to the session pool to allocate from.
 * @return 0 on success, -1 on failure.
 *
 * @see ls_buf_xd
 */
int ls_buf_x(ls_buf_t *pThis, int size, ls_xpool_t *pool);

/** @ls_buf_xd
 * @brief Destroys the buffer.  DOES NOT FREE \e pThis!
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] pool - A pointer to the session pool to deallocate from.
 * @return Void.
 *
 * @see ls_buf_x
 */
void ls_buf_xd(ls_buf_t *pThis, ls_xpool_t *pool);

/** @ls_buf_xdelete
 * @brief Deletes the buffer, opposite of \link #ls_buf_xnew buf xnew \endlink
 * @details If a buf was created with \link #ls_buf_xnew buf xnew, \endlink
 *  it must be deleted with \link #ls_buf_xdelete buf xdelete. \endlink
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] pool - A pointer to the session pool to deallocate from.
 * @return Void.
 *
 * @see ls_buf_xnew
 */
void ls_buf_xdelete(ls_buf_t *pThis, ls_xpool_t *pool);

/** @ls_buf_new
 * @brief Creates and initializes a new buffer.
 *
 * @param[in] size - The initial size to set the buffer to.
 * @return A pointer to the created buffer if successful, NULL if not.
 *
 * @see ls_buf_delete
 */
ls_inline ls_buf_t *ls_buf_new(int size)
{   return ls_buf_xnew(size, NULL);  }

/** @ls_buf
 * @brief Initializes the buffer to a given size.
 *
 * @param[in] pThis - A pointer to an allocated lsr buf object.
 * @param[in] size - The initial size to set the buffer to.
 * @return 0 on success, -1 on failure.
 *
 * @see ls_buf_d
 */
ls_inline int ls_buf(ls_buf_t *pThis, int size)
{   return ls_buf_x(pThis, size, NULL);  }

/** @ls_buf_d
 * @brief Destroys the buffer.  DOES NOT FREE \e pThis!
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @return Void.
 *
 * @see ls_buf
 */
ls_inline void ls_buf_d(ls_buf_t *pThis)
{   ls_buf_xd(pThis, NULL);  }

/** @ls_buf_delete
 * @brief Deletes the buffer, opposite of \link #ls_buf_new buf new \endlink
 * @details If a buf was created with \link #ls_buf_new buf new, \endlink
 *  it must be deleted with \link #ls_buf_delete buf delete. \endlink
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @return Void.
 *
 * @see ls_buf_new
 */
ls_inline void ls_buf_delete(ls_buf_t *pThis)
{   ls_buf_xdelete(pThis, NULL); }

/** @ls_buf_xreserve
 * @brief Reserves \e size total bytes for the buffer from the session pool.
 *  If \e size is lower than the current size, it will shrink.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] size - The total number of bytes to reserve.
 * @param[in] pool - A pointer to the session pool to allocate from.
 * @return 0 on success, -1 on failure.
 */
int ls_buf_xreserve(ls_buf_t *pThis, int size, ls_xpool_t *pool);

/** @ls_buf_xgrow
 * @brief Extends the buffer by \e size bytes.
 * @details Allocates from the given session pool.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] size - The size to grow the buffer by.
 * @param[in] pool - A pointer to the session pool to allocate from.
 * @return 0 on success, -1 on failure.
 */
int ls_buf_xgrow(ls_buf_t *pThis, int size, ls_xpool_t *pool);

/** @ls_buf_xappend2
 * @brief Appends the buffer with a given buffer.
 * @details It will check if there is enough space in the buffer and will grow
 *  the buffer from the session pool if there is not enough space.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] pBuf - A pointer to the source buffer.
 * @param[in] size - The size of pBuf.
 * @param[in] pool - A pointer to the pool to allocate from.
 * @return The size appended or -1 if it failed.
 */
int ls_buf_xappend2(
    ls_buf_t *pThis, const char *pBuf, int size, ls_xpool_t *pool);

/** @ls_buf_xappend
 * @brief Appends the buffer with a given buffer.
 * @details Since the size is not passed in,
 *  it will have to calculate the length.
 *  It will check if there is enough space in the buffer
 *  and will grow the buffer from the session pool if there is not enough space.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] pBuf - A pointer to the source buffer.
 * @param[in] pool - A pointer to the pool to allocate from.
 * @return The size appended or -1 if it failed.
 */
ls_inline int ls_buf_xappend(
    ls_buf_t *pThis, const char *pBuf, ls_xpool_t *pool)
{   return ls_buf_xappend2(pThis, pBuf, strlen(pBuf), pool); }

/** @ls_buf_reserve
 * @brief Reserves \e size total bytes for the buffer.
 *  If \e size is lower than the current size, it will shrink.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] size - The total number of bytes to reserve.
 * @return 0 on success, -1 on failure.
 */
ls_inline int ls_buf_reserve(ls_buf_t *pThis, int size)
{   return ls_buf_xreserve(pThis, size, NULL);   }

/** @ls_buf_available
 * @brief Gets the number of bytes left in the buffer.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @return The number of bytes left.
 */
ls_inline int ls_buf_available(const ls_buf_t *pThis)
{   return pThis->pbufend - pThis->pend;    }

/** @ls_buf_begin
 * @brief Gets the beginning of the buffer.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @return A pointer to the beginning.
 */
ls_inline char *ls_buf_begin(const ls_buf_t *pThis)
{   return pThis->pbuf;   }

/** @ls_buf_end
 * @brief Gets the end of the buffer.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @return A pointer to the end of the buffer.
 */
ls_inline char *ls_buf_end(const ls_buf_t *pThis)
{   return pThis->pend;   }

/** @ls_buf_getp
 * @brief Gets a pointer of a given offset from the start of the buffer.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] offset - The offset from the beginning of the buffer.
 * @return The pointer associated with the offset.
 */
ls_inline char *ls_buf_getp(const ls_buf_t *pThis, int offset)
{   return pThis->pbuf + offset; }

/** @ls_buf_used
 * @brief Tells the buffer that the user appended \e size more bytes.
 * @details
 *  Do not call this after the calls \link #ls_buf_append buf append,\endlink
 *  \link #ls_buf_append2 buf append2,\endlink
 *  \link #ls_buf_unsafeapp buf append unsafe,\endlink
 *  \link #ls_buf_xappend buf xappend,\endlink
 *  and \link #ls_buf_xappend2 buf xappend2.\endlink
 *  It will be updated within those functions.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] size - The size to add.
 * @return Void.
 */
ls_inline void ls_buf_used(ls_buf_t *pThis, int size)
{   pThis->pend += size;     }

/** @ls_buf_clear
 * @brief Clears the buffer to 0 bytes used.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @return Void.
 */
ls_inline void ls_buf_clear(ls_buf_t *pThis)
{   pThis->pend = pThis->pbuf;    }

/** @ls_buf_capacity
 * @brief Gets the total capacity of the buffer
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @return The total capacity.
 */
ls_inline int ls_buf_capacity(const ls_buf_t *pThis)
{   return pThis->pbufend - pThis->pbuf;  }

/** @ls_buf_size
 * @brief Gets the size used in the buffer so far.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @return The size used.
 */
ls_inline int ls_buf_size(const ls_buf_t *pThis)
{   return pThis->pend - pThis->pbuf;   }

/** @ls_buf_resize
 * @brief Resizes the used amount to \e size bytes.
 * @details The size must be less than or equal to capacity.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] size - The size to resize the buffer to.
 * @return Void.
 */
ls_inline void ls_buf_resize(ls_buf_t *pThis, int size)
{
    assert(size <= ls_buf_capacity(pThis));
    pThis->pend = pThis->pbuf + size;
}

/** @ls_buf_grow
 * @brief Extends the buffer by \e size bytes.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] size - The size to grow the buffer by.
 * @return 0 on success, -1 on failure.
 */
ls_inline int ls_buf_grow(ls_buf_t *pThis, int size)
{   return ls_buf_xgrow(pThis, size, NULL);  }

/** @ls_buf_unsafeapp
 * @brief Appends the buffer with a given buffer.
 * @details This function is unsafe in that it will not check
 *  if there is enough space allocated.
 *  This function exists to speed up the append process if the user can
 *  guarantee that the buffer is large enough.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] pBuf - A pointer to the source buffer.
 * @param[in] size - The size of pBuf.
 * @return The size appended.
 */
ls_inline int ls_buf_unsafeapp(ls_buf_t *pThis, const char *pBuf, int size)
{
    memmove(ls_buf_end(pThis), pBuf, size);
    ls_buf_used(pThis, size);
    return size;
}

/** @ls_buf_unsafeappch
 * @brief Appends the buffer with a character.
 * @details This function is unsafe in that it will not check
 *  if there is enough space allocated.
 *  This function exists to speed up the append process if the user can
 *  guarantee that the buffer is large enough.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] ch - The character to append to the buffer.
 * @return Void.
 */
ls_inline void ls_buf_unsafeappch(ls_buf_t *pThis, char ch)
{   *pThis->pend++ = ch;   }

/** @ls_buf_append2
 * @brief Appends the buffer with a given buffer.
 * @details It will check if there is enough space in the buffer and will
 *  grow the buffer if there is not enough space.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] pBuf - A pointer to the source buffer.
 * @param[in] size - The size of pBuf.
 * @return The size appended or -1 if it failed.
 */
ls_inline int ls_buf_append2(ls_buf_t *pThis, const char *pBuf, int size)
{   return ls_buf_xappend2(pThis, pBuf, size, NULL);     }

/** @ls_buf_append
 * @brief Appends the buffer with a given buffer.
 * @details Since the size is not passed in,
 *  it will have to calculate the length.
 *  It will check if there is enough space in the buffer
 *  and will grow the buffer if there is not enough space.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] pBuf - A pointer to the source buffer.
 * @return The size appended or -1 if it failed.
 */
ls_inline int ls_buf_append(ls_buf_t *pThis, const char *pBuf)
{   return ls_buf_xappend2(pThis, pBuf, strlen(pBuf), NULL); }

/** @ls_buf_empty
 * @brief Specifies whether or not a lsr buf object is empty.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @return Non-zero if empty, 0 if not.
 */
ls_inline int ls_buf_empty(const ls_buf_t *pThis)
{   return (pThis->pbuf == pThis->pend);  }

/** @ls_buf_full
 * @brief Specifies whether or not a lsr buf object is full.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @return Non-zero if full, 0 if not.
 */
ls_inline int ls_buf_full(const ls_buf_t *pThis)
{   return (pThis->pend == pThis->pbufend); }

/** @ls_buf_getoffset
 * @brief Given a pointer, calculates the offset relative to the start of
 *  the buffer.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] p - The pointer to get the offset of.
 * @return The offset.
 */
ls_inline int ls_buf_getoffset(const ls_buf_t *pThis, const char *p)
{   return p - pThis->pbuf;    }

/** @ls_buf_popfrontto
 * @brief Pops the front \e size bytes from \e pThis and stores in \e pBuf.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[out] pBuf - A pointer to the allocated buffer to copy to.
 * @param[in] size - The number of bytes to attempt to copy.
 * @return The number of bytes copied.
 */
int ls_buf_popfrontto(ls_buf_t *pThis, char *pBuf, int size);

/** @ls_buf_popfront
 * @brief Pops the front \e size bytes from \e pThis.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] size - The number of bytes to pop.
 * @return The number of bytes popped.
 */
int ls_buf_popfront(ls_buf_t *pThis, int size);

/** @ls_buf_popend
 * @brief Pops the ending \e size bytes from \e pThis.
 *
 * @param[in] pThis - A pointer to an initialized lsr buf object.
 * @param[in] size - The number of bytes to pop.
 * @return The number of bytes popped.
 */
int ls_buf_popend(ls_buf_t *pThis, int size);

/** @ls_buf_swap
 * @brief Swaps the contents of the two buffers.
 *
 * @param[in,out] pThis - A pointer to an initialized lsr buf object.
 * @param[in,out] pRhs - A pointer to another initialized lsr buf object.
 * @return Void.
 */
void ls_buf_swap(ls_buf_t *pThis, ls_buf_t *pRhs);

/** @ls_xbuf_new
 * @brief Creates and initializes a new buffer from the session pool.
 *
 * @param[in] size - The initial size to set the buffer to.
 * @param[in] pool - A pointer to the session pool to allocate from.
 * @return A pointer to the created buffer if successful, NULL if not.
 *
 * @see ls_xbuf_delete
 */
ls_xbuf_t *ls_xbuf_new(int size, ls_xpool_t *pool);

/** @ls_xbuf
 * @brief Initializes the buffer to a given size.
 *
 * @param[in] pThis - A pointer to an allocated lsr xbuf object.
 * @param[in] size - The initial size to set the buffer to.
 * @param[in] pool - A pointer to the pool the buffer should allocate from.
 * @return 0 on success, -1 on failure.
 */
int ls_xbuf(ls_xbuf_t *pThis, int size, ls_xpool_t *pool);

/** @ls_xbuf_d
 * @brief Destroys the buffer.  DOES NOT FREE \e pThis!
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @return Void.
 *
 * @see ls_xbuf_d
 */
void ls_xbuf_d(ls_xbuf_t *pThis);

/** @ls_xbuf_delete
 * @brief Deletes the buffer, opposite of \link #ls_xbuf_new xbuf new \endlink
 * @details If a buf was created with \link #ls_xbuf_new xbuf new, \endlink
 * it must be deleted with \link #ls_xbuf_delete xbuf delete. \endlink
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @return Void.
 *
 * @see ls_xbuf_new
 */
void ls_xbuf_delete(ls_xbuf_t *pThis);

/** @ls_xbuf_reserve
 * @brief Reserves \e size total bytes for the buffer.
 *  If \e size is lower than the current size, it will shrink.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @param[in] size - The total number of bytes to reserve.
 * @return 0 on success, -1 on failure.
 *
 * @see ls_xbuf
 */
ls_inline int ls_xbuf_reserve(ls_xbuf_t *pThis, int size)
{   return ls_buf_xreserve(&pThis->buf, size, pThis->pool); }

/** @ls_xbuf_available
 * @brief Gets the number of bytes left in the buffer.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @return The number of bytes left
 */
ls_inline int ls_xbuf_available(const ls_xbuf_t *pThis)
{   return pThis->buf.pbufend - pThis->buf.pend;    }

/** @ls_xbuf_begin
 * @brief Gets the beginning of the buffer.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @return A pointer to the beginning.
 */
ls_inline char *ls_xbuf_begin(const ls_xbuf_t *pThis)
{   return pThis->buf.pbuf;     }

/** @ls_xbuf_end
 * @brief Gets the end of the buffer.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @return A pointer to the end of the buffer.
 */
ls_inline char *ls_xbuf_end(const ls_xbuf_t *pThis)
{   return pThis->buf.pend;    }

/** @ls_xbuf_getp
 * @brief Gets a pointer of a given offset from the start of the buffer.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @param[in] offset - The offset from the beginning of the buffer.
 * @return The pointer associated with the offset.
 */
ls_inline char *ls_xbuf_getp(const ls_xbuf_t *pThis, int offset)
{   return pThis->buf.pbuf + offset; }

/** @ls_xbuf_used
 * @brief Tells the buffer that the user appended \e size more bytes.
 * @details
 *  Do not call this after the calls \link #ls_xbuf_append xbuf append,\endlink
 *  \link #ls_xbuf_append2 xbuf append2,\endlink
 *  and \link #ls_xbuf_unsafeapp xbuf append unsafe.\endlink
 *  It will be updated within those functions.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @param[in] size - The size to add.
 * @return Void.
 */
ls_inline void ls_xbuf_used(ls_xbuf_t *pThis, int size)
{   pThis->buf.pend += size;     }

/** @ls_xbuf_clear
 * @brief Clears the buffer to 0 bytes used.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @return Void.
 */
ls_inline void ls_xbuf_clear(ls_xbuf_t *pThis)
{   pThis->buf.pend = pThis->buf.pbuf;    }

/** @ls_xbuf_capacity
 * @brief Gets the total capacity of the buffer
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @return The total capacity.
 */
ls_inline int ls_xbuf_capacity(const ls_xbuf_t *pThis)
{   return pThis->buf.pbufend - pThis->buf.pbuf;  }

/** @ls_xbuf_size
 * @brief Gets the size used in the buffer so far.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @return The size used.
 */
ls_inline int ls_xbuf_size(const ls_xbuf_t *pThis)
{   return pThis->buf.pend - pThis->buf.pbuf;   }

/** @ls_xbuf_resize
 * @brief Resizes the used amount to \e size bytes.
 * @details The size must be less than or equal to capacity.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @param[in] size - The size to resize the buffer to.
 * @return Void.
 */
ls_inline void ls_xbuf_resize(ls_xbuf_t *pThis, int size)
{   ls_buf_resize(&pThis->buf, size);  }

/** @ls_xbuf_grow
 * @brief Extends the buffer by \e size bytes.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @param[in] size - The size to grow the buffer by.
 * @return 0 on success, -1 on failure.
 */
ls_inline int ls_xbuf_grow(ls_xbuf_t *pThis, int size)
{   return ls_buf_xgrow(&pThis->buf, size, pThis->pool);    }

/** @ls_xbuf_unsafeapp
 * @brief Appends the buffer with a given buffer.
 * @details This function is unsafe in that it will not check
 *  if there is enough space allocated.
 *  This function exists to speed up the append process if the user can
 *  guarantee that the buffer is large enough.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @param[in] pBuf - A pointer to the source buffer.
 * @param[in] size - The size of pBuf.
 * @return The size appended.
 */
ls_inline int ls_xbuf_unsafeapp(ls_xbuf_t *pThis, const char *pBuf,
                                int size)
{   return ls_buf_unsafeapp(&pThis->buf, pBuf, size);  }

/** @ls_xbuf_unsafeappch
 * @brief Appends the buffer with a character.
 * @details This function is unsafe in that it will not check
 *  if there is enough space allocated.
 *  This function exists to speed up the append process if the user can
 *  guarantee that the buffer is large enough.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @param[in] ch - The character to append to the buffer.
 * @return Void.
 */
ls_inline void ls_xbuf_unsafeappch(ls_xbuf_t *pThis, char ch)
{   *pThis->buf.pend++ = ch;   }

/** @ls_xbuf_append2
 * @brief Appends the buffer with a given buffer.
 * @details It will check if there is enough space in the buffer and will grow
 *  the buffer if there is not enough space.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @param[in] pBuf - A pointer to the source buffer.
 * @param[in] size - The size of pBuf.
 * @return The size appended or -1 if it failed.
 */
ls_inline int ls_xbuf_append2(ls_xbuf_t *pThis, const char *pBuf, int size)
{   return ls_buf_xappend2(&pThis->buf, pBuf, size, pThis->pool);   }

/** @ls_xbuf_append
 * @brief Appends the buffer with a given buffer.
 * @details Since the size is not passed in,
 *  it will have to calculate the length.
 *  It will check if there is enough space in the buffer
 *  and will grow the buffer if there is not enough space.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @param[in] pBuf - A pointer to the source buffer.
 * @return The size appended or -1 if it failed.
 */
ls_inline int ls_xbuf_append(ls_xbuf_t *pThis, const char *pBuf)
{   return ls_xbuf_append2(pThis, pBuf, strlen(pBuf)); }

/** @ls_xbuf_empty
 * @brief Specifies whether or not a lsr xbuf object is empty.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @return 0 for false, true otherwise.
 */
ls_inline int ls_xbuf_empty(const ls_xbuf_t *pThis)
{   return (pThis->buf.pbuf == pThis->buf.pend);  }

/** @ls_xbuf_full
 * @brief Specifies whether or not a lsr xbuf object is full.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @return 0 for false, true otherwise.
 */
ls_inline int ls_xbuf_full(const ls_xbuf_t *pThis)
{   return (pThis->buf.pend == pThis->buf.pbufend); }

/** @ls_xbuf_getoffset
 * @brief Given a pointer, calculates the offset relative to the start of
 *  the buffer.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @param[in] p - The pointer to get the offset of.
 * @return The offset.
 */
ls_inline int ls_xbuf_getoffset(const ls_xbuf_t *pThis, const char *p)
{   return p - pThis->buf.pbuf;    }

/** @ls_xbuf_popfrontto
 * @brief Pops the front \e size bytes from \e pThis and stores in \e pBuf.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @param[out] pBuf - A pointer to the allocated buffer to copy to.
 * @param[in] size - The number of bytes to attempt to copy.
 * @return The number of bytes copied.
 */
ls_inline int ls_xbuf_popfrontto(ls_xbuf_t *pThis, char *pBuf, int size)
{   return ls_buf_popfrontto(&pThis->buf, pBuf, size);    }

/** @ls_xbuf_popfront
 * @brief Pops the front \e size bytes from \e pThis.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @param[in] size - The number of bytes to pop.
 * @return The number of bytes popped.
 */
ls_inline int ls_xbuf_popfront(ls_xbuf_t *pThis, int size)
{   return ls_buf_popfront(&pThis->buf, size);    }

/** @ls_xbuf_popend
 * @brief Pops the ending \e size bytes from \e pThis.
 *
 * @param[in] pThis - A pointer to an initialized lsr xbuf object.
 * @param[in] size - The number of bytes to pop.
 * @return The number of bytes popped.
 */
ls_inline int ls_xbuf_popend(ls_xbuf_t *pThis, int size)
{   return ls_buf_popend(&pThis->buf, size);    }

/** @ls_xbuf_swap
 * @brief Swaps the contents of the two buffers.
 *
 * @param[in,out] pThis - A pointer to an initialized lsr xbuf object.
 * @param[in,out] pRhs - A pointer to another initialized lsr xbuf object.
 * @return Void.
 */
void ls_xbuf_swap(ls_xbuf_t *pThis, ls_xbuf_t *pRhs);


#ifdef __cplusplus
}
#endif


#endif // LS_BUF_H
