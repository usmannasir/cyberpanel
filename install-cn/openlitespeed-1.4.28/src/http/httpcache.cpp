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
#include "httpcache.h"
#include <util/datetime.h>


HttpCache::HttpCache(int initSize)
    : CacheDataMap(initSize)
{
}

HttpCache::~HttpCache()
{
}
void HttpCache::releaseAll()
{
    dirtyAll();
    for (DirtyCacheList::iterator iter = m_dirty.begin();
         iter != m_dirty.end(); ++iter)
        recycle(*iter);
}

int HttpCache::dirty(CacheElement *data)
{
    assert(data);
    remove(data->getKey());
    if (data->isInUse())
        m_dirty.push_back(data);
    else
        recycle(data);
    return 0;
}

void HttpCache::dirtyAll()
{
    iterator iterEnd = end();
    for (iterator iter = begin(); iter != iterEnd; iter = next(iter))
        m_dirty.push_back(iter.second());
    clear();
}

#define CACHE_DATA_TIMEOUT 300
#define CACHE_TIMEOUT 60 * 60

void HttpCache::clean()
{
    CacheElement *pData;
    iterator iterEnd = end();
    for (iterator iter = begin(); iter != iterEnd;)
    {
        pData = iter.second();
        if (pData->getRef() == 0)
        {
            long t = DateTime::s_curTime - pData->getLastAccess();
            if (t > CACHE_TIMEOUT)
            {
                iterator iterDel = iter;
                iter = next(iter);
                erase(iterDel);
                recycle(pData);
                continue;
            }
            else if (t > CACHE_DATA_TIMEOUT)
                pData->release();
        }
        iter = next(iter);
    }
    for (DirtyCacheList::iterator it = m_dirty.begin(); it != m_dirty.end();)
    {
        if (!(*it)->isInUse())
        {
            recycle(*it);
            it = m_dirty.erase(it);
        }
        else
            ++it;
    }
}


void HttpCache::onTimer()
{
    clean();
}


