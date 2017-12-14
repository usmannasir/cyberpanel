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
#include "radixtree.h"

#include <lsdef.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_str.h>
#include <util/ghash.h>

#include <assert.h>
#include <fnmatch.h>
#include <string.h>

#include <new>

#define RNSTATE_NOCHILD     0
#define RNSTATE_CNODE       1
#define RNSTATE_PNODE       2
#define RNSTATE_CARRAY      3
#define RNSTATE_PARRAY      4
#define RNSTATE_HASH        5
#define RN_USEHASHCNT      10
#define RN_HASHSZ         256
#define RNWC_ARRAYSTARTSZ   4

#define RTFLAG_PTR        (1 << 0) // This flag is for internal use only.

struct rnheader_s
{
    RadixNode  *body;
    int         len;
    char        label[0];
};


struct rnwchelp_s
{
    int off;
    int total;
};


struct rnprint_s
{
    int offset;
    int mode;
};

#define rnh_size(iLen) (sizeof(void *) + sizeof(int) + iLen)

// NOTICE: size should be size + 1 to account for '\0', but
// the first part also had a -1, so I just canceled it out. (size + 1 + 4 - 1)
#define rnh_roundup(size) ((size + 4) & ~(4 - 1))

#define rnh_roundedsize(iLen) (rnh_roundup(rnh_size(iLen)))


/**
 * This function currently only works for contexts.
 * Cases checked:
 * - No more children.
 * - '/' is the last character.
 * Length of the current label is stored in iChildLen.
 * Return value is if there are any children left.
 */
static int rnNextOffset(const char *pLabel, int iLabelLen,
                        int &iChildLen)
{
    const char *ptr = (const char *)memchr(pLabel, '/', iLabelLen);
    if (ptr == NULL)
        iChildLen = iLabelLen;
    else if ((iChildLen = ptr - pLabel) < iLabelLen - 1)
        return 1;
    return 0;
}


static const char *rnGetLengths(int iFlags, const char *pLabel,
                                int iLabelLen, int &iHasChildren,
                                int &iChildLen, int &iGCLen)
{
    if ((iFlags & RTFLAG_NOCONTEXT) != 0)
    {
        if (pLabel[iLabelLen - 1] == '/')
            iChildLen = iLabelLen - 1;
        else
            iChildLen = iLabelLen;
    }
    else
        iHasChildren = rnNextOffset(pLabel, iLabelLen, iChildLen);
    if (iLabelLen == iChildLen)
        iGCLen = 0;
    else
        iGCLen = iLabelLen - iChildLen - 1;
    return pLabel + iChildLen + 1;
}


static void *rnDoAlloc(int iFlags, ls_xpool_t *pool, int iSize)
{
    if (((iFlags & RTFLAG_GLOBALPOOL) == 0)
        && (pool != NULL))
        return ls_xpool_alloc(pool, iSize);
    return ls_palloc(iSize);
}


static void *rnDoRealloc(int iFlags, ls_xpool_t *pool, void *pOld,
                         int iSize)
{
    if ((iFlags & RTFLAG_GLOBALPOOL) == 0)
        return ls_xpool_realloc(pool, pOld, iSize);
    return ls_prealloc(pOld, iSize);
}


static void rnDoFree(int iFlags, ls_xpool_t *pool, void *ptr)
{
    if ((iFlags & RTFLAG_GLOBALPOOL) == 0)
        ls_xpool_free(pool, ptr);
    else
        ls_pfree(ptr);
}


static int rnDoCmp(int iFlags, const char *p1, const char *p2, int len)
{
    if ((iFlags & RTFLAG_CICMP) != 0)
        return strncasecmp(p1, p2, len);
    return strncmp(p1, p2, len);
}


static int rnCheckWC(const char *pLabel, int iLabelLen)
{
    int i;
    for (i = 0; i < iLabelLen; ++i)
    {
        switch (pLabel[i])
        {
        case '?':
        case '*':
        case '[':
        case '{':
            return 1;
        default:
            break;
        }
    }
    return 0;
}


int RadixTree::setRootLabel(const char *pLabel, int iLabelLen)
{
    if (pLabel == NULL || iLabelLen == 0)
        return LS_FAIL;
    if (m_pRoot == NULL)
        m_pRoot = (rnheader_t *)rnDoAlloc(m_iFlags, m_pool,
                                          rnh_size(iLabelLen + 1));
    else
        m_pRoot = (rnheader_t *)rnDoRealloc(m_iFlags, m_pool, m_pRoot,
                                            rnh_size(iLabelLen + 1));
    if (m_pRoot == NULL)
        return LS_FAIL;
    m_pRoot->body = NULL;
    m_pRoot->len = iLabelLen;
    memmove(m_pRoot->label, pLabel, iLabelLen);
    m_pRoot->label[iLabelLen] = '\0';
    return LS_OK;
}


void RadixTree::setNoContext()
{
    if (m_pRoot == NULL)
    {
        m_pRoot = (rnheader_t *)rnDoAlloc(m_iFlags, m_pool,
                                          sizeof(rnheader_t));
        m_pRoot->body = NULL;
    }
    m_pRoot->label[0] = '\0';
    m_pRoot->len = 0;
    m_iFlags |= RTFLAG_NOCONTEXT;
}


int RadixTree::checkPrefix(const char *pLabel, int iLabelLen) const
{
    if (m_pRoot == NULL)
        return LS_FAIL;
    if (m_pRoot->len > iLabelLen)
        return LS_FAIL;
    return rnDoCmp(m_iFlags, m_pRoot->label, pLabel, m_pRoot->len);
}


RadixNode *RadixTree::insert(const char *pLabel, int iLabelLen,
                             void *pObj)
{
    ls_xpool_t *pool = NULL;
    RadixNode *pDest = NULL;
    const char *pChild = pLabel;
    int iChildLen = iLabelLen;
    if (m_pRoot == NULL)
        return NULL;
    if ((m_iFlags & RTFLAG_NOCONTEXT) == 0)
    {
        if (checkPrefix(pLabel, iLabelLen) != 0)
            return NULL;
        pChild += m_pRoot->len;
        iChildLen -= m_pRoot->len;
    }

    if ((m_iFlags & RTFLAG_GLOBALPOOL) == 0)
        pool = m_pool;

    if (iChildLen == 0)
    {
        if (m_pRoot->body == NULL)
            m_pRoot->body = RadixNode::newNode(pool, NULL, pObj);
        else if (m_pRoot->body->getObj() == NULL)
            m_pRoot->body->setObj(pObj);
        else
            return NULL;
        pDest = m_pRoot->body;
    }
    else if (m_pRoot->body != NULL)
        return m_pRoot->body->insert(pool, pChild, iChildLen, pObj,
                                     m_iFlags, m_iMode);
    else
        m_pRoot->body = RadixNode::newBranch(pool, pChild, iChildLen, pObj,
                                             NULL, pDest, m_iFlags, m_iMode);
    return pDest;
}


