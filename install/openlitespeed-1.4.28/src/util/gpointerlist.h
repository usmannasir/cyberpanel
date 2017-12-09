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
#ifndef GPOINTERLIST_H
#define GPOINTERLIST_H


#include <lsr/ls_ptrlist.h>

#include <stddef.h>
#include <string.h>
#include <sys/types.h>

typedef int (*gpl_for_each_fn)(void *);

class GPointerList : private ls_ptrlist_t
{
    int allocate(int capacity)
    {   return ls_ptrlist_reserve(this, capacity);   }
    GPointerList(const GPointerList &rhs)
    {   ls_ptrlist_copy(this, &rhs);   }
    void operator=(const GPointerList &rhs);
public:
    typedef void **iterator;
    typedef void *const *const_iterator;

    GPointerList()
    {   ls_ptrlist(this, 0);   }
    explicit GPointerList(size_t initSize)
    {   ls_ptrlist(this, initSize);   }
    ~GPointerList()
    {   ls_ptrlist_d(this);   }

    ssize_t size() const    {   return pend - pstore;   }
    bool empty() const      {   return pend == pstore;  }
    bool full() const       {   return pend == pstoreend;   }
    size_t capacity() const {   return pstoreend - pstore;  }
    void clear()            {   pend = pstore;          }
    iterator begin()        {   return pstore;            }
    iterator end()          {   return pend;              }
    const_iterator begin() const    {   return pstore;    }
    const_iterator end() const      {   return pend;      }
    void *back() const             {   return *(pend - 1);   }
    int reserve(size_t sz)        {   return allocate(sz);  }
    int resize(size_t sz) {   return ls_ptrlist_resize(this, sz); }
    int grow(size_t sz)   {   return allocate(sz + capacity()); }

    iterator erase(iterator iter)
    {
        /** Do not use *(-- to avoid trigger compiler bug */
        --pend;
        *iter = *pend;
        return iter;
    }

    int  push_back(void *pPointer)
    {   return ls_ptrlist_pushback(this, pPointer);   }
    int  push_back(const void *pPointer)
    {   return push_back((void *)pPointer);   }
    int  push_back(const GPointerList &list)
    {   return ls_ptrlist_pushback2(this, &list);   }
    void unsafe_push_back(void *pPointer)
    {   *pend++ = pPointer;   }
    void unsafe_push_back(void **pPointer, int n)
    {   ls_ptrlist_unsafepushbackn(this, pPointer, n);   }

    void *pop_back()
    {
        /** Do not use *(-- to avoid trigger compiler bug */
        --pend;
        return *pend;
    }
    void unsafe_pop_back(void **pPointer, int n)
    {   ls_ptrlist_unsafepopbackn(this, pPointer, n);   }
    int pop_front(void **pPointer, int n)
    {   return ls_ptrlist_popfront(this, pPointer, n);   }

    void *&operator[](size_t off)        {   return *(pstore + off);   }
    void *&operator[](size_t off) const  {   return *(pstore + off);   }

    void sort(int(*compare)(const void *, const void *))
    {   ls_ptrlist_sort(this, compare);   }
    void swap(GPointerList &rhs)
    {   ls_ptrlist_swap(this, &rhs);   }

    const_iterator lower_bound(const void *pKey,
                               int(*compare)(const void *, const void *)) const
    {   return ls_ptrlist_lowerbound(this, pKey, compare);   }
    const_iterator bfind(const void *pKey,
                         int(*compare)(const void *, const void *)) const
    {   return ls_ptrlist_bfind(this, pKey, compare);   }
    int for_each(iterator beg, iterator end, gpl_for_each_fn fn)
    {   return ls_ptrlist_foreach(beg, end, fn);   }

};

template< typename T >
class TPointerList : public GPointerList
{
    void operator=(const TPointerList &rhs);
    TPointerList(const TPointerList &rhs);
public:
    typedef T **iterator;
    typedef T *const *const_iterator;
    TPointerList() {}

    explicit TPointerList(size_t initSize)
        : GPointerList(initSize)
    {}
    iterator begin()        {   return (iterator)GPointerList::begin();   }
    iterator end()          {   return (iterator)GPointerList::end();    }
    const_iterator begin() const
    {   return (const_iterator)GPointerList::begin();    }
    const_iterator end() const
    {   return (const_iterator)GPointerList::end();      }

    T *pop_back()
    {   return (T *)GPointerList::pop_back();   }
    T *&operator[](size_t off)
    {   return (T *&)GPointerList::operator[](off); }

    T *&operator[](size_t off) const
    {   return (T *&)GPointerList::operator[](off); }

    T *back() const
    {   return (T *)GPointerList::back();    }

    iterator erase(iterator iter)
    {   return (iterator)GPointerList::erase((GPointerList::iterator)iter);    }

    void release_objects()
    {
        for (iterator iter = begin(); iter < end(); ++iter)
            if (*iter) delete *iter;
        GPointerList::clear();
    }

    int copy(const TPointerList &rhs)
    {
        release_objects();
        for (const_iterator iter = rhs.begin(); iter < rhs.end(); ++iter)
            push_back(new T(**iter));
        return size();
    }

    int append(const TPointerList &rhs)
    {
        for (const_iterator iter = rhs.begin(); iter < rhs.end(); ++iter)
            if (find(*iter) == end())
                push_back(new T(**iter));
        return size();
    }

    const_iterator find(const T *obj) const
    {
        for (const_iterator iter = begin(); iter < end(); ++iter)
            if (**iter == *obj)
                return iter;
        return end();
    }


    iterator lower_bound(const void *pKey,
                         int(*compare)(const void *, const void *)) const
    {   return (iterator)GPointerList::lower_bound(pKey, compare);   }

    iterator bfind(const void *pKey,
                   int(*compare)(const void *, const void *)) const
    {   return (iterator)GPointerList::bfind(pKey, compare);  }

    int for_each(iterator beg, iterator end, gpl_for_each_fn fn)
    {   return GPointerList::for_each((void **)beg, (void **)end, fn);    }
};

#endif
