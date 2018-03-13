/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2016  LiteSpeed Technologies, Inc.                 *
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
#include "cacheconfig.h"
#include "ls.h"

#include "dirhashcachestore.h"
#include <http/httpvhost.h>

CacheConfig::CacheConfig()
    : m_iCacheConfigBits(0)
    , m_iCacheFlag(0x027C)   //0000 0010 0111 1100
    , m_defaultAge(3600)
    , m_privateAge(3600)
    , m_iMaxStale(200)
    , m_lMaxObjSize(10000000)
      //, m_iBypassPercentage(5)
    , m_iLevele(0)
    , m_iOnlyUseOwnUrlExclude(0)
    , m_iOwnStore(0)
    , m_iAddEtag(0)
    , m_pUrlExclude(NULL)
    , m_pParentUrlExclude(NULL)
    , m_pVHostMapExclude(NULL)
    , m_pStore(NULL)
{
}


CacheConfig::~CacheConfig()
{
    if (m_pUrlExclude)
        delete m_pUrlExclude;
    if (m_iLevele == LSI_CFG_SERVER && m_pVHostMapExclude)
        delete m_pVHostMapExclude;
    if (m_iOwnStore && m_pStore)
        delete m_pStore;

    m_pUrlExclude = NULL;
    m_pParentUrlExclude = NULL;
    m_pVHostMapExclude = NULL;
    m_pStore = NULL;
}


void CacheConfig::inherit(const CacheConfig *pParent)
{
    if (pParent)
    {
        if (!(m_iCacheConfigBits & CACHE_MAX_AGE_SET))
            m_defaultAge = pParent->m_defaultAge;
        if (!(m_iCacheConfigBits & CACHE_PRIVATE_AGE_SET))
            m_privateAge = pParent->m_privateAge;
        if (!(m_iCacheConfigBits & CACHE_STALE_AGE_SET))
            m_iMaxStale = pParent->m_iMaxStale;
        if (!(m_iCacheConfigBits & CACHE_MAX_OBJ_SIZE))
            m_lMaxObjSize = pParent->m_lMaxObjSize;
        m_iCacheFlag = (m_iCacheFlag & m_iCacheConfigBits) |
                       (pParent->m_iCacheFlag & ~m_iCacheConfigBits);
        m_pParentUrlExclude = pParent->m_pUrlExclude;
        m_pUrlExclude = NULL;
        m_pVHostMapExclude = pParent->m_pVHostMapExclude;
        m_iOnlyUseOwnUrlExclude = 0;
        m_pStore = pParent->getStore();
        m_iOwnStore = 0;
        m_iAddEtag = pParent->getAddEtagType();
    }
}


void CacheConfig::apply(const CacheConfig *pParent)
{
    if (pParent)
    {
        if (pParent->m_iCacheConfigBits & CACHE_MAX_AGE_SET)
            m_defaultAge = pParent->m_defaultAge;
        if (pParent->m_iCacheConfigBits & CACHE_PRIVATE_AGE_SET)
            m_privateAge = pParent->m_privateAge;
        if (pParent->m_iCacheConfigBits & CACHE_STALE_AGE_SET)
            m_iMaxStale = pParent->m_iMaxStale;
        if (pParent->m_iCacheConfigBits & CACHE_MAX_OBJ_SIZE)
            m_lMaxObjSize = pParent->m_lMaxObjSize;

        m_iCacheFlag = (pParent->m_iCacheFlag & pParent->m_iCacheConfigBits) |
                       (m_iCacheFlag & ~pParent->m_iCacheConfigBits);
    }

}

#define CACHE_LITEMAGE_BITS (CACHE_QS_CACHE | CACHE_REQ_COOKIE_CACHE \
                             | CACHE_IGNORE_REQ_CACHE_CTRL_HEADER \
                             | CACHE_IGNORE_RESP_CACHE_CTRL_HEADER \
                             | CACHE_RESP_COOKIE_CACHE \
                             | CACHE_CHECK_PUBLIC  )

int CacheConfig::isLitemagReady()
{
    if ((m_iCacheFlag & (CACHE_LITEMAGE_BITS | CACHE_ENABLE_PUBLIC
                         | CACHE_ENABLE_PRIVATE)) ==  CACHE_LITEMAGE_BITS)
    {
        if (m_lMaxObjSize >= 500 * 1024)
            return 1;
    }
    return 0;
}


void CacheConfig::setLitemageDefault()
{
    setConfigBit(CACHE_LITEMAGE_BITS, 1);
    setConfigBit(CACHE_ENABLE_PUBLIC | CACHE_ENABLE_PRIVATE, 0);
    setMaxObjSize(1024 * 1024);
}


