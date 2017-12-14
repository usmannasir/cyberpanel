/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013  LiteSpeed Technologies, Inc.                        *
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

#include "shmcachemanager.h"
#include "cacheentry.h"
#include <log4cxx/logger.h>
#include <shm/lsshmhash.h>
#include <util/datetime.h>
#include <util/pcutil.h>

#include <ctype.h>


typedef struct shm_purgedata_s
{
    purgeinfo_t         x_purgeinfo;
    LsShmOffset_t       x_offNext;
} shm_purgedata_t;


/*
 */
static inline int shouldExpireData(
    purgeinfo_t *pData, int32_t sec, int16_t msec)
{
    return ((pData->tmSecs > sec)
            || ((pData->tmSecs == sec) && (pData->tmMsec > msec)));
}


class ShmPurgeData
{
private:
    inline shm_purgedata_t *shmptr() const
    {
        return (shm_purgedata_t *)m_pool->offset2ptr(m_shmoff);
    }

public:

    ShmPurgeData()
        : m_pool(0)
        , m_shmoff(0)
    {}
    ShmPurgeData(LsShmPool *pPool, LsShmOffset_t shmoff)
        : m_pool(pPool)
        , m_shmoff(shmoff)
    {}
    ~ShmPurgeData()
    {}

    void setPool(LsShmPool *pPool)
    {
        m_pool = pPool;
    }

    void setShmOff(LsShmOffset_t shmoff)
    {
        m_shmoff = shmoff;
    }

    LsShmOffset_t getShmOff()
    {
        return m_shmoff;
    }

    void setFlag(int flag)
    {
        shmptr()->x_purgeinfo.flags = flag;
    }

    int16_t getFlag() const
    {
        return shmptr()->x_purgeinfo.flags;
    }

    void setLastPurgeTime(int32_t sec, int16_t msec)
    {
        shmptr()->x_purgeinfo.tmSecs = sec;
        shmptr()->x_purgeinfo.tmMsec = msec;
    }

    int shouldExpire(int32_t sec, int16_t msec)
    {
        return shouldExpireData(&(shmptr()->x_purgeinfo), sec, msec);
    }

private:
    LsShmPool       *m_pool;
    LsShmOffset_t    m_shmoff;
};


typedef struct shm_privpurgedata_s
{
    int32_t          x_tmFlush;
    int16_t          x_msFlush;
    int16_t          x_keyLen;
    LsShmOffset_t    x_listhead;
    int32_t          x_lock;
    int32_t          x_tmLastUpdate;
    char             x_verifykey[16];
} shm_privpurgedata_t;


class ShmPrivatePurgeData
{
public:
    ShmPrivatePurgeData()
        : m_pool(NULL)
        , m_shmoff(0)
    {}
    ShmPrivatePurgeData(LsShmPool *pPool, LsShmOffset_t shmoff)
        : m_pool(pPool)
        , m_shmoff(shmoff)
    {}
    ~ShmPrivatePurgeData()
    {}

    void setPool(LsShmPool *pPool)
    {
        m_pool = pPool;
    }

    void setShmOff(LsShmOffset_t shmoff)
    {
        m_shmoff = shmoff;
    }

    LsShmOffset_t getShmOff()
    {
        return m_shmoff;
    }

    LsShmOffset_t addUpdate(purgeinfo_t *pInfo);
    int shouldPurge(int idTag, int32_t sec, int16_t msec);

    void setLastFlushTime(int32_t sec, int16_t msec)
    {
        shm_privpurgedata_t *pPrivate =
            (shm_privpurgedata_t *)m_pool->offset2ptr(m_shmoff);
        pPrivate->x_tmFlush = sec;
        pPrivate->x_msFlush = msec;

    }

    int isFlushed(int32_t sec, int16_t msec)
    {
        shm_privpurgedata_t *pPrivate =
            (shm_privpurgedata_t *)m_pool->offset2ptr(m_shmoff);
        return (sec < pPrivate->x_tmFlush
                || (sec == pPrivate->x_tmFlush && msec <= pPrivate->x_msFlush));
    }

    int isFetchAll()
    {
        shm_privpurgedata_t *pPrivate =
            (shm_privpurgedata_t *)m_pool->offset2ptr(m_shmoff);
        return pPrivate->x_tmLastUpdate <= pPrivate->x_tmFlush;
    }
    purgeinfo_t *findTagInfo(int idTag);

