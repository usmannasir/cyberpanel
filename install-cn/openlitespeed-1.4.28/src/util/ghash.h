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
#ifndef GHASH_H
#define GHASH_H

#include <lsr/ls_hash.h>
#include <lsr/ls_internal.h>

#include <stddef.h>

typedef unsigned long hash_key_t;

class GHash : private ls_hash_t
{
private:
    GHash(const GHash &rhs);
    void operator=(const GHash &rhs);
public:
    class HashElem : private ls_hashelem_t
    {
        friend class GHash;
        void setKey(const void *pKey)
        {   pkey = pKey;  }

        //Forbidden functions
        HashElem &operator++();
        HashElem operator++(int);
        HashElem &operator--();
        HashElem operator--(int);

    public:
        const void *getKey() const  {   return pkey;  }
        void       *getData() const {   return pdata; }
        hash_key_t  getHKey() const {   return hkey;  }
        HashElem   *getNext() const {   return (HashElem *)next; }
        const void *first() const   {   return pkey;  }
        void       *second() const  {   return pdata; }
    };

    typedef HashElem *iterator;
    typedef const HashElem *const_iterator;

    typedef hash_key_t (*hasher)(const void *);
    typedef int (*value_compare)(const void *pVal1, const void *pVal2);
    //typedef int (*for_each_fn)( iterator iter);
    //typedef int (*for_each_fn2)( iterator iter, void *pUData);
    typedef ls_hash_foreach_fn for_each_fn;
    typedef ls_hash_foreach2_fn for_each2_fn;

    static hash_key_t hfString(const void *__s);
    static int  cmpString(const void *pVal1, const void *pVal2);

    static hash_key_t hfCiString(const void *__s);
    static int  cmpCiString(const void *pVal1, const void *pVal2);

    static int  cmpIpv6(const void *pVal1, const void *pVal2);
    static hash_key_t hfIpv6(const void *pKey);

    GHash(size_t init_size, hasher hf, value_compare vc,
          ls_xpool_t *pool = NULL)
    {   ls_hash(this, init_size, hf, vc, pool);    }

    ~GHash()
    {
        ls_hash_d(this);
    }

    void        clear()                     {   ls_hash_clear(this); }
    void        erase(iterator iter)      {   ls_hash_erase(this, iter);   }
    void        swap(GHash &rhs)         {   ls_hash_swap(this, &rhs);    }

    hasher     hash_function() const        {   return hf_fn;    }
    value_compare    value_comp() const     {   return vc_fn;    }
    void        setLoadFactor(int f)      {   if (f > 0)    load_factor = f;  }
    void        setGrowFactor(int f)      {   if (f > 0)    grow_factor = f;  }

    bool        empty() const               {   return sizenow == 0; }
    size_t      size() const                {   return sizenow;      }
    size_t      capacity() const            {   return sizemax;  }

    iterator        begin()                 {   return (iterator)ls_hash_begin(this);    }
    iterator        end()                   {   return NULL;    }
    const_iterator  begin() const           {   return ((GHash *)this)->begin(); }
    const_iterator  end() const             {   return ((GHash *)this)->end();   }

    iterator find(const void *pKey)
    {
        return (iterator)(*find_fn)(this, pKey);
    }

    const_iterator find(const void *pKey) const
    {
        return (const_iterator)((GHash *)this)->find(pKey);
    }

    iterator insert(const void *pKey, void *pValue)
    {
        return (iterator)(*insert_fn)(this, pKey, pValue);
    }

    iterator update(const void *pKey, void *pValue)
    {
        return (iterator)(*update_fn)(this, pKey, pValue);
    }

    iterator next(iterator iter)
    {
        return (iterator)ls_hash_next(this, iter);
    }

    const_iterator next(const_iterator iter) const
    {
        return ((GHash *)this)->next((iterator)iter);
    }

    int for_each(iterator beg, iterator end, for_each_fn fun)
    {
        return ls_hash_foreach(this, beg, end, fun);
    }

    int for_each2(iterator beg, iterator end, for_each2_fn fun, void *pUData)
    {
        return ls_hash_foreach2(this, beg, end, fun, pUData);
    }

};

template< class T >
class THash
    : public GHash
{
private:
    THash(const THash &rhs);
    void operator=(const THash &rhs);
public:
    class iterator
    {
        GHash::iterator m_iter;
    public:
        iterator()
        {}

        iterator(GHash::iterator iter) : m_iter(iter)
        {}
        iterator(GHash::const_iterator iter)
            : m_iter((GHash::iterator)iter)
        {}

        iterator(const iterator &rhs) : m_iter(rhs.m_iter)
        {}

        const void *first() const
        {  return  m_iter->first();   }

        T second() const
        {   return (T)(m_iter->second());   }

        operator GHash::iterator()
        {   return m_iter;  }

    };
    typedef iterator const_iterator;

    THash(int initsize, GHash::hasher hf, GHash::value_compare cf)
        : GHash(initsize, hf, cf)
    {};
    ~THash() {};

    iterator insert(const void *pKey, const T &val)
    {   return GHash::insert(pKey, (void *)val);  }

    iterator update(const void *pKey, const T &val)
    {   return GHash::update(pKey, (void *)val);  }

    iterator find(const void *pKey)
    {   return GHash::find(pKey);   }

    const_iterator find(const void *pKey) const
    {   return GHash::find(pKey);   }

    iterator begin()
    {   return GHash::begin();        }

    static int deleteObj(const void *pKey, void *pData)
    {
        delete(T)(pData);
        return 0;
    }

    void release_objects()
    {
        GHash::for_each(begin(), end(), deleteObj);
        GHash::clear();
    }

};


#endif
