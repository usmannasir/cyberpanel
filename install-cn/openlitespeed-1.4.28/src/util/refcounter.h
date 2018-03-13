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
#ifndef REFCOUNTER_H
#define REFCOUNTER_H


#include <lsdef.h>

class RefCounter
{
    int     m_iRef;

public:
    RefCounter() : m_iRef(0) {};
    ~RefCounter() {};
    int incRef()            {   return ++m_iRef;    }
    int decRef()            {   return --m_iRef;    }
    int incRef(int n)     {   return m_iRef += n; }
    int decRef(int n)     {   return m_iRef -= n; }
    int getRef() const      {   return m_iRef;      }
    void reset()    { m_iRef = 0; }

    LS_NO_COPY_ASSIGN(RefCounter);
};

#endif
