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
#ifndef DENIEDDIR_H
#define DENIEDDIR_H


#include <util/gpointerlist.h>

class DirItem;

class DeniedDir : public TPointerList<DirItem>
{
private:

    DeniedDir(const DeniedDir &rhs);
    void operator=(const DeniedDir &rhs);

    const DirItem *find(const char *) const;
    DirItem *find(const char *);
    void insert(DirItem *pDir);
    void sort();

public:
    DeniedDir();
    ~DeniedDir();
    int  addDir(const char *pDir);
    bool isDenied(const char *pPath);
    bool isDenied(iterator iter, const char *pPath);
    void clear();
    iterator lower_bound(const char *pPath);
    iterator next_included(iterator iter, const char *pPath);
    const char *getPath(iterator iter);

};


#endif
