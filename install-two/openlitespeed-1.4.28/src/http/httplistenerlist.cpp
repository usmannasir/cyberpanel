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
#include "httplistenerlist.h"
#include <http/httplistener.h>
#include <http/vhostmap.h>
#include <log4cxx/logger.h>

#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static int stopListener(void *pListener)
{   ((HttpListener *)pListener)->stop(); return 0;  }

static int suspendListener(void *pListener)
{   ((HttpListener *)pListener)->suspend(); return 0;  }

static int suspendSSLListener(void *pListener)
{
    if (((HttpListener *)pListener)->isSSL())
        ((HttpListener *)pListener)->suspend();
    return 0;
}

static int resumeListener(void *pListener)
{
    ((HttpListener *)pListener)->resume();
    return 0;
}

static int resumeSSLListener(void *pListener)
{
    if (((HttpListener *)pListener)->isSSL())
        ((HttpListener *)pListener)->resume();
    return 0;
}

static int resumeButSSLListener(void *pListener)
{
    if (!((HttpListener *)pListener)->isSSL())
        ((HttpListener *)pListener)->resume();
    return 0;
}

static int endConfigListener(void *pListener)
{
    ((HttpListener *)pListener)->endConfig();
    return 0;
}


HttpListenerList::HttpListenerList()
{
}

HttpListenerList::~HttpListenerList()
{
    release_objects();
}

static int s_compare(const void *p1, const void *p2)
{
    return strcmp((*((HttpListener **)p1))->getName(),
                  (*((HttpListener **)p2))->getName());
}
static int f_compare(const void *p1, const void *p2)
{
    return strcmp((const char *)p1,
                  ((HttpListener *)p2)->getName());
}

int HttpListenerList::add(HttpListener *pListener)
{
    assert(pListener != NULL);
    push_back(pListener);
    sort(s_compare);
    return 0;
}

int HttpListenerList::remove(HttpListener *pListener)
{
    assert(pListener != NULL);
    iterator iter = bfind(pListener->getName(), f_compare);
    if (iter != end())
    {
        erase(iter);
        sort(s_compare);
    }
    return 0;
}

//HttpListener* HttpListenerList::get( const char * pName ) const
//{
//    if ( pName == NULL )
//        return NULL;
//    iterator iter = bfind( pName, f_compare );
//    if ( iter == end() )
//        return NULL;
//    else
//        return (*iter);
//}

HttpListener *HttpListenerList::get(const char *pName, const char *pAddr)
{
    iterator iter;
    char achBuf[256];
    if (pName)
    {
        iter = bfind(pName, f_compare);
        if (iter != end())
            return *iter;
    }
    if (pAddr)
    {
        iter = bfind(pAddr, f_compare);
        if (iter != end())
        {
            HttpListener *p = *iter;
            p->setName(pName);
            sort(s_compare);
            return p;
        }
        if (strncmp(pAddr, "0.0.0.0:", 8) == 0)
        {
            snprintf(achBuf, 256, "*:%s", pAddr + 8);
            pAddr = achBuf;
        }
        for (iterator iter = begin(); iter != end(); ++iter)
        {
            if (strcasecmp(pAddr, (*iter)->getAddrStr()) == 0)
            {
                HttpListener *p = *iter;
                p->setName(pName);
                sort(s_compare);
                return p;
            }
        }
    }
    return NULL;
}


void HttpListenerList::stopAll()
{
    for_each(begin(), end(), stopListener);
}

void HttpListenerList::suspendAll()
{
    for_each(begin(), end(), suspendListener);
}

void HttpListenerList::suspendSSL()
{
    for_each(begin(), end(), suspendSSLListener);
}

void HttpListenerList::resumeAll()
{
    for_each(begin(), end(), resumeListener);
}

void HttpListenerList::resumeSSL()
{
    for_each(begin(), end(), resumeSSLListener);
}

