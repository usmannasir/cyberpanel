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
#include "ceheader.h"
#include "dirhashcacheentry.h"
#include <lsr/ls_fileio.h>

#include <http/httpresp.h>
#include <util/ni_fio.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>
#include <util/datetime.h>

DirHashCacheEntry::DirHashCacheEntry()
    : CacheEntry()
    , m_lastCheck(-1)
{
}


DirHashCacheEntry::~DirHashCacheEntry()
{
    if (getFdStore() != -1)
        close(getFdStore());

}
//<"LSCH"><CeHeader><CacheKey><ResponseHeader><ResponseBody>
int DirHashCacheEntry::loadCeHeader()
{
    int fd = getFdStore();
    if (fd == -1)
    {
        errno = EBADF;
        return LS_FAIL;
    }
    if (nio_lseek(fd, getStartOffset(), SEEK_SET) == -1)
        return LS_FAIL;
    char achBuf[CACHE_ENTRY_MAGIC_LEN + sizeof(CeHeader) ];
    int  *pId = (int *)achBuf;
    if (nio_read(fd, achBuf, CACHE_ENTRY_MAGIC_LEN + sizeof(CeHeader))
        < CACHE_ENTRY_MAGIC_LEN + (int)sizeof(CeHeader))
        return LS_FAIL;
    if (*pId != CE_ID)
        return LS_FAIL;
    memmove(&getHeader(), &achBuf[CACHE_ENTRY_MAGIC_LEN], sizeof(CeHeader));
    int len = getHeader().m_keyLen;
    if (len > 0)
    {
        char *p = getKey().prealloc(len + 1);
        if (!p)
            return LS_FAIL;
        if (nio_read(fd, p, len) < len)
            return LS_FAIL;
        *(p + len) = 0;
    }
    len = getHeader().m_tagLen;
    if (len > 0)
    {
        char *p = getTag().prealloc(len + 1);
        if (!p)
            return -1;
        if (nio_read(fd, p, len) < len)
            return -1;
        *(p + len) = 0;
    }
    return 0;

}

int DirHashCacheEntry::saveCeHeader()
{
    int fd = getFdStore();
    if (fd == -1)
    {
        errno = EBADF;
        return LS_FAIL;
    }
    if (nio_lseek(fd, getStartOffset(), SEEK_SET) == -1)
        return LS_FAIL;
    char achBuf[CACHE_ENTRY_MAGIC_LEN + sizeof(CeHeader) ];
    int *pId = (int *)achBuf;
    *pId = CE_ID;
    memmove(&achBuf[CACHE_ENTRY_MAGIC_LEN], &getHeader(), sizeof(CeHeader));
    if (nio_write(fd, achBuf, CACHE_ENTRY_MAGIC_LEN + sizeof(CeHeader)) <
        CACHE_ENTRY_MAGIC_LEN + (int)sizeof(CeHeader))
        return LS_FAIL;
    if (getHeader().m_keyLen > 0)
    {
        if (nio_write(fd, getKey().c_str(), getHeader().m_keyLen) <
            getHeader().m_keyLen)
            return LS_FAIL;
    }
    if (getHeader().m_tagLen > 0)
    {
        if (nio_write(fd, getTag().c_str(), getHeader().m_tagLen) <
            getHeader().m_tagLen)
            return LS_FAIL;
    }
    return 0;
}

int DirHashCacheEntry::allocate(int size)
{
    int fd = getFdStore();
    if (fd == -1)
    {
        errno = EBADF;
        return LS_FAIL;
    }
    struct stat st;
    if (fstat(fd, &st) == -1)
        return LS_FAIL;
    if (st.st_size < size)
    {
        if (ftruncate(fd, size) == -1)
            return LS_FAIL;
    }
    return 0;
}

int DirHashCacheEntry::releaseTmpResource()
{
    int fd = getFdStore();
    if (fd != -1)
    {
        close(fd);
        setFdStore(-1);
    }
    return 0;
}

int DirHashCacheEntry::saveRespHeaders(HttpRespHeaders *pHeader)
{
    int total = 0;
    IOVec iov;
    const char *pKey;
    int keyLen;

    pKey = pHeader->getHeader(HttpRespHeaders::H_X_LITESPEED_TAG, &keyLen);
    if (pKey && keyLen > 0)
    {
        setTag(pKey, keyLen);
        //getHeader().m_tagLen = keyLen;
        if (ls_fio_write(getFdStore(), pKey, keyLen) <
            keyLen)
            return -1;
        pHeader->del(HttpRespHeaders::H_X_LITESPEED_TAG);
    }
    int addCrlf = 1;
    total = pHeader->appendToIov(&iov, addCrlf);
    if (!addCrlf)
    {
        iov.append("\r\n", 2);
        total += 2;
    }
    if (nio_writev(getFdStore(), iov.get(), iov.len()) < total)
        return LS_FAIL;
    pKey = pHeader->getHeader(HttpRespHeaders::H_LAST_MODIFIED, &keyLen);
    if (pKey)
        getHeader().m_tmLastMod = DateTime::parseHttpTime(pKey);
    /*
     * FIXME: need to locate etag header location
        pHeader->getHeader( HttpRespHeaders::H_ETAG, &pKey, &keyLen);
        if ( pKey )
        {
            getHeader().m_offETag = m_iEtagStarts;
            getHeader().m_lenETag = m_iEtagLen;
        }
    */
    return total;

}



