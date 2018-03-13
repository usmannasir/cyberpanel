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
#ifndef LS_BASE64_H
#define LS_BASE64_H

/**
 * @file
 */

#ifdef __cplusplus
extern "C" {
#endif

/** @ls_base64_decode
 * @brief Decodes an encoded buffer.
 *
 * @param[in] encoded - The encoded buffer to decode.
 * @param[in] encodeLen - The length of the encoded buffer.
 * @param[out] decoded - The buffer to put the decoded buffer into.  Must have
 *  allocated enough space.
 * @return The length of the decoded buffer.
 */
int ls_base64_decode(const char *encoded, int encodeLen, char *decoded);

/** @ls_base64_encode
 * @brief Encodes a given buffer.
 *
 * @param[in] decoded - The buffer to encode.
 * @param[in] decodedLen - The length of the buffer to encode.
 * @param[out] encoded - The buffer to put the encoded buffer into.  Must have
 *  allocated enough space.
 * @return The length of the encoded buffer.
 */
int ls_base64_encode(const char *decoded, int decodedLen, char *encoded);

/** @ls_base64_encodelen
 * @brief Given a length, gets the expected length of an encoded buffer.
 *
 * @param[in] len - The length of the buffer to encode.
 * @return The expected length of an encoded buffer.
 */
static inline int ls_base64_encodelen(int len)
{   return (((len + 2) / 3) * 4); }

#ifdef __cplusplus
}
#endif

#endif //LS_BASE64_H