    static void release(LsShmPool *pPool, shm_privpurgedata_t *pList);

    void lock();
    void unlock();
private:

    LsShmPool       *m_pool;
    LsShmOffset_t    m_shmoff;
};


void ShmPrivatePurgeData::lock()
{
    shm_privpurgedata_t *pList =
        (shm_privpurgedata_t *)m_pool->offset2ptr(m_shmoff);
    ls_shmlock_lock(&pList->x_lock);
}


void ShmPrivatePurgeData::unlock()
{
    shm_privpurgedata_t *pList =
        (shm_privpurgedata_t *)m_pool->offset2ptr(m_shmoff);
    ls_shmlock_unlock(&pList->x_lock);
}


/*
 */
LsShmOffset_t ShmPrivatePurgeData::addUpdate(purgeinfo_t *pInfo)
{
    shm_purgedata_t *pData;
    shm_privpurgedata_t *pList =
        (shm_privpurgedata_t *)m_pool->offset2ptr(m_shmoff);

    lock();

    pList->x_tmLastUpdate = DateTime::s_curTime;

    LsShmOffset_t offData = pList->x_listhead;
    while (offData != 0)
    {
        pData = (shm_purgedata_t *)m_pool->offset2ptr(offData);
        if (pData->x_purgeinfo.idTag == pInfo->idTag)
            break;
        offData = pData->x_offNext;
    }
    if (offData == 0)
    {
        int remapped = 0;
        offData = m_pool->alloc2(sizeof(shm_purgedata_t), remapped);
        if (remapped)
            pList = (shm_privpurgedata_t *)m_pool->offset2ptr(m_shmoff);

        if (offData != 0)
        {
            pData = (shm_purgedata_t *)m_pool->offset2ptr(offData);
            pData->x_offNext = pList->x_listhead;
            pList->x_listhead = offData;
        }
        else
        {
            unlock();
            return 0;
        }
    }
    memmove(&pData->x_purgeinfo, pInfo, sizeof(*pInfo));

    unlock();

    return offData;
}


purgeinfo_t *ShmPrivatePurgeData::findTagInfo(int idTag)
{
    shm_purgedata_t *pData = NULL;
    shm_privpurgedata_t *pList =
        (shm_privpurgedata_t *)m_pool->offset2ptr(m_shmoff);
    lock();
    LsShmOffset_t offData = pList->x_listhead;
    while (offData != 0)
    {
        pData = (shm_purgedata_t *)m_pool->offset2ptr(offData);
        if (pData->x_purgeinfo.idTag == idTag)
        {
//             LOG4CXX_NS::Logger::getRootLogger()->debug(
//                     "tag: %d, entry timestamp: %d.%d, purge timestamp: %d.%d, flag, %d",
//                     idTag, sec, (int)msec, pData->x_purgeinfo.tmSecs,
//                     pData->x_purgeinfo.tmMsec, pData->x_purgeinfo.flags );

            unlock();
            return &pData->x_purgeinfo;
        }
        offData = pData->x_offNext;
    }
    unlock();
    return NULL;
}


/*
 */
int ShmPrivatePurgeData::shouldPurge(int idTag, int32_t sec, int16_t msec)
{
    purgeinfo_t *pInfo = findTagInfo(idTag);
    if (pInfo)
    {
        if (shouldExpireData(pInfo, sec, msec))
            return pInfo->flags;

    }
    return 0;
}


void ShmPrivatePurgeData::release(LsShmPool *pPool,
                                  shm_privpurgedata_t *pList)
{
    LsShmOffset_t offData = pList->x_listhead;
    while (pList->x_listhead != 0)
    {
        offData = pList->x_listhead;
        shm_purgedata_t *pData = (shm_purgedata_t *)pPool->offset2ptr(offData);
        pList->x_listhead = pData->x_offNext;
        pPool->release2(offData, sizeof(shm_purgedata_t));
    }
}

ShmCacheManager::~ShmCacheManager()
{
    if (m_pPublicPurge != NULL)
        m_pPublicPurge->close();
    if (m_pSessions != NULL)
        m_pSessions->close();
    if (m_pStr2IdHash != NULL)
        m_pStr2IdHash->close();
    if (m_pId2VaryStr != NULL)
        m_pId2VaryStr->close();
    m_id2StrList.release_objects();
}



