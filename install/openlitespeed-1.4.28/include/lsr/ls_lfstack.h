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
#ifndef LS_LFSTACK_H
#define LS_LFSTACK_H

#include <lsr/ls_node.h>


/**
 * @file
 * This version is the lock free stack implementation.
 *  ls_lfstack_ uses atomic functions where necessary to provide
 *  the concurrency protection.
 * \warning This version does not protect against the reclamation problem.
 *
 * This uses ls_lfnodei_t as the nodes.  In order to use the stack,
 * the objects the user wishes to link should either inherit from,
 * or contain a ls_lfnodei_t struct.
 *
 * Other Versions:
 *  - lsr/ls_stack.h
 *  - lsr/ls_tsstack.h
 */


#ifdef __cplusplus
extern "C" {
#endif

typedef struct ls_lfstack_s ls_lfstack_t;

/** @ls_lfstack_new
 * @brief Creates a new lock free stack object.
 * @details This function allocates and initializes an object
 * to manage a node-based stack (LIFO) without the use of locks.
 *
 * @return A pointer to an initialized lock free stack object,
 * else NULL on error.
 *
 * @see ls_lfstack_delete
 */
ls_lfstack_t *ls_lfstack_new();

/** @ls_lfstack_init
 * @brief Initializes a lock free stack object.
 * @details This function initializes an object to manage a
 * node-based stack (LIFO) without the use of locks.
 *
 * @param[in] pThis - A pointer to an allocated lock free stack object.
 * @return Void.
 *
 * @see ls_lfstack_destroy
 */
void ls_lfstack_init(ls_lfstack_t *pThis);

/** @ls_lfstack_destroy
 * @brief Destroys a lock free stack object.
 *
 * @param[in] pThis - A pointer to an initialized lock free stack object.
 * @return Void.
 *
 * @see ls_lfstack_init
 */
void ls_lfstack_destroy(ls_lfstack_t *pThis);

/** @ls_lfstack_delete
 * @brief Destroys then deletes a lock free stack object.
 * @details The object should have been created with a previous
 * successful call to ls_lfstack_new.
 *
 * @param[in] pThis - A pointer to an initialized lock free stack object.
 * @return Void.
 *
 * @see ls_lfstack_new
 */
void ls_lfstack_delete(ls_lfstack_t *pThis);

/** @ls_lfstack_push
 * @brief Pushes an object onto the top of a lock free stack.
 * @details This function will block until it succeeds.
 *
 * @param[in] pThis - A pointer to an initialized lock free stack object.
 * @param[in] pNode - A pointer to a user defined object to push on the stack.
 * @return 0 on success, else -1 on failure.
 */
int ls_lfstack_push(ls_lfstack_t *pThis, ls_lfnodei_t *pNode);

/** @ls_lfstack_pop
 * @brief Pops an object from the top of a lock free stack.
 * @details This function will block until it succeeds.
 *
 * @param[in] pThis - A pointer to an initialized lock free stack object.
 * @return A pointer to the object if one exists, else NULL if empty.
 */
ls_lfnodei_t *ls_lfstack_pop(ls_lfstack_t *pThis);

#ifdef __cplusplus
}
#endif

#endif //LS_LFSTACK_H

