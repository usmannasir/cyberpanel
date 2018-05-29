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
#ifndef DIRHASHCACHESTORE_H
#define DIRHASHCACHESTORE_H

#include <lsdef.h>
#include "cachestore.h"


class CacheHash;
class DirHashCacheEntry;

class DirHashCacheStore : public CacheStore
{

    int buildCacheLocation(char *pBuf, int len, const CacheHash &hash,
                           int isPrivate);
    int updateEntryState(DirHashCacheEntry *pEntry);
    int isChanged(CacheEntry *pEntry, const char *pPath, int len);
    int isEntryExists(CacheHash &hash, const char *pSuffix,
                      struct stat *pStat);
    int isEntryUpdating(const CacheHash &hash, int isPrivate);
    int isEntryStale(const CacheHash &hash, int isPrivate);
    int isEntryExist(const CacheHash &hash, const char *pSuffix,
                     struct stat *pStat, int isPrivate);
    
    int processStale(CacheEntry *pEntry, char *pBuf, int pathLen);

protected:
    int renameDiskEntry(CacheEntry *pEntry, char *pFrom,
                        const char *pFromSuffix, const char *pToSuffix, int validate);

public:
    DirHashCacheStore();

    ~DirHashCacheStore();

    virtual int clearStrage();


    virtual CacheEntry *getCacheEntry(CacheHash &hash, CacheKey *pKey,
                                      int maxStale, int32_t lastCacheFlush);

    virtual CacheEntry *createCacheEntry(const CacheHash &hash, CacheKey *pKey,
                                         int force);

    virtual void cancelEntry(CacheEntry *pEntry, int remove);

    virtual CacheEntry *getCacheEntry(const char *pKey, int keyLen);

    virtual CacheEntry *getWriteEntry(const char *pKey, int keyLen,
                                      const char *pHash);

    virtual int saveEntry(CacheEntry *pEntry);

    virtual int publish(CacheEntry *pEntry);

    virtual void removePermEntry(CacheEntry *pEntry);


//    int &ls_fio_stat(char achBuf[4096], struct stat *st);



    LS_NO_COPY_ASSIGN(DirHashCacheStore);
};

#endif