inline CacheInfo *ShmCacheManager::getCacheInfo()
{
    return (CacheInfo *)m_pStr2IdHash->offset2ptr(m_CacheInfoOff);
}

int ShmCacheManager::getPrivateSessionCount() const
{
    return m_pSessions->size();
}



/*
 */
LsShmOffset_t ShmCacheManager::getSession(const char *pId, int len)
{
    shm_privpurgedata_t *pData;
    int valLen = sizeof(*pData);
    int flag = LSSHM_VAL_NONE;
    m_pSessions->lock();
    LsShmOffset_t offVal = m_pSessions->get(pId, len, &valLen, &flag);
    if ((offVal != 0) && (flag & LSSHM_VAL_CREATED))
    {
        pData = (shm_privpurgedata_t *)m_pSessions->offset2ptr(offVal);
        memset(pData, 0, sizeof(*pData));
        ls_shmlock_setup(&pData->x_lock);
        pData->x_tmLastUpdate = DateTime::s_curTime;
    }
    m_pSessions->unlock();
    return offVal;
}


int ShmCacheManager::findSession(CacheKey *pKey,
                                 ShmPrivatePurgeData *pData)
{
    char achKey[8192];
    int len;
    int valLen;
    len = pKey->getPrivateId(achKey, &achKey[8192]);
    if (len > 0)
    {
        LsShmOffset_t offVal = m_pSessions->find(achKey, len, &valLen);
        if (offVal != 0)
        {
            pData->setShmOff(offVal);
            pData->setPool(m_pSessions->getPool());
            return 1;
        }
    }
    return 0;
}

#define PRIVATE_SESSION_TIMEOUT 3600
// void ShmCacheManager::cleanupExpiredSessions()
// {
//     LsShmHash::iteroffset iter, iterNext;
//     shm_privpurgedata_t * pSession;
//     m_pSessions->disableLock();
//     m_pSessions->lock();
//     iter = m_pSessions->begin();
//     while(iter != m_pSessions->end())
//     {
//         iterNext = m_pSessions->next(iter);
//         pSession = (shm_privpurgedata_t *)m_pSessions->offset2iteratorData( iter );
//         //pSession = (shm_privpurgedata_t *)iter->getVal();
//         if ( pSession->x_tmLastUpdate < DateTime::s_curTime - PRIVATE_SESSION_TIMEOUT )
//         {
//             ShmPrivatePurgeData::release(m_pSessions->getPool(), pSession);
//             m_pSessions->eraseIterator(iter);
//             getCacheInfo()->incSessionPurged();
//         }
//         iter = iterNext;
//     }
//     m_pSessions->unlock();
//     m_pSessions->enableLock();
// }


static int shm_privpurgedata_cleanup(LsShmHash::iterator iter, void *pArg1)
{
    shm_privpurgedata_t *pSession;
    LsShmHash *pSessions = (LsShmHash *)pArg1;
    pSession = (shm_privpurgedata_t *)pSessions->getIterDataPtr(iter);
    ls_shmlock_lock(&pSession->x_lock);
    ShmPrivatePurgeData::release(pSessions->getPool(), pSession);
    ls_shmlock_unlock(&pSession->x_lock);
    return LS_OK;
}


void ShmCacheManager::cleanupExpiredSessions()
{
    int count = m_pSessions->trim(DateTime::s_curTime -
                                  PRIVATE_SESSION_TIMEOUT,
                                  shm_privpurgedata_cleanup, m_pSessions);
    getCacheInfo()->incSessionPurged(count);
}


void *ShmCacheManager::getPrivateCacheInfo(const char *pPrivateId,
        int len, int force)
{
    LsShmOffset_t offPrivate;
    int valLen;
    if (force)
        offPrivate = getSession(pPrivateId, len);
    else
        offPrivate = m_pSessions->find(pPrivateId, len, &valLen);
    return (void *)(long)offPrivate;
}


