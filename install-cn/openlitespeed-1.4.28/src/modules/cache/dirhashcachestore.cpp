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
#include <ls.h>
#include "dirhashcachestore.h"
#include "dirhashcacheentry.h"
#include "cachehash.h"

#include <util/datetime.h>
#include <util/stringtool.h>
#include <util/ni_fio.h>

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define DHCS_SOURCE_MATCH   1
#define DHCS_DEST_CHECK     2

DirHashCacheStore::DirHashCacheStore()
    : CacheStore()
{
}


DirHashCacheStore::~DirHashCacheStore()
{
    release_objects();
}


int DirHashCacheStore::clearStrage()
{
    //rename root directory
    //fork and delete root directory
    return 0;
}

int DirHashCacheStore::updateEntryState(DirHashCacheEntry *pEntry)
{
    struct stat st;
    if (fstat(pEntry->getFdStore(), &st) == -1)
        return -1;
    pEntry->m_lastCheck = DateTime::s_curTime;
    pEntry->setLastAccess(DateTime::s_curTime);
    pEntry->m_lastMod   = st.st_mtime;
    pEntry->m_inode     = st.st_ino;
    pEntry->m_lSize     = st.st_size;
    return 0;
}

int DirHashCacheStore::isEntryExist(const CacheHash &hash, const char *pSuffix,
                                    struct stat *pStat, int isPrivate)
{
    char achBuf[4096];
    struct stat st;
    int n = buildCacheLocation(achBuf, 4096, hash, isPrivate);
    if (pSuffix)
        strcpy(&achBuf[n], pSuffix);
    if (!pStat)
        pStat = &st;
    if (nio_stat(achBuf, pStat) == 0)
        return 1;
    return 0;
}

int DirHashCacheStore::isEntryUpdating(const CacheHash &hash, int isPrivate)
{
    struct stat st;
    if ((isEntryExist(hash, ".tmp", &st, isPrivate) == 1) &&
        (DateTime::s_curTime - st.st_mtime <= 300))
        return 1;
    return 0;
}

int DirHashCacheStore::isEntryStale(const CacheHash &hash, int isPrivate)
{
    struct stat st;
    if (isEntryExist(hash, ".S", &st, isPrivate) == 1)
        return 1;
    return 0;
}

int DirHashCacheStore::processStale(CacheEntry *pEntry, char *pBuf, int pathLen)
{
    int dispose = 0;
    if (DateTime::s_curTime - pEntry->getExpireTime() > pEntry->getMaxStale())
        {
        g_api->log(NULL, LSI_LOG_DEBUG, "[CACHE] [%p] has expired, dispose"
                   , pEntry);

        getManager()->incStats(pEntry->isPrivate(), offsetof(cachestats_t,
                               expired));

        dispose = 1;
    }
    else
    {
        if (!pEntry->isStale())
        {
            pEntry->setStale(1);
            if (!pathLen)
                pathLen = buildCacheLocation(pBuf, 4096, pEntry->getHashKey(),
                                             pEntry->isPrivate());
            if (renameDiskEntry(pEntry, pBuf, NULL, ".S",
                                DHCS_SOURCE_MATCH | DHCS_DEST_CHECK) != 0)
            {
                g_api->log(NULL, LSI_LOG_DEBUG, "[CACHE] [%p] is stale, [%s] mark stale"
                           , pEntry, pBuf);
                dispose = 1;
            }

        }
        if (!pEntry->isUpdating())
        {
            if (isEntryUpdating(pEntry->getHashKey(), pEntry->isPrivate()))
                pEntry->setUpdating(1);
        }
    }
    return dispose;
}


