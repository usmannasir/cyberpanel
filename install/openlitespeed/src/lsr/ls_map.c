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


#include <lsdef.h>
#include <lsr/ls_map.h>
#include <lsr/ls_internal.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_xpool.h>

#include <stdio.h>


const void *ls_map_getnodekey(ls_map_iter node)
{    return node->pkey;    }


void *ls_map_getnodeval(ls_map_iter node)
{    return node->pvalue;  }


static ls_map_iter ls_map_get_grandparent(ls_map_iter node);
static ls_map_iter ls_map_get_uncle(ls_map_iter node);
static void ls_map_rotate_left(ls_map_t *pThis, ls_map_iter node);
static void ls_map_rotate_right(ls_map_t *pThis, ls_map_iter node);
static void ls_map_fix_tree(ls_map_t *pThis, ls_map_iter node);
static int ls_map_insertnode(ls_map_t *pThis, ls_map_iter node);
static ls_map_iter ls_map_remove_end_node(ls_map_t *pThis,
        ls_map_iter node,
        char nullify);
static ls_map_iter ls_map_remove_node_from_tree(ls_map_t *pThis,
        ls_map_iter node);


ls_inline void *ls_map_do_alloc(ls_xpool_t *pool, size_t size)
{
    return ((pool != NULL) ? ls_xpool_alloc(pool, size) : ls_palloc(size));
}


ls_inline void ls_map_do_free(ls_xpool_t *pool, void *ptr)
{
    if (pool != NULL)
        ls_xpool_free(pool, ptr);
    else
        ls_pfree(ptr);
    return;
}


ls_map_t *ls_map_new(ls_map_value_compare vc, ls_xpool_t *pool)
{
    ls_map_t *pThis;
    pThis = (ls_map_t *)ls_map_do_alloc(pool, sizeof(ls_map_t));
    if (pThis == NULL)
        return NULL;
    if (ls_map(pThis, vc, pool) == NULL)
    {
        ls_map_do_free(pool, pThis);
        return NULL;
    }
    return pThis;
}


ls_map_t *ls_map(ls_map_t *pThis, ls_map_value_compare vc,
                 ls_xpool_t *pool)
{
    pThis->sizenow = 0;
    pThis->root = NULL;
    pThis->detached = NULL;
    pThis->vc_fn = vc;
    pThis->xpool = pool;
    pThis->insert_fn = ls_map_insert;
    pThis->update_fn = ls_map_update;
    pThis->find_fn = ls_map_find;

    assert(pThis->vc_fn);
    return pThis;
}


void ls_map_d(ls_map_t *pThis)
{
    ls_map_clear(pThis);
    memset(pThis, 0, sizeof(ls_map_t));
}


void ls_map_delete(ls_map_t *pThis)
{
    ls_map_clear(pThis);
    ls_map_do_free(pThis->xpool, pThis);
}


void ls_map_clear(ls_map_t *pThis)
{
    ls_map_releasenodes(pThis, pThis->root);
    ls_map_releasenodes(pThis, pThis->detached);
    pThis->root = NULL;
    pThis->sizenow = 0;
}


void ls_map_releasenodes(ls_map_t *pThis, ls_map_iter node)
{
    if (node == NULL)
        return;
    if (node->left != NULL)
        ls_map_releasenodes(pThis, node->left);
    if (node->right != NULL)
        ls_map_releasenodes(pThis, node->right);
    ls_map_do_free(pThis->xpool, node);
}


void ls_map_swap(ls_map_t *lhs, ls_map_t *rhs)
{
    char temp[ sizeof(ls_map_t) ];
    assert(lhs != NULL && rhs != NULL);
    memmove(temp, lhs, sizeof(ls_map_t));
    memmove(lhs, rhs, sizeof(ls_map_t));
    memmove(rhs, temp, sizeof(ls_map_t));
}


void *ls_map_detachnode(ls_map_t *pThis, ls_map_iter node)
{
    void *pVal;
    ls_map_iter ptr;
    if (node == NULL)
        return NULL;
    pVal = node->pvalue;
    ptr = ls_map_remove_node_from_tree(pThis, node);
    --(pThis->sizenow);
    ptr->pkey = NULL;
    ptr->pvalue = NULL;
    ptr->parent = NULL;
    ptr->right = NULL;
    ptr->left = pThis->detached;
    pThis->detached = ptr;
    return pVal;
}


int ls_map_attachnode(ls_map_t *pThis, const void *pKey, void *pVal)
{
    ls_mapnode_t *node = pThis->detached;
    if (node == NULL)
        return LS_FAIL;
    pThis->detached = pThis->detached->left;
    node->pkey = pKey;
    node->pvalue = pVal;
    node->left = NULL;
    node->right = NULL;
    node->parent = NULL;
    return ls_map_insertnode(pThis, node);
}


