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
#ifndef GFACTORY_H
#define GFACTORY_H


#include <lsdef.h>
#include <util/hashstringmap.h>

class Duplicable;

class GFactory
{
    typedef HashStringMap<Duplicable *> _store;

    _store      m_typeRegistry;
    _store      m_objRegistry;
    Duplicable *remove(_store *pStore, const char *pName);

public:
    GFactory();
    ~GFactory();
    Duplicable *getObj(const char *pName, const char *pType);
    Duplicable *removeObj(const char *pName)
    {   return remove(&m_objRegistry, pName);     }
    Duplicable *removeType(const char *pType)
    {   return remove(&m_typeRegistry, pType);    }
    int registerType(Duplicable *pType);


    LS_NO_COPY_ASSIGN(GFactory);
};

#endif
