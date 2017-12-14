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
#ifndef STRINGMAP_H
#define STRINGMAP_H


#include <lsdef.h>

#include <string.h>

#include <map>
namespace std
{
template <>
class less< const char * >
{
public:
    bool operator()(const char *const &x, const char *const &y) const
    {   return (strcmp(x, y) < 0); }
};

}

template< class T >
class StringMap : public std::map< const char *, T >
{
    typedef std::map< const char *, T> CONT;

public:
    StringMap(int initsize = 0) {};
    ~StringMap() {};

    typedef typename CONT::iterator iterator;
    typedef typename CONT::const_iterator const_iterator;

    bool insert(const char *pKey, const T &val)
    {
        typename std::pair< iterator, bool > ret;
        ret = CONT::insert(std::make_pair(pKey, val));
        return ret.second;
    }
    bool insertUpdate(const char *pKey, const T &val)
    {
        typename std::pair< iterator, bool > ret;
        ret = CONT::insert(std::make_pair(pKey, val));
        if (!ret.second)
            ret.first->second = val;
        return true;
    }

    const_iterator find(const char *pKey) const
    {
        return CONT::find(pKey);
    }

    iterator find(const char *pKey)
    {
        return CONT::find(pKey);
    }

    size_t remove(const char *pKey)
    {
        return CONT::erase(pKey);
    }

    void release_objects()
    {
        iterator iter;
        for (iter = CONT::begin(); iter != CONT::end();)
        {
            T &p = iter->second;
            CONT::erase(iter);
            delete p;
            iter = CONT::begin();
        }
    }


    LS_NO_COPY_ASSIGN(StringMap);
};

#endif
