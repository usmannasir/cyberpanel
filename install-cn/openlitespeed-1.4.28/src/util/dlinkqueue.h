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
#ifndef DLINKQUEUE_H
#define DLINKQUEUE_H


#include <util/linkedobj.h>

class LinkQueue
{
    LinkedObj   m_head;
    int         m_iTotal;

    LinkQueue(const LinkQueue &rhs);
    LinkQueue &operator=(const LinkQueue &rhs);

public:
    LinkQueue()
        : m_iTotal(0)
    {}
    ~LinkQueue() {}
    int size() const    {   return m_iTotal;    }
    void push(LinkedObj *pObj)
    {   m_head.addNext(pObj);     ++m_iTotal;     }
    LinkedObj *pop()
    {
        if (m_iTotal)
        {   --m_iTotal; return m_head.removeNext(); }
        return NULL;
    }
    LinkedObj *begin() const
    {   return m_head.next();       }
    LinkedObj *end() const
    {   return NULL;                }
    LinkedObj *head()   {   return  &m_head;      }
    LinkedObj *removeNext(LinkedObj *pObj)
    {   --m_iTotal; return pObj->removeNext();  }
    void addNext(LinkedObj *pObj, LinkedObj *pNext)
    {   ++m_iTotal;  pObj->addNext(pNext);  }
};

class DLinkQueue
{
    DLinkedObj      m_head;
    int             m_iTotal;

    DLinkQueue(const DLinkQueue &rhs);
    DLinkQueue &operator=(const DLinkQueue &rhs);

public:
    DLinkQueue()
        : m_head(&m_head, &m_head)
        , m_iTotal(0)
    {}
    ~DLinkQueue()
    {}
    int size() const    {   return m_iTotal;    }
    bool empty() const  {   return m_head.next() == &m_head;   }

    void append(DLinkedObj *pReq)
    {
        m_head.prev()->addNext(pReq);
        ++m_iTotal;
    }

    void push_front(DLinkedObj *pReq)
    {
        m_head.next()->addPrev(pReq);
        ++m_iTotal;
    }

    void insert(DLinkedObj *pReq, DLinkedObj *pReqToInsert)
    {
        pReq->addPrev(pReqToInsert);
        ++m_iTotal;
    }

    void insert_after(DLinkedObj *pReq, DLinkedObj *pReqToAppend)
    {
        pReq->addNext(pReqToAppend);
        ++m_iTotal;
    }

    void remove(DLinkedObj *pReq)
    {
        assert(pReq != &m_head);
        if (pReq->next())
        {
            pReq->remove();
            --m_iTotal;
        }
    }

    DLinkedObj *pop_front()
    {
        if (m_head.next() != &m_head)
        {
            --m_iTotal;
            return m_head.removeNext();
        }
        assert(m_iTotal == 0);
        return NULL;
    }

    void pop_all()
    {
        while (m_head.next() != &m_head)
        {
            --m_iTotal;
            m_head.removeNext();
        }
    }


    DLinkedObj *begin()
    {   return m_head.next();    }
    DLinkedObj *end()
    {   return &m_head;          }

};


template< typename T>
class TDLinkQueue : public DLinkQueue
{
public:
    TDLinkQueue()   {}
    ~TDLinkQueue()  {}

    void release_objects()
    {
        T *p;
        while ((p = pop_front()) != NULL)
            delete p;
    }

    void append(T *pReq)
    {   DLinkQueue::append(pReq);     }

    void push_front(T *pReq)
    {   DLinkQueue::push_front(pReq); }

    void remove(T *pReq)
    {   DLinkQueue::remove(pReq);     }

    T *next(const T *pObj)
    {   return (T *)pObj->next();       }

    T *pop_front()
    {   return (T *)DLinkQueue::pop_front();  }

    T *begin()
    {   return (T *)DLinkQueue::begin();      }

    T *end()
    {   return (T *)DLinkQueue::end();    }

};


#endif
