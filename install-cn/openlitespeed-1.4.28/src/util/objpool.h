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
#ifndef OBJPOOL_H
#define OBJPOOL_H

//#define DISABLE_OBJ_POOL


#include <util/gpointerlist.h>

#include <assert.h>
typedef int (*ForEachObj)(void *pObj, void *param);

class GObjPool
{
    int m_iChunkSize;
    int m_iPoolSize;
    GPointerList m_freeList;
    virtual void *newObj() = 0;
    virtual void   releaseObj(void *pObj) = 0;
    GObjPool(const GObjPool &rhs);
    GObjPool &operator=(const GObjPool &rhs);
protected:
    int allocate(int size);
public:

    explicit GObjPool(int chunkSize = 10);
    virtual ~GObjPool()   {}

    void *get()
    {
#ifndef DISABLE_OBJ_POOL
        if (m_freeList.empty())
        {
            if (allocate(m_iChunkSize))
                return NULL;
        }
        void *pObj = m_freeList.back();
        m_freeList.pop_back();
        return pObj;
#else
        return newObj();
#endif
    }

    void recycle(void *pObj)
    {
#ifndef DISABLE_OBJ_POOL
        if (pObj)
            m_freeList.unsafe_push_back(pObj);
#else
        releaseObj(pObj);
#endif
    }

    int get(void **pObj, int n)
    {
#ifndef DISABLE_OBJ_POOL
        if ((int)m_freeList.size() < n)
        {
            if (allocate((n < m_iChunkSize) ? m_iChunkSize : n))
                return 0;
        }
        m_freeList.unsafe_pop_back(pObj, n);
#else
        for (int i = 0; i < n; ++i)
            pObj[i] = newObj();

#endif
        return n;
    }

    void recycle(void **pObj, int n)
    {
#ifndef DISABLE_OBJ_POOL
        if (pObj)
            m_freeList.unsafe_push_back(pObj, n);
#else
        for (int i = 0; i < n; ++i)
            releaseObj(pObj[i]);
#endif
    }

    int size() const                {   return m_freeList.size();   }

    void shrinkTo(int sz)
    {
        int curSize = m_freeList.size();
        int i;
        for (i = 0; i < curSize - sz; ++i)
        {
            void *pObj = m_freeList.back();
            m_freeList.pop_back();
            releaseObj(pObj);
            --m_iPoolSize;
        }
    }

    void applyAll(ForEachObj fn, void *param)
    {
        GPointerList::iterator iter;
        for (iter = begin(); iter != end(); ++iter)
            (*fn)(*iter, param);
    }

    GPointerList::iterator begin()  {   return m_freeList.begin();  }
    GPointerList::iterator end()    {   return m_freeList.end();    }
    void clear()                    {   m_freeList.clear();         }
    int getPoolSize() const         {   return m_iPoolSize;          }
    int getPoolCapacity() const     {   return m_freeList.capacity();   }
};

template <class T >
class ObjPool : public GObjPool
{

    void *newObj()
    {   return new T();  }

    void releaseObj(void *pObj)
    {   delete(T *)pObj; }

public:

    typedef T **iterator;
    explicit ObjPool(int initSize = 10, int chunkSize = 10)
        : GObjPool(chunkSize)
    {
        if (initSize)
            allocate(initSize);
    }

    ~ObjPool()
    {
        release();
    }
    iterator begin()
    {   return (iterator)GObjPool::begin(); }
    iterator end()
    {   return (iterator)GObjPool::end();   }
    T *get()
    {   return (T *)GObjPool::get();     }
    int get(T **pObj, int n)
    {
        return GObjPool::get((void **)pObj, n);
    }

    void release()
    {
        for (iterator iter = begin(); iter != end(); ++iter)
            if (*iter)
                releaseObj(*iter);
        GObjPool::clear();
    }
};




#endif
