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
#ifndef RESOURCEPOOL_H
#define RESOURCEPOOL_H

#include <util/objpool.h>
#include <util/tsingleton.h>

class AutoBuf;
typedef ObjPool<AutoBuf>                AutoBufPool;

class ResourcePool : public TSingleton<ResourcePool>
{
    friend class TSingleton<ResourcePool>;

    AutoBufPool m_poolAutoBuf;
private:
    ResourcePool(const ResourcePool &rhs);
    void operator=(const ResourcePool &rhs);
public:
    ResourcePool();
    ~ResourcePool();

    void recycle(AutoBuf *pBuf);

    AutoBuf *getAutoBuf()
    {   return m_poolAutoBuf.get();     }

    void releaseAll();

    void onTimer();
};



#endif //RESOURCEPOOL_H



