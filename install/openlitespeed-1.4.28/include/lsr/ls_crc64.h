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
#ifndef LS_CRC64_H
#define LS_CRC64_H

#define __STDC_CONSTANT_MACROS
#include <inttypes.h>
#include <sys/types.h>

/**
 * @file
 */

#ifdef __cplusplus
extern "C" {
#endif

/** @ls_crc64
 * @brief Calculates the crc code for a chunk of data.
 *
 * @param[in] crc - The initial crc state.
 * @param[in] buf - A pointer to the data to process.
 * @param[in] size - The size of the data.
 * @return The updated crc code.
 */
extern uint64_t ls_crc64(uint64_t crc, const uint8_t *buf, size_t size);

#ifdef __cplusplus
}
#endif

#endif //LS_CRC64_H
