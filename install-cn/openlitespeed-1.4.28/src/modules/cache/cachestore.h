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
#ifndef CACHESTORE_H
#define CACHESTORE_H


#include <lsdef.h>
#include <util/hashstringmap.h>
#include <util/gpointerlist.h>
#include <util/autostr.h>
#include <inttypes.h>
#include "cachemanager.h"

#define MAX_STALE_AGE 600

class CacheEntry;
class CacheHash;
struct CacheKey;
class CacheManager;

class CacheStore : public HashStringMap<CacheEntry *>
{
public:
    CacheStore();

    virtual ~CacheStore();

    int reset();

    int initManager();

    virtual int clearStrage() = 0;

    virtual CacheEntry *getCacheEntry(CacheHash &hash,
                                      CacheKey *pKey, int maxStale,
                                      int32_t lastCacheFlush) = 0;

    virtual CacheEntry *createCacheEntry(const CacheHash &hash,
                                         CacheKey *pKey,
                                         int force) = 0;

//    virtual CacheEntry * getCacheEntry( const char * pKey, int keyLen ) = 0;

//    virtual CacheEntry * getWriteEntry( const char * pKey, int keyLen,
//                        const char * pHash ) = 0;

    virtual int saveEntry(CacheEntry *pEntry) = 0;

    virtual void cancelEntry(CacheEntry *pEntry, int remove) = 0;

    //virtual int dirty( const char * pKey, int keyLen ) = 0;
    virtual int publish(CacheEntry *pEntry) = 0;

    //virtual int isDirty( CacheEntry * pEntry, long tmCur ) = 0;


    virtual void removePermEntry(CacheEntry *pEntry) = 0;

    virtual int stale(CacheEntry *pEntry);

    virtual int dispose(CacheStore::iterator iter, int isRemovePermEntry);

    int     purge(CacheEntry  *pEntry);
    int     refresh(CacheEntry  *pEntry);

    void houseKeeping();

    void setStorageRoot(const char *pRoot);
    const AutoStr2 &getRoot() const
    {
        return m_sRoot;
    }


    void addToDirtyList(CacheEntry *pEntry)
    {   m_dirtyList.push_back(pEntry);        }

    CacheManager *getManager()   {   return m_pManager;    }


    const AutoStr2 *getName() const {   return &m_sName;     }

//     void setMaxObjSize(long objSize)
//     {
//         m_iMaxObjSize = objSize;
//     }
//     long getMaxObjSize()
//     {
//         return m_iMaxObjSize;
//     }

protected:
    virtual int renameDiskEntry(CacheEntry *pEntry, char *pFrom,
                                const char *pFromSuffix, const char *pToSuffix, int validate) = 0;

private:
    int m_iTotalEntries;
    int m_iTotalHit;
    int m_iTotalMiss;

    TPointerList< CacheEntry >       m_dirtyList;
    CacheManager                    *m_pManager;


    AutoStr2  m_sRoot;
    AutoStr2  m_sName;
};

#endif

