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
#ifndef LS_TSSTACK_H
#define LS_TSSTACK_H

#include <lsr/ls_lock.h>
#include <lsr/ls_node.h>
#include <lsr/ls_stack.h>
#include <lsr/ls_types.h>

/**
 * @file
 * This version is the thread safe stack implementation.
 *  ls_tsstack_ uses spin locks to provide the concurrency protection.
 *
 * This uses ls_nodei_t as the nodes.  In order to use the stack,
 * the objects the user wishes to link should either inherit from,
 * or contain a ls_nodei_t struct.
 *
 * Other Versions:
 *  - lsr/ls_lfstack.h
 *  - lsr/ls_stack.h
 */

#define LSR_TSSTACK_SLEEP_TIME 250


#ifdef __cplusplus
extern "C" {
#endif

typedef struct ls_tsstack_s
{
    ls_stack_t      stack;
    ls_spinlock_t   lock;
} ls_tsstack_t;

/** @ls_tsstack_init
 * @brief Initializes a thread safe stack object.
 * @details The function initializes an object to manage a
 * node-based stack (LIFO).
 *
 * @param[in] pThis - A pointer to an allocated thread safe stack object.
 * @return Void.
 *
 * @see ls_tsstack_destroy
 */
ls_inline void ls_tsstack_init(ls_tsstack_t *pThis)
{
    ls_stack_init(&pThis->stack);
    ls_spinlock_setup(&pThis->lock);
}

/** @ls_tsstack_destroy
 * @brief Destroys a thread safe stack object.
 *
 * @param[in] pThis - A pointer to an initialized thread safe stack object.
 *
 * @see ls_tsstack_init
 */
ls_inline void ls_tsstack_destroy(ls_tsstack_t *pThis)
{
    ls_spinlock_lock(&pThis->lock);
    ls_stack_destroy(&pThis->stack);
    ls_spinlock_unlock(&pThis->lock);
}

/** @ls_tsstack_new
 * @brief Creates a new thread safe stack object.
 * @details The function allocates and initializes an object
 * to manage a node-based stack (LIFO).
 *
 * @return A pointer to an initialized thread safe stack object,
 * else NULL on error.
 *
 * @see ls_tsstack_delete
 */
ls_tsstack_t *ls_tsstack_new();

/** @ls_tsstack_delete
 * @brief Destroys then deletes a thread safe stack object.
 * @details The object should have been created with a previous
 * successful call to ls_tsstack_new.
 *
 * @param[in] pThis - A pointer to an initialized thread safe stack object.
 * @return Void.
 *
 * @see ls_tsstack_new
 */
void ls_tsstack_delete(ls_tsstack_t *pThis);

/** @ls_tsstack_trypush
 * @brief Tries to push an object onto the top of a thread safe stack.
 * @details This function will try to push onto the stack only once.
 * It will return immediately, regardless of the result.
 *
 * @param[in] pThis - A pointer to an initialized thread safe stack object.
 * @param[in] pNode - A pointer to the user defined object to push onto
 * the queue.
 * @return 0 on success, else -1 on failure.
 */
ls_inline int ls_tsstack_trypush(ls_tsstack_t *pThis, ls_nodei_t *pNode)
{
    if (ls_spinlock_trylock(&pThis->lock))
        return -1;
    ls_stack_push(&pThis->stack, pNode);
    ls_spinlock_unlock(&pThis->lock);
    return 0;
}

/** @ls_tsstack_push
 * @brief Pushes an object onto the top of a thread safe stack.
 * @details This function will block until it succeeds.
 *
 * @param[in] pThis - A pointer to an initialized thread safe stack object.
 * @param[in] pNode - A pointer to a user defined object to put on the stack.
 * @return Void.
 */
ls_inline void ls_tsstack_push(ls_tsstack_t *pThis, ls_nodei_t *pNode)
{
    while (1)
    {
        if (ls_tsstack_trypush(pThis, pNode) == 0)
            return;
        usleep(LSR_TSSTACK_SLEEP_TIME);
    }
}

/** @ls_tsstack_trypop
 * @brief Tries to pop an object from the top of a thread safe stack.
 * @details This function will try to pop from the stack only once.
 * It will return immediately, regardless of result.
 *
 * @param[in] pThis - A pointer to an initialized thread safe stack object.
 * @param[in,out] pRet - A pointer to the popped object if there is one
 * available.
 * @return 0 on success, else -1 on failure.
 * \note If successful, the value stored in pRet is the result of a pop.
 * If the stack is empty, this will be NULL.
 */
ls_inline int ls_tsstack_trypop(ls_tsstack_t *pThis, ls_nodei_t **pRet)
{
    if (ls_spinlock_trylock(&pThis->lock))
        return -1;
    *pRet = ls_stack_pop(&pThis->stack);
    ls_spinlock_unlock(&pThis->lock);
    return 0;
}

/** @ls_tsstack_pop
 * @brief Pops an object from the top of a thread safe stack.
 * @details This function will block until it succeeds.
 *
 * @param[in] pThis - A pointer to an initialized thread safe stack object.
 * @return A pointer to the object if one exists, else NULL if empty.
 */
ls_inline ls_nodei_t *ls_tsstack_pop(ls_tsstack_t *pThis)
{
    ls_nodei_t *pRet;

    while (1)
    {
        if (ls_tsstack_trypop(pThis, &pRet) == 0)
            return pRet;
        usleep(LSR_TSSTACK_SLEEP_TIME);
    }
}

#ifdef __cplusplus
}
#endif



#endif //LS_TSSTACK_H


