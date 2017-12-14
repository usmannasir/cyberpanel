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
#ifndef LS_STACK_H
#define LS_STACK_H

#include <lsr/ls_node.h>
#include <lsr/ls_types.h>

#include <stdlib.h>

/**
 * @file
 *
 * \warning This version is the simple stack implementation.
 *  ls_stack_ does \b NOT provide any concurrency protection.
 *
 * This uses ls_nodei_t as the nodes.  In order to use the stack,
 * the objects the user wishes to link should either inherit from,
 * or contain a ls_nodei_t struct.
 *
 * Other Versions:
 *  - lsr/ls_lfstack.h
 *  - lsr/ls_tsstack.h
 */


#ifdef __cplusplus
extern "C" {
#endif

typedef struct ls_stack_s
{
    ls_nodei_t *phead;
} ls_stack_t;

/** @ls_stack_init
 * @brief Initializes a simple stack object.
 * @details The function initalizes an object to manage a
 * node-based stack (LIFO). This implementation is
 * \b NOT thread safe.
 *
 * @param[in] pThis - A pointer to an allocated stack object.
 * @return Void.
 *
 * @see ls_stack_destroy
 */
ls_inline void ls_stack_init(ls_stack_t *pThis)
{
    pThis->phead = NULL;
}

/** @ls_stack_destroy
 * @brief Destroys a stack object.
 *
 * @param[in] pThis - A pointer to an initialized stack object.
 * @return Void.
 *
 * @see ls_stack_init
 */
ls_inline void ls_stack_destroy(ls_stack_t *pThis)
{
    pThis->phead = NULL;
}

/** @ls_stack_new
 * @brief Creates a new stack object.
 * @details The function allocates and initalizes an object
 * to manage a node-based stack (LIFO).  This implementation is
 * \b NOT thread safe.
 *
 * @return A pointer to an initialized stack object, else NULL on error.
 *
 * @see ls_stack_delete
 */
ls_stack_t *ls_stack_new();

/** @ls_stack_delete
 * @brief Destroys then deletes a stack object.
 * @details The object should have been created with a previous
 * successful call to ls_stack_new.
 *
 * @param[in] pThis - A pointer to an initialized stack object.
 * @return Void.
 *
 * @see ls_stack_new
 */
void ls_stack_delete(ls_stack_t *pThis);

/** @ls_stack_push
 * @brief Pushes an object onto the top of a stack.
 *
 * @param[in] pThis - A pointer to an initalized stack object.
 * @param[in] pNode - A pointer to the user defined object to put on the stack.
 * @return Void.
 */
ls_inline void ls_stack_push(ls_stack_t *pThis, ls_nodei_t *pNode)
{
    pNode->next = pThis->phead;
    pThis->phead = pNode;
}

/** @ls_stack_pop
 * @brief Pops an object from the top of a stack.
 *
 * @param[in] pThis - A pointer to an initialized stack object.
 * @return a pointer to the object if one exists, else NULL if empty.
 */
ls_inline ls_nodei_t *ls_stack_pop(ls_stack_t *pThis)
{
    ls_nodei_t *pNode = pThis->phead;
    if (pNode)
        pThis->phead = pNode->next;
    return pNode;
}

#ifdef __cplusplus
}
#endif



#endif //LS_STACK_H

