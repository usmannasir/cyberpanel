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
#ifndef LS_DLINKQ_H
#define LS_DLINKQ_H


#include <stdbool.h>
#include <lsr/ls_link.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_types.h>


/**
 * @file
 * \warning ABANDONED... for now.
 */


#ifdef __cplusplus
extern "C" {
#endif

/**
 * @typedef ls_linkq_t
 */
typedef struct ls_linkq_s
{
    ls_link_t m_head;
    int m_iTotal;
} ls_linkq_t;

/**
 * @typedef ls_dlinkq_t
 */
typedef struct ls_dlinkq_s
{
    ls_dlink_t m_head;
    int m_iTotal;
} ls_dlinkq_t;


/**
 * @ls_linkq
 * @brief Initializes a queue of singly linked list objects.
 *
 * @param[in] pThis - A pointer to an allocated linked list queue object.
 * @return Void.
 *
 * @see ls_linkq_new, ls_linkq_d
 */
ls_inline void ls_linkq(ls_linkq_t *pThis)
{
    ls_link(&pThis->m_head, NULL);
    pThis->m_iTotal = 0;
}

/**
 * @ls_linkq_new
 * @brief Creates (allocates and initializes)
 *   a new queue of singly linked list objects.
 *
 * @return A pointer to an initialized linked list queue object,
 *   else NULL on error.
 *
 * @see ls_linkq, ls_linkq_delete
 */
ls_inline ls_linkq_t *ls_linkq_new()
{
    ls_linkq_t *pThis;
    if ((pThis = (ls_linkq_t *)ls_palloc(sizeof(*pThis))) != NULL)
        ls_linkq(pThis);
    return pThis;
}

/**
 * @ls_linkq_d
 * @brief Destroys the singly linked list <b> queue object</b>.
 * @note It is the user's responsibility to destroy or delete
 *   the linked list objects, depending on how the objects were created.
 *
 * @param[in] pThis - A pointer to an initialized linked list queue object.
 * @return Void.
 *
 * @see ls_linkq
 */
ls_inline void ls_linkq_d(ls_linkq_t *pThis)
{}

/**
 * @ls_linkq_delete
 * @brief Destroys the singly linked list <b> queue object</b>,
 *   then deletes the object.
 * @details The object should have been created with a previous
 *   successful call to ls_linkq_new.
 * @note It is the user's responsibility to destroy or delete
 *   the linked list objects, depending on how the objects were created.
 *
 * @param[in] pThis - A pointer to an initialized linked list queue object.
 * @return Void.
 *
 * @see ls_linkq_new
 */
ls_inline void ls_linkq_delete(ls_linkq_t *pThis)
{   ls_linkq_d(pThis);  ls_pfree(pThis);   }

/**
 * @ls_linkq_size
 * @brief Gets the size of a singly linked list queue object.
 *
 * @param[in] pThis - A pointer to an initialized linked list queue object.
 * @return The size in terms of number of elements.
 */
ls_inline int ls_linkq_size(const ls_linkq_t *pThis)
{   return pThis->m_iTotal;  }

/**
 * @ls_linkq_push
 * @brief Pushes an element to a linked list queue object.
 *
 * @param[in] pThis - A pointer to an initialized linked list queue object.
 * @param[in] pObj - A pointer to a singly linked list object.
 * @return Void.
 */
ls_inline void ls_linkq_push(ls_linkq_t *pThis,  ls_link_t *pObj)
{   ls_link_addnext(&pThis->m_head, pObj);  ++pThis->m_iTotal;  }

/**
 * @ls_linkq_pop
 * @brief Pops an element from a linked list queue object.
 *
 * @param[in] pThis - A pointer to an initialized linked list queue object.
 * @return A pointer to the linked list object if the queue is not empty,
 *   else NULL.
 */
ls_inline ls_link_t *ls_linkq_pop(ls_linkq_t *pThis)
{
    if (pThis->m_iTotal != 0)
    {
        --pThis->m_iTotal;
        return ls_link_removenext(&pThis->m_head);
    }
    return NULL;
}

/**
 * @ls_linkq_begin
 * @brief Gets a pointer to the linked list object at the head (beginning)
 *   of a linked list queue object.
 * @details The routine does \e not pop anything from the object.
 *
 * @param[in] pThis - A pointer to an initialized linked list queue object.
 * @return A pointer to the linked list object at the beginning of the queue.
 */
ls_inline ls_link_t *ls_linkq_begin(const ls_linkq_t *pThis)
{   return ls_link_next(&pThis->m_head);  }

/**
 * @ls_linkq_end
 * @brief Gets the end of a linked list queue object.
 *
 * @param[in] pThis - A pointer to an initialized linked list queue object.
 * @return A pointer to the end of the queue (NULL).
 */
ls_inline ls_link_t *ls_linkq_end(const ls_linkq_t *pThis)
{   return NULL;  }

/**
 * @ls_linkq_head
 * @brief Gets the head of a linked list queue object.
 *
 * @param[in] pThis - A pointer to an initialized linked list queue object.
 * @return A pointer to the head of the queue.
 */
ls_inline ls_link_t *ls_linkq_head(ls_linkq_t *pThis)
{   return &pThis->m_head;  }

/**
 * @ls_linkq_removenext
 * @brief Removes a linked list element from a linked list queue object.
 *
 * @param[in] pThis - A pointer to an initialized linked list queue object.
 * @param[in] pObj - A pointer to a linked list object
 *   whose \e next is to be removed.
 * @return A pointer to the removed linked list object.
 * @warning It is expected that the queue object is \e not empty.
 */
ls_inline ls_link_t *ls_linkq_removenext(
    ls_linkq_t *pThis, ls_link_t *pObj)
{    --pThis->m_iTotal;  return ls_link_removenext(pObj);  }

/**
 * @ls_linkq_addnext
 * @brief Adds a linked list element to a linked list queue object.
 *
 * @param[in] pThis - A pointer to an initialized linked list queue object.
 * @param[in] pObj - A pointer to a linked list object
 *   where the new element is to be added.
 * @param[in] pNext - A pointer to the singly linked list object to add.
 * @return Void.
 */
ls_inline void ls_linkq_addnext(
    ls_linkq_t *pThis, ls_link_t *pObj, ls_link_t *pNext)
{   ++pThis->m_iTotal;  ls_link_addnext(pObj, pNext);  }

/**
 * @ls_dlinkq
 * @brief Initializes a queue of doubly linked list objects.
 *
 * @param[in] pThis - A pointer to an allocated doubly linked list queue object.
 * @return Void.
 *
 * @see ls_dlinkq_new, ls_dlinkq_d
 */
ls_inline void ls_dlinkq(ls_dlinkq_t *pThis)
{
    ls_dlink(&pThis->m_head, &pThis->m_head, &pThis->m_head);
    pThis->m_iTotal = 0;
}

/**
 * @ls_dlinkq_new
 * @brief Creates (allocates and initializes)
 *   a new queue of doubly linked list objects.
 *
 * @return A pointer to an initialized linked list queue object,
 *   else NULL on error.
 *
 * @see ls_dlinkq, ls_dlinkq_delete
 */
ls_inline ls_dlinkq_t *ls_dlinkq_new()
{
    ls_dlinkq_t *pThis;
    if ((pThis = (ls_dlinkq_t *)ls_palloc(sizeof(*pThis))) != NULL)
        ls_dlinkq(pThis);
    return pThis;
}

/**
 * @ls_dlinkq_d
 * @brief Destroys the doubly linked list <b> queue object</b>.
 * @note It is the user's responsibility to destroy or delete
 *   the linked list objects, depending on how the objects were created.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list queue
 *   object.
 * @return Void.
 *
 * @see ls_dlinkq
 */
ls_inline void ls_dlinkq_d(ls_dlinkq_t *pThis)
{}

/**
 * @ls_dlinkq_delete
 * @brief Destroys the doubly linked list <b> queue object</b>,
 *   then deletes the object.
 * @details The object should have been created with a previous
 *   successful call to ls_dlinkq_new.
 * @note It is the user's responsibility to destroy or delete
 *   the linked list objects, depending on how the objects were created.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list queue
 *   object.
 * @return Void.
 *
 * @see ls_dlinkq_new
 */
ls_inline void ls_dlinkq_delete(ls_dlinkq_t *pThis)
{   ls_dlinkq_d(pThis);  ls_pfree(pThis);   }

/**
 * @ls_dlinkq_size
 * @brief Gets the size of a doubly linked list queue object.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list queue
 *   object.
 * @return The size in terms of number of elements.
 */
ls_inline int ls_dlinkq_size(const ls_dlinkq_t *pThis)
{   return pThis->m_iTotal;  }

/**
 * @ls_dlinkq_empty
 * @brief Specifies whether or not a doubly linked list queue object
 *   contains any elements.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list queue
 *   object.
 * @return True if empty, else false.
 */
ls_inline bool ls_dlinkq_empty(const ls_dlinkq_t *pThis)
{   return ls_dlink_next(&pThis->m_head) == &pThis->m_head;  }

/**
 * @ls_dlinkq_append
 * @brief Pushes an element to the end of a doubly linked list queue object.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list queue
 *   object.
 * @param[in] pReq - A pointer to the linked list object to append.
 * @return Void.
 */
ls_inline void ls_dlinkq_append(ls_dlinkq_t *pThis, ls_dlink_t *pReq)
{
    ls_dlink_addnext(ls_dlink_prev(&pThis->m_head), pReq);
    ++pThis->m_iTotal;
}

/**
 * @ls_dlinkq_pushfront
 * @brief Pushes an element to the beginning (front)
 *   of a doubly linked list queue object.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list queue object.
 * @param[in] pReq - A pointer to the linked list object to add.
 * @return Void.
 */
ls_inline void ls_dlinkq_pushfront(ls_dlinkq_t *pThis, ls_dlink_t *pReq)
{
    ls_dlink_addprev(ls_dlink_next(&pThis->m_head), pReq);
    ++pThis->m_iTotal;
}

/**
 * @ls_dlinkq_remove
 * @brief Removes a linked list element from a doubly linked list queue object.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list queue
 *   object.
 * @param[in] pReq - A pointer to the linked list object to remove.
 * @return Void.
 */
ls_inline void ls_dlinkq_remove(ls_dlinkq_t *pThis, ls_dlink_t *pReq)
{
    assert(pReq != &pThis->m_head);
    if (ls_dlink_next(pReq) != NULL)
    {
        ls_dlink_remove(pReq);
        --pThis->m_iTotal;
    }
}

/**
 * @ls_dlinkq_popfront
 * @brief Pops an element from the beginning (front)
 *   of a doubly linked list queue object.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list queue
 *   object.
 * @return A pointer to the linked list object if the queue is not empty,
 *   else NULL.
 */
ls_inline ls_dlink_t *ls_dlinkq_popfront(ls_dlinkq_t *pThis)
{
    if (ls_dlink_next(&pThis->m_head) != &pThis->m_head)
    {
        --pThis->m_iTotal;
        return ls_dlink_removenext(&pThis->m_head);
    }
    assert(pThis->m_iTotal == 0);
    return NULL;
}

/**
 * @ls_dlinkq_begin
 * @brief Gets a pointer to the linked list object at the head (beginning)
 *   of a doubly linked list queue object.
 * @details The routine does \e not pop anything from the object.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list queue
 *   object.
 * @return A pointer to the linked list object at the beginning of the queue.
 */
ls_inline ls_dlink_t *ls_dlinkq_begin(ls_dlinkq_t *pThis)
{   return ls_dlink_next(&pThis->m_head);  }

/**
 * @ls_dlinkq_end
 * @brief Gets the end of a doubly linked list queue object.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list queue
 *   object.
 * @return A pointer to the end of the queue.
 */
ls_inline ls_dlink_t *ls_dlinkq_end(ls_dlinkq_t *pThis)
{   return &pThis->m_head;  }


#ifdef __cplusplus
}
#endif

#endif  /* LS_DLINKQ_H */

