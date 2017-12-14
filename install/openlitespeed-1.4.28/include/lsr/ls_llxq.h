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
#ifndef LS_LLXQ_H
#define LS_LLXQ_H

#include <sys/time.h>


/**
 * @file
 */


#ifdef __cplusplus
extern "C" {
#endif

typedef struct ls_llxq_s    ls_llxq_t;

/**
 * @ls_llxq_new
 * @brief Creates a new lockless queue object.
 * @details The routine allocates and initializes an object
 *  to manage a queue of objects without the use of locks.
 *
 * @param[in] size - The size of the circular queue in terms of objects.
 * @return A pointer to an initialized lockless queue object,
 *  else NULL on error.
 * @note \e Size must be a power of 2.
 *
 * @see ls_llxq_delete
 */
ls_llxq_t *ls_llxq_new(unsigned int size);

/**
 * @ls_llxq_init
 * @brief Initializes a lockless queue object.
 *
 * @param[in] pThis - A pointer to an allocated lockless queue object.
 * @param[in] size - The size of the circular queue in terms of objects.
 * @return 0 on success.
 * @note \e Size must be a power of 2.
 *
 * @see ls_llxq_destroy
 */
int ls_llxq_init(ls_llxq_t *pThis, unsigned int size);

/**
 * @ls_llxq_destroy
 * @brief Destroys a lockless queue object.
 *
 * @param[in] pThis - A pointer to an initialized lockless queue object.
 * @return Void.
 *
 * @see ls_llxq_init
 */
void ls_llxq_destroy(ls_llxq_t *pThis);

/**
 * @ls_llxq_delete
 * @brief Destroys then deletes a lockless queue object.
 * @details The object should have been created with a previous
 *   successful call to ls_llxq_new.
 *
 * @param[in] pThis - A pointer to an initialized lockless queue object.
 * @return Void.
 *
 * @see ls_llxq_new
 */
void ls_llxq_delete(ls_llxq_t *pThis);

/**
 * @ls_llxq_newqueue
 * @brief Adds a new circular queue to a lockless queue object.
 * @details The new queue immediately becomes the one used for
 *   producers to \e put on, while previous queues continue to
 *   be consumed with \e get until they are sequentially emptied,
 *   and freed.
 *
 * @param[in] pThis - A pointer to an initialized lockless queue object.
 * @param[in] size - The size of the new circular queue in terms of objects.
 * @return 0 on success,
 *   1 if simultaneously another thread succeeded in adding a new queue
 *   (in which case this thread's request is not processed),
 *   else -1 on error including insufficient system memory or no space
 *   on the object's list of queues.
 * @note \e Size must be a power of 2.
 * @note There is a system defined number of queues that may be
 *   managed at any one time.
 *   Attempts which exceed this number result in failure until
 *   queues are consumed and freed.
 */
int ls_llxq_newqueue(ls_llxq_t *pThis, unsigned int size);

/**
 * @ls_llxq_put
 * @brief Put an object on a lockless queue.
 * @details If the current circular queue buffer is filled,
 *   a new one is created up to the system defined maximum.
 *
 * @param[in] pThis - A pointer to an initialized lockless queue object.
 * @param[in] data - A pointer to the user defined object to put on the queue.
 * @return 0 on success, else -1 on error.
 */
int ls_llxq_put(ls_llxq_t *pThis, void *data);

/**
 * @ls_llxq_timedput
 * @brief Put an object on a lockless queue.
 *
 * @param[in] pThis - A pointer to an initialized lockless queue object.
 * @param[in] data - A pointer to the user defined object to put on the queue.
 * @param[in] timeout - The duration of time before returning if unable
 *  to put on the queue; a NULL pointer specifies a blocking call.
 * @return 0 on success, else -1 on error including timeout.
 */
int ls_llxq_timedput(ls_llxq_t *pThis, void *data,
                     struct timespec *timeout);

/**
 * @ls_llxq_timedget
 * @brief Get an object from a lockless queue.
 *
 * @param[in] pThis - A pointer to an initialized lockless queue object.
 * @param[in] timeout - The duration of time before returning if data is not
 *  available from the queue; a NULL pointer specifies a blocking call.
 * @return a pointer to the object on success,
 *  else NULL on error including timeout.
 */
void *ls_llxq_timedget(ls_llxq_t *pThis, struct timespec *timeout);

#ifdef __cplusplus
}
#endif

#endif //LS_LLXQ_H