int ShmCacheManager::setPrivateTagFlag(void *pPrivatePurgeData,
                                       purgeinfo_t *pPurginfo)
{
    ShmPrivatePurgeData privatePurge;
    if (pPrivatePurgeData == NULL)
        return LS_FAIL;
    privatePurge.setPool(m_pSessions->getPool());
    privatePurge.setShmOff((LsShmOffset_t)(long)pPrivatePurgeData);

    privatePurge.addUpdate(pPurginfo);
    return 0;
}


purgeinfo_t *ShmCacheManager::getPrivateTagInfo(void *pPrivatePurgeData,
        int tagId)
{
    ShmPrivatePurgeData privatePurge;
    if (pPrivatePurgeData == NULL)
        return NULL;
    privatePurge.setPool(m_pSessions->getPool());
    privatePurge.setShmOff((LsShmOffset_t)(long)pPrivatePurgeData);
    purgeinfo_t *pInfo = privatePurge.findTagInfo(tagId);
    return pInfo;
}



int ShmCacheManager::isFetchAll(void *pPrivatePurgeData)
{
    ShmPrivatePurgeData privatePurge;
    if (pPrivatePurgeData == NULL)
        return LS_FAIL;
    privatePurge.setPool(m_pSessions->getPool());
    privatePurge.setShmOff((LsShmOffset_t)(long)pPrivatePurgeData);
    return privatePurge.isFetchAll();
}



#define PRIVATE_VERIFY_KEY_SET 1
int ShmCacheManager::setVerifyKey(void *pPrivatePurgeData,
                                  const char *pVerifyKey, int len)
{
    shm_privpurgedata_t *pPrivate =
        (shm_privpurgedata_t *)m_pSessions->offset2ptr((LsShmOffset_t)(
                    long)pPrivatePurgeData);
    if (len <= 16)
    {
        memmove(pPrivate->x_verifykey, pVerifyKey, len);
        pPrivate->x_keyLen = len;
    }
    pPrivate->x_tmLastUpdate = DateTime::s_curTime;
    return 0;
}


const char *ShmCacheManager::getVerifyKey(void *pPrivatePurgeData,
        int *len)
{
    shm_privpurgedata_t *pPrivate =
        (shm_privpurgedata_t *)m_pSessions->offset2ptr((LsShmOffset_t)(
                    long)pPrivatePurgeData);
    if (pPrivate->x_keyLen > 0
        && DateTime::s_curTime - pPrivate->x_tmLastUpdate < 600)
    {
        *len = pPrivate->x_keyLen;
        return pPrivate->x_verifykey;
    }
    return NULL;
}


int ShmCacheManager::findTagId(const char *pTag, int len)
{
    int valLen;
    LsShmOffset_t offVal;
    offVal = m_pStr2IdHash->find(pTag, len, &valLen);
    if (offVal != 0)
        return *(int32_t *)m_pStr2IdHash->offset2ptr(offVal);
    return -1;
}


int ShmCacheManager::getTagId(const char *pTag, int len)
{
    int valLen;
    LsShmOffset_t offVal;
    offVal = m_pStr2IdHash->find(pTag, len, &valLen);
    if (offVal != 0)
        return *(int32_t *)m_pStr2IdHash->offset2ptr(offVal);
    int id = getNextPrivateTagId() - 1;
    int initflag = LSSHM_VAL_NONE;
    valLen = sizeof(int32_t);
    if ((offVal = m_pStr2IdHash->get(pTag, len, &valLen, &initflag)) != 0)
    {
        *(int32_t *)m_pStr2IdHash->offset2ptr(offVal) = id;
        return id;
    }
    else
        return -1;
}



/*
 */
LsShmOffset_t ShmCacheManager::addUpdate(
    const char *pKey, int keyLen, int flag, int32_t sec, int16_t msec)
{
    purgeinfo_t *pData;
    int valLen = sizeof(*pData);
    int initflag = LSSHM_VAL_NONE;
    LsShmOffset_t offVal;
    if ((offVal = m_pPublicPurge->get(pKey, keyLen, &valLen, &initflag)) != 0)
    {
        pData = (purgeinfo_t *)m_pPublicPurge->offset2ptr(offVal);
        pData->tmSecs = sec;
        pData->tmMsec = msec;
        pData->flags = flag;
//         LOG4CXX_NS::Logger::getRootLogger()->debug(
//                 "mark tag: %.*s, purge timestamp: %d.%d, flag, %d",
//                 keyLen, pKey, sec, (int)msec, flag );

    }
    return offVal;
}





