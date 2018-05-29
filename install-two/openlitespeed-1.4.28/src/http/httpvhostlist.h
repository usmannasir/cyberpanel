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
#ifndef HTTPVHOSTLIST_H
#define HTTPVHOSTLIST_H



#include <util/gpointerlist.h>

class HttpVHost;
class HttpVHostMapImpl;

class VHostList : public TPointerList<HttpVHost>
{
public:
    void releaseUnused();

};

class HttpVHostMap
{
private:
    HttpVHostMapImpl *m_impl;
    HttpVHostMap(const HttpVHostMap &rhs) {}
    void operator=(const HttpVHostMap &rhs) {}
public:
    HttpVHostMap();
    ~HttpVHostMap();
    int add(HttpVHost *pHost);
    int remove(HttpVHost *pHost);
    HttpVHost *get(const char *pName) const;
    HttpVHost *get(int index)
    const;    //The index here just base on the order in the map, not added order
    int size() const;
    void appendTo(VHostList &list);
    void swap(HttpVHostMap &rhs);
    void moveNonExist(HttpVHostMap &rhs);
    void onTimer();
    void onTimer30Secs();
    void offsetChroot(const char *pChroot, int len);
    int  writeStatusReport(int fd) const;
    int  writeRTReport(int fd) const;
    void release_objects();
    static void incRef(HttpVHost *pHost);
    static void decRef(HttpVHost *pHost);
    static const char *getName(HttpVHost *pHost);
    static const char *addMatchName(HttpVHost *pHost, const char *pName);
};

#endif
