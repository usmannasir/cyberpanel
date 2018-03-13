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
#include "httpvhostlist.h"
#include <http/httpvhost.h>
#include <util/hashstringmap.h>

#include <stdio.h>
#include <unistd.h>
#include <lsr/ls_strtool.h>

class HttpVHostMapImpl: public HashStringMap<HttpVHost *>
{
    friend class HttpVHostMap;
    ~HttpVHostMapImpl()
    {
        release_objects();
    }

    void appendTo(VHostList &pList)
    {
        iterator iter, iterEnd = end();
        for (iter = begin(); iter != iterEnd; iter = next(iter))
        {
            if (iter.second()->getRef() == 0)
                delete iter.second();
            else
                pList.push_back(iter.second());
        }
        clear();
    }


    void moveNonExist(HttpVHostMapImpl &rhs)
    {
        for (iterator iter = rhs.begin(); iter != rhs.end();)
        {
            if (find(iter.first()) == end())
            {
                iterator iterMove = iter;
                iter = next(iter);
                insert(iterMove.first(), iterMove.second());
                rhs.erase(iterMove);
            }
            else
                iter = next(iter);
        }
    }
    int writeRTReport(int fd) const
    {
        const_iterator iter;
        const_iterator iterEnd = end();
        char achBuf[1024];
        for (iter = begin(); iter != iterEnd; iter = next(iter))
        {
            iter.second()->getReqStats()->finalizeRpt();
            int len = ls_snprintf(achBuf, 1024, "REQ_RATE [%s]: "
                                  "REQ_PROCESSING: %d, REQ_PER_SEC: %d, TOT_REQS: %d\n",
                                  iter.first(), iter.second()->getRef(),
                                  iter.second()->getReqStats()->getRPS(),
                                  iter.second()->getReqStats()->getTotal());
            iter.second()->getReqStats()->reset();
            if (::write(fd, achBuf, len) != len)
                return LS_FAIL;
        }
        return 0;
    }

    int writeStatusReport(int fd) const
    {
        const_iterator iter;
        const_iterator iterEnd = end();
        char achBuf[1024];
        for (iter = begin(); iter != iterEnd; iter = next(iter))
        {
            if (strcmp(iter.first(), DEFAULT_ADMIN_SERVER_NAME) != 0)
            {
                int len = ls_snprintf(achBuf, 1024, "VHOST [%s] %d\n", iter.first(),
                                      (iter.second()->isEnabled() != 0));
                if (::write(fd, achBuf, len) != len)
                    return LS_FAIL;
            }
        }
        return 0;
    }

    static int callTimer(const void *pKey, void *pData)
    {   ((HttpVHost *)pData)->onTimer();  return 0;  }

    static int callTimer30Secs(const void *pKey, void *pData)
    {   ((HttpVHost *)pData)->onTimer30Secs();   return 0; }


    void onTimer()
    {
        for_each(begin(), end(), callTimer);
    }
    void onTimer30Secs()
    {
        for_each(begin(), end(), callTimer30Secs);
    }
    void offsetChroot(const char *pChroot, int len)
    {
        const_iterator iter;
        const_iterator iterEnd = end();
        for (iter = begin(); iter != iterEnd; iter = next(iter))
            iter.second()->offsetChroot(pChroot, len);
    }
};

HttpVHostMap::HttpVHostMap()
    : m_impl(new HttpVHostMapImpl())
{

}

HttpVHostMap::~HttpVHostMap()
{
    delete m_impl;
}

int HttpVHostMap::add(HttpVHost *pHost)
{
    if (pHost != NULL)
    {
        HttpVHostMapImpl::const_iterator iter;
        HttpVHostMapImpl::const_iterator iterEnd = m_impl->end();
        for (iter = m_impl->begin(); iter != iterEnd; iter = m_impl->next(iter))
        {
            if (iter.second() == pHost)
                return LS_FAIL;
        }

        return !m_impl->insert(pHost->getName(), pHost);
    }
    else
        return LS_FAIL;
}

int HttpVHostMap::remove(HttpVHost *pHost)
{
    if (pHost != NULL)
    {
        m_impl->remove(pHost->getName());
        return 0;
    }
    else
        return LS_FAIL;
}

HttpVHost *HttpVHostMap::get(const char *pName) const
{
    if (pName == NULL)
        return NULL;
    HttpVHostMapImpl::const_iterator iter = m_impl->find(pName);
    if (iter == m_impl->end())
        return NULL;
    else
    {
//        if ( iter.second() == NULL )
//        {
//        }
//        if ( iter.second() != NULL )
//        {
//        }
        return iter.second();
    }
}

HttpVHost *HttpVHostMap::get(int index) const
{
    if (index < 0 || index >= size())
        return NULL;

    HttpVHostMapImpl::const_iterator iter = m_impl->begin();
    for (int i = 0; i < index ; ++i)
        iter = m_impl->next(iter);
    return iter.second();
}

int HttpVHostMap::size() const
{
    return m_impl->size();
}

void HttpVHostMap::swap(HttpVHostMap &rhs)
{
    HttpVHostMapImpl *temp;
    temp = m_impl;
    m_impl = rhs.m_impl;
    rhs.m_impl = temp;
}

void HttpVHostMap::appendTo(VHostList &pList)
{
    m_impl->appendTo(pList);
}

void HttpVHostMap::moveNonExist(HttpVHostMap &rhs)
{
    m_impl->moveNonExist(*(rhs.m_impl));
}


void HttpVHostMap::onTimer()
{
    m_impl->onTimer();
}

void HttpVHostMap::onTimer30Secs()
{
    m_impl->onTimer30Secs();
}

void HttpVHostMap::offsetChroot(const char *pChroot, int len)
{
    m_impl->offsetChroot(pChroot, len);
}


int HttpVHostMap::writeRTReport(int fd) const
{
    return m_impl->writeRTReport(fd);
}

int HttpVHostMap::writeStatusReport(int fd) const
{
    return m_impl->writeStatusReport(fd);
}

void HttpVHostMap::release_objects()
{
    m_impl->release_objects();
}

void VHostList::releaseUnused()
{
    iterator iter;
    for (iter = begin(); iter != end();)
    {
        if ((*iter)->getRef() <= 0)
        {
            delete(*iter);
            erase(iter);
        }
        else
            ++iter;
    }
}

void HttpVHostMap::incRef(HttpVHost *pHost)
{
    pHost->incMappingRef();
}
void HttpVHostMap::decRef(HttpVHost *pHost)
{
    pHost->decMappingRef();
}

const char *HttpVHostMap::getName(HttpVHost *pHost)
{
    return pHost->getName();
}

const char *HttpVHostMap::addMatchName(HttpVHost *pHost,
                                       const char *pName)
{
    return pHost->addMatchName(pName)->c_str();
}