void *ls_map_deletenode(ls_map_t *pThis, ls_map_iter node)
{
    void *val;
    ls_map_iter ptr;
    if (node == NULL)
        return NULL;
    val = node->pvalue;
    ptr = ls_map_remove_node_from_tree(pThis, node);
    --(pThis->sizenow);
    ls_map_do_free(pThis->xpool, ptr);
    return val;
}


ls_map_iter ls_map_begin(ls_map_t *pThis)
{
    ls_map_iter ptr = pThis->root;
    while (ptr->left != NULL)
        ptr = ptr->left;
    return ptr;
}


ls_map_iter ls_map_end(ls_map_t *pThis)
{
    ls_map_iter ptr = pThis->root;
    while (ptr->right != NULL)
        ptr = ptr->right;
    return ptr;
}


ls_map_iter ls_map_next(ls_map_t *pThis, ls_map_iter node)
{
    ls_map_iter pUp;
    if (node == NULL)
        return NULL;
    if (node->right == NULL)
    {
        if (node->parent != NULL)
        {
            if (pThis->vc_fn(node->pkey, node->parent->pkey) > 0)
            {
                pUp = node->parent;
                while (pUp->parent != NULL
                       && pThis->vc_fn(pUp->pkey, pUp->parent->pkey) > 0)
                    pUp = pUp->parent;
                if (pUp->parent == NULL)
                    return NULL;
                return pUp->parent;
            }
            else
                return node->parent;
        }
        else
            return NULL;
    }

    node = node->right;
    while (node->left != NULL)
        node = node->left;
    return node;
}


int ls_map_foreach(ls_map_t *pThis, ls_map_iter beg, ls_map_iter end,
                   ls_map_foreach_fn fun)
{
    int iCount = 0;
    ls_map_iter iterNext = beg;
    ls_map_iter iter;

    if (fun == NULL)
    {
        errno = EINVAL;
        return LS_FAIL;
    }
    if (beg == NULL)
        return 0;

    if (end == NULL)
        return 0;

    while ((iterNext != NULL)
           && (pThis->vc_fn(iterNext->pkey, end->pkey) <= 0))
    {
        iter = iterNext;
        iterNext = ls_map_next(pThis, iterNext);
        if (fun(iter->pkey, iter->pvalue) != LS_OK)
            break;
        ++iCount;
    }
    return iCount;
}


int ls_map_foreach2(ls_map_t *pThis, ls_map_iter beg,
                    ls_map_iter end, ls_map_foreach2_fn fun, void *pUData)
{
    int iCount = 0;
    ls_map_iter iterNext = beg;
    ls_map_iter iter;

    if (fun == NULL)
    {
        errno = EINVAL;
        return LS_FAIL;
    }
    if (beg == NULL)
        return 0;

    if (end == NULL)
        return 0;

    while ((iterNext != NULL)
           && (pThis->vc_fn(iterNext->pkey, end->pkey) <= 0))
    {
        iter = iterNext;
        iterNext = ls_map_next(pThis, iterNext);
        if (fun(iter->pkey, iter->pvalue, pUData) != LS_OK)
            break;
        ++iCount;
    }
    return iCount;
}


int ls_map_insert(ls_map_t *pThis, const void *pKey, void *pValue)
{
    ls_map_iter pNode;
    pNode = (ls_map_iter)ls_map_do_alloc(pThis->xpool, sizeof(ls_mapnode_t));
    if (pNode == NULL)
        return LS_FAIL;

    pNode->pkey = pKey;
    pNode->pvalue = pValue;
    pNode->left = NULL;
    pNode->right = NULL;
    pNode->parent = NULL;
    if (ls_map_insertnode(pThis, pNode) == LS_FAIL)
    {
        ls_map_do_free(pThis->xpool, pNode);
        return LS_FAIL;
    }
    return LS_OK;
}


ls_map_iter ls_map_find(ls_map_t *pThis, const void *pKey)
{
    ls_map_iter ptr = pThis->root;
    int iComp;
    if (pThis == NULL)
        return NULL;
    if (pThis->vc_fn == NULL)
        return NULL;
    while (ptr != NULL && (iComp = pThis->vc_fn(ptr->pkey, pKey)) != 0)
        ptr = (iComp > 0 ? ptr->left : ptr->right);
    return ptr;
}


void *ls_map_update(ls_map_t *pThis, const void *pKey, void *pValue,
                    ls_map_iter node)
{
    void *pOldValue;
    if (node != NULL)
    {
        if (pThis->vc_fn(node->pkey, pKey) != 0)
            return NULL;
    }
    else if ((node = ls_map_find(pThis, pKey)) == NULL)
        return NULL;

    node->pkey = pKey;
    pOldValue = node->pvalue;
    node->pvalue = pValue;
    return pOldValue;
}