int ShmCacheManager::processPrivatePurgeCmd(
    CacheKey *pKey, const char *pValue,
    int iValLen, time_t curTime, int curTimeMS)
{
    char achKey[ 8192 ];
    int len;
    len = pKey->getPrivateId(achKey, &achKey[8192]);
    if (len <= 0)
        return -1;
    ShmPrivatePurgeData privatePurge;
    privatePurge.setPool(m_pSessions->getPool());
    privatePurge.setShmOff(getSession(achKey, len));
    return processPurgeCmdEx(&privatePurge, pValue, iValLen, curTime,
                             curTimeMS);

}


int ShmCacheManager::processPurgeCmdEx(
    ShmPrivatePurgeData *pPrivate, const char *pValue, int iValLen,
    time_t curTime, int curTimeMS)
{
    int flag;
    const char *pValueEnd, *pNext;
    const char *pEnd = pValue + iValLen;
    int stale = 0;
    if (strncasecmp(pValue, "stale,", 6 ) == 0)
    {
        stale = 1;
        pValue += 6;
    }
    while (pValue < pEnd)
    {
        if (isspace(*pValue))
        {
            ++pValue;
            continue;
        }
        pValueEnd = (const char *)memchr(pValue, ',', pEnd - pValue);
        if (!pValueEnd)
            pValueEnd = pNext = pEnd;
        else
            pNext = pValueEnd + 1;

        while (isspace(pValueEnd[-1]))
            --pValueEnd;

        flag = PDF_PURGE;

        if ((pValueEnd - pValue > 2)
            && (pValueEnd[-2] == '~')
            && ((pValueEnd[-1] | 0x20) == 's'))
        {
            flag |= PDF_STALE;
            pValueEnd -= 2;
        }
        else if ((pValueEnd - pValue > 6)
            && (strncasecmp(pValueEnd - 6, "~stale", 6 ) == 0))
        {
            flag |= PDF_STALE;
            pValueEnd -= 6;
        }
        else if (stale)
        {
            flag |= PDF_STALE;
        }

        if (strncmp(pValue, "tag=", 4) == 0)
        {
            pValue += 4;
            flag |= PDF_TAG;
        }
        if (*pValue == '*')
        {
            if (pValue == pValueEnd - 1)
            {
                //only a "*".
                if (pPrivate)
                    pPrivate->setLastFlushTime(curTime, curTimeMS);
                else
                {
                    CacheInfo *pInfo = (CacheInfo *)m_pStr2IdHash->
                                       offset2ptr(m_CacheInfoOff);
                    pInfo->setPurgeTime(curTime, curTimeMS);
                }
                pValue = pNext;
                continue;
            }
            else
            {
                //prefix
                flag |= PDF_PREFIX;
            }
        }
        else if (pValueEnd[-1] == '*')
            flag |= PDF_POSTFIX;
        if (pPrivate)
        {
            int idTag = getTagId(pValue, pValueEnd - pValue);
            if (idTag != -1)
            {
                purgeinfo_t purgeinfo = { (int32_t)curTime, (int16_t)curTimeMS,
                                          (uint8_t)flag, (uint8_t)idTag
                                        };
                pPrivate->addUpdate(&purgeinfo);
            }
        }
        else
            addUpdate(pValue, pValueEnd - pValue, flag, curTime, curTimeMS);
        pValue = pNext;
    }
    return 0;
}


/*
 */
int ShmCacheManager::shouldPurge(const char *pKey, int keyLen,
                                 int32_t sec, int16_t msec)
{
    int valLen;
    LsShmOffset_t offVal;
    int ret = 0;
    const char *p = pKey;
    const char *pEnd = pKey + keyLen;
    while (p < pEnd)
    {
        const char *pTagEnd = (const char *)memchr(p, ',', pEnd - p);
        if (pTagEnd == NULL)
            pTagEnd = pEnd;

        //     LOG4CXX_NS::Logger::getRootLogger()->debug(
        //         "Lookup tag: '%.*s', create timestamp: %d.%d",
        //          keyLen, pKey, sec, (int)msec );

        while (isblank(*p))
            ++p;

        const char *pTagEndBak = pTagEnd;
        while (isblank(*(pTagEndBak - 1)))
            --pTagEndBak;

        if (pTagEndBak > p &&
            (offVal = m_pPublicPurge->find(p, pTagEndBak - p, &valLen)) != 0)
        {
            purgeinfo_t *pData = (purgeinfo_t *)m_pPublicPurge->offset2ptr(offVal);
            //         LOG4CXX_NS::Logger::getRootLogger()->debug(
            //             "Found tag: '%.*s', purge timestamp: %d.%d, flag: %d",
            //             keyLen, pKey, pData->tmSecs, (int)pData->tmMsec, pData->flags);
            if (shouldExpireData(pData, sec, msec))
            {
                ret = pData->flags;
                break;
            }
        }
        p = pTagEnd + 1;
    }
    return ret;
}