void *RadixTree::erase(const char *pLabel, int iLabelLen) const
{
    if ((((m_iFlags & RTFLAG_NOCONTEXT) == 0)
         && (checkPrefix(pLabel, iLabelLen) != 0))
        || (m_pRoot->body == NULL))
        return NULL;
    return m_pRoot->body->erase(pLabel + m_pRoot->len,
                                iLabelLen - m_pRoot->len, m_iFlags);
}


void *RadixTree::update(const char *pLabel, int iLabelLen,
                        void *pObj) const
{
    if ((((m_iFlags & RTFLAG_NOCONTEXT) == 0)
         && (checkPrefix(pLabel, iLabelLen) != 0))
        || (m_pRoot->body == NULL))
        return NULL;
    return m_pRoot->body->update(pLabel + m_pRoot->len,
                                 iLabelLen - m_pRoot->len, pObj, m_iFlags);
}


void *RadixTree::find(const char *pLabel, int iLabelLen) const
{
    if ((((m_iFlags & RTFLAG_NOCONTEXT) == 0)
         && (checkPrefix(pLabel, iLabelLen) != 0))
        || (m_pRoot->body == NULL))
        return NULL;
    return m_pRoot->body->find(pLabel + m_pRoot->len, iLabelLen - m_pRoot->len,
                               m_iFlags);
}


void *RadixTree::bestMatch(const char *pLabel, int iLabelLen) const
{
    if ((((m_iFlags & RTFLAG_NOCONTEXT) == 0)
         && (checkPrefix(pLabel, iLabelLen) != 0))
        || (m_pRoot->body == NULL))
        return NULL;
    return m_pRoot->body->find(pLabel + m_pRoot->len, iLabelLen - m_pRoot->len,
                               m_iFlags | RTFLAG_BESTMATCH);
}


int RadixTree::for_each(rn_foreach fun)
{
    if (m_pRoot != NULL && m_pRoot->body != NULL)
        return m_pRoot->body->for_each(fun, m_pRoot->label, m_pRoot->len);
    return 0;
}


int RadixTree::for_each2(rn_foreach2 fun, void *pUData)
{
    if (m_pRoot != NULL && m_pRoot->body != NULL)
        return m_pRoot->body->for_each2(fun, pUData, m_pRoot->label,
                                        m_pRoot->len);
    return 0;
}


RadixNode::RadixNode(RadixNode *pParent, void *pObj)
    : m_iNumExact(0)
    , m_iState(RNSTATE_NOCHILD)
    , m_pParent(pParent)
    , m_iOrig(1)
    , m_pObj(pObj)
    , m_pCHeaders(NULL)
    , m_pWC(NULL)
{
    ls_str(&m_label, NULL, 0);
}


void *RadixNode::getParentObj()
{
    void *pObj;
    if (m_pParent == NULL)
        return NULL;
    else if ((pObj = m_pParent->getObj()) != NULL)
        return pObj;
    return m_pParent->getParentObj();
}


RadixNode *RadixNode::insert(ls_xpool_t *pool, const char *pLabel,
                             int iLabelLen, void *pObj, int iFlags, int iMode)
{
    const char *pGC;
    int iChildLen, iGCLen;
    rnwchelp_t wcHelp;
    rnheader_t *pHeader = NULL;
    RadixNode *pDest = NULL;
    int iWC = 0, iHasChildren = 0, ret = 0;

    pGC = rnGetLengths(iFlags, pLabel, iLabelLen, iHasChildren, iChildLen,
                       iGCLen);

    if (((iFlags & RTFLAG_WILDCARD) != 0)
        && (rnCheckWC(pLabel, iChildLen) != 0))
    {
        if (m_pWC == NULL)
        {
            m_pWC = (rnwc_t *)rnDoAlloc(iFlags, pool, sizeof(rnwc_t));
            m_pWC->m_iNumWild = 0;
            m_pWC->m_iState = RNSTATE_NOCHILD;
            m_pWC->m_pC = NULL;
        }
        iWC = 1;
        wcHelp.off = 0;
        wcHelp.total = 0;
        ret = getWCHeader(iFlags, pool, pLabel, iChildLen, pHeader, &wcHelp);
    }
    else
        ret = getHeader(iFlags, pool, pLabel, iChildLen, pHeader);

    if (ret == -1)
        return NULL;
    else if (ret == 0)
    {
        if (iHasChildren == 0)
        {
            if ((pHeader->body->m_iOrig == 1)
                && (pHeader->body->m_pObj != NULL))
                return NULL;
            else if ((iFlags & RTFLAG_PTR) != 0)
            {
                if ((pHeader->body->m_iOrig == 0)
                    && (*pHeader->body->m_pOrig != NULL))
                    return NULL;
                pHeader->body->m_iOrig = 0;
                // Do the set obj.
                // No need to cast because a void ** is passed in.
            }
            pHeader->body->setObj(pObj);
            return pHeader->body;
        }
        pDest = pHeader->body->insert(pool, pGC, iGCLen, pObj, iFlags, iMode);
        if ((iWC != 0) && ((iFlags & RTFLAG_MERGE) != 0))
            ret = merge(pool, pGC, iGCLen, iFlags | RTFLAG_PTR, iMode,
                        pDest->getObjPtr(), pHeader);
        if (ret == LS_FAIL)
            return NULL;
        return pDest;
    }

    pHeader->len = iChildLen;
    memmove(pHeader->label, pLabel, iChildLen);
    pHeader->label[iChildLen] = '\0';
    if (iHasChildren != 0)
    {
        pHeader->body = newBranch(pool, pGC, iGCLen, pObj, this, pDest, iFlags,
                                  iMode);

        if (pHeader->body == NULL)
        {
            rnDoFree(iFlags, pool, pHeader);
            return NULL;
        }
    }
    else
    {
        pDest = newNode(pool, this, pObj);
        if (pDest == NULL)
        {
            rnDoFree(iFlags, pool, pHeader);
            return NULL;
        }
        if ((iFlags & RTFLAG_PTR) != 0)
            pDest->m_iOrig = 0;
        pHeader->body = pDest;
    }

    if (iWC != 0)
    {
        ret = setWCHeader(iFlags, iMode, pool, pHeader, &wcHelp);

        if (ret == LS_FAIL)
            return NULL;
        else if ((iFlags & RTFLAG_MERGE) != 0)
            ret = merge(pool, pGC, iGCLen, iFlags | RTFLAG_PTR, iMode,
                        pDest->getObjPtr(), pHeader);
    }
    else
        ret = setHeader(iFlags, iMode, pool, pHeader);
    if (ret == LS_FAIL)
        return NULL;
    return pDest;
}


