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
#ifndef LS_TYPES_H
#define LS_TYPES_H

/**
 * @file
 */

#ifdef __cplusplus
extern "C" {
#endif

#include <lsdef.h>

typedef unsigned long          ls_hash_key_t;
typedef struct ls_ptrlist_s    ls_ptrlist_t;
typedef ls_ptrlist_t           ls_strlist_t;
/**
 * @addtogroup LSR_STR_GROUP
 * @{
 */
typedef struct ls_str_s        ls_str_t;
typedef struct ls_strpair_s   ls_strpair_t;
/**
 * @}
 */
typedef struct ls_xpool_s      ls_xpool_t;

typedef uint32_t (*h32_fn)(const void *pVal);
typedef uint64_t (*h64_fn)(const void *pVal);
typedef int (*v_comp)(const void *pVal1, const void *pVal2);

typedef uint32_t (*h2_32_fn)(const void *pVal, size_t len);
typedef uint64_t (*h2_64_fn)(const void *pVal, size_t len);
typedef int (*v2_comp)(const void *pVal1, const void *pVal2, size_t len);

#ifdef __cplusplus
}
#endif

#endif //LS_TYPES_H