int ShmCacheManager::isPurgedByTag(
    const char *pTag, CacheEntry *pEntry, CacheKey *pKey, bool isCheckPrivate)
{
    ShmPrivatePurgeData privatePurge;
    const char *pTagEnd;
    bool isPrivate;
    int ret;
    int foundPrivate = -1;
    const char * p = pTag;
    const char * pEnd = pTag + pEntry->getHeader().m_tagLen;
    while(p < pEnd)
    {
        const char * pComma = (const char *)memchr(p, ',', pEnd - p);
        if (pComma == NULL)
            pComma = pEnd;
        while(p < pComma && isspace(*p))
            ++p;
        
        /******
         * COMMENTS:
         * Both public and private pKey will have the IP save,
         * but public pKey->m_ipLen is <0 (real length * -1)
         * and private pKey->m_ipLen is >0 (real elngth)
         */
        isPrivate = (pKey->m_ipLen > 0);
        //assert(isCheckPrivate == isPrivate);
        
        if (strncasecmp(p, "public:", 7) == 0)
        {
            p += 7;
            isPrivate = 0;
            while(p < pComma && isspace(*p))
                ++p;
        }
        if (p < pComma)
        {
            pTagEnd = pComma;
            while(isspace(pTagEnd[-1]))
                --pTagEnd;
            if (isPrivate)
            { 
                if (foundPrivate == -1)
                    foundPrivate = findSession(pKey, &privatePurge);
                if (foundPrivate == 1)
                {
                    if (privatePurge.isFlushed(pEntry->getHeader().m_tmCreated,
                                       pEntry->getHeader().m_msCreated))
                        return 1;
                    int tagId = findTagId(pTag, pEntry->getHeader().m_tagLen);
                    if (tagId != -1)
                    {
                        ret= privatePurge.shouldPurge(tagId,
                                             pEntry->getHeader().m_tmCreated,
                                             pEntry->getHeader().m_msCreated);
                        if (ret)
                            return ret;
                    }
                }
            }
            else
            {
                ret = shouldPurge(p, pTagEnd - p, pEntry->getHeader().m_tmCreated,
                                  pEntry->getHeader().m_msCreated);
                if (ret)
                    return ret;
            }
        }
        p = pComma + 1;
    }
    return 0;
}



int ShmCacheManager::isPurged(CacheEntry *pEntry, CacheKey *pKey,
                              bool isCheckPrivate)
{
    int ret = 0;
    CacheInfo *pInfo = (CacheInfo *)m_pPublicPurge->
                       offset2ptr(m_CacheInfoOff);
    if (pInfo->shouldPurge(pEntry->getHeader().m_tmCreated,
                           pEntry->getHeader().m_msCreated))
        ret = 1;
    else
    {
        const char *pTag = pEntry->getTag().c_str();
        if (pTag)
        {
            ret = isPurgedByTag(pTag, pEntry, pKey, isCheckPrivate);
        }
        if (!ret)
        {
            if (shouldPurge(pEntry->getKey().c_str(), pEntry->getKeyLen(),
                            pEntry->getHeader().m_tmCreated,
                            pEntry->getHeader().m_msCreated))
                ret = 1;

        }
    }
    if (ret)
        ls_atomic_add(&pInfo->getStats(pEntry->isPrivate())->purged, 1);
    return ret;
}


void ShmCacheManager::logShmError()
{
    const char *pErrStr = LsShm::getErrMsg();
    LOG4CXX_NS::Logger::getRootLogger()->error("[SHM] %s", pErrStr);
    LsShm::clrErrMsg();
}

