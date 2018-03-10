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
#include "cacheentry.h"

#include <string.h>
#include <unistd.h>

#include <util/dlinkqueue.h>
#include <ls.h>

CacheEntry::CacheEntry()
    : m_lastAccess(0)
    , m_iHits(0)
//     , m_iTestHits(0)
    , m_iMaxStale(0)
    , m_needDelay(0)
    , m_startOffset(0)
    , m_fdStore(-1)
    , m_pWaitQue(NULL)
{
}


CacheEntry::~CacheEntry()
{
    if (m_fdStore != -1)
        close(m_fdStore);
    if (m_pWaitQue)
        delete m_pWaitQue;
}


void CacheEntry::appendToWaitQ(DLinkedObj *pObj)
{
    if (!m_pWaitQue)
        m_pWaitQue = new DLinkQueue();
    m_pWaitQue->append(pObj);
}


int CacheKey::getPrivateId(char *pBuf, char *pBufEnd)
{
    char *p = pBuf;
    if (m_ipLen <= 0)
        return -1;
    if (m_iCookiePrivate > 0)
    {
        if (p + m_iCookiePrivate + 1 > pBufEnd)
            return -1;
        *p++ = '~';
        memmove(p , m_sCookie.c_str() + m_iCookieVary, m_iCookiePrivate);
        p += m_iCookiePrivate;
    }
    if (p + m_ipLen + 1 > pBufEnd)
        return -1;
    *p++ = '@';
    memmove(p, m_pIP, m_ipLen);
    p += m_ipLen;
    *p = 0;
    return p - pBuf;
}


int CacheEntry::setKey(const CacheHash &hash, CacheKey *pKey)
{
    m_hashKey.copy(hash);
    int len = pKey->m_iUriLen + ((pKey->m_iQsLen > 0) ? pKey->m_iQsLen + 1 :
                                 0);
    int l;
    m_header.m_iPrivLen = 0;
    if (pKey->m_ipLen > 0)
    {
        len += pKey->m_ipLen + 1;
        m_header.m_iPrivLen = pKey->m_ipLen + 1;
        if (pKey->m_iCookiePrivate > 0)
        {
            len += pKey->m_iCookiePrivate + 1;
            m_header.m_iPrivLen += pKey->m_iCookiePrivate + 1;
        }
    }
    if (pKey->m_iCookieVary > 0)
        len += pKey->m_iCookieVary + 1;

    char *pBuf = m_sKey.prealloc(len + 1);
    if (!pBuf)
        return -1;
    memmove(pBuf, pKey->m_pUri, pKey->m_iUriLen + 1);
    l = pKey->m_iUriLen;
    if (pKey->m_iQsLen > 0)
    {
        pBuf[ l++ ] = '?';
        memmove(pBuf + l , pKey->m_pQs, pKey->m_iQsLen + 1);
        l += pKey->m_iQsLen;
    }
    if (pKey->m_iCookieVary > 0)
    {
        pBuf[l++] = '#';
        memmove(pBuf + l , pKey->m_sCookie.c_str(), pKey->m_iCookieVary);
        l += pKey->m_iCookieVary;
    }
    if (pKey->m_ipLen > 0)
    {
        if (pKey->m_iCookiePrivate > 0)
        {
            pBuf[l++] = '~';
            memmove(pBuf + l , pKey->m_sCookie.c_str() + pKey->m_iCookieVary,
                    pKey->m_iCookiePrivate);
            l += pKey->m_iCookiePrivate;
        }
        pBuf[l++] = '@';
        memmove(pBuf + l, pKey->m_pIP, pKey->m_ipLen);
        l += pKey->m_ipLen;
    }
    m_header.m_keyLen = len;
    return 0;
}

int CacheEntry::verifyKey(CacheKey *pKey) const
{
    const char *p = m_sKey.c_str();
    if (!p || strncmp(pKey->m_pUri, p, pKey->m_iUriLen) != 0)
        return -1;
    p += pKey->m_iUriLen;
    if (pKey->m_iQsLen > 0)
    {
        if ((*p  != '?') ||
            (memcmp(p + 1, pKey->m_pQs, pKey->m_iQsLen) != 0))
            return -2;
        p += pKey->m_iQsLen + 1;
    }

    if (pKey->m_iCookieVary > 0)
    {
        if ((*p  != '#') ||
            (memcmp(p + 1, pKey->m_sCookie.c_str(), pKey->m_iCookieVary) != 0))
            return -3;
        p += pKey->m_iCookieVary + 1;

    }

    //pKey->m_ipLen < 0 is for the public cache key
    bool isPublic = false;
    if (pKey->m_ipLen < 0)
    {
        pKey->m_ipLen = 0 - pKey->m_ipLen;
        isPublic = true;
    }
    
    if (pKey->m_ipLen > 0)
    {
        if (pKey->m_iCookiePrivate > 0)
        {
            if (!isPublic)
            {
                if ((*p  != '~') ||
                    (memcmp(p + 1, pKey->m_sCookie.c_str() + pKey->m_iCookieVary,
                            pKey->m_iCookiePrivate) != 0))
                    return -4;
            }
            p += pKey->m_iCookiePrivate + 1;
        }
        
        if (!isPublic)
        {
            if ((*p  != '@') ||
                (memcmp(p + 1, pKey->m_pIP, pKey->m_ipLen) != 0))
                return -5;
            p += pKey->m_ipLen + 1;
        }
    }
    if (m_header.m_keyLen - (isPublic ? m_header.m_iPrivLen : 0)
        > p - m_sKey.c_str())
    {
        LSI_DBG(NULL,
                   "[CACHE]CacheEntry::verifyKey failed, keylen %d, privLen %d and check len %ld.\n",
                   m_header.m_keyLen, m_header.m_iPrivLen, p - m_sKey.c_str());
        return -6;
    }
    return 0;
}


void CacheEntry::setTag(const char *pTag, int len)
{
    m_sTag.setStr(pTag, len);
    m_header.m_tagLen = len;
}

