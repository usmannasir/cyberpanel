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
#ifndef LS_CONFPARSER_H
#define LS_CONFPARSER_H

//#define LSR_CONFPARSERDEBUG

#include <lsr/ls_objarray.h>
#include <lsr/ls_str.h>
#include <lsr/ls_types.h>

#ifdef LSR_CONFPARSERDEBUG
#include <stdio.h>
#endif

/**
 * @file
 */

#ifdef __cplusplus
extern "C" {
#endif

typedef struct ls_confparser_s ls_confparser_t;

/**
 * @typedef ls_confparser_t
 * @brief A Configuration Parser that separates a string
 *  into delimited parameters.
 * @details @note The member variables of the structure
 *  are expected to be reused.\n
 *  If the user needs to save the parameter and plans to reuse the structure,
 *  then a deep copy of the parameter must be made.
 */
struct ls_confparser_s
{
    ls_objarray_t  plist;
    ls_str_t       pstr;
};


/** @ls_confparser
 * @brief Initializes the given confparser and its internal structures.
 *
 * @param[in] pThis - A pointer to an allocated confparser.
 * @return Void.
 *
 * @see ls_confparser_d
 */
void ls_confparser(ls_confparser_t *pThis);

/** @ls_confparser_d
 * @brief Destroys the given confparser and its internal structures.
 *  DOES NOT FREE pThis!
 *
 * @param[in] pThis - A pointer to an initialized confparser.
 * @return Void.
 *
 * @see ls_confparser
 */
void ls_confparser_d(ls_confparser_t *pThis);

/** @ls_confparser_line
 * @brief Parses a line and splits it into a list of parameters
 *  with the surrounding white spaces and quotes removed.
 * @details The returned list is an \link #ls_objarray_t object array \endlink
 *  of \link ls_str.h lsr str structs. \endlink  Each str struct will have
 *  the pointer to a parameter and the length of the parameter.
 *
 * @param[in] pThis - A pointer to an initialized confparser.
 * @param[in] pLine - A pointer to the beginning of the line.
 * @param[in] pLineEnd - A pointer to the end of the line.
 * @return The pointer to the list upon completion,
 *  or NULL if there were no parameters.
 *
 * @see ls_objarray.h, ls_str.h
 */
ls_objarray_t *ls_confparser_line(ls_confparser_t *pThis,
                                  const char *pLine, const char *pLineEnd);

/** @ls_confparser_linekv
 * @brief Parses a line and splits it into an
 *  \link #ls_objarray_t object array \endlink containing a key
 *  and a value with the surrounding white spaces and quotes removed.
 * @details The returned list is an \link #ls_objarray_t object array \endlink
 *  of \link ls_str.h lsr str structs.\endlink  The first str struct will be
 *  for the key and the second struct will be for the value.
 *
 * @param[in] pThis - A pointer to an initialized confparser.
 * @param[in] pLine - A pointer to the beginning of the line.
 * @param[in] pLineEnd - A pointer to the end of the line.
 * @return The pointer to the list upon completion,
 *  or NULL if there were no parameters.
 * @note If the line only contains a key,
 *  there will still be two items in the list.
 *  The value string will just be set to NULL and the length 0.
 *
 * @see ls_objarray.h, ls_str.h
 */
ls_objarray_t *ls_confparser_linekv(ls_confparser_t *pThis,
                                    const char *pLine, const char *pLineEnd);

/** @ls_confparser_multi
 * @brief Parses a block of parameters (multiple lines)
 *  and splits it into a list of parameters
 *  with the surrounding white spaces and quotes removed.
 * @details The returned list is an \link #ls_objarray_t object array \endlink
 *  of \link ls_str.h lsr str structs.\endlink  Each str struct will have
 *  the pointer to a parameter and the length of the parameter.
 *
 * @param[in] pThis - A pointer to an initialized confparser.
 * @param[in] pBlock - A pointer to the beginning of the block.
 * @param[in] pBlockEnd - A pointer to the end of the block.
 * @return The pointer to the list upon completion,
 *  or NULL if there were no parameters.
 *
 * @see ls_objarray.h, ls_str.h
 */
ls_objarray_t *ls_confparser_multi(ls_confparser_t *pThis,
                                   const char *pBlock, const char *pBlockEnd);

/** @ls_confparser_getlist
 * @brief Gets the list of a confparser.
 * @details The returned list is an \link #ls_objarray_t object array \endlink
 *  of \link ls_str.h lsr str structs.\endlink  Each str struct will have
 * the pointer to the parameter and the length of the parameter.
 *
 * @param[in] pThis - A pointer to an initialized confparser.
 * @return A pointer to the list.
 *
 * @see ls_objarray.h, ls_str.h
 */
ls_inline ls_objarray_t *ls_confparser_getlist(ls_confparser_t *pThis)
{   return &pThis->plist;  }




#ifdef __cplusplus
}
#endif

#endif  /* LS_CONFPARSER_H */