void *RadixNode::erase(const char *pLabel, int iLabelLen, int iFlags)
{
    void *pObj;
    RadixNode *pNode;
    if (iLabelLen == 0)
        pNode = this;
    else if ((pNode = findChild(pLabel, iLabelLen,
                                iFlags | RTFLAG_UPDATE)) == NULL)
        return NULL;

    if (pNode->m_iOrig == 0)
        return NULL;
    pObj = pNode->m_pObj;
    pNode->m_pObj = NULL;
    return pObj;
}


void *RadixNode::update(const char *pLabel, int iLabelLen, void *pObj,
                        int iFlags)
{
    void *pTmp;
    RadixNode *pNode;
    assert(pObj != NULL);
    if (iLabelLen == 0)
        pNode = this;
    else if ((pNode = findChild(pLabel, iLabelLen,
                                iFlags | RTFLAG_UPDATE)) == NULL)
        return NULL;
    if ((pNode->m_iOrig == 0) || (pNode->m_pObj == NULL))
        return NULL;
    pTmp = pNode->m_pObj;
    pNode->m_pObj = pObj;
    return pTmp;
}


void *RadixNode::find(const char *pLabel, int iLabelLen, int iFlags)
{
    RadixNode *pNode;
    if (iLabelLen == 0)
        pNode = this;
    else if ((pNode = findChild(pLabel, iLabelLen, iFlags)) == NULL)
    {
        if ((iFlags & RTFLAG_BESTMATCH) == 0)
            return NULL;
        pNode = this;
    }
    return pNode->getObj();
}


void *RadixNode::bestMatch(const char *pLabel, int iLabelLen,
                           int iFlags)
{
    return find(pLabel, iLabelLen, iFlags | RTFLAG_BESTMATCH);
}


int RadixNode::for_each(rn_foreach fun, const char *pKey, int iKeyLen)
{
    int incr = 0;
    void *pObj;
    if ((pObj = getObj()) != NULL)
    {
        if (fun(pObj, pKey, iKeyLen) != 0)
            return 0;
        incr = 1;
    }
    return for_each_child(fun) + incr;
}


int RadixNode::for_each_child(rn_foreach fun)
{
    rnheader_t *pHeader;
    GHash::iterator iter;
    int i, iNum = getNumExact(), count = 0;
    switch (getState())
    {
    case RNSTATE_CNODE:
    case RNSTATE_PNODE:
        return count + m_pCHeaders->body->for_each(fun, m_pCHeaders->label,
                m_pCHeaders->len);
    case RNSTATE_CARRAY:
        pHeader = m_pCHeaders;
        for (i = 0; i < iNum; ++i)
        {
            count += pHeader->body->for_each(fun, pHeader->label,
                                             pHeader->len);
            pHeader = (rnheader_t *)(&pHeader->label[0]
                                     + rnh_roundup(pHeader->len));
        }
        break;
    case RNSTATE_PARRAY:
        for (i = 0; i < iNum; ++i)
        {
            pHeader = m_pPHeaders[i];
            count += pHeader->body->for_each(fun, pHeader->label,
                                             pHeader->len);
        }
        break;
    case RNSTATE_HASH:
        iter = m_pHash->begin();
        while (iter != m_pHash->end())
        {
            pHeader = (rnheader_t *)iter->second();
            count += pHeader->body->for_each(fun, pHeader->label,
                                             pHeader->len);
            iter = m_pHash->next(iter);
        }
        break;
    default:
        break;
    }
    if (m_pWC == NULL)
        return count;
    iNum = getNumWild();
    switch (getWCState())
    {
    case RNSTATE_CNODE:
    case RNSTATE_PNODE:
        return count + m_pWC->m_pC->body->for_each(fun, m_pWC->m_pC->label,
                m_pWC->m_pC->len);
    case RNSTATE_CARRAY:
        pHeader = m_pWC->m_pC;
        for (i = 0; i < iNum; ++i)
        {
            count += pHeader->body->for_each(fun, pHeader->label,
                                             pHeader->len);
            pHeader = (rnheader_t *)(&pHeader->label[0]
                                     + rnh_roundup(pHeader->len));
        }
        break;
    case RNSTATE_PARRAY:
        for (i = 0; i < iNum; ++i)
        {
            pHeader = m_pWC->m_pP[i];
            count += pHeader->body->for_each(fun, pHeader->label,
                                             pHeader->len);
        }
    default:
        break;
    }
    return count;
}


int RadixNode::for_each2(rn_foreach2 fun, void *pUData, const char *pKey,
                         int iKeyLen)
{
    int incr = 0;
    void *pObj;
    if ((pObj = getObj()) != NULL)
    {
        if (fun(pObj, pUData, pKey, iKeyLen) != 0)
            return 0;
        incr = 1;
    }
    return for_each_child2(fun, pUData) + incr;
}


int RadixNode::for_each_child2(rn_foreach2 fun, void *pUData)
{
    rnheader_t *pHeader;
    GHash::iterator iter;
    int i, iNum = getNumExact(), count = 0;
    switch (getState())
    {
    case RNSTATE_CNODE:
    case RNSTATE_PNODE:
        return count + m_pCHeaders->body->for_each2(fun, pUData,
                m_pCHeaders->label,
                m_pCHeaders->len);
    case RNSTATE_CARRAY:
        pHeader = m_pCHeaders;
        for (i = 0; i < iNum; ++i)
        {
            count += pHeader->body->for_each2(fun, pUData, pHeader->label,
                                              pHeader->len);
            pHeader = (rnheader_t *)(&pHeader->label[0]
                                     + rnh_roundup(pHeader->len));
        }
        break;
    case RNSTATE_PARRAY:
        for (i = 0; i < iNum; ++i)
        {
            pHeader = m_pPHeaders[i];
            count += pHeader->body->for_each2(fun, pUData, pHeader->label,
                                              pHeader->len);
        }
        break;
    case RNSTATE_HASH:
        iter = m_pHash->begin();
        while (iter != m_pHash->end())
        {
            pHeader = (rnheader_t *)iter->second();
            count += pHeader->body->for_each2(fun, pUData, pHeader->label,
                                              pHeader->len);
            iter = m_pHash->next(iter);
        }
        break;
    default:
        break;
    }
    if (m_pWC == NULL)
        return count;
    iNum = getNumWild();
    switch (getWCState())
    {
    case RNSTATE_CNODE:
    case RNSTATE_PNODE:
        return count + m_pWC->m_pC->body->for_each2(fun, pUData,
                m_pWC->m_pC->label,
                m_pWC->m_pC->len);
    case RNSTATE_CARRAY:
        pHeader = m_pWC->m_pC;
        for (i = 0; i < iNum; ++i)
        {
            count += pHeader->body->for_each2(fun, pUData, pHeader->label,
                                              pHeader->len);
            pHeader = (rnheader_t *)(&pHeader->label[0]
                                     + rnh_roundup(pHeader->len));
        }
        break;
    case RNSTATE_PARRAY:
        for (i = 0; i < iNum; ++i)
        {
            pHeader = m_pWC->m_pP[i];
            count += pHeader->body->for_each2(fun, pUData, pHeader->label,
                                              pHeader->len);
        }
    default:
        break;
    }
    return count;
}


