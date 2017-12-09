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
#ifndef HTTPLISTENERLIST_H
#define HTTPLISTENERLIST_H



#include <util/gpointerlist.h>
class HttpListener;
class HttpVHost;
class HttpListenerList : public TPointerList< HttpListener >
{
    HttpListenerList(const HttpListenerList &rhs);
    void operator=(const HttpListenerList &rhs);
public:
    HttpListenerList();
    ~HttpListenerList();
    int add(HttpListener *pListener);
    int remove(HttpListener *pListener);
    //HttpListener* get( const char * pName ) const;
    HttpListener *get(const char *pName, const char *pAddr);
    void stopAll();
    void suspendAll();
    void suspendSSL();
    void resumeAll();
    void resumeSSL();
    void resumeAllButSSL();
    void endConfig();
    void clear();
    void moveNonExist(HttpListenerList &rhs);
    void removeVHostMappings(HttpVHost *pVHost);
    int  writeStatusReport(int fd);
    int  writeRTReport(int fd);
    void releaseUnused();
    int  saveInUseListnersTo(HttpListenerList &rhs);
    void passListeners();
    void recvListeners();
};

#endif
