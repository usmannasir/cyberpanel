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
#include <util/gfactory.h>
#include <util/duplicable.h>

GFactory::GFactory()
{}
GFactory::~GFactory()
{
    m_typeRegistry.release_objects();
    m_objRegistry.release_objects();
}

Duplicable *GFactory::getObj(const char *pName, const char *pType)
{
    _store::iterator iter = m_objRegistry.find(pName);
    if (iter != m_objRegistry.end())
        return iter.second();
    _store::iterator proto = m_typeRegistry.find(pType);
    if (proto == m_typeRegistry.end())
        return NULL;
    Duplicable *pObj = proto.second()->dup(pName);
    if (pObj)
        m_objRegistry.insert(pObj->getName(), pObj);
    return pObj;
}

Duplicable *GFactory::remove(_store *pStore, const char *pName)
{
    _store::iterator iter = pStore->remove(pName);
    if (iter != pStore->end())
        return iter.second();
    else
        return NULL;
}

int GFactory::registerType(Duplicable *pType)
{
    if (!pType)
        return LS_FAIL;
    m_typeRegistry.insert(pType->getName(), pType);
    return 0;
}


