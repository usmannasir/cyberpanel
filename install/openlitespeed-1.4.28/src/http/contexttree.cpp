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
#include "contexttree.h"
#include <http/handlertype.h>
#include <http/httpcontext.h>
#include <util/pool.h>
#include <util/radixtree.h>

#include <errno.h>
#include <string.h>


ContextTree::ContextTree()
    : m_pRootContext(NULL)
{
    m_pURITree = new RadixTree();
    m_pLocTree = new RadixTree();
    m_pURITree->setUseWildCard();
    m_pLocTree->setUseWildCard();
    m_pURITree->setRootLabel("/", 1);
    m_pLocTree->setRootLabel("/", 1);
}


ContextTree::~ContextTree()
{
    delete m_pURITree;
    delete m_pLocTree;
}


void ContextTree::setRootContext(const HttpContext *pContext)
{
    m_pRootContext = pContext;
    m_pURITree->setRootLabel(pContext->getURI(), pContext->getURILen());
}


void ContextTree::setRootLocation(const char *pLocation, int iLocLen)
{
    m_pLocTree->setRootLabel(pLocation, iLocLen);
}


int ContextTree::add(HttpContext *pContext)
{
    RadixNode *pRadixNode;
    const char *pURI = pContext->getURI();
    int iUriLen = pContext->getURILen();

    pRadixNode = m_pURITree->insert(pURI, iUriLen, pContext);
    if (pRadixNode == NULL)
        return EINVAL;
    updateTreeAfterAdd(pRadixNode, pContext);
    if (pContext->getParent() == NULL)
        pContext->setParent(m_pRootContext);
    if (pContext->getLocation() != NULL)
    {
        pURI = pContext->getLocation();
        iUriLen = pContext->getLocationLen();
        pRadixNode = m_pLocTree->insert(pURI, iUriLen, pContext);
    }
    return LS_OK;
}


const HttpContext *ContextTree::bestMatch(const char *pURI,
        int iUriLen) const
{
    return (HttpContext *)m_pURITree->bestMatch(pURI, iUriLen);
}


const HttpContext *ContextTree::matchLocation(const char *pLoc,
        int iLocLen) const
{
    return (HttpContext *)m_pLocTree->bestMatch(pLoc, iLocLen);
}


HttpContext *ContextTree::getContext(const char *pURI,
                                     int iUriLen) const
{
    return (HttpContext *)m_pURITree->find(pURI, iUriLen);
}


void ContextTree::contextInherit()
{
    m_pURITree->for_each2(inherit, (void *)m_pRootContext);
    ((HttpContext *)m_pRootContext)->matchListInherit(m_pRootContext);

}


int ContextTree::inherit(void *pObj, void *pUData, const char *pKey,
                         int iKeyLen)
{
    HttpContext *pContext = (HttpContext *)pObj;
    const HttpContext *pRootContext = (const HttpContext *)pUData;
    pContext->inherit(pRootContext);
    return LS_OK;
}


int ContextTree::updateChildren(void *pObj, void *pUData, const char *pKey,
                                int iKeyLen)
{
    HttpContext *pNewParent = (HttpContext *)pUData;
    HttpContext *pContext = (HttpContext *)pObj;
    if ((pContext != NULL)
        && ((pContext->getHandler() == NULL)
            || (pContext->getHandlerType() != HandlerType::HT_REDIRECT)))
    {
        if (pContext->getParent() == pNewParent->getParent())
            pContext->setParent(pNewParent);
    }
    return LS_OK;
}


HttpContext *ContextTree::getParentContext(RadixNode *pCurNode)
{
    RadixNode *pParent;
    HttpContext *pParentContext;
    if ((pParent = pCurNode->getParent()) != NULL)
    {
        if (((pParentContext = (HttpContext *)pParent->getObj()) != NULL)
            && ((pParentContext->getHandler() == NULL)
                || (pParentContext->getHandlerType()
                    != HandlerType::HT_REDIRECT)))
            return pParentContext;
        return getParentContext(pParent);
    }
    return NULL;
}


void ContextTree::updateTreeAfterAdd(RadixNode *pRadixNode,
                                     HttpContext *pContext)
{
    HttpContext *pOldParent = getParentContext(pRadixNode);
    pContext->setParent(pOldParent);
    pRadixNode->for_each_child2(updateChildren, pContext);
}


