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
#include "contextnode.h"
#include <util/pool.h>

#include <http/contextlist.h>
#include <http/handlertype.h>
#include <http/httpcontext.h>


ContextNode::ContextNode(const char *pchLabel, ContextNode *pParentNode)
    : HashStringMap< ContextNode * >(10)
    , m_pParentNode(pParentNode)
    , m_pContext(NULL)
    , m_pLabel(NULL)
    , m_lHTALastCheck(0)
    , m_iHTAState(HTA_UNKNOWN)
    , m_iRelease(1)
{
    m_pLabel = Pool::dupstr(pchLabel);
}

ContextNode::~ContextNode()
{
    if (m_iRelease && m_pContext)
        delete m_pContext;
    if (m_pLabel)
        Pool::deallocate2(m_pLabel);
    release_objects();
}

void ContextNode::setLabel(const char *l)
{   m_pLabel = Pool::dupstr(l);  }

void ContextNode::setContextUpdateParent(HttpContext *pContext,
        int noRedirect)
{
    if (pContext == m_pContext)
        return;
    HttpContext *pNewParent = pContext;
    HttpContext *pOldParent = m_pContext;
    if (!pNewParent)
        pNewParent = getParentContext();
    if (!pOldParent)
        pOldParent = getParentContext();
    setChildrenParentContext(pOldParent, pNewParent, noRedirect);
    if (pContext)
    {
        if (m_pContext)
            pContext->setParent(m_pContext->getParent());
        else
            pContext->setParent(getParentContext());
    }
    m_pContext = pContext;

}

void ContextNode::setChildrenParentContext(const HttpContext *pOldParent,
        const HttpContext *pNewParent, int noRedirect)
{
    iterator iter = begin();
    while (iter != end())
    {
        HttpContext *pContext = iter.second()->getContext();
        if ((pContext) && ((!noRedirect)
                           || (pContext->getHandlerType() != HandlerType::HT_REDIRECT)))
        {
            if (pContext->getParent() == pOldParent)
                pContext->setParent(pNewParent);
        }
        else
        {
            iter.second()->setChildrenParentContext(pOldParent, pNewParent,
                                                    noRedirect);
        }
        iter = next(iter);
    }
}

void ContextNode::removeRedirectContext(HttpContext *pParent)
{
    iterator iter = begin();
    while (iter != end())
    {
        HttpContext *pContext = iter.second()->getContext();
        if (pContext)
        {
            if ((pContext->getHandlerType() == HandlerType::HT_REDIRECT) &&
                (pContext->getParent() == pParent))
            {
                delete pContext;
                iter.second()->setContext(NULL);
            }
        }
        iter.second()->removeRedirectContext(pParent);
        iter = next(iter);
    }
}

void ContextNode::contextInherit(const HttpContext *pRootContext)
{
    if (m_pContext)
        m_pContext->inherit(pRootContext);
    iterator iter = begin();
    while (iter != end())
    {
        iter.second()->contextInherit(pRootContext);
        iter = next(iter);
    }
}


HttpContext *ContextNode::getParentContext()
{
    if (m_pParentNode != NULL)
    {
        if (m_pParentNode->getContext())
        {
            if ((!m_pParentNode->getContext()->getHandler()) ||
                (m_pParentNode->getContext()->getHandlerType()
                 != HandlerType::HT_REDIRECT))
                return m_pParentNode->getContext();
        }
        return m_pParentNode->getParentContext();
    }
    return NULL;

}



ContextNode *ContextNode::insertChild(const char *pchLabel)
{
    ContextNode *pNewChild = new ContextNode(pchLabel, this);
    if (pNewChild)
        insert(pNewChild->getLabel(), pNewChild);
    return pNewChild;
}


void ContextNode::getAllContexts(ContextList &list)
{
    if (m_pContext)
        list.add(m_pContext, 0);
    iterator iter = begin();
    while (iter != end())
    {
        iter.second()->getAllContexts(list);
        iter = next(iter);
    }

}


