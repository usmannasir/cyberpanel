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
#ifndef LS_STR_H
#define LS_STR_H

#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <lsr/ls_types.h>

/**
 * @file
 * This structure is essentially a string with the length included.
 * It will do any allocation for the user as necessary.  If the user
 * wishes to use the session pool,  the *_xp functions must be called
 * when it is available.  Any other function may use the regular ls_str_*
 * functions because they do not allocate.
 *
 * The user must remain consistent with the xp or non xp version, as any
 * mixing will likely cause errors.
 */

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @defgroup LSR_STR_GROUP Str Group
 * @{
 *
 * This module defines the ls_str structures.
 *
 * @see ls_str.h
 *
 */

/**
 * @typedef ls_str_t
 * @brief A structure like a char *, except it has the string length as well.
 */
struct ls_str_s
{
    char    *ptr;
    size_t   len;
};

/**
 * @typedef ls_strpair_t
 * @brief A str pair structure that can be used for key/value pairs.
 */
struct ls_strpair_s
{
    ls_str_t key;
    ls_str_t val;
};

/**
 * @}
 */

/** @ls_str_new
 * @brief Creates a new lsr str object.  Initializes the
 * buffer and length to a deep copy of \e pStr and \e len.
 *
 * @param[in] pStr - The string to duplicate.  May be NULL.
 * @param[in] len - The length of the string.
 * @return A pointer to the lsr str object if successful, NULL if not.
 *
 * @see ls_str_delete
 */
ls_str_t *ls_str_new(const char *pStr, size_t len);

/** @ls_str
 * @brief Initializes a given lsr str.  Initializes the
 * buffer and length to a deep copy of \e pStr and \e len.
 *
 * @param[in] pThis - A pointer to an allocated lsr str object.
 * @param[in] pStr - The string to duplicate.  May be NULL.
 * @param[in] len - The length of the string.
 * @return The lsr str object if successful, NULL if not.
 *
 * @see ls_str_d
 */
ls_str_t *ls_str(ls_str_t *pThis, const char *pStr, size_t len);

/** @ls_str_copy
 * @brief Copies the source lsr str to the dest lsr str.  Makes a
 * deep copy of the string.  Must be destroyed with ls_str_d
 *
 * @param[in] dest - A pointer to an initialized lsr str object.
 * @param[in] src - A pointer to another initialized lsr str object.
 * @return Dest if successful, NULL if not.
 *
 * @see ls_str, ls_str_d
 */
ls_str_t *ls_str_copy(ls_str_t *dest, const ls_str_t *src);

/** @ls_str_d
 * @brief Destroys the internals of the lsr str object.  DOES NOT FREE pThis!
 * The opposite of ls_str.
 *
 * @param[in] pThis - A pointer to an initialized lsr str object.
 * @return Void.
 *
 * @see ls_str
 */
void       ls_str_d(ls_str_t *pThis);

/** @ls_str_delete
 * @brief Destroys and deletes the lsr str object. The opposite of ls_str_new.
 * @details The object should have been created with a previous
 *   successful call to ls_str_new.
 *
 * @param[in] pThis - A pointer to an initialized lsr str object.
 * @return Void.
 *
 * @see ls_str_new
 */
void       ls_str_delete(ls_str_t *pThis);

/** @ls_str_blank
 * @brief Clears the internals of the lsr str object.  DOES NOT FREE THE BUF!
 *
 * @param[in] pThis - A pointer to an initialized lsr str object.
 * @return Void.
 */
ls_inline void ls_str_blank(ls_str_t *pThis)
{   pThis->ptr = NULL; pThis->len = 0;       }

/** @ls_str_len
 * @brief Gets the length of the lsr str object.
 *
 * @param[in] pThis - A pointer to an initialized lsr str object.
 * @return The length.
 */
ls_inline size_t        ls_str_len(const ls_str_t *pThis)
{   return pThis->len;    }

/** @ls_str_setlen
 * @brief Sets the length of the string.
 *
 * @param[in] pThis - A pointer to an initialized lsr str object.
 * @param[in] len - The length to set the lsr str object to.
 * @return Void.
 */
ls_inline void          ls_str_setlen(ls_str_t *pThis, size_t len)
{   pThis->len = len;    }

/** @ls_str_buf
 * @brief Gets a char * of the string.
 *
 * @param[in] pThis - A pointer to an initialized lsr str object.
 * @return A char * of the string.
 */
ls_inline char         *ls_str_buf(const ls_str_t *pThis)
{   return pThis->ptr;   }

/** @ls_str_cstr
 * @brief Gets a \e const char * of the string.
 *
 * @param[in] pThis - A pointer to an initialized lsr str object.
 * @return A \e const char * of the string.
 */
ls_inline const char   *ls_str_cstr(const ls_str_t *pThis)
{   return pThis->ptr;   }

/** @ls_str_prealloc
 * @brief Preallocates space in the lsr str object.
 * @details Useful for when you want a buffer created for later use.
 *
 * @param[in] pThis - A pointer to an initialized lsr str object.
 * @param[in] size - The size to allocate.
 * @return The allocated space, NULL if error.
 */
char   *ls_str_prealloc(ls_str_t *pThis, size_t size);

/** @ls_str_dup
 * @brief Sets the lsr str object to \e pStr.  Will create a deep copy.
 *
 * @param[in] pThis - A pointer to an initialized lsr str object.
 * @param[in] pStr - The string to set the lsr str object to.
 * @param[in] len - The length of the string.
 * @return The number of bytes set.
 */
size_t   ls_str_dup(ls_str_t *pThis, const char *pStr, size_t len);

/** @ls_str_append
 * @brief Appends the current lsr str object with \e pStr.  Will allocate a deep copy.
 *
 * @param[in] pThis - A pointer to an initialized lsr str object.
 * @param[in] pStr - The string to append the lsr str object to.
 * @param[in] len - The length of the string.
 * @return Void.
 */
void    ls_str_append(ls_str_t *pThis, const char *pStr, size_t len);

/** @ls_str_cmp
 * @brief A comparison function for lsr str. Case Sensitive.
 * @details This may be used for lsr hash or map comparison.
 *
 * @param[in] pVal1 - The first lsr str object to compare.
 * @param[in] pVal2 - The second lsr str object to compare.
 * @return Result according to #ls_hash_val_comp.
 */
int     ls_str_cmp(const void *pVal1, const void *pVal2);

/** @ls_str_bcmp
 * @brief A binary comparison function for lsr str.
 * @details This may be used for lsr hash or map comparison.
 *
 * @param[in] pVal1 - The first ls_str object to compare.
 * @param[in] pVal2 - The second ls_str object to compare.
 * @return Result according to #ls_hash_val_comp.
 */
int     ls_str_bcmp(const void *pVal1, const void *pVal2);

/** @ls_str_hf
 * @brief A hash function for lsr str structure. Case Sensitive.
 * @details This may be used for lsr hash.
 *
 * @param[in] pKey - The key to calculate.
 * @return The hash key.
 */
ls_hash_key_t  ls_str_hf(const void *pKey);

/** @ls_str_hfxx
 * @brief A hash function for lsr str structure using xxhash. Case Sensitive.
 * @details This may be used for lsr hash.
 *
 * @param[in] pKey - The key to calculate.
 * @return The hash key.
 */
ls_hash_key_t  ls_str_xh32(const void *pKey);

/** @ls_str_cmpci
 * @brief A comparison function for lsr str. Case Insensitive.
 * @details This may be used for lsr hash or map comparison.
 *
 * @param[in] pVal1 - The first lsr str object to compare.
 * @param[in] pVal2 - The second lsr str object to compare.
 * @return Result according to #ls_hash_val_comp.
 */
int             ls_str_cmpci(const void *pVal1, const void *pVal2);

/** @ls_str_hfci
 * @brief A hash function for lsr str. Case Insensitive.
 * @details This may be used for lsr hash.
 *
 * @param[in] pKey - The key to calculate.
 * @return The hash key.
 */
ls_hash_key_t  ls_str_hfci(const void *pKey);

/** @ls_str_set
 * @brief Sets the lsr str object to the \e pStr.  WILL NOT MAKE A DEEP COPY!
 * @warning This may be used if the user does not want to create a deep
 * copy of the string.  However, with that said, the user is responsible
 * with deallocating the string and may not destroy the lsr str unless
 * it is \link #ls_str_blank blanked. \endlink
 *
 * @param[in] pThis - A pointer to an initialized lsr str object.
 * @param[in] pStr - The string to set to.
 * @param[in] len - The length of the string.
 * @return Void.
 */
ls_inline void ls_str_set(ls_str_t *pThis, char *pStr, size_t len)
{
    pThis->ptr = pStr;
    pThis->len = len;
}

/** @ls_str_xnew
 * @brief Creates a new lsr str object.
 * @details Initializes the buffer and length to a deep copy
 * of \e pStr and \e len from the given session pool.  Must delete
 * with \link #ls_str_xdelete delete xp. \endlink
 *
 * @param[in] pStr - The string to duplicate.  May be NULL.
 * @param[in] len - The length of the string.
 * @param[in] pool - A pointer to the pool to allocate from.
 * @return The lsr str object if successful, NULL if not.
 *
 * @see ls_str_xdelete
 */
ls_str_t  *ls_str_xnew(const char *pStr, size_t len, ls_xpool_t *pool);

/** @ls_str_x
 * @brief Initializes a given lsr str from the session pool.  Initializes the
 * buffer and length to a deep copy of \e pStr and \e len.
 * @details Must destroy with \link #ls_str_xd destroy xp. \endlink
 *
 * @param[in] pThis - A pointer to an allocated str to initialize.
 * @param[in] pStr - The string to duplicate.  May be NULL.
 * @param[in] len - The length of the string.
 * @param[in] pool - A pointer to the pool to allocate from.
 * @return The lsr str object if successful, NULL if not.
 *
 * @see ls_str_xd
 */
ls_str_t  *ls_str_x(ls_str_t *pThis, const char *pStr, size_t len,
                    ls_xpool_t *pool);

/** @ls_str_xcopy
 * @brief Copies the source lsr str object to the destination lsr str object.  Makes a
 * deep copy of the string.  Must destroy with \link #ls_str_xd destroy xp. \endlink
 *
 * @param[in] dest - A pointer to an allocated lsr str object.
 * @param[in] src - A pointer to an initialized lsr str object.
 * @param[in] pool - A pointer to the pool to allocate from.
 * @return Dest if successful, NULL if not.
 *
 * @see ls_str_xd
 */
ls_str_t  *ls_str_xcopy(ls_str_t *dest, const ls_str_t *src,
                        ls_xpool_t *pool);

/** @ls_str_xd
 * @brief Destroys the internals of the lsr str object.  DOES NOT FREE pThis!
 * The opposite of ls_str_x.
 *
 * @param[in] pThis - A pointer to an initialized lsr str object.
 * @param[in] pool - The pool to deallocate from.
 * @return Void.
 *
 * @see ls_str_x
 */
void        ls_str_xd(ls_str_t *pThis, ls_xpool_t *pool);

/** @ls_str_xdelete
 * @brief Destroys and deletes the lsr str object. The opposite of ls_str_xnew.
 * @details The object should have been created with a previous
 *   successful call to ls_str_xnew.
 *
 * @param[in] pThis - A pointer to an initialized lsr str object.
 * @param[in] pool - A pointer to the pool to deallocate from.
 * @return Void.
 *
 * @see ls_str_xnew
 */
void        ls_str_xdelete(ls_str_t *pThis, ls_xpool_t *pool);

/** @ls_str_xprealloc
 * @brief Preallocates space in the lsr str object from the session pool.
 * @details Useful for when you want a buffer created for later use.
 *
 * @param[in] pThis - A pointer to an initialized lsr str object.
 * @param[in] size - The size to allocate.
 * @param[in] pool - A pointer to the pool to allocate from.
 * @return The allocated space, NULL if error.
 */
char   *ls_str_xprealloc(ls_str_t *pThis, int size, ls_xpool_t *pool);

/** @ls_str_xsetstr
 * @brief Sets the lsr str object to \e pStr.  Will create a deep copy.
 *
 * @param[in] pThis - A pointer to an initialized lsr str object.
 * @param[in] pStr - The string to set the lsr str object to.
 * @param[in] len - The length of the string.
 * @param[in] pool - A pointer to the pool to allocate from.
 * @return The number of bytes set.
 */
size_t  ls_str_xsetstr(ls_str_t *pThis, const char *pStr, size_t len,
                       ls_xpool_t *pool);

/** @ls_str_xappend
 * @brief Appends the current lsr str object with \e pStr.  Will allocate a deep copy
 * from the session pool.
 *
 * @param[in] pThis - A pointer to an initialized lsr str object.
 * @param[in] pStr - The string to append to the struct.
 * @param[in] len - The length of the string.
 * @param[in] pool - A pointer to the pool to allocate from.
 * @return Void.
 */
void    ls_str_xappend(ls_str_t *pThis, const char *pStr, size_t len,
                       ls_xpool_t *pool);


/** @LS_STR_CONST
 * @brief Initialize const ls_str_t object with const string literal
 *     const ls_str_t abc = LS_STR_CONST("abc");
 *
 * @param[in] x - must be a const string literal, like "abcd"
 */

#define LS_STR_CONST(x)         { (char*)x, sizeof(x) - 1 }


/** @LS_STRPAIR_CONST
 * @brief Initialize const ls_strpair_t object with const string literal
 *     const ls_strpair_t abc = LS_STRPAIR_CONST("abc", "def");
 *
 * @param[in] x - must be a const string literal, like "abcd"
 * @param[in] y - must be a const string literal, like "abcd"
 */
#define LS_STRPAIR_CONST(x, y)  { { (char*)x, sizeof(x) - 1 }, { (char*)y, sizeof(y) - 1 }  }

#ifdef __cplusplus
}
#endif


#endif //LS_STR_H
