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
#ifndef LS_LFQUEUE_H
#define LS_LFQUEUE_H

#include <lsr/ls_node.h>
#include <sys/time.h>


/**
 * @file
 */


#ifdef __cplusplus
extern "C" {
#endif

typedef struct ls_mpscq_s  ls_mpscq_t;
typedef struct ls_lfqueue_s  ls_lfqueue_t;


/**
 * @ls_mpscq_new
 * @brief Creates a new multi-producer single-consumer (mpsc)
 *  lockless queue object.
 * @details The routine allocates and initializes an object
 *  to manage a node-based fifo queue of objects without the use of locks.
 *
 * @param[in] pNode - A pointer to a user allocated empty node for processing.
 * @return A pointer to an initialized mpsc lockless queue object,
 *  else NULL on error.
 *
 * @see ls_mpscq_delete
 */
ls_mpscq_t *ls_mpscq_new(ls_lfnoden_t *pNode);

/**
 * @ls_mpscq_init
 * @brief Initializes a multi-producer single-consumer (mpsc)
 *  lockless queue object.
 *
 * @param[in] pThis - A pointer to an allocated mpsc lockless queue object.
 * @param[in] pNode - A pointer to a user allocated empty node for processing.
 * @return 0 on success.
 *
 * @see ls_mpscq_destroy
 */
int ls_mpscq_init(ls_mpscq_t *pThis, ls_lfnoden_t *pNode);

/**
 * @ls_mpscq_destroy
 * @brief Destroys an mpsc lockless queue object.
 *
 * @param[in] pThis - A pointer to an initialized mpsc lockless queue object.
 * @return Void.
 *
 * @see ls_mpscq_init
 */
void ls_mpscq_destroy(ls_mpscq_t *pThis);

/**
 * @ls_mpscq_delete
 * @brief Destroys then deletes an mpsc lockless queue object.
 * @details The object should have been created with a previous
 *   successful call to ls_mpscq_new.
 *
 * @param[in] pThis - A pointer to an initialized mpsc lockless queue object.
 * @return Void.
 *
 * @see ls_mpscq_new
 */
void ls_mpscq_delete(ls_mpscq_t *pThis);

/**
 * @ls_mpscq_put
 * @brief Put an object on an mpsc lockless queue.
 *
 * @param[in] pThis - A pointer to an initialized mpsc lockless queue object.
 * @param[in] data - A pointer to the user defined object to put on the queue.
 * @return 0 on success, else -1 on error.
 */
int ls_mpscq_put(ls_mpscq_t *pThis, ls_lfnoden_t *data);

/**
 * @ls_mpscq_get
 * @brief Get an object from an mpsc lockless queue.
 *
 * @param[in] pThis - A pointer to an initialized mpsc lockless queue object.
 * @return a pointer to the object on success, else NULL on error.
 */
ls_lfnoden_t *ls_mpscq_get(ls_mpscq_t *pThis);

/**
 * @ls_mpscq_empty
 * @brief Checks if the mpsc lockless queue is empty.
 *
 * @param[in] pThis - A pointer to an initialized mpsc lockless queue object.
 * @return true if empty, else false if not.
 */
int ls_mpscq_empty(ls_mpscq_t *pThis);


/**
 * @ls_lfqueue_new
 * @brief Creates a new multi-producer multi-consumer (mpmc)
 *  lockless queue object.
 * @details The routine allocates and initializes an object
 *  to manage a node-based fifo queue of objects without the use of locks.
 *
 * @return A pointer to an initialized mpmc lockless queue object,
 *  else NULL on error.
 *
 * @see ls_lfqueue_delete
 */
ls_lfqueue_t *ls_lfqueue_new();

/**
 * @ls_lfqueue_init
 * @brief Initializes a multi-producer multi-consumer (mpmc)
 *  lockless queue object.
 *
 * @param[in] pThis - A pointer to an allocated mpmc lockless queue object.
 * @return 0 on success.
 *
 * @see ls_lfqueue_destroy
 */
int ls_lfqueue_init(ls_lfqueue_t *pThis);

/**
 * @ls_lfqueue_destroy
 * @brief Destroys an mpmc lockless queue object.
 *
 * @param[in] pThis - A pointer to an initialized mpmc lockless queue object.
 * @return Void.
 *
 * @see ls_lfqueue_init
 */
void ls_lfqueue_destroy(ls_lfqueue_t *pThis);

/**
 * @ls_lfqueue_delete
 * @brief Destroys then deletes an mpmc lockless queue object.
 * @details The object should have been created with a previous
 *   successful call to ls_lfqueue_new.
 *
 * @param[in] pThis - A pointer to an initialized mpmc lockless queue object.
 * @return Void.
 *
 * @see ls_lfqueue_new
 */
void ls_lfqueue_delete(ls_lfqueue_t *pThis);

/**
 * @ls_lfqueue_put
 * @brief Put a node on an mpmc lockless queue.
 *
 * @param[in] pThis - A pointer to an initialized mpmc lockless queue object.
 * @param[in] data - A pointer to the node to put on the queue.
 * @return 0 on success, else -1 on error.
 */
int ls_lfqueue_put(ls_lfqueue_t *pThis, ls_lfnodei_t *data);

/**
 * @ls_lfqueue_putn
 * @brief Put a linked list of nodes on an mpmc lockless queue.
 *
 * @param[in] pThis - A pointer to an initialized mpmc lockless queue object.
 * @param[in] data1 - A pointer to the first node to put on the queue.
 * @param[in] datan - A pointer to the last node to put on the queue.
 * @return 0 on success, else -1 on error.
 */
int ls_lfqueue_putn(ls_lfqueue_t *pThis, ls_lfnodei_t *data1,
                    ls_lfnodei_t *datan);

/**
 * @ls_lfqueue_get
 * @brief Get a node from an mpmc lockless queue.
 *
 * @param[in] pThis - A pointer to an initialized mpmc lockless queue object.
 * @return a pointer to the node on success, else NULL on error.
 */
ls_lfnodei_t *ls_lfqueue_get(ls_lfqueue_t *pThis);

/**
 * @ls_lfqueue_timedget
 * @brief Get a node from an mpmc lockless queue.
 *
 * @param[in] pThis - A pointer to an initialized mpmc lockless queue object.
 * @param[in] timeout - The duration of time before returning if data is not
 *  available from the queue; a NULL pointer specifies a blocking call.
 * @return a pointer to the object on success,
 *  else NULL on error including timeout.
 */
ls_lfnodei_t *ls_lfqueue_timedget(ls_lfqueue_t *pThis,
                                  struct timespec *timeout);

/**
 * @ls_lfqueue_empty
 * @brief Checks if the mpsc lockless queue is empty.
 *
 * @param[in] pThis - A pointer to an initialized mpmc lockless queue object.
 * @return true if empty, else false if not.
 */
int ls_lfqueue_empty(ls_lfqueue_t *pThis);


#ifdef __cplusplus
}
#endif

#endif //LS_LFQUEUE_H