#define CACHE_INFO_MAGIC   0x43490005
int ShmCacheManager::initCacheInfo(LsShmPool *pPool)
{
    int remapped;
    LsShmOffset_t infoOff;
    LsShmReg *pCacheInfoReg;
    pCacheInfoReg = pPool->getShm()->findReg("CACHINFO");
    if (pCacheInfoReg == NULL)
    {
        infoOff = pPool->alloc2(sizeof(CacheInfo) + sizeof(int32_t), remapped);
        int32_t *pMagic = (int32_t *)pPool->offset2ptr(infoOff);
        *pMagic = CACHE_INFO_MAGIC;
        CacheInfo *pInfo = (CacheInfo *)pPool->offset2ptr(infoOff + sizeof(
                               int32_t));
        memset(pInfo, 0, sizeof(*pInfo));
        pInfo->setPurgeTime(time(NULL) + 1, 0);
        pCacheInfoReg = pPool->getShm()->addReg("CACHINFO");
        //should use CAS to make sure nobody take over it before us
        pCacheInfoReg->x_iValue = infoOff;
    }
    else
    {
        infoOff = pCacheInfoReg->x_iValue;
        int32_t *pMagic = (int32_t *)pPool->offset2ptr(infoOff);
        if (*pMagic != CACHE_INFO_MAGIC)
            return LS_FAIL;
    }
    m_CacheInfoOff = infoOff + sizeof(int32_t);
    return 0;
}


int ShmCacheManager::initTables(LsShmPool *pPool)
{
    m_pPublicPurge = pPool->getNamedHash("public", 1000, LsShmHash::hashXXH32,
                                         memcmp, 0);
    if (!m_pPublicPurge)
        return -1;

    m_pSessions = pPool->getNamedHash("private", 1000, LsShmHash::hashXXH32,
                                      memcmp, LSSHM_FLAG_LRU);
    if (!m_pSessions)
        return -1;

    m_pStr2IdHash = pPool->getNamedHash("tags", 20, LsShmHash::hashXXH32,
                                        memcmp,  0);
    if (!m_pStr2IdHash)
        return -1;

    m_pUrlVary = (TShmHash<int32_t> *)pPool->getNamedHash("urlVary", 1000,
                 LsShmHash::hashXXH32, memcmp, 0);
    if (!m_pUrlVary)
        return -1;
    m_pUrlVary->disableAutoLock();

    m_pId2VaryStr = pPool->getNamedHash("id2vary", 100,
                                        LsShmHash::hashXXH32, memcmp, 0);
    if (!m_pId2VaryStr)
        return -1;

    populatePrivateTag();
    return 0;
}

int ShmCacheManager::init(const char *pStoreDir)
{
    LsShm *pShm;
    LsShmPool *pPool;
    const char *pFileName = ".cacheman";
    int attempts;
    int ret = -1;
    for (attempts = 0; attempts < 3; ++attempts)
    {
        pShm = LsShm::open(pFileName, 40960, pStoreDir);

        if (!pShm)
        {
            pShm = LsShm::open(pFileName, 40960, pStoreDir);
            if (!pShm)
            {
                logShmError();
                return LS_FAIL;
            }
        }

        pPool = pShm->getGlobalPool();
        if (!pPool)
        {
            pShm->deleteFile();
            pShm->close();
            continue;
        }

        pPool->disableAutoLock();
        pPool->lock();

        if ((initCacheInfo(pPool) == LS_FAIL)
            || (ret = initTables(pPool)) == LS_FAIL)
        {
            pPool->unlock();
            pPool->close();
            pShm->deleteFile();
            pShm->close();
        }
        else
            break;
    }

    pPool->unlock();
    pPool->enableAutoLock();

    return ret;
}


int ShmCacheManager::addUrlVary(const char *pUrl, int len, int id)
{
    int ret = 0;
    int valLen;
    LsShmOffset_t offVal;
    m_pUrlVary->lock();
    if ((offVal = m_pUrlVary->find(pUrl, len, &valLen)) != 0)
    {
        if (id != *(int32_t *)m_pUrlVary->offset2ptr(offVal))
            *(int32_t *)m_pUrlVary->offset2ptr(offVal) = id;
    }
    else
    {
        int initflag = LSSHM_VAL_NONE;
        valLen = sizeof(int32_t);
        if ((offVal = m_pUrlVary->get(pUrl, len, &valLen, &initflag)) != 0)
            * (int32_t *)m_pUrlVary->offset2ptr(offVal) = id;
        else
            ret =  -1;
    }
    m_pUrlVary->unlock();
    return ret;
}


