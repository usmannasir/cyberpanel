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
#ifndef CONTEXTLIST_H
#define CONTEXTLIST_H



#include <util/autostr.h>
#include <util/gpointerlist.h>

class HttpContext;
class ContextMatchList : public TPointerList< HttpContext >
{
public:
    ContextMatchList()
        : TPointerList< HttpContext >(2)
    {}
    ~ContextMatchList() { clear(); }
};
class ContextList : public TPointerList< HttpContext >
{
    int         m_size;
    AutoStr     m_sTags;
    ContextList(const ContextList &rhs);
    void operator=(const ContextList &rhs);
public:
    ContextList();
    ~ContextList();
    void release();
    int add(HttpContext *pContext, int release);
    int merge(const ContextList *rhs, int release);
    void releaseUnused(long curTime, long timeout);
};


#endif
