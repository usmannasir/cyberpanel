/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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
#ifndef GMAP_H
#define GMAP_H

#include <lsr/ls_map.h>
#include <lsr/ls_internal.h>

//#define GMAP_DEBUG

class GMap : private ls_map_t
{
private:
    GMap(const GMap &rhs);
    void operator=(const GMap &rhs);
public:

    class GMapNode : private ls_mapnode_t
    {
        friend class GMap;

        //Forbidden functions
        GMapNode &operator++();
        GMapNode operator++(int);
        GMapNode &operator--();
        GMapNode operator--(int);
    public:
        const void *getKey() const      {   return pkey;  }
        void       *getValue() const    {   return pvalue;}
    };

    typedef GMapNode *iterator;
    typedef const GMapNode *const_iterator;

    typedef ls_map_value_compare value_compare;
    typedef ls_map_foreach_fn for_each_fn;
    typedef ls_map_foreach2_fn for_each2_fn;

public:
    GMap(value_compare vc, ls_xpool_t *pool = NULL)
    {   ls_map(this, vc, pool);    }

    ~GMap()
    {   clear();    }

    void        clear()                 {   ls_map_clear(this);  }
    void        swap(GMap &rhs)      {   ls_map_swap(this, &rhs); }
    bool        empty() const           {   return sizenow == 0; }
    size_t      size() const            {   return sizenow;  }
    value_compare    val_comp() const    {   return vc_fn;    }

    iterator        begin()             {   return (iterator)ls_map_begin(this); }
    iterator        end()               {   return (iterator)ls_map_end(this);   }
    const_iterator  begin() const       {   return ((GMap *)this)->begin(); }
    const_iterator  end() const         {   return ((GMap *)this)->end();   }

    iterator find(const void *pKey) const
    {
        return (iterator)(*find_fn)((GMap *)this, pKey);
    }

    int insert(const void *pKey, void *pValue)
    {
        return (*insert_fn)(this, pKey, pValue);
    }

    void *update(const void *pKey, void *pValue, iterator node = NULL)
    {
        return (*update_fn)(this, pKey, pValue, node);
    }

    void *detachNode(iterator node)
    {
        return ls_map_detachnode(this, node);
    }

    int attachNode(const void *pKey, void *pVal)
    {
        return ls_map_attachnode(this, pKey, pVal);
    }

    void *deleteNode(iterator node)
    {
        return ls_map_deletenode(this, node);
    }

    iterator next(iterator iter)
    {
        return (iterator)ls_map_next(this, iter);
    }

    const_iterator next(const_iterator iter) const
    {
        return (const_iterator)ls_map_next((GMap *)this, (iterator)iter);
    }

    int for_each(iterator beg, iterator end, for_each_fn fun)
    {
        return ls_map_foreach(this, beg, end, fun);
    }

    int for_each2(iterator beg, iterator end, for_each2_fn fun, void *pUData)
    {
        return ls_map_foreach2(this, beg, end, fun, pUData);
    }

#ifdef LSR_MAP_DEBUG
    static void printTree(GMap *pThis)
    {   ls_map_printTree(pThis);  }
#endif
};



template< class T >
class TMap
    : public GMap
{
private:
    TMap(const TMap &rhs);
    void operator=(const TMap &rhs);
public:
    class iterator
    {
        GMap::iterator m_iter;
    public:
        iterator()
        {}

        iterator(GMap::iterator iter) : m_iter(iter)
        {}
//         iterator( GMap::const_iterator iter )
//             : m_iter( (GMap::iterator)iter )
//         {}

        iterator(const iterator &rhs) : m_iter(rhs.m_iter)
        {}

        const void *first() const
        {  return  m_iter->getKey();   }

        T second() const
        {   return (T)(m_iter->getValue());   }

        operator GMap::iterator()
        {   return m_iter;  }

    };
    typedef iterator const_iterator;

    TMap(GMap::value_compare cf)
        : GMap(cf)
    {};
    ~TMap() {};

    int insert(const void *pKey, const T *val)
    {   return GMap::insert(pKey, (void *)val);  }

    void *update(const void *pKey, const T *val, TMap::iterator node = NULL)
    {   return GMap::update(pKey, (void *)val, (GMap::iterator)node);  }

    iterator find(const void *pKey)
    {   return GMap::find(pKey);   }

    T *detachNode(TMap::iterator node)
    {   return GMap::detachNode(node);  }

    int attachNode(const void *pKey, const T *val)
    {   return GMap::attachNode(pKey, (void *)val); }

    iterator begin()
    {   return GMap::begin();        }

    static int deleteObj(TMap::iterator iter/* GMap::iterator iter */)
    {
        delete(T)(iter->second());
        return 0;
    }

    void release_objects()
    {
        GMap::for_each(begin(), end(), deleteObj);
        GMap::clear();
    }

};

#endif // GMAP_H


