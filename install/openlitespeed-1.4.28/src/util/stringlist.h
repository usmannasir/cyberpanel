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
#ifndef STRINGLIST_H
#define STRINGLIST_H



#include <util/gpointerlist.h>
class AutoStr2;
class StringList: public TPointerList<AutoStr2>
{
    void operator=(const StringList &rhs);
public:
    StringList()    {}
    ~StringList();
    StringList(const StringList &rhs);
    const AutoStr2 *add(const char *pStr, int len);
    const AutoStr2 *add(const char *pStr);
    const AutoStr2 *find(const char *pString) const;
    int split(const char *pBegin, const char *pEnd, const char *delim);
    void remove(const char *pString);
    void clear();
    void sort();
    AutoStr2 *bfind(const char *pStr) const;
    void insert(AutoStr2 *pDir);
    AutoStr2 *const *lower_bound(const char *pStr) const;
};

#endif