// Internal Functions

static ls_map_iter ls_map_get_grandparent(ls_map_iter node)
{
    if (node != NULL && node->parent != NULL)
        return node->parent->parent;
    return NULL;
}


static ls_map_iter ls_map_get_uncle(ls_map_iter node)
{
    ls_map_iter pGrandparent = ls_map_get_grandparent(node);
    if (pGrandparent == NULL)
        return NULL;
    if (node->parent == pGrandparent->left)
        return pGrandparent->right;
    return pGrandparent->left;
}


static void ls_map_rotate_left(ls_map_t *pThis, ls_map_iter node)
{
    ls_map_iter pSwap = node->right;
    node->right = pSwap->left;
    if (pSwap->left != NULL)
        pSwap->left->parent = node;

    pSwap->parent = node->parent;
    if (node->parent == NULL)
        pThis->root = pSwap;
    else if (node == node->parent->left)
        node->parent->left = pSwap;
    else
        node->parent->right = pSwap;

    pSwap->left = node;
    node->parent = pSwap;
}


static void ls_map_rotate_right(ls_map_t *pThis, ls_map_iter node)
{
    ls_map_iter pSwap = node->left;
    node->left = pSwap->right;
    if (pSwap->right != NULL)
        pSwap->right->parent = node;

    pSwap->parent = node->parent;
    if (node->parent == NULL)
        pThis->root = pSwap;
    else if (node == node->parent->left)
        node->parent->left = pSwap;
    else
        node->parent->right = pSwap;

    pSwap->right = node;
    node->parent = pSwap;
}


static void ls_map_fix_tree(ls_map_t *pThis, ls_map_iter node)
{
    ls_map_iter pGrandparent, pUncle;
    if (node->parent == NULL)
    {
        node->color = BLACK;
        return;
    }
    else if (node->parent->color == BLACK)
        return;
    else if (((pUncle = ls_map_get_uncle(node)) != NULL)
             && (pUncle->color == RED))
    {
        node->parent->color = BLACK;
        pUncle->color = BLACK;
        pGrandparent = ls_map_get_grandparent(node);
        pGrandparent->color = RED;
        ls_map_fix_tree(pThis, pGrandparent);
    }
    else
    {
        pGrandparent = ls_map_get_grandparent(node);
        if ((node == node->parent->right)
            && (node->parent == pGrandparent->left))
        {
            ls_map_rotate_left(pThis, node->parent);
            node = node->left;
        }
        else if ((node == node->parent->left)
                 && (node->parent == pGrandparent->right))
        {
            ls_map_rotate_right(pThis, node->parent);
            node = node->right;
        }
        pGrandparent = ls_map_get_grandparent(node);
        node->parent->color = BLACK;
        pGrandparent->color = RED;

        if (node == node->parent->left)
            ls_map_rotate_right(pThis, pGrandparent);
        else
            ls_map_rotate_left(pThis, pGrandparent);
    }
}


static int ls_map_insert_into_tree(ls_map_iter pCurrent, ls_map_iter pNew,
                                   ls_map_value_compare vc)
{
    int iComp = vc(pCurrent->pkey, pNew->pkey);
    if (iComp < 0)
        if (pCurrent->right == NULL)
        {
            pCurrent->right = pNew;
            pNew->parent = pCurrent;
            return LS_OK;
        }
        else
            return ls_map_insert_into_tree(pCurrent->right, pNew, vc);
    else if (iComp > 0)
        if (pCurrent->left == NULL)
        {
            pCurrent->left = pNew;
            pNew->parent = pCurrent;
            return LS_OK;
        }
        else
            return ls_map_insert_into_tree(pCurrent->left, pNew, vc);
    else
        return LS_FAIL;
}


static int ls_map_insertnode(ls_map_t *pThis, ls_map_iter node)
{
    if (pThis->root == NULL)
    {
        node->color = BLACK;
        pThis->root = node;
        ++pThis->sizenow;
        return LS_OK;
    }

    node->color = RED;
    if (ls_map_insert_into_tree(pThis->root, node, pThis->vc_fn) != LS_OK)
        return LS_FAIL;

    ls_map_fix_tree(pThis, node);
    pThis->root->color = BLACK;
    ++pThis->sizenow;
    return LS_OK;
}