RadixNode *RadixNode::newNode(ls_xpool_t *pool, RadixNode *pParent,
                              void *pObj)
{
    void *ptr = rnDoAlloc(0, pool, sizeof(RadixNode));
    if (ptr == NULL)
        return NULL;
    return new(ptr) RadixNode(pParent, pObj);
}


/**
* This function handles the creation of RadixNodes.  This should only
* be necessary if the branch is not found in the current tree.
* pDest will have the RadixNode that contains the object.
* Return value is new child.
*/
RadixNode *RadixNode::newBranch(ls_xpool_t *pool, const char *pLabel,
                                int iLabelLen, void *pObj,
                                RadixNode *pParent, RadixNode *&pDest,
                                int iFlags, int iMode)
{
    RadixNode *pMyNode;
    rnheader_t *pMyChildHeader;
    const char *pGC;
    int iChildLen, iGCLen;
    int *pModeToSet, iHasChildren = 0;
    pMyNode = newNode(pool, pParent, NULL);

    pGC = rnGetLengths(iFlags, pLabel, iLabelLen, iHasChildren, iChildLen,
                       iGCLen);

    pMyChildHeader = (rnheader_t *)rnDoAlloc(iFlags, pool,
                     rnh_size(iChildLen + 1));
    if (pMyChildHeader == NULL)
    {
        rnDoFree(iFlags, pool, pMyNode);
        return NULL;
    }

    pMyChildHeader->len = iChildLen;
    memmove(pMyChildHeader->label, pLabel, iChildLen);
    pMyChildHeader->label[iChildLen] = '\0';
    if (iHasChildren != 0)
    {
        pMyChildHeader->body = newBranch(pool, pGC, iGCLen, pObj, pMyNode,
                                         pDest, iFlags, iMode);
        if (pMyChildHeader->body == NULL)
        {
            rnDoFree(iFlags, pool, pMyChildHeader);
            rnDoFree(iFlags, pool, pMyNode);
            return NULL;
        }
    }
    else
    {
        pDest = newNode(pool, pMyNode, pObj);
        if (pDest == NULL)
        {
            rnDoFree(iFlags, pool, pMyChildHeader);
            rnDoFree(iFlags, pool, pMyNode);
            return NULL;
        }
        if ((iFlags & RTFLAG_PTR) != 0)
            pDest->m_iOrig = 0;
        pMyChildHeader->body = pDest;
    }

    if (((iFlags & RTFLAG_WILDCARD) != 0)
        && (rnCheckWC(pLabel, iChildLen) != 0))
    {
        pMyNode->m_pWC = (rnwc_t *)rnDoAlloc(iFlags, pool, sizeof(rnwc_t));
        pMyNode->m_pWC->m_pC = pMyChildHeader;
        pMyNode->m_pWC->m_iNumWild = 1;
        pModeToSet = &pMyNode->m_pWC->m_iState;
    }
    else
    {
        pMyNode->m_pCHeaders = pMyChildHeader;
        pMyNode->incrNumExact();
        pModeToSet = &pMyNode->m_iState;
    }

    if (iMode == RTMODE_CONTIGUOUS)
        *pModeToSet = RNSTATE_CNODE;
    else
        *pModeToSet = RNSTATE_PNODE;

    return pMyNode;
}


//returns 1 if new, 0 if child matched, -1 if alloc failed.
int RadixNode::getHeader(int iFlags, ls_xpool_t *pool, const char *pLabel,
                         int iLabelLen, rnheader_t *&pHeader)
{
    rnheader_t *pTmp;
    GHash::iterator pHashNode;
    ls_str_t hashMatch;
    int iOffset;
    int i, iExact = getNumExact();
    switch (getState())
    {
    case RNSTATE_NOCHILD:
        break;
    case RNSTATE_CNODE:
        pTmp = m_pCHeaders;
        if ((pTmp->len == iLabelLen)
            && (rnDoCmp(iFlags, &pTmp->label[0], pLabel, pTmp->len) == 0))
        {
            pHeader = pTmp;
            return 0;
        }
        iOffset = rnh_roundedsize(m_pCHeaders->len);
        pTmp = (rnheader_t *)rnDoRealloc(iFlags, pool, m_pCHeaders,
                                         iOffset + rnh_roundedsize(iLabelLen));
        if (pTmp == NULL)
            return -1;
        m_pCHeaders = pTmp;
        pHeader = (rnheader_t *)((char *)m_pCHeaders + iOffset);
        return 1;
    case RNSTATE_PNODE:
        pTmp = m_pCHeaders;
        if ((pTmp->len == iLabelLen)
            && (rnDoCmp(iFlags, &pTmp->label[0], pLabel, iLabelLen) == 0))
        {
            pHeader = pTmp;
            return 0;
        }
        break;
    case RNSTATE_CARRAY:
        pTmp = m_pCHeaders;
        for (i = 0; i < iExact; ++i)
        {
            if ((iLabelLen == pTmp->len)
                && (rnDoCmp(iFlags, &pTmp->label[0], pLabel, pTmp->len) == 0))
            {
                pHeader = pTmp;
                return 0;
            }
            pTmp = (rnheader_t *)(&pTmp->label[0] + rnh_roundup(pTmp->len));
        }
        iOffset = (char *)pTmp - (char *)m_pCHeaders;
        if (iExact < RN_USEHASHCNT)
        {
            pTmp = (rnheader_t *)rnDoRealloc(iFlags, pool, m_pCHeaders,
                                             iOffset + rnh_roundedsize(iLabelLen));
            if (pTmp == NULL)
            {
                pHeader = NULL;
                return -1;
            }
            m_pCHeaders = pTmp;
            pHeader = (rnheader_t *)((char *)pTmp + iOffset);
            return 1;
        }
        break;
    case RNSTATE_PARRAY:
        for (i = 0; i < iExact; ++i)
        {
            pTmp = m_pPHeaders[i];
            if ((iLabelLen == pTmp->len)
                && (rnDoCmp(iFlags, &pTmp->label[0], pLabel, pTmp->len) == 0))
            {
                pHeader = pTmp;
                return 0;
            }
        }
        break;
    case RNSTATE_HASH:
        ls_str_set(&hashMatch, (char *)pLabel, iLabelLen);
        pHashNode = m_pHash->find(&hashMatch);
        if (pHashNode != NULL)
        {
            pHeader = (rnheader_t *)pHashNode->getData();
            return 0;
        }
        break;
    default:
        return -1;
    }
    pTmp = (rnheader_t *)rnDoAlloc(iFlags, pool, rnh_size(iLabelLen + 1));
    if (pTmp == NULL)
        return -1;
    pHeader = pTmp;
    return 1;
}


