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
#ifndef CONTEXTNODE_H
#define CONTEXTNODE_H


#include <util/hashstringmap.h>

#define HTA_UNKNOWN         0
#define HTA_NONE            1
#define HTA_EXIST           2

class HttpContext;
class ContextList;

class ContextNode : public HashStringMap< ContextNode * >
{

    ContextNode        *m_pParentNode;
    HttpContext        *m_pContext;
    char               *m_pLabel;
    long                m_lHTALastCheck;
    short               m_iHTAState;
    short               m_iRelease;

    ContextNode(const ContextNode &rhs);
    void operator=(const ContextNode &rhs);

public:

    ContextNode(const char *pchLabel, ContextNode *pParentNode);

    const HttpContext *getContext() const  {   return m_pContext ;     }
    HttpContext *getContext()              {   return m_pContext ;     }
    ContextNode *getParentNode() const     {   return m_pParentNode ;  }
    HttpContext *getParentContext();
    void setChildrenParentContext(const HttpContext *pOldParent,
                                  const HttpContext *pNewParent, int noUpdateRedirect);
    const char *getLabel() const            {   return m_pLabel ;       }
    void setLabel(const char *l);

    void removeRedirectContext(HttpContext *pParent);
    void contextInherit(const HttpContext *pRootContext);

    void setRelease(short r)              {   m_iRelease = r;         }
    short getRelease() const                {   return m_iRelease;      }

    void setHTAState(char state)          {   m_iHTAState = state;    }
    short getHTAState()  const              {   return m_iHTAState;     }

    long getLastCheck() const               {   return m_lHTALastCheck; }
    void setLastCheck(long check)         {   m_lHTALastCheck = check;}

    void setContext(HttpContext *pContext) {  m_pContext = pContext;  }
    void setContextUpdateParent(HttpContext *pContext, int noUpdateRedirect);
    ContextNode *insertChild(const char *pchLabel);
    ContextNode *match(const char *pStart);
    ContextNode()
        : HashStringMap< ContextNode * >(10)
        , m_pLabel(NULL)
        , m_lHTALastCheck(0)
        , m_iHTAState(HTA_UNKNOWN)
    {}

    ~ContextNode();
    ContextNode *getChildNode(const char *pStart, long lastCheck = 0)
    {
        iterator iter ;
        iter = find(pStart);
        if (iter == end())
        {
            ContextNode *pNode = insertChild(pStart);
            if (pNode)
                pNode->setLastCheck(lastCheck);
            return pNode;
        }
        else
            return iter.second();
    }
    void getAllContexts(ContextList &list);
};

#endif