CacheEntry *DirHashCacheStore::getCacheEntry(CacheHash &hash,
        CacheKey *pKey, int maxStale, int32_t lastCacheFlush)
{
    char achBuf[4096] = "";
    int fd;
    //FIXME: look up cache entry in memory, then on disk
    CacheStore::iterator iter = find(hash.getKey());
    CacheEntry *pEntry = NULL;
    int dispose = 0;
    int stale = 0;
    int pathLen = 0;
    int ret = 0;

    if (iter != end())
    {
        pEntry = iter.second();

        if (pEntry->isUnderConstruct())
            return pEntry;

        int lastCheck = ((DirHashCacheEntry *)pEntry)->m_lastCheck;

        if ((DateTime::s_curTime != lastCheck)
            || (lastCheck == -1))   //This entry is being written to disk
        {
            pathLen = buildCacheLocation(achBuf, 4096, hash,
                                         pEntry->isPrivate());
            if (isChanged((DirHashCacheEntry *)pEntry, achBuf, pathLen))
            {
                g_api->log(NULL, LSI_LOG_DEBUG, "[CACHE] [%p] path [%s] has been modified "
                           "on disk, mark dirty", pEntry, achBuf);

                //updated by another process, do not remove current object on disk
                erase(iter);
                addToDirtyList(pEntry);
                pEntry = NULL;
                iter = end();
            }
        }
    }
    if ((pEntry == NULL) || (pEntry->getFdStore() == -1))
    {
        if (!pathLen)
            pathLen = buildCacheLocation(achBuf, 4096, hash,
                                         pKey->m_pIP != NULL);

        fd = ::open(achBuf, O_RDONLY);
        if (fd == -1)
        {
            strcpy(&achBuf[pathLen], ".S");
            fd = ::open(achBuf, O_RDONLY);
            achBuf[pathLen] = 0;
            if (fd == -1)
            {
                if (errno != ENOENT)
                {
                    strcpy(&achBuf[pathLen], ": open() failed");
                    perror(achBuf);
                }
                if (pEntry)
                    CacheStore::dispose(iter, 1);

                getManager()->incStats(pKey->m_pIP != NULL, offsetof(cachestats_t,
                                       misses));

                return NULL;
            }
            stale = 1;
        }
        ::fcntl(fd, F_SETFD, FD_CLOEXEC);
        if (pEntry)
            pEntry->setFdStore(fd);
        //LS_INFO( "getCacheEntry(), open fd: %d, entry: %p", fd, pEntry ));
    }
    if (!pEntry)
    {
        pEntry = new DirHashCacheEntry();
        pEntry->setFdStore(fd);
        pEntry->setHashKey(hash);
        //pEntry->setKey( hash, pURI, iURILen, pQS, iQSLen, pIP, ipLen, pCookie, cookieLen );
        pEntry->loadCeHeader();
        //assert( pEntry->verifyHashKey() == 0 );
        updateEntryState((DirHashCacheEntry *)pEntry);
        if (stale)
            pEntry->setStale(1);
        pEntry->setMaxStale(maxStale);
    }

    if (pEntry->isStale() || DateTime::s_curTime > pEntry->getExpireTime())
    {
        dispose = processStale(pEntry, achBuf, pathLen);
    }
    g_api->log(NULL, LSI_LOG_DEBUG,
               "[CACHE] check [%p] against cache manager, tag: '%s' \n",
               pEntry, pEntry->getTag().c_str());

    if (pEntry->getHeader().m_tmCreated <= lastCacheFlush)
    {
        g_api->log(NULL, LSI_LOG_DEBUG,
                   "[CACHE] [%p] has been flushed, dispose.\n", pEntry);
        dispose = 1;
    }
    
    if (!dispose )
    {
        int flag = getManager()->isPurged(pEntry, pKey, (lastCacheFlush >= 0));
        if (flag)
        {
            g_api->log(NULL, LSI_LOG_DEBUG,
                       "[CACHE] [%p] has been purged by cache manager, %s",
                       pEntry, (flag & PDF_STALE) ? "stale" : "dispose");
            if (flag &PDF_STALE)
                dispose = processStale(pEntry, achBuf, pathLen);
            else
                dispose = 1;
        }
    }

    if (dispose)
    {
        if (iter != end())
            CacheStore::dispose(iter, 1);
        else
        {
            if (!achBuf[0])
                buildCacheLocation(achBuf, 4096, hash, pEntry->isPrivate());
            delete pEntry;
            unlink(achBuf);
        }
        return NULL;
    }

    if ((ret = pEntry->verifyKey(pKey)) != 0)
    {
        g_api->log(NULL, LSI_LOG_DEBUG,
                   "[CACHE] [%p] does not match cache key, key confliction detect, do not use [ret=%d].\n"
                   , pEntry, ret);

        getManager()->incStats(pEntry->isPrivate(), offsetof(cachestats_t,
                               collisions));

        if (iter == end())
            delete pEntry;
        return NULL;
    }
    if (iter == end())
        insert((char *)pEntry->getHashKey().getKey(), pEntry);
    return pEntry;

}

int DirHashCacheStore::buildCacheLocation(char *pBuf, int len,
        const CacheHash &hash, int isPrivate)
{
    const unsigned char *achHash = hash.getKey();
    int n = snprintf(pBuf, len, "%s%s%x/%x/%x/", getRoot().c_str(),
                     isPrivate ? "priv/" : "",
                     (achHash[0]) >> 4, achHash[0] & 0xf, (achHash[1]) >> 4);
    StringTool::hexEncode((char *)achHash, HASH_KEY_LEN, &pBuf[n]);
    n += 2 * HASH_KEY_LEN;
    return n;
}