int RadixNode::setHeader(int iFlags, int iMode, ls_xpool_t *pool,
                         rnheader_t *pHeader)
{
    GHash *pHash;
    void *ptr;
    rnheader_t *pTmp, **pArray;
    int i, iExact = getNumExact();
    switch (getState())
    {
    case RNSTATE_NOCHILD:
        m_pCHeaders = pHeader;
        if (iMode == RTMODE_CONTIGUOUS)
            setState(RNSTATE_CNODE);
        else
            setState(RNSTATE_PNODE);
        break;
    case RNSTATE_CNODE:
        setState(RNSTATE_CARRAY);
        break;
    case RNSTATE_PNODE:
        pArray = (rnheader_t **)rnDoAlloc(iFlags, pool,
                                          sizeof(rnheader_t *) * (RN_USEHASHCNT >> 1));
        if (pArray == NULL)
        {
            rnDoFree(iFlags, pool, pHeader);
            return LS_FAIL;
        }
        pArray[0] = m_pCHeaders;
        pArray[1] = pHeader;
        m_pPHeaders = pArray;
        setState(RNSTATE_PARRAY);
        break;
    case RNSTATE_CARRAY:
        if (iExact < RN_USEHASHCNT)
            break;
        ptr = rnDoAlloc(iFlags, pool, sizeof(GHash));
        if ((iFlags & RTFLAG_CICMP) != 0)
            pHash = new(ptr) GHash(RN_HASHSZ, ls_str_hfci, ls_str_cmpci,
                                   pool);
        else
            pHash = new(ptr) GHash(RN_HASHSZ, ls_str_xh32, ls_str_cmp, pool);
        pTmp = (rnheader_t *)m_pCHeaders;
        for (i = 0; i < iExact; ++i)
        {
            pTmp->body->setLabel(pTmp->label, pTmp->len);
            if (pHash->insert(pTmp->body->getLabel(), pTmp) == NULL)
            {
                pHash->~GHash();
                rnDoFree(iFlags, pool, pHash);
                rnDoFree(iFlags, pool, pHeader);
                return LS_FAIL;
            }
            pTmp = (rnheader_t *)(&pTmp->label[0] + rnh_roundup(pTmp->len));
        }
        pHeader->body->setLabel(pHeader->label, pHeader->len);
        if (pHash->insert(pHeader->body->getLabel(), pHeader) == NULL)
        {
            pHash->~GHash();
            rnDoFree(iFlags, pool, pHash);
            rnDoFree(iFlags, pool, pHeader);
            return LS_FAIL;
        }
        m_pHash = pHash;
        setState(RNSTATE_HASH);
        break;
    case RNSTATE_PARRAY:
        if (iExact < RN_USEHASHCNT)
        {
            if (iExact == RN_USEHASHCNT >> 1)
            {
                pArray = (rnheader_t **)rnDoRealloc(iFlags, pool, m_pPHeaders,
                                                    sizeof(rnheader_t *) * RN_USEHASHCNT);
                if (pArray == NULL)
                {
                    rnDoFree(iFlags, pool, pHeader);
                    return LS_FAIL;
                }
                m_pPHeaders = pArray;
            }
            m_pPHeaders[iExact] = pHeader;
            break;
        }

        ptr = rnDoAlloc(iFlags, pool, sizeof(GHash));
        if ((iFlags & RTFLAG_CICMP) != 0)
            pHash = new(ptr) GHash(RN_HASHSZ, ls_str_hfci, ls_str_cmpci,
                                   pool);
        else
            pHash = new(ptr) GHash(RN_HASHSZ, ls_str_xh32, ls_str_cmp, pool);

        for (i = 0; i < iExact; ++i)
        {
            pTmp = m_pPHeaders[i];
            pTmp->body->setLabel(pTmp->label, pTmp->len);
            if (pHash->insert(pTmp->body->getLabel(), pTmp) == NULL)
            {
                pHash->~GHash();
                rnDoFree(iFlags, pool, pHash);
                rnDoFree(iFlags, pool, pHeader);
                return LS_FAIL;
            }
        }
        pHeader->body->setLabel(pHeader->label, pHeader->len);
        if (pHash->insert(pHeader->body->getLabel(), pHeader) == NULL)
        {
            pHash->~GHash();
            rnDoFree(iFlags, pool, pHash);
            rnDoFree(iFlags, pool, pHeader);
            return LS_FAIL;
        }
        rnDoFree(iFlags, pool, m_pPHeaders);
        m_pHash = pHash;
        setState(RNSTATE_HASH);
        break;
    case RNSTATE_HASH:
        pHeader->body->setLabel(pHeader->label, pHeader->len);
        if (m_pHash->insert(pHeader->body->getLabel(), pHeader) == NULL)
        {
            rnDoFree(iFlags, pool, pHeader);
            return LS_FAIL;
        }
        break;
    default:
        return LS_FAIL;
    }
    incrNumExact();
    return LS_OK;
}


//returns 1 if new, 0 if child matched, -1 if alloc failed.
int RadixNode::getWCHeader(int iFlags, ls_xpool_t *pool,
                           const char *pLabel,
                           int iLabelLen, rnheader_t *&pHeader, rnwchelp_t *pHelp)
{
    rnheader_t *pTmp;
    int iOffsetSet = 0;
    int i, iCount = getNumWild();
    switch (getWCState())
    {
    case RNSTATE_NOCHILD:
        break;
    case RNSTATE_CNODE:
    case RNSTATE_PNODE:
        pTmp = m_pWC->m_pC;
        if ((pTmp->len == iLabelLen)
            && (fnmatch(pTmp->label, pLabel, FNM_LEADING_DIR) == 0))
        {
            pHeader = pTmp;
            return 0;
        }
        break;
    case RNSTATE_CARRAY:
        pTmp = m_pWC->m_pC;
        for (i = 0; i < iCount; ++i)
        {
            if (iLabelLen > pTmp->len && iOffsetSet == 0)
            {
                pHelp->off = (char *)pTmp - (char *)m_pWC->m_pC;
                iOffsetSet = 1;
            }
            if ((iLabelLen == pTmp->len)
                && (fnmatch(pTmp->label, pLabel, FNM_LEADING_DIR) == 0))
            {
                pHeader = pTmp;
                return 0;
            }
            pTmp = (rnheader_t *)(&pTmp->label[0] + rnh_roundup(pTmp->len));
        }
        pHelp->total = (char *)pTmp - (char *)m_pWC->m_pC;
        if (pHelp->off == 0 && iOffsetSet == 0)
            pHelp->off = pHelp->total;
        break;
    case RNSTATE_PARRAY:
        for (i = 0; i < iCount; ++i)
        {
            pTmp = m_pWC->m_pP[i];
            if (iLabelLen > pTmp->len)
                break;
            else if ((iLabelLen == pTmp->len)
                     && (fnmatch(pTmp->label, pLabel, FNM_LEADING_DIR) == 0))
            {
                pHeader = pTmp;
                return 0;
            }
        }
        pHelp->off = i;
        break;
    default:
        return -1;
    }
    pTmp = (rnheader_t *)rnDoAlloc(iFlags, pool, rnh_size(iLabelLen + 1));
    if (pTmp == NULL)
        return -1;
    pHeader = pTmp;
    return 1;
}