int ShmCacheManager::getVaryId(const char *pVary, int varyLen)
{
    int valLen;
    LsShmOffset_t offVal;
    offVal = m_pStr2IdHash->find(pVary, varyLen, &valLen);
    if (offVal != 0)
        return *(int32_t *)m_pStr2IdHash->offset2ptr(offVal);
    int id = getNextVaryId() - 1;
    int initflag = LSSHM_VAL_NONE;
    valLen = sizeof(int32_t);
    if ((offVal = m_pStr2IdHash->get(pVary, varyLen, &valLen, &initflag)) != 0)
        * (int32_t *)m_pStr2IdHash->offset2ptr(offVal) = id;
    else
        return -1;

    valLen = varyLen + 1;
    offVal = m_pId2VaryStr->get(&id, sizeof(id), &valLen, &initflag);
    if (offVal != 0)
        memmove(m_pId2VaryStr->offset2ptr(offVal), pVary, varyLen + 1);
    else
        return -1;
    addId2StrList(id, pVary, varyLen);
    return id;
}


const AutoStr2 *ShmCacheManager::addId2StrList(int id, const char *pVary,
        int varyLen)
{
    AutoStr2 *pStr = new AutoStr2(pVary, varyLen);
    if (m_id2StrList.size() <= id)
    {
        while (m_id2StrList.size() < id)
            m_id2StrList.push_back((void *)NULL);
        m_id2StrList.push_back(pStr);
    }
    else
        m_id2StrList[id] = pStr;
    return pStr;
}


const AutoStr2 *ShmCacheManager::getVaryStrById(uint id)
{
    const AutoStr2 *pId = NULL;
    if (id < (uint)m_id2StrList.size())
        pId = m_id2StrList[id];
    if (pId == NULL)
    {
        int valLen;
        LsShmOffset_t offVal;
        offVal = m_pId2VaryStr->find(&id, sizeof(id), &valLen);
        if (offVal != 0)
        {
            pId = addId2StrList(
                      id, (const char *)m_pId2VaryStr->offset2ptr(offVal), valLen - 1);
        }
    }
    return pId;
}


const AutoStr2 *ShmCacheManager::getUrlVary(const char *pUrl, int len)
{
    int valLen;
    LsShmOffset_t offVal;
    m_pUrlVary->lock();
    offVal = m_pUrlVary->find(pUrl, len, &valLen);
    m_pUrlVary->unlock();

    if (offVal != 0)
    {
        int id = *(int32_t *)m_pUrlVary->offset2ptr(offVal);
        return getVaryStrById(id);
    }
    return NULL;
}

int ShmCacheManager::getNextVaryId()
{   return getCacheInfo()->getNextVaryId(); }


int ShmCacheManager::getNextPrivateTagId()
{   return getCacheInfo()->getNextPrivateTagId(); }


int ShmCacheManager::houseKeeping()
{
    int last = getCacheInfo()->getLastHouseKeeping();
    if (DateTime::s_curTime - last < 60)
        return 0;
    if (getCacheInfo()->setLastHouseKeeping(last, DateTime::s_curTime) == 0)
        return 0;
    cleanupExpiredSessions();
    return 1;
}


int ShmCacheManager::shouldCleanDiskCache()
{
    int last = getCacheInfo()->getLastCleanDiskCache();
    if (DateTime::s_curTime - last < 86400)
        return 0;
//    if (getCacheInfo()->getNewPurgeCount() < 500)
//        return 0;
    ++m_attempts;
    double loads[3];
    if (getloadavg(loads, 3) == -1)
        return 0;
    if (loads[1] < (double)PCUtil::getNumProcessors() / 6
        * (1 + (double)m_attempts / 60))
    {
        getCacheInfo()->setLastCleanDiskCache(last, DateTime::s_curTime);
        m_attempts = 0;
        return 1;
    }
    return 0;
}


