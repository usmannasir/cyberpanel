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
#ifndef LS_LINK_H
#define LS_LINK_H


#include <assert.h>
#include <stddef.h>
#include <string.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_types.h>


/**
 * @file
 */


#ifdef __cplusplus
extern "C" {
#endif

/**
 * @typedef ls_link_t
 */
typedef struct ls_link_s
{
    struct ls_link_s *next;
    void *pobj;
} ls_link_t;

/**
 * @typedef ls_dlink_t
 */
typedef struct ls_dlink_s
{
    struct ls_dlink_s *next;
    struct ls_dlink_s *prev;
    void *pobj;
} ls_dlink_t;


/**
 * @ls_link
 * @brief Initializes a singly linked list object.
 *
 * @param[in] pThis - A pointer to an allocated linked list object.
 * @param[in] next - A pointer to the next linked object, which could be NULL.
 * @return Void.
 *
 * @see ls_link_new, ls_link_d
 */
ls_inline void ls_link(ls_link_t *pThis, ls_link_t *next)
{   pThis->next = next;  pThis->pobj = NULL;  }

/**
 * @ls_link_new
 * @brief Creates (allocates and initializes)
 *   a new singly linked list object.
 *
 * @param[in] next - A pointer to the next linked object, which could be NULL.
 * @return A pointer to an initialized linked list object, else NULL on error.
 *
 * @see ls_link, ls_link_delete
 */
ls_inline ls_link_t *ls_link_new(ls_link_t *next)
{
    ls_link_t *pThis;
    if ((pThis = (ls_link_t *)
                 ls_palloc(sizeof(*pThis))) != NULL)
        ls_link(pThis, next);
    return pThis;
}

/**
 * @ls_link_d
 * @brief Destroys a singly linked list object.
 *
 * @param[in] pThis - A pointer to an initialized linked list object.
 * @return Void.
 *
 * @see ls_link
 */
ls_inline void ls_link_d(ls_link_t *pThis)
{}

/**
 * @ls_link_delete
 * @brief Destroys a singly linked list object, then deletes the object.
 * @details The object should have been created with a previous
 *   successful call to ls_link_new.
 *
 * @param[in] pThis - A pointer to an initialized linked list object.
 * @return Void.
 *
 * @see ls_link_new
 */
ls_inline void ls_link_delete(ls_link_t *pThis)
{   ls_link_d(pThis);  ls_pfree(pThis);   }

/**
 * @ls_link_getobj
 * @brief Gets the object referenced by a singly linked list object.
 *
 * @param[in] pThis - A pointer to an initialized linked list object.
 * @return A pointer to the object referenced by the link object.
 */
ls_inline void *ls_link_getobj(const ls_link_t *pThis)
{   return pThis->pobj;  }

/**
 * @ls_link_setobj
 * @brief Sets the object referenced by a singly linked list object.
 *
 * @param[in] pThis - A pointer to an initialized linked list object.
 * @param[in] pObj - A pointer to the object to be referenced.
 * @return Void.
 */
ls_inline void ls_link_setobj(ls_link_t *pThis, void *pObj)
{   pThis->pobj = pObj;  }

/**
 * @ls_link_next
 * @brief Gets the next object in a singly linked list relative to pThis.
 *
 * @param[in] pThis - A pointer to an initialized linked list object.
 * @return A pointer to the next object in the list.
 *
 * @see ls_link_setnext
 */
ls_inline ls_link_t *ls_link_next(const ls_link_t *pThis)
{   return pThis->next;  }

/**
 * @ls_link_setnext
 * @brief Sets the next link object in a singly linked list relative to pThis.
 *
 * @param[in] pThis - A pointer to an initialized linked list object.
 * @param[in] pNext - A pointer to the object to set as \e next.
 * @return Void.
 *
 * @see ls_link_next
 */
ls_inline void ls_link_setnext(ls_link_t *pThis, ls_link_t *pNext)
{   pThis->next = pNext;  }

/**
 * @ls_link_addnext
 * @brief Adds the next object to a singly linked list relative to pThis.
 *
 * @param[in] pThis - A pointer to an initialized linked list object.
 * @param[in] pNext - A pointer to the object to add.
 * @return Void.
 *
 * @see ls_link_removenext
 */
ls_inline void ls_link_addnext(ls_link_t *pThis, ls_link_t *pNext)
{
    ls_link_t *pTemp = pThis->next;
    ls_link_setnext(pThis, pNext);
    ls_link_setnext(pNext, pTemp);
}

/**
 * @ls_link_removenext
 * @brief Removes the \e next object from a singly linked list relative to pThis.
 *
 * @param[in] pThis - A pointer to an initialized linked list object.
 * @return A pointer to the object removed (could be NULL).
 *
 * @see ls_link_addnext
 */
ls_inline ls_link_t *ls_link_removenext(ls_link_t *pThis)
{
    ls_link_t *pNext = pThis->next;
    if (pNext)
    {
        ls_link_setnext(pThis, pNext->next);
        ls_link_setnext(pNext, NULL);
    }
    return pNext;
}


/**
 * @ls_dlink
 * @brief Initializes a doubly linked list object.
 *
 * @param[in] pThis - A pointer to an allocated doubly linked list object.
 * @param[in] prev - A pointer to the previous linked object, which could be NULL.
 * @param[in] next - A pointer to the next linked object, which could be NULL.
 * @return Void.
 *
 * @see ls_dlink_new, ls_dlink_d
 */
ls_inline void ls_dlink(
    ls_dlink_t *pThis, ls_dlink_t *prev, ls_dlink_t *next)
{
    pThis->next = next;
    pThis->prev = prev;
    pThis->pobj = NULL;
}

/**
 * @ls_dlink_new
 * @brief Creates (allocates and initializes)
 *   a new doubly linked list object.
 *
 * @param[in] prev - A pointer to the previous linked object, which could be NULL.
 * @param[in] next - A pointer to the next linked object, which could be NULL.
 * @return A pointer to an initialized linked list object, else NULL on error.
 *
 * @see ls_dlink, ls_dlink_delete
 */
ls_inline ls_dlink_t *ls_dlink_new(ls_dlink_t *prev, ls_dlink_t *next)
{
    ls_dlink_t *pThis;
    if ((pThis = (ls_dlink_t *)
                 ls_palloc(sizeof(*pThis))) != NULL)
        ls_dlink(pThis, prev, next);
    return pThis;
}

/**
 * @ls_dlink_d
 * @brief Destroys a doubly linked list object.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list object.
 * @return Void.
 *
 * @see ls_dlink
 */
ls_inline void ls_dlink_d(ls_dlink_t *pThis)
{}

/**
 * @ls_dlink_delete
 * @brief Destroys a doubly linked list object, then deletes the object.
 * @details The object should have been created with a previous
 *   successful call to ls_dlink_new.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list object.
 * @return Void.
 *
 * @see ls_dlink_new
 */
ls_inline void ls_dlink_delete(ls_dlink_t *pThis)
{   ls_dlink_d(pThis);  ls_pfree(pThis);   }

/**
 * @ls_dlink_getobj
 * @brief Gets the object referenced by a doubly linked list object.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list object.
 * @return A pointer to the object referenced by the link object.
 */
ls_inline void *ls_dlink_getobj(const ls_dlink_t *pThis)
{   return pThis->pobj;  }

/**
 * @ls_dlink_setobj
 * @brief Sets the object referenced by a doubly linked list object.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list object.
 * @param[in] pObj - A pointer to the object to be referenced.
 * @return Void.
 */
ls_inline void ls_dlink_setobj(ls_dlink_t *pThis, void *pObj)
{   pThis->pobj = pObj;  }

/**
 * @ls_dlink_prev
 * @brief Gets the previous object in a doubly linked list relative to pThis.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list object.
 * @return A pointer to the previous object in the list.
 *
 * @see ls_dlink_setprev
 */
ls_inline ls_dlink_t *ls_dlink_prev(const ls_dlink_t *pThis)
{   return pThis->prev;  }

/**
 * @ls_dlink_setprev
 * @brief Sets the previous object in a doubly linked list relative to pThis.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list object.
 * @param[in] pPrev - A pointer to the object to set as \e previous.
 * @return Void.
 *
 * @see ls_dlink_prev
 */
ls_inline void ls_dlink_setprev(ls_dlink_t *pThis, ls_dlink_t *pPrev)
{   pThis->prev = pPrev;  }

/**
 * @ls_dlink_next
 * @brief Gets the next object in a doubly linked list relative to pThis.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list object.
 * @return A pointer to the next object in the list.
 *
 * @see ls_dlink_setnext
 */
ls_inline ls_dlink_t *ls_dlink_next(const ls_dlink_t *pThis)
{   return pThis->next;  }

/**
 * @ls_dlink_setnext
 * @brief Sets the next object in a doubly linked list relative to pThis.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list object.
 * @param[in] pNext - A pointer to the object to set as \e next.
 * @return Void.
 *
 * @see ls_dlink_next
 */
ls_inline void ls_dlink_setnext(ls_dlink_t *pThis, ls_dlink_t *pNext)
{   pThis->next = pNext;  }

/**
 * @ls_dlink_addnext
 * @brief Adds the \e next object to a doubly linked list relative to pThis.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list object.
 * @param[in] pNext - A pointer to the object to add.
 * @return Void.
 *
 * @see ls_dlink_removenext
 */
ls_inline void ls_dlink_addnext(ls_dlink_t *pThis, ls_dlink_t *pNext)
{
    assert(pNext);
    ls_dlink_t *pTemp = ls_dlink_next(pThis);
    ls_dlink_setnext(pThis, pNext);
    ls_dlink_setnext(pNext, pTemp);
    pNext->prev = pThis;
    if (pTemp)
        pTemp->prev = pNext;
}

/**
 * @ls_dlink_removenext
 * @brief Removes the \e next object from a doubly linked list relative to pThis.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list object.
 * @return A pointer to the object removed (could be NULL).
 *
 * @see ls_dlink_addnext
 */
ls_inline ls_dlink_t *ls_dlink_removenext(ls_dlink_t *pThis)
{
    ls_dlink_t *pTemp;
    ls_dlink_t *pNext = ls_dlink_next(pThis);
    if (pNext)
    {
        pTemp = ls_dlink_next(pNext);
        ls_dlink_setnext(pThis, pTemp);
        if (pTemp)
            pTemp->prev = pThis;
        memset(pNext, 0, sizeof(ls_dlink_t));
    }
    return pNext;
}

/**
 * @ls_dlink_addprev
 * @brief Adds the \e previous object to a doubly linked list relative to pThis.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list object.
 * @param[in] pPrev - A pointer to the object to add.
 * @return Void.
 *
 * @see ls_dlink_removeprev
 */
ls_inline void ls_dlink_addprev(ls_dlink_t *pThis, ls_dlink_t *pPrev)
{
    assert(pPrev);
    ls_dlink_t *pTemp;
    pTemp = pThis->prev;
    pThis->prev = pPrev;
    pPrev->prev = pTemp;
    ls_dlink_setnext(pPrev, pThis);
    if (pTemp)
        ls_dlink_setnext(pTemp, pPrev);
}

/**
 * @ls_dlink_removeprev
 * @brief Removes the \e previous object from a doubly linked list relative to pThis.
 *
 * @param[in] pThis - A pointer to an initialized doubly linked list object.
 * @return A pointer to the object removed (could be NULL).
 *
 * @see ls_dlink_addprev
 */
ls_inline ls_dlink_t *ls_dlink_removeprev(ls_dlink_t *pThis)
{
    ls_dlink_t *pPrev = pThis->prev;
    if (pThis->prev)
    {
        pThis->prev = pPrev->prev;
        if (pThis->prev)
            ls_dlink_setnext(pThis->prev, pThis);
        memset(pPrev, 0, sizeof(ls_dlink_t));
    }
    return pPrev;
}

/**
 * @ls_dlink_remove
 * @brief Removes an object from a doubly linked list.
 *
 * @param[in] pThis - A pointer to the initialized doubly linked list object
 *   to remove.
 * @return A pointer to the \e next object in the list (could be NULL).
 *
 * @see ls_dlink_removenext, ls_dlink_removeprev
 */
ls_inline ls_dlink_t *ls_dlink_remove(ls_dlink_t *pThis)
{
    ls_dlink_t *pNext = ls_dlink_next(pThis);
    if (pNext)
        pNext->prev = pThis->prev;
    if (pThis->prev)
        ls_dlink_setnext(pThis->prev, ls_dlink_next(pThis));
    memset(pThis, 0, sizeof(ls_dlink_t));
    return pNext;
}


#ifdef __cplusplus
}
#endif

#endif  /* LS_LINK_H */