int RadixNode::setWCHeader(int iFlags, int iMode, ls_xpool_t *pool,
                           rnheader_t *pHeader, rnwchelp_t *pHelp)
{
    rnheader_t *pTmp, **pArray;
    int iOrigOff, iNewOff, iCount = getNumWild();
    switch (getWCState())
    {
    case RNSTATE_NOCHILD:
        m_pWC->m_pC = pHeader;
        if (iMode == RTMODE_CONTIGUOUS)
            setWCState(RNSTATE_CNODE);
        else
            setWCState(RNSTATE_PNODE);
        break;
    case RNSTATE_CNODE:
        pTmp = m_pWC->m_pC;
        iOrigOff = rnh_roundedsize(pTmp->len);
        iNewOff = rnh_roundedsize(pHeader->len);
        if (pTmp == NULL)
            return LS_FAIL;
        if (pTmp->len < pHeader->len)
        {
            pHeader = (rnheader_t *)rnDoRealloc(iFlags, pool, pHeader,
                                                iOrigOff + iNewOff);
            if (pHeader == NULL)
                return LS_FAIL;
            memmove((char *)pHeader + iNewOff, pTmp, rnh_size(pTmp->len + 1));
            m_pWC->m_pC = pHeader;
            rnDoFree(iFlags, pool, pTmp);
        }
        else
        {
            pTmp = (rnheader_t *)rnDoRealloc(iFlags, pool, pTmp,
                                             iOrigOff + iNewOff);
            if (pTmp == NULL)
            {
                rnDoFree(iFlags, pool, pHeader);
                return LS_FAIL;
            }
            memmove((char *)pTmp + iOrigOff, pHeader, rnh_size(pHeader->len + 1));
            m_pWC->m_pC = pTmp;
            rnDoFree(iFlags, pool, pHeader);
        }
        setWCState(RNSTATE_CARRAY);
        break;
    case RNSTATE_PNODE:
        pTmp = m_pWC->m_pC;
        pArray = (rnheader_t **)rnDoAlloc(iFlags, pool,
                                          sizeof(rnheader_t *) * RNWC_ARRAYSTARTSZ);
        if (pArray == NULL)
        {
            rnDoFree(iFlags, pool, pHeader);
            return LS_FAIL;
        }
        if (pHeader->len < pTmp->len)
        {
            pArray[0] = pHeader;
            pArray[1] = m_pWC->m_pC;
        }
        else
        {
            pArray[0] = m_pWC->m_pC;
            pArray[1] = pHeader;
        }
        m_pWC->m_pP = pArray;
        setWCState(RNSTATE_PARRAY);
        break;
    case RNSTATE_CARRAY:
        iNewOff = rnh_roundedsize(pHeader->len);
        pTmp = (rnheader_t *)rnDoRealloc(iFlags, pool, m_pWC->m_pC,
                                         pHelp->total + iNewOff);
        if (pTmp == NULL)
        {
            rnDoFree(iFlags, pool, pHeader);
            return LS_FAIL;
        }
        m_pWC->m_pC = pTmp;
        if (pHelp->off != pHelp->total)
        {
            memmove((char *)pTmp + pHelp->off + iNewOff,
                    (char *)pTmp + pHelp->off, pHelp->total - pHelp->off);
        }
        memmove((char *)pTmp + pHelp->off, pHeader, rnh_size(pHeader->len + 1));
        rnDoFree(iFlags, pool, pHeader);
        break;
    case RNSTATE_PARRAY:
        if ((iCount & (iCount - 1)) == 0)
        {
            pArray = (rnheader_t **)rnDoRealloc(iFlags, pool, m_pWC->m_pP,
                                                sizeof(rnheader_t *) * (iCount << 1));
            if (pArray == NULL)
                return LS_FAIL;
            m_pWC->m_pP = pArray;
        }
        memmove(m_pWC->m_pP + pHelp->off + 1, m_pWC->m_pP + pHelp->off,
                sizeof(rnheader_t *) * (iCount - pHelp->off));
        m_pWC->m_pP[pHelp->off] = pHeader;
        break;
    default:
        return LS_FAIL;
    }
    incrNumWild();
    return LS_OK;
}


void RadixNode::mergeSelf(void **pOrig)
{
    if ((m_iOrig == 1) && (m_pObj == NULL))
    {
        m_pOrig = pOrig;
        m_iOrig = 0;
    }
    //if m_iOrig is 0, it has to already have an object.
}


