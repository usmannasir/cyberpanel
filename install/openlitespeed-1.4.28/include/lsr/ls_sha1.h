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
#ifndef LS_SHA1_H
#define LS_SHA1_H

#include <fcntl.h>
#include <string.h>
#include <unistd.h>

#include <sys/types.h>
#include <sys/stat.h>

/**
 * @file
 * This file provides an alternative option to OpenSSL's version of SHA1.
 * To select implementations, either have or comment out \c USE_OPENSSL_SHA1.
 *
 * By default, OpenSSL's version is used.
 *
 * To use, user must either:
 *      \li Call #ls_sha1
 *      \li Call #ls_sha1_init, #ls_sha1_update, #ls_sha1_finish, #ls_sha1_free in that order.
 *          This version is useful if the user needs to process the input in chunks.
 */

#define USE_OPENSSL_SHA1


#if defined(_MSC_VER) && !defined(EFIX64) && !defined(EFI32)
#include <basetsd.h>
typedef UINT32 uint32_t;
#else
#include <inttypes.h>
#endif

#ifdef __cplusplus
extern "C" {
#endif

//#define LSR_SHA1_DEBUG

#if defined( USE_OPENSSL_SHA1 )

#include <openssl/sha.h>
typedef SHA_CTX ls_sha1_ctx_t;

#else
typedef struct ls_sha1_ctx_s
{
    uint32_t        m_total[2];
    uint32_t        m_digest_state[5];
    unsigned char   m_buf[64];
} ls_sha1_ctx_t;
#endif

/** @ls_sha1_init
 * @brief Initializes the SHA1 ctx.  Must be called first if the user is
 * doing the calls him/herself.
 *
 * @param[in] ctx - A pointer to an allocated ctx.
 * @return 1 for success, else 0 for failure.
 */
int             ls_sha1_init(ls_sha1_ctx_t *ctx);

/** @ls_sha1_free
 * @brief Sets everything in the ctx to 0.
 *
 * @param[in] ctx - A pointer to an initialized ctx.
 * @return Void.
 */
void            ls_sha1_free(ls_sha1_ctx_t *ctx);

/** @ls_sha1_update
 * @brief Updates the SHA1 with a new buffer.
 *
 * @param[in] ctx - A pointer to an initialized ctx.
 * @param[in] input - A pointer to the buffer to add to the SHA1.
 * @param[in] ilen - The length of the buffer.
 * @return 1 for success, else 0 for failure.
 */
int             ls_sha1_update(ls_sha1_ctx_t *ctx,
                               const unsigned char *input, size_t ilen);

/** @ls_sha1_finish
 * @brief Calculates the result after finishing the SHA1.
 *
 * @param[in] ctx - A pointer to an initialized ctx.
 * @param[out] output - A pointer to the result of the hash.
 * @return 1 for success, else 0 for failure.
 */
int             ls_sha1_finish(ls_sha1_ctx_t *ctx, unsigned char *output);

/** @ls_sha1
 * @brief Calculates the entire input buffer and returns the result.
 *
 * @param[in] input - A pointer to the buffer to calculate.
 * @param[in] ilen - The length of input.
 * @param[out] output - A pointer to the result of the calculation.
 * @return Output on success, NULL on failure.
 */
unsigned char  *ls_sha1(const unsigned char *input, size_t ilen,
                        unsigned char *output);

#ifdef __cplusplus
}
#endif

#endif //LS_SHA1_H
