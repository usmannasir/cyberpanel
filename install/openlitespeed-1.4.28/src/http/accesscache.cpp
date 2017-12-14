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
#include "accesscache.h"


AccessCache::AccessCache(int initSize)
    : m_cache(initSize)
      //, m_cache6( initSize, GHash::hf_ipv6, GHash::cmp_ipv6 )
{}


int  AccessCache::isAllowed(const struct sockaddr *pAddr)
{
    switch (pAddr->sa_family)
    {
    case AF_INET:
        {
            in_addr_t addr = ((sockaddr_in *)pAddr)->sin_addr.s_addr;
            IPAcc acc = m_cache.find(addr);
            if (acc.isNull())
            {
                int ret = m_accessCtrl.hasAccess(addr);
                m_cache.update(addr, ret);
                return ret;
            }
            return (int)acc.getAccess();
        }
    case AF_INET6:
        {
            in6_addr *addr = &((sockaddr_in6 *)pAddr)->sin6_addr;
            return m_accessCtrl.hasAccess(*addr);
        }
        /*        {
                    in6_addr * addr = &((sockaddr_in6 *)pAddr)->sin6_addr;
                    IPAcc acc = m_cache6.find( *addr );
                    if ( acc.isNull() )
                    {
                        int ret = m_accessCtrl.hasAccess( *addr );
                        m_cache6.add( *addr, ret );
                        return ret;
                    }
                    return (int)acc.getAccess();
                }*/
    }
    return 0;
}


void AccessCache::onTimer()
{
    if (m_cache.size() > 10000)
        m_cache.clear();
    //if ( m_cache6.size() > 10000 )
    //    m_cache6.clear();
}