int RadixNode::merge(ls_xpool_t *pool, const char *pMatch,
                     int iMatchLen,
                     int iFlags, int iMode, void **pOrig, rnheader_t *pHeaderAdded)
{
    int i, iCount = getNumWild();
    rnheader_t *pHeader;
    GHash::iterator iter;
    switch (getState())
    {
    case RNSTATE_NOCHILD:
        break;
    case RNSTATE_CNODE:
    case RNSTATE_PNODE:
        if (fnmatch(pHeaderAdded->label, m_pCHeaders->label,
                    FNM_LEADING_DIR) == 0)
        {
            if (iMatchLen == 0)
                m_pCHeaders->body->mergeSelf(pOrig);
            else
                m_pCHeaders->body->insert(pool, pMatch, iMatchLen, pOrig,
                                          iFlags, iMode);
        }
        break;
    case RNSTATE_CARRAY:
        pHeader = m_pCHeaders;
        for (i = 0; i < m_iNumExact; ++i)
        {
            if (fnmatch(pHeaderAdded->label, pHeader->label,
                        FNM_LEADING_DIR) == 0)
            {
                if (iMatchLen == 0)
                    pHeader->body->mergeSelf(pOrig);
                else
                    pHeader->body->insert(pool, pMatch, iMatchLen, pOrig,
                                          iFlags, iMode);
            }
            pHeader = (rnheader_t *)(&pHeader->label[0]
                                     + rnh_roundup(pHeader->len));
        }
        break;
    case RNSTATE_PARRAY:
        for (i = 0; i < m_iNumExact; ++i)
        {
            pHeader = m_pPHeaders[i];
            if (fnmatch(pHeaderAdded->label, pHeader->label,
                        FNM_LEADING_DIR) == 0)
            {
                if (iMatchLen == 0)
                    pHeader->body->mergeSelf(pOrig);
                else
                    pHeader->body->insert(pool, pMatch, iMatchLen, pOrig,
                                          iFlags, iMode);
            }
        }
        break;
    case RNSTATE_HASH:
        for (iter = m_pHash->begin(); iter != NULL; iter = m_pHash->next(iter))
        {
            pHeader = (rnheader_t *)iter->getData();
            if (fnmatch(pHeaderAdded->label, pHeader->label,
                        FNM_LEADING_DIR) == 0)
            {
                if (iMatchLen == 0)
                    pHeader->body->mergeSelf(pOrig);
                else
                    pHeader->body->insert(pool, pMatch, iMatchLen, pOrig,
                                          iFlags, iMode);
            }
        }
        break;
    default:
        return LS_FAIL;
    }

    switch (getWCState())
    {
    case RNSTATE_NOCHILD:
        return LS_FAIL;
    case RNSTATE_CNODE:
    case RNSTATE_PNODE:
        return LS_OK;//only child.
    case RNSTATE_CARRAY:
        pHeader = m_pWC->m_pC;
        for (i = 0; i < iCount; ++i)
        {
            if (pHeaderAdded == pHeader)
                return LS_OK;
            if (fnmatch(pHeaderAdded->label, pHeader->label,
                        FNM_LEADING_DIR) == 0)
            {
                if (iMatchLen == 0)
                    pHeader->body->mergeSelf(pOrig);
                else
                    pHeader->body->insert(pool, pMatch, iMatchLen, pOrig,
                                          iFlags, iMode);
            }
            pHeader = (rnheader_t *)(&pHeader->label[0]
                                     + rnh_roundup(pHeader->len));
        }
        break;
    case RNSTATE_PARRAY:
        for (i = 0; i < iCount; ++i)
        {
            pHeader = m_pWC->m_pP[i];
            if (pHeaderAdded == pHeader)
                return LS_OK;
            if (fnmatch(pHeaderAdded->label, pHeader->label,
                        FNM_LEADING_DIR) == 0)
            {
                if (iMatchLen == 0)
                    pHeader->body->mergeSelf(pOrig);
                else
                    pHeader->body->insert(pool, pMatch, iMatchLen, pOrig,
                                          iFlags, iMode);
            }
        }
        break;
    default:
        return LS_FAIL;
    }
    return LS_OK;
}


RadixNode *RadixNode::searchExact(const char *pLabel, int iLabelLen,
                                  int iFlags)
{
    int i;
    rnheader_t *pHeader;
    GHash::iterator pHashNode;
    ls_str_t hashMatch;

    switch (getState())
    {
    case RNSTATE_CNODE:
    case RNSTATE_PNODE:
        if (iLabelLen < m_pCHeaders->len)
            return NULL;
        if (rnDoCmp(iFlags, m_pCHeaders->label, pLabel, iLabelLen) != 0)
            return NULL;
        pHeader = m_pCHeaders;
        break;
    case RNSTATE_CARRAY:
        pHeader = m_pCHeaders;
        for (i = 0; i < m_iNumExact; ++i)
        {
            if ((iLabelLen == pHeader->len)
                && (rnDoCmp(iFlags, pHeader->label, pLabel,
                            pHeader->len) == 0))
                return pHeader->body;
            pHeader = (rnheader_t *)(&pHeader->label[0]
                                     + rnh_roundup(pHeader->len));
        }
        return NULL;
    case RNSTATE_PARRAY:
        for (i = 0; i < m_iNumExact; ++i)
        {
            pHeader = m_pPHeaders[i];
            if ((iLabelLen == pHeader->len)
                && (rnDoCmp(iFlags, pHeader->label, pLabel, pHeader->len) == 0))
                return pHeader->body;
        }
        return NULL;
    case RNSTATE_HASH:
        ls_str_set(&hashMatch, (char *)pLabel, iLabelLen);
        pHashNode = m_pHash->find(&hashMatch);
        if (pHashNode == NULL)
            return NULL;
        pHeader = (rnheader_t *)pHashNode->getData();
        break;
    default:
        return NULL;
    }
    return pHeader->body;
}


RadixNode *RadixNode::searchWild(const char *pLabel, int iLabelLen,
                                 int iFlags)
{
    rnheader_t *pHeader;
    int i, iCount = getNumWild();

    if (m_pWC == NULL)
        return NULL;

    switch (getWCState())
    {
    case RNSTATE_CNODE:
    case RNSTATE_PNODE:
        if ((iFlags & RTFLAG_UPDATE) == 0)
        {
            if (fnmatch(m_pWC->m_pC->label, pLabel, FNM_LEADING_DIR) != 0)
                return NULL;
        }
        else
        {
            if ((iLabelLen != m_pWC->m_pC->len)
                || (rnDoCmp(iFlags, m_pWC->m_pC->label, pLabel,
                            m_pWC->m_pC->len) != 0))
                return NULL;
        }
        return m_pWC->m_pC->body;
    case RNSTATE_CARRAY:
        pHeader = m_pWC->m_pC;
        if ((iFlags & RTFLAG_UPDATE) == 0)
        {
            for (i = 0; i < iCount; ++i)
            {
                if (fnmatch(pHeader->label, pLabel, FNM_LEADING_DIR) == 0)
                    return pHeader->body;
                pHeader = (rnheader_t *)(&pHeader->label[0]
                                         + rnh_roundup(pHeader->len));
            }
        }
        else
        {
            for (i = 0; i < iCount; ++i)
            {
                if ((iLabelLen == pHeader->len)
                    && (rnDoCmp(iFlags, &pHeader->label[0], pLabel,
                                pHeader->len) == 0))
                    return pHeader->body;
                pHeader = (rnheader_t *)(&pHeader->label[0]
                                         + rnh_roundup(pHeader->len));
            }
        }
        break;
    case RNSTATE_PARRAY:
        if ((iFlags & RTFLAG_UPDATE) == 0)
        {
            for (i = 0; i < iCount; ++i)
            {
                pHeader = m_pWC->m_pP[i];
                if (fnmatch(pHeader->label, pLabel, FNM_LEADING_DIR) == 0)
                    return pHeader->body;
            }
        }
        else
        {
            for (i = 0; i < iCount; ++i)
            {
                pHeader = m_pWC->m_pP[i];
                if ((iLabelLen == pHeader->len)
                    && (rnDoCmp(iFlags, pHeader->label, pLabel,
                                pHeader->len) == 0))
                    return pHeader->body;
            }
        }
        break;
    default:
        return NULL;
    }
    return NULL;
}


/**
 * This function compares labels of the search target and current children.
 * If found, it will call findChildData, which may recurse back to findChild.
 */