static ls_map_iter ls_map_remove_end_node(ls_map_t *pThis,
        ls_map_iter node,
        char nullify)
{
    ls_map_iter pSibling, pParent = node->parent;
    if (pParent == NULL)
    {
        if (nullify)
            pThis->root = NULL;
        return node;
    }

    /* A sibling must exist because there can't be two black nodes
     * in a row without two on the other side to balance it.
     */
    pSibling = (node == pParent->left ? pParent->right : pParent->left);

    if (pSibling->color == RED)
    {
        pParent->color = RED;
        pSibling->color = BLACK;
        if (node == pParent->left)
            ls_map_rotate_left(pThis, pParent);
        else
            ls_map_rotate_right(pThis, pParent);
        pSibling = (node == pParent->left ? pParent->right : pParent->left);
    }

    // From this point on, Sibling must be black.
    if (((pSibling->left == NULL) || (pSibling->left->color == BLACK))
        && ((pSibling->right == NULL) || (pSibling->right->color == BLACK)))
    {
        pSibling->color = RED;
        if (nullify == 1)
        {
            if (node == pParent->left)
                pParent->left = NULL;
            else
                pParent->right = NULL;
        }

        if (pParent->color == BLACK)
            ls_map_remove_end_node(pThis, pParent, 0);
        else
            pParent->color = BLACK;

        return node;
    }

    // From this point on, at least one of Sibling's children is red.
    if ((node == pParent->left)
        && (pSibling->left != NULL)
        && (pSibling->left->color == RED))
    {
        pSibling->color = RED;
        pSibling->left->color = BLACK;
        ls_map_rotate_right(pThis, pSibling);
    }
    else if ((node == pParent->right)
             && (pSibling->right != NULL)
             && (pSibling->right->color == RED))
    {
        pSibling->color = RED;
        pSibling->right->color = BLACK;
        ls_map_rotate_left(pThis, pSibling);
    }

    pSibling = (node == pParent->left ? pParent->right : pParent->left);

    /* From earlier, sibling must be black and we have two cases here:
     * - Node is Parent's left child and Sibling's right child is red.
     * - Node is Parent's right child and Sibling's left child is red.
     */

    pSibling->color = pParent->color;
    pParent->color = BLACK;

    if (node == pParent->left)
    {
        pSibling->right->color = BLACK;
        ls_map_rotate_left(pThis, pParent);
        if (nullify == 1)
            pParent->left = NULL;
    }
    else
    {
        pSibling->left->color = BLACK;
        ls_map_rotate_right(pThis, pParent);
        if (nullify == 1)
            pParent->right = NULL;
    }
    return node;
}


static ls_map_iter ls_map_remove_node_from_tree(ls_map_t *pThis,
        ls_map_iter node)
{
    ls_map_iter pPtrParent, pChild, ptr = node;
    //Replace with successor if there are 2 children.
    if (node->left != NULL && node->right != NULL)
    {
        pPtrParent = ptr;
        ptr = ptr->right;
        while (ptr->left != NULL)
        {
            pPtrParent = ptr;
            ptr = ptr->left;
        }
        node->pkey = ptr->pkey;
        node->pvalue = ptr->pvalue;
    }
    else
        pPtrParent = node->parent;

    //Now we want to delete Ptr from tree
    if (ptr->color == RED)
    {
        if (ptr == pPtrParent->left)
            pPtrParent->left = NULL;
        else
            pPtrParent->right = NULL;
        return ptr;
    }

    pChild = (ptr->left == NULL ? ptr->right : ptr->left);

    if ((pChild != NULL)
        && (pChild->color == RED))
    {
        if (pPtrParent == NULL)
            pThis->root = pChild;
        else if (ptr == pPtrParent->left)
            pPtrParent->left = pChild;
        else
            pPtrParent->right = pChild;

        pChild->parent = pPtrParent;
        pChild->color = BLACK;
        return ptr;
    }

    //At this point, we know ptr has no children, otherwise there will
    //be some invalid properties in the tree.
    return ls_map_remove_end_node(pThis, ptr, 1);
}


#ifdef LSR_MAP_DEBUG
void ls_map_print(ls_map_iter node, int layer)
{
    int iMyLayer = layer;
    const char *sColor, *sLColor, *sRColor;
    if (node == NULL)
        return;
    sColor = node->color == BLACK ? "B" : "R";
    if (node->left == NULL)
        sLColor = "";
    else
        sLColor = node->left->color == BLACK ? "B" : "R";

    if (node->right == NULL)
        sRColor = "";
    else
        sRColor = node->right->color == BLACK ? "B" : "R";

    printf("Layer: %d, %p%s [ left = %p%s; right = %p%s ]\n",
           iMyLayer, node, sColor, node->left, sLColor, node->right, sRColor);
    ls_map_print(node->left, ++layer);
    ls_map_print(node->right, layer);
}
#endif