void HttpListenerList::resumeAllButSSL()
{
    for_each(begin(), end(), resumeButSSLListener);
}

void HttpListenerList::endConfig()
{
    for_each(begin(), end(), endConfigListener);
}

void HttpListenerList::clear()
{
    release_objects();
}

static int compare_fd(const void *p1, const void *p2)
{
    return (*(const HttpListener **)p1)->getfd() - (*(const HttpListener **)
            p2)->getfd();
}

void HttpListenerList::passListeners()
{
    int startfd = 1000;
    int count = 0;
    int sort = 0;
    for (iterator iter = begin(); iter != end(); ++iter)
    {
        if ((*iter)->getfd() >= 1000)
            sort = 1;
        if ((*iter)->getfd() != -1)
            ++count;
    }
    close(startfd + count);
    if (sort)
        this->sort(compare_fd);
    for (iterator iter = end() - 1; iter >= begin(); --iter)
    {
        if ((*iter)->getfd() != -1)
        {
            --count;
            LS_INFO("Pass listener %s, copy fd %d to %d.", (*iter)->getAddrStr(),
                    (*iter)->getfd(), startfd + count);
            dup2((*iter)->getfd(), startfd + count);
        }
    }
}


void HttpListenerList::recvListeners()
{
    int         startfd = 1000;
    char        achSockAddr[128];
    socklen_t   len;
    struct sockaddr *pAddr = (struct sockaddr *)achSockAddr;
    len = 128;
    if (getpeername(startfd, pAddr, &len) != -1)
        startfd = 300;      // Must not be connected
    else
    {
        len = 128;
        if (getsockname(startfd, pAddr, &len) == -1)
            startfd = 300;  // Must be a server socket
    }
    while (1)
    {
        len = 128;
        if (getpeername(startfd, pAddr, &len) != -1)
            break;      // Must not be connected
        len = 128;
        if (getsockname(startfd, pAddr, &len) == -1)
            break;      // Must be a server socket
        if (pAddr->sa_family != PF_UNIX)
        {
            int fd = dup(startfd);
            HttpListener *pListener = new HttpListener();
            pListener->assign(fd, pAddr);
            push_back(pListener);
            sort(s_compare);
        }
        close(startfd);
        ++startfd;
    }
}



void HttpListenerList::moveNonExist(HttpListenerList &rhs)
{
    for (iterator iter = rhs.begin(); iter != rhs.end();)
    {
        if (bfind((*iter)->getName(), f_compare) == end())
        {
            add(*iter);
            rhs.erase(iter);
        }
        else
            ++iter;
    }
}

void HttpListenerList::removeVHostMappings(HttpVHost *pVHost)
{
    for (iterator iter = begin(); iter != end(); ++iter)
        (*iter)->getVHostMap()->removeVHost(pVHost);
}

int HttpListenerList::writeRTReport(int fd)
{
    return 0;
}

int HttpListenerList::writeStatusReport(int fd)
{
    iterator iter;
    iterator iterEnd = end();
    for (iter = begin(); iter != iterEnd; ++iter)
    {
        if ((*iter)->writeStatusReport(fd) == -1)
            return LS_FAIL;
    }
    return 0;
}

void HttpListenerList::releaseUnused()
{
    iterator iter;
    for (iter = begin(); iter != end();)
    {
        (*iter)->stop();
        if ((*iter)->getVHostMap()->getRef() <= 0)
        {
            delete(*iter);
            erase(iter);
        }
        else
            ++iter;
    }
}

int HttpListenerList::saveInUseListnersTo(HttpListenerList &rhs)
{
    int add = 0;
    iterator iter;
    for (iter = begin(); iter != end();)
    {
        (*iter)->stop();
        if ((*iter)->getVHostMap()->getRef() <= 0)
            delete(*iter);
        else
        {
            rhs.add(*iter);
            add++;
        }
        erase(iter);
    }
    return add;
}