RadixNode *RadixNode::findChild(const char *pLabel, int iLabelLen,
                                int iFlags)
{
    RadixNode *pExactOut, *pWildOut;
    const char *pGC;
    int iChildLen, iGCLen;
    int iHasChildren = 0;

    pGC = rnGetLengths(iFlags, pLabel, iLabelLen, iHasChildren, iChildLen,
                       iGCLen);

    pWildOut = searchWild(pLabel, iChildLen, iFlags);
    pExactOut = searchExact(pLabel, iChildLen, iFlags);

    if (pExactOut != NULL)
        return findChildData(pGC, iGCLen, pExactOut, iHasChildren, iFlags);
    else if (pWildOut != NULL)
        return findChildData(pGC, iGCLen, pWildOut, iHasChildren, iFlags);
    else if (((iFlags & RTFLAG_BESTMATCH) == 0) || (getObj() == NULL))
        return NULL;
    return this;
}


/**
 * This function is called when a child matches.  It will check if
 * it needs to recurse deeper, and if it doesn't, returns the pointer to
 * the object.
 */
RadixNode *RadixNode::findChildData(const char *pLabel, int iLabelLen,
                                    RadixNode *pNode, int iHasChildren, int iFlags)
{
    RadixNode *pOut;
    if (iHasChildren == 0)
        pOut = pNode;
    else if (pNode->hasChildren())
        pOut = pNode->findChild(pLabel, iLabelLen, iFlags);
    else if ((iFlags & RTFLAG_BESTMATCH) == 0)
        return NULL;
    else
        pOut = pNode;

    if (((iFlags & RTFLAG_BESTMATCH) == 0)
        || (pOut != NULL && pOut->getObj() != NULL))
        return pOut;
    else if (getObj() != NULL)
        return this;
    return NULL;
}


void RadixTree::printTree()
{
    rnprint_t helper;
    if (m_pRoot == NULL)
        return;
    if (m_pRoot->body == NULL)
    {
        printf("Only root prefix: %.*s\n", m_pRoot->len, m_pRoot->label);
        return;
    }
    printf("%.*s  ->%p\n", m_pRoot->len, m_pRoot->label,
           m_pRoot->body->getObj());
    helper.offset = 2;
    helper.mode = m_iMode;
    m_pRoot->body->printChildren(&helper);
}


/**
 * For debugging, the for_each function for the hash table.
 */
int RadixNode::printHash(const void *key, void *data, void *extra)
{
    rnheader_t *pHeader = (rnheader_t *)data;
    ls_str_t *pStr = pHeader->body->getLabel();
    rnprint_t *pHelper = (rnprint_t *)extra;
    rnprint_t myHelper;
    myHelper.mode = pHelper->mode;
    myHelper.offset = pHelper->offset + 2;
    int i;
    for (i = 0; i < pHelper->offset; ++i)
        printf("|");
    printf("%.*s  ->", pHeader->len, pHeader->label);
    printf("(%d)%p, (%.*s)\n", pHeader->body->m_iOrig, pHeader->body->getObj(),
           (int)ls_str_len(pStr), ls_str_cstr(pStr));
    if (pHeader->body->hasChildren())
        pHeader->body->printChildren(&myHelper);

    return 0;
}


/**
 * For debugging.
 */
void RadixNode::printChildren(rnprint_t *pHelper)
{
    int i;
    int j, iCount = getNumWild();
    rnheader_t *pHeader;
    rnprint_t myHelper;
    myHelper.mode = pHelper->mode;
    myHelper.offset = pHelper->offset + 2;
    if (!hasChildren())
        return;
    switch (getState())
    {
    case RNSTATE_CNODE:
    case RNSTATE_PNODE:
        for (i = 0; i < pHelper->offset; ++i)
            printf("|");
        printf("%.*s  ->", m_pCHeaders->len, m_pCHeaders->label);
        printf("(%d)%p\n", m_pCHeaders->body->m_iOrig,
               m_pCHeaders->body->getObj());
        if (m_pCHeaders->body->hasChildren())
            m_pCHeaders->body->printChildren(&myHelper);
        break;
    case RNSTATE_CARRAY:
        pHeader = m_pCHeaders;
        for (j = 0; j < m_iNumExact; ++j)
        {
            for (i = 0; i < pHelper->offset; ++i)
                printf("|");
            printf("%.*s  ->", pHeader->len, pHeader->label);
            printf("(%d)%p\n", pHeader->body->m_iOrig,
                   pHeader->body->getObj());
            if (pHeader->body->hasChildren())
                pHeader->body->printChildren(&myHelper);

            pHeader = (rnheader_t *)(&pHeader->label[0]
                                     + rnh_roundup(pHeader->len));
        }
        break;
    case RNSTATE_PARRAY:
        for (j = 0; j < m_iNumExact; ++j)
        {
            pHeader = m_pPHeaders[j];
            for (i = 0; i < pHelper->offset; ++i)
                printf("|");
            printf("%.*s  ->", pHeader->len, pHeader->label);
            printf("(%d)%p\n", pHeader->body->m_iOrig,
                   pHeader->body->getObj());
            if (pHeader->body->hasChildren())
                pHeader->body->printChildren(&myHelper);
        }
        break;
    case RNSTATE_HASH:
        myHelper.offset -= 2;
        m_pHash->for_each2(m_pHash->begin(), m_pHash->end(), printHash,
                           (void *)&myHelper);
        break;
    default:
        break;
    }
    if ((m_pWC == NULL) || (iCount == 0))
        return;
    if (pHelper->mode == RTMODE_CONTIGUOUS)
    {
        pHeader = m_pWC->m_pC;
        for (j = 0; j < iCount; ++j)
        {
            for (i = 0; i < pHelper->offset; ++i)
                printf("|");
            printf("%.*s  ->", pHeader->len, pHeader->label);
            printf("(%d)%p\n", pHeader->body->m_iOrig,
                   pHeader->body->getObj());
            if (pHeader->body->hasChildren())
                pHeader->body->printChildren(&myHelper);

            pHeader = (rnheader_t *)(&pHeader->label[0]
                                     + rnh_roundup(pHeader->len));
        }
    }
    else if (iCount == 1)
    {
        pHeader = m_pWC->m_pC;
        for (i = 0; i < pHelper->offset; ++i)
            printf("|");
        printf("%.*s  ->", pHeader->len, pHeader->label);
        printf("(%d)%p\n", pHeader->body->m_iOrig,
               pHeader->body->getObj());
        if (pHeader->body->hasChildren())
            pHeader->body->printChildren(&myHelper);
    }
    else
    {
        for (j = 0; j < iCount; ++j)
        {
            pHeader = m_pWC->m_pP[j];
            for (i = 0; i < pHelper->offset; ++i)
                printf("|");
            printf("%.*s  ->", pHeader->len, pHeader->label);
            printf("(%d)%p\n", pHeader->body->m_iOrig,
                   pHeader->body->getObj());
            if (pHeader->body->hasChildren())
                pHeader->body->printChildren(&myHelper);
        }
    }
}




