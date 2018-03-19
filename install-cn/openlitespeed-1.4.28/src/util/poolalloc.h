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
#ifndef _POOLALLOC_H_
#define _POOLALLOC_H_

#include <util/pool.h>

template<class T>
class PoolAllocator
{
    void operator=(const PoolAllocator &rhs);
public:
    Pool *m_pPool;
    PoolAllocator(const PoolAllocator &) throw() { }

    typedef size_t          size_type;
    typedef ptrdiff_t       difference_type;
    typedef T            *pointer;
    typedef const T      *const_pointer;
    typedef T            &reference;
    typedef const T      &const_reference;
    typedef T             value_type;

    template <class V> struct rebind
    {
        typedef PoolAllocator<V> other;
    };

    PoolAllocator(Pool *pool = NULL) throw()
        : m_pPool(pool)
    {}
#ifndef WIN32
    template <class U> PoolAllocator(const PoolAllocator<U> &rhs) throw()
        : m_pPool(rhs.m_pPool)  {}
#endif

    ~PoolAllocator() throw() {}

    pointer address(reference __x) const { return &__x; }
    const_pointer address(const_reference __x) const { return &__x; }

    pointer allocate(size_t __n, const void * = 0)
    {
        return (pointer) Pool::allocate(__n * sizeof(T));
    }

    // __p is not permitted to be a null pointer.
    void deallocate(void *__p, size_t __n)
    {
        Pool::deallocate(__p, __n * sizeof(T));
    }

    size_t max_size() const throw()
    {
        return size_t(-1) / sizeof(T);
    }

    void construct(pointer __p, const T &__val) { new(__p) T(__val); }
    void destroy(pointer __p) { __p->~T(); }

    char *_Charalloc(size_type _Size)
    {
        return (char *)(Pool::allocate(_Size));
    }


};

#endif //_POOLALLOC_H_


