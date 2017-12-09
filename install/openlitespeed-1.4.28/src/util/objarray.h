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
#ifndef OBJARRAY_H
#define OBJARRAY_H

#include <lsr/ls_objarray.h>

#include <string.h>

class ObjArray : private ls_objarray_t
{
private:
    ObjArray(const ObjArray &rhs);
    void operator=(const ObjArray &rhs);
public:
    ObjArray(int objSize)                     {   ls_objarray_init(this, objSize); }
    ~ObjArray() {};

    void    init(int objSize)                 {   ls_objarray_init(this, objSize); }
    void    release(ls_xpool_t *pool)         {   ls_objarray_release(this, pool); }
    void    clear()                             {   sizenow = 0; }

    int     getCapacity() const                 {   return sizemax;     }
    int     getSize() const                     {   return sizenow;     }
    int     getObjSize() const                  {   return objsize;     }
    void   *getArray()                          {   return parray;      }
    const void *getArray() const                {   return parray;      }
    void   *getObj(int index) const             {   return ls_objarray_getobj(this, index);}
    void   *getNew()                            {   return ls_objarray_getnew(this); }

    void    setSize(int size)                 {   ls_objarray_setsize(this, size); }

    void setCapacity(ls_xpool_t *pool, int numObj)
    {   ls_objarray_setcapacity(this, pool, numObj); }

    void guarantee(ls_xpool_t *pool, int numObj)
    {   ls_objarray_guarantee(this, pool, numObj);   }
};

template< class T >
class TObjArray : public ObjArray
{
private:
    TObjArray(const TObjArray &rhs);
    void operator=(const TObjArray &rhs);
public:
    TObjArray()
        : ObjArray(sizeof(T))
    {};
    ~TObjArray() {};

    void    init()                      {   ObjArray::init(sizeof(T));   }
    T      *getArray()                  {   return (T *)ObjArray::getArray(); }
    const T*getArray() const            {   return (const T *)ObjArray::getArray(); }
    T      *getObj(int index) const     {   return (T *)ObjArray::getObj(index);  }
    T      *getNew()                    {   return (T *)ObjArray::getNew(); }
    T      *newObj()                    {   return getNew();    }

    T *begin()      {   return  getArray();    }
    T *end()        {   return (T *)getArray() + getSize();   }

    const T *begin() const     {   return  getArray();    }
    const T *end() const       {   return (const T *)getArray() + getSize();   }

    void copy(TObjArray &other, ls_xpool_t *pool)
    {
        setCapacity(pool, other.getCapacity());
        setSize(other.getSize());
        memmove(getArray(), other.getArray(), getSize() * sizeof(T));
    }
};


#endif //OBJARRAY_H