class TempUmask
{
public:
    TempUmask(int newumask)
    {
        m_umask = umask(newumask);
    }
    ~TempUmask()
    {
        umask(m_umask);
    }
private:
    int m_umask;
};


static int createMissingPath(char *pPath, char *pPathEnd, int isPrivate)
{
    struct stat st;
    pPathEnd[-2] = 0;
    if ((nio_stat(pPath, &st) == -1) && (errno == ENOENT))
    {
        pPathEnd[-4] = 0;
        if ((nio_stat(pPath, &st) == -1) && (errno == ENOENT))
        {
            if (isPrivate)
            {
                pPathEnd[-6] = 0;
                if ((nio_stat(pPath, &st) == -1) && (errno == ENOENT))
                {
                    if ((mkdir(pPath, 0770) == -1) && (errno != EEXIST))
                        return -1;
                }
                pPathEnd[-6] = '/';
            }
            if ((mkdir(pPath, 0770) == -1) && (errno != EEXIST))
                return -1;
        }
        pPathEnd[-4] = '/';
        if (mkdir(pPath, 0770) == -1)
            return -1;
    }
    pPathEnd[-2] = '/';
    if (mkdir(pPath, 0770) == -1)
        return -1;
    return 0;

}

CacheEntry *DirHashCacheStore::createCacheEntry(
    const CacheHash &hash, CacheKey *pKey, int force)
{
    char achBuf[4096];
    char *pPathEnd;
    int n = buildCacheLocation(achBuf, 4096, hash, pKey->m_pIP != NULL);
    struct stat st;
    TempUmask tumsk(0007);

//    if ( stat( achBuf, &st ) == 0 )
//    {
//        if ( !force )
//            return NULL;
//        //FIXME: rename the cache entry to make it dirty
//    }
//    else
    {
        strcpy(&achBuf[n], ".tmp");
        if (nio_stat(achBuf, &st) == 0)
        {
            //in progress
            if (DateTime::s_curTime - st.st_mtime > 120)
                unlink(achBuf);
            else
                return NULL;
        }
    }

    pPathEnd = &achBuf[n - 2 * HASH_KEY_LEN - 1];
    *pPathEnd = 0;

    if ((nio_stat(achBuf, &st) == -1) && (errno == ENOENT))
    {
        if (createMissingPath(achBuf, pPathEnd,
                              pKey->isPrivate()) == -1)
            return NULL;

    }
    *pPathEnd = '/';

    int fd = ::open(achBuf, O_RDWR | O_CREAT | O_TRUNC | O_EXCL, 0660);
    if (fd == -1)
        return NULL;
    ::fcntl(fd, F_SETFD, FD_CLOEXEC);
    //LS_INFO( "createCacheEntry(), open fd: %d", fd ));

    CacheEntry *pEntry = new DirHashCacheEntry();
    pEntry->setFdStore(fd);
    pEntry->setKey(hash, pKey);
    if (pKey->m_pIP && pKey->m_ipLen > 0)
        pEntry->getHeader().m_flag |= CeHeader::CEH_PRIVATE;
    //Do not save now since tag is not ready, will call it later
    //pEntry->saveCeHeader();

    //update current entry
    CacheStore::iterator iter = find(hash.getKey());
    if (iter != end())
        iter.second()->setUpdating(1);
    return pEntry;
}

// remove:  0  do not remove temp file
//          1  remove temp file without checking
//          -1 check temp file inode then remove
void DirHashCacheStore::cancelEntry(CacheEntry *pEntry, int remove)
{
    char achBuf[4096];
    CacheStore::iterator iter = find(pEntry->getHashKey().getKey());
    if (iter != end())
        iter.second()->setUpdating(0);
    if (remove)
    {
        int n = buildCacheLocation(achBuf, 4096, pEntry->getHashKey(),
                                   pEntry->isPrivate());
        strcpy(&achBuf[n], ".tmp");
        if ((pEntry->getFdStore() != -1) && remove == -1)
        {
            struct stat stFd;
            struct stat stDir;
            fstat(pEntry->getFdStore(), &stFd);
            if ((nio_stat(achBuf, &stDir) != 0) ||
                (stFd.st_ino != stDir.st_ino))    //tmp has been modified by someone else
                remove = 0;
        }
        if (remove)
            unlink(achBuf);
    }
    close(pEntry->getFdStore());
    pEntry->setFdStore(-1);
    delete pEntry;

}


CacheEntry *DirHashCacheStore::getCacheEntry(const char *pKey,
        int keyLen)
{
    return NULL;
}

CacheEntry *DirHashCacheStore::getWriteEntry(const char *pKey,
        int keyLen, const char *pHash)
{
    return NULL;
}

