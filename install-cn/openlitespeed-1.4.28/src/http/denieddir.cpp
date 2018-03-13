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
#include "denieddir.h"

#include <lsdef.h>
#include <util/autostr.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

class DirItem
{
public:
    DirItem(const char *path, bool includeSub):
        m_sPath(path), m_bIncludeSub(includeSub) {};
    ~DirItem() {};
    bool isDenied(const char *path);
    const char *getPath() const { return m_sPath.c_str(); }
    bool includeSub() const { return m_bIncludeSub; }
    void setIncludeSub(bool includeSub) { m_bIncludeSub = includeSub ; }

private:
    AutoStr2    m_sPath;
    bool        m_bIncludeSub;
    LS_NO_COPY_ASSIGN(DirItem);
};


bool DirItem::isDenied(const char *path)
{
    if (m_bIncludeSub)
        return (strncmp(m_sPath.c_str(), path, m_sPath.len()) == 0);
    else
        return (strcmp(m_sPath.c_str(), path) == 0);
}


static int compare(const void *val1, const void *val2)
{
    return strcmp((*(const DirItem **)val1)->getPath(),
                  (*(const DirItem **)val2)->getPath());
}


void DeniedDir::sort()
{
    ::qsort(begin(), size(), sizeof(DirItem **), compare);
}


DeniedDir::iterator DeniedDir::lower_bound(const char *pPath)
{
    if (!pPath)
        return NULL;
    int e = size();
    int b = 0;
    while (b != e)
    {
        int m = (b + e) / 2;
        int c = strcmp(pPath, (*(begin() + m))->getPath());
        if (c == 0)
            return begin() + m;
        else if (c < 0)
            e = m;
        else
            b = m + 1;
    }
    if (b == 0)
        return NULL;
    return begin() + b - 1;

}


DirItem *DeniedDir::find(const char *pPath)
{
    DirItem **p = lower_bound(pPath);
    if ((p) && (strcmp(pPath, (*p)->getPath()) == 0))
        return *p;
    return NULL;
}


void DeniedDir::insert(DirItem *pDir)
{
    push_back(pDir);
    sort();
}


DeniedDir::DeniedDir()
{}


DeniedDir::~DeniedDir()
{
    clear();
}


int DeniedDir::addDir(const char *pDir)
{
    while (1)
    {
        //if ( *pDir != '/' )
        //{
        //    LS_ERROR( "[config] failed to add denied dir, need absolute path - %s!", pDir ));
        //    break;
        //}
        int len = strlen(pDir);
        //if ( len >= 256 - 1 )
        //{
        //    LS_ERROR( "[config] denied path is too long - %s!", pDir ));
        //    break;
        //}
        char buf[256];
        bool includeSub = false;
        strcpy(buf, pDir);
        char *pEnd = buf + len - 1;
        if (*(pEnd) == '*')
        {
            includeSub = true;
            *(pEnd) = 0;
        }
        else if (*(pEnd) != '/')
        {
            *(++pEnd) = '/';
            *(++pEnd) = 0;
        }
        //if ( ( GPath::clean(buf) != 0 ) ||!GPath::isValid( buf ) )
        //{
        //    LS_ERROR( "[config] invalid denied path - %s!", buf ));
        //    break;
        //}
        DirItem *pos = find(buf);
        if (pos != NULL)
            pos->setIncludeSub(includeSub);
        else
        {
            DirItem *pItem = new DirItem(buf, includeSub);
            insert(pItem);
        }
        return 0;
    }
    return 1;

}


bool DeniedDir::isDenied(const char *pPath)
{
    DirItem **pos = lower_bound(pPath);
    return isDenied(pos, pPath);
}


bool DeniedDir::isDenied(iterator iter, const char *pPath)
{
    if (iter != NULL)
    {
        if ((*iter)->isDenied(pPath))
            return true;
    }
    return false;
}


void DeniedDir::clear()
{
    release_objects();
}


DeniedDir::iterator DeniedDir::next_included(iterator iter,
        const char *pPath)
{
    if (iter == NULL)
        iter = begin();
    else if (iter != end())
        ++iter;
    if (iter != end())
    {
        if (strncmp((*iter)->getPath(), pPath, strlen(pPath)) == 0)
            return iter;
    }
    return end();
}


const char *DeniedDir::getPath(iterator iter)
{   return (*iter)->getPath();  }


