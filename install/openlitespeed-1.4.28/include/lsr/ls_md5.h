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
#ifndef LS_MD5_H
#define LS_MD5_H

#include <stdint.h>
#include <string.h>

/**
 * @file
 * This file provides an option for anyone who wishes to not use OpenSSL's version
 * of MD5.  To select implementations, either have or comment out USE_OPENSSL_MD5.
 *
 * By default, OpenSSL's version is used.
 *
 * To use, user must either:
 *      \li Call #ls_md5
 *      \li Call #ls_md5_init, #ls_md5_update (May call this multiple times), #ls_md5_final in that order.
 */

#define USE_OPENSSL_MD5


#define LSR_MD5_DIGEST_LEN 16
#define LSR_MD5_CHUNKSIZE 16
#define LSR_MD5_BUFSIZE 64

#ifdef __cplusplus
extern "C" {
#endif


#if defined( USE_OPENSSL_MD5 )
#include <openssl/md5.h>
typedef MD5_CTX ls_md5_ctx_t;
#else
typedef struct ls_md5_ctx_s
{
    uint32_t A, B, C, D,
             lo, hi;
    uint32_t chunk[LSR_MD5_CHUNKSIZE];
    unsigned char shiftBuf[LSR_MD5_BUFSIZE];
} ls_md5_ctx_t;
#endif

/** @ls_md5_init
 * @brief Initializes the MD5 ctx.  Must be called first if the user is
 * doing the calls him/herself.
 *
 * @param[in] ctx - A pointer to an allocated ctx.
 */
int             ls_md5_init(ls_md5_ctx_t *ctx);

/** @ls_md5_update
 * @brief Updates the MD5 with a new buffer.
 *
 * @param[in] ctx - A pointer to an initialized ctx.
 * @param[in] p - A pointer to the buffer to add to the MD5.
 * @param[in] len - The length of the buffer.
 */
int             ls_md5_update(ls_md5_ctx_t *ctx, const void *p,
                              size_t len);

/** @ls_md5_final
 * @brief Calculates the result after finishing the MD5.
 *
 * @param[out] ret - A pointer to the result of the hash.
 * @param[in] ctx - A pointer to an initialized ctx.
 */
int             ls_md5_final(unsigned char *ret, ls_md5_ctx_t *ctx);

/** @ls_md5
 * @brief Calculates the \e p buffer and returns the result.
 *
 * @param[in] p - A pointer to the buffer to calculate.
 * @param[in] len - The length of p.
 * @param[out] ret - A pointer to the result of the calculation.
 * @return Ret on success, NULL on failure.
 */
unsigned char  *ls_md5(const unsigned char *p, size_t len,
                       unsigned char *ret);

#ifdef __cplusplus
}
#endif

#endif // LS_MD5_H