int DirHashCacheStore::saveEntry(CacheEntry *pEntry)
{

    return 0;
}

void DirHashCacheStore::removePermEntry(CacheEntry *pEntry)
{
    char achBuf[4096];
    buildCacheLocation(achBuf, 4096, pEntry->getHashKey(),
                       pEntry->isPrivate());
    unlink(achBuf);
}
/*
void DirHashCacheStore::renameDiskEntry( CacheEntry * pEntry )
{
    char achBuf[4096];
    char achBufNew[4096];
    buildCacheLocation( achBuf, 4096, pEntry->getHashKey() );
    strcpy( achBufNew, achBuf );
    strcat( achBufNew, ".d" );
    rename( achBuf, achBufNew );
    //unlink( achBuf );
}
*/

/*
int DirHashCacheStore::dirty( const char * pKey, int keyLen )
{

}
*/

int DirHashCacheStore::isChanged(CacheEntry *pEntry, const char *pPath,
                                 int len)
{
    DirHashCacheEntry *pE = (DirHashCacheEntry *) pEntry;
    pE->m_lastCheck = DateTime::s_curTime;

    struct stat st;
    int ret = nio_stat(pPath, &st);
    if (ret == -1)
    {
        strcpy((char *)pPath + len, ".S");
        ret = nio_stat(pPath, &st);
        *((char *)pPath + len) = 0;
        if (ret == -1)
            return 1;
        pEntry->setStale(1);
        strcpy((char *)pPath + len, ".tmp");
        ret = nio_stat(pPath, &st);
        *((char *)pPath + len) = 0;
        pEntry->setUpdating(ret == 0);

    }
    if ((st.st_mtime != pE->m_lastMod) ||
        (st.st_ino  != pE->m_inode) ||
        (st.st_size != pE->m_lSize))
        return 1;
    return 0;
}

int DirHashCacheStore::renameDiskEntry(CacheEntry *pEntry, char *pFrom,
                                       const char *pFromSuffix, const char *pToSuffix, int validate)
{
    struct stat stFromFd;
    struct stat stFromDir;
    struct stat stTo;
    char achFrom[4096];
    char achTo[4096];
    int fd = pEntry->getFdStore();
    if (!pFrom)
        pFrom = achFrom;
    int n = buildCacheLocation(pFrom, 4090, pEntry->getHashKey(),
                               pEntry->isPrivate());
    if (n == -1)
        return -1;
    memmove(achTo, pFrom, n + 1);
    if (pFromSuffix)
        strcat(&pFrom[n], pFromSuffix);
    if (pToSuffix)
        strcat(&achTo[n], pToSuffix);
    if (validate & DHCS_SOURCE_MATCH)
    {
        fstat(fd, &stFromFd);
        if (nio_stat(pFrom, &stFromDir) == -1)
            return -2;
        if (stFromFd.st_ino !=
            stFromDir.st_ino)    //tmp has been modified by someone else
            return -2;
    }
    if ((validate & DHCS_DEST_CHECK)
        && (stat(achTo, &stTo) != -1))        // old
    {
        if (stFromFd.st_mtime >= stTo.st_mtime)
            unlink(achTo);
        else
            return -3;
    }

    if (rename(pFrom, achTo) == -1)
        return -1;
    return 0;

}

int DirHashCacheStore::publish(CacheEntry *pEntry)
{
    char achTmp[4096];
    int fd = pEntry->getFdStore();
    if (fd == -1)
    {
        errno = EBADF;
        return -1;
    }
    pEntry->getHeader().m_tmExpire += DateTime::s_curTime -
                                      pEntry->getHeader().m_tmCreated;
    if (nio_lseek(fd, pEntry->getStartOffset() + 4, SEEK_SET) == -1)
        return -1;
    if (nio_write(fd, &pEntry->getHeader(), sizeof(CeHeader)) <
        (int)sizeof(CeHeader))
        return -1;

    int ret = renameDiskEntry(pEntry, achTmp, ".tmp", NULL,
                              DHCS_SOURCE_MATCH | DHCS_DEST_CHECK);
    if (ret)
        return ret;

    int len = strlen(achTmp);
    achTmp[len - 3] = 'S';
    achTmp[len - 2] = 0;
    unlink(achTmp);

    CacheStore::iterator iter = find(pEntry->getHashKey().getKey());
    if (iter != end())
        dispose(iter, 0);

    updateEntryState((DirHashCacheEntry *)pEntry);
    insert((char *)pEntry->getHashKey().getKey(), pEntry);
    getManager()->incStats(pEntry->isPrivate(), offsetof(cachestats_t,
                           created));

    return 0;
}



