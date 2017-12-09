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
#ifndef HTTPCACHE_H
#define HTTPCACHE_H



#include <http/cacheelement.h>
#include <util/gpointerlist.h>
#include <util/hashstringmap.h>

#include <assert.h>

typedef HashStringMap<CacheElement *> CacheDataMap;
typedef TPointerList<CacheElement> DirtyCacheList;

class HttpCache : public CacheDataMap
{
    DirtyCacheList m_dirty;

    void release();

    HttpCache(const HttpCache &rhs);
    void operator=(const HttpCache &rhs);
    void clean();
    void dirtyAll();

protected:
    virtual CacheElement *allocElement() = 0;
    virtual void recycle(CacheElement *pData) = 0;
public:
    HttpCache(int initSize);
    virtual ~HttpCache();
    void releaseAll();
    int add(CacheElement *data)
    {
        assert(data != NULL);
        return insert(data->getKey(), data) ? 0 : -1;
    }
    int dirty(CacheElement *data);
    void onTimer();
};

#endif
