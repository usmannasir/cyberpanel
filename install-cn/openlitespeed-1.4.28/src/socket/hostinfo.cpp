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
#include <string.h>
#include <assert.h>
#include <errno.h>
#include "hostinfo.h"

#define H_BUF_SIZE      8192
#define H_MAX_ENTRIES   36

HostInfo::HostInfo()
{
    init();
}


HostInfo::HostInfo(const hostent &rhs)
{
    init();
    *this = rhs;
}


int HostInfo::init()
{
    memset((hostent *)this, 0, sizeof(hostent));
    m_pBuf = new char[H_BUF_SIZE];
    if (m_pBuf == NULL)
        return ENOMEM;
    h_aliases = (char **)m_pBuf;
    *h_aliases = NULL;
    h_addr_list = (char **)m_pBuf + H_MAX_ENTRIES;
    *h_addr_list = NULL;
    assert((char *)h_addr_list - (char *)h_aliases
           == H_MAX_ENTRIES * sizeof(char *));
    return 0;
}


HostInfo::~HostInfo()
{
    if (m_pBuf)
        delete[] m_pBuf;
}


char *HostInfo::buf_memcpy(char *&pBuf, const char *pSrc, int n)
{
    char *p = pBuf;
    ::memmove(p, pSrc, n);
    pBuf += n;
    return p;
}


char *HostInfo::buf_strncpy(char *&pBuf, const char *pSrc, int n)
{
    int len = strlen(pSrc) + 1;
    return buf_memcpy(pBuf, pSrc, (len > n) ? n : len);
}


void HostInfo::copyMemArray(char **const pDestArray,
                            const char *const *const pArray, int length, char *&pBuf)
{
    if (pArray == NULL)
    {
        *pDestArray = NULL;
        return;
    }
    const char *const *pTemp = (const char *const *) pArray;
    int iSize = 0;
    int iValidLength;
    while (*pTemp)
    {
        iValidLength = (length == -1) ? strlen(*pTemp) + 1 : length;

        *(pDestArray + iSize) = buf_memcpy(pBuf, *pTemp, iValidLength);
        iSize++;
        pTemp++;
    }
    *(pDestArray + iSize) = NULL;

}


HostInfo &HostInfo::operator=(const hostent &rhs)
{
    char *pBuf = m_pBuf + sizeof(char *) * 2 * H_MAX_ENTRIES;
    h_name          = buf_strncpy(pBuf, rhs.h_name, 127);
    h_addrtype      = rhs.h_addrtype;
    h_length        = rhs.h_length;
    copyMemArray(h_aliases, rhs.h_aliases, -1, pBuf);
    copyMemArray(h_addr_list, rhs.h_addr_list, rhs.h_length, pBuf);
    return *this;
}


bool HostInfo::getHostByName(const char *name)
{
    struct hostent *pHosts = NULL;
    int iRetry = 0;
#ifdef gethostbyname_r
    int lh_errno;
    do
    {
        pHosts = ::gethostbyname_r(name, (char *)this, m_pBuf, H_BUF_SIZE,
                                   &lh_errno);
        iRetry ++;
    }
    while ((pHosts == NULL) && (lh_errno == TRY_AGAIN) && (iRetry < 3));
    return (pHosts != NULL);

#else
    do
    {
        pHosts = ::gethostbyname(name);
        iRetry ++;
    }
    while ((pHosts == NULL) && (h_errno == TRY_AGAIN) && (iRetry < 3));
    if (pHosts != NULL)
        *this = *pHosts;
    return (pHosts != NULL);

#endif
}


bool HostInfo::getHostByAddr(const void *addr, int len, int type)
{
    struct hostent *pHosts = NULL;
    int iRetry = 0;
#ifdef gethostbyaddr_r
    int lh_errno;
    do
    {
        pHosts = ::gethostbyaddr_r((const char *)addr, len, type, (char *)this,
                                   m_pBuf, H_BUF_SIZE, &lh_errno);
        iRetry ++;
    }
    while ((pHosts == NULL) && (lh_errno == TRY_AGAIN) && (iRetry < 3));

    return (pHosts != NULL);
#else
    {
        //NOTE: delare a auto-lock
        //AutoLock lock( HostInfoLock.getInstance() );
        do
        {
            pHosts = ::gethostbyaddr((const char *)addr, len, type);
            iRetry ++;
        }
        while ((pHosts == NULL) && (h_errno == TRY_AGAIN) && (iRetry < 3));

        if (pHosts != NULL)
            *this = *pHosts;
    }
    return (pHosts != NULL);

#endif
}

