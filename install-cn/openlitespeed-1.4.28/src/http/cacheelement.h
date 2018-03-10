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
#ifndef CACHEELEMENT_H
#define CACHEELEMENT_H



#include <lsdef.h>
#include <util/refcounter.h>

#include <sys/types.h>


class CacheElement : public RefCounter
{
    time_t  m_lastAccess;
public:
    CacheElement() {};
    virtual ~CacheElement() {};
    bool isInUse() const    {   return getRef() > 0;    }
    time_t getLastAccess() const    {   return m_lastAccess;    }
    void setLastAccess(time_t tm) {   m_lastAccess = tm;      }

    virtual const char *getKey() const = 0;
    virtual int32_t release() = 0;
    LS_NO_COPY_ASSIGN(CacheElement);
};

#endif
