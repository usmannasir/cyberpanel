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
#include <sslpp/sslsesscache.h>
#include <sslpp/sslconnection.h>

#include <log4cxx/logger.h>
#include <shm/lsshmhash.h>
#include <shm/lsshmtypes.h>
#include <util/datetime.h>
#include <util/stringtool.h>

#include <openssl/bio.h>
#include <openssl/err.h>
#include <openssl/rand.h>

#define shmSslCache "SSLCache"
#define shmSsl  "SSL"
static int s_numNew = 0;


typedef struct SslSessData_s
{
    int32_t             x_iExpireTime;
    uint32_t            x_iValueLen;
    u_int8_t            x_sessionData[0];
} SslSessData_t;

static int checkStatElem(LsShmHash::iteroffset iIterOff, void *pData);
static void printId(const char *tag, unsigned char *pId, int iIdLen);
// static int printAll(LsShmHash::iteroffset iIterOff, void *pUData);

static int isExpired(SslSessData_t *pObj)
{
    return ((DateTime::s_curTime - pObj->x_iExpireTime) > 0);
}


SslSessCache::SslSessCache()
    : m_expireSec(0)
    , m_maxEntries(0)
    , m_pSessStore(NULL)
{
}


SslSessCache::~SslSessCache()
{
}


int SslSessCache::initShm()
{
    LsShm *pShm;
    LsShmPool *pPool;

    if ((pShm = LsShm::open(shmSsl, 0)) == NULL)
        return LS_FAIL;
    if ((pPool = pShm->getGlobalPool()) == NULL)
        return LS_FAIL;
    if ((m_pSessStore = pPool->getNamedHash(shmSslCache, 10000,
                                            LsShmHash::hash32id, memcmp, LSSHM_FLAG_LRU)) != NULL)
    {
        m_pSessStore->disableAutoLock(); // we will be responsible for the lock
        s_numNew = 0;
        return LS_OK;
    }
    return LS_FAIL;
}


int SslSessCache::init(int32_t iTimeout, int iMaxEntries)
{
    if (isReady())
    {
        LS_DBG_L("[SSL_SESS] SslSessCache already initialized.");
        return LS_OK;
    }
    m_expireSec = iTimeout;
    m_maxEntries = iMaxEntries;
    return initShm();
}


/**
 * newSessionCb() is the callback that openssl will use to get a new session id
 * Given the SSL_SESSION, this function will convert it to an identifiable
 * format (ASN1) and add the session to the cache.
 */
static int newSessionCb(SSL *pSSL, SSL_SESSION *pSess)
{
    int iDataLen;
    SslSessCache &cache = SslSessCache::getInstance();
    unsigned char data[20480];
    unsigned char *pAsn1 = &data[sizeof(SslSessData_t)];
    SslSessData_t *pObj = (SslSessData_t *)data;

    s_numNew++;
    // flush out expired data
    if (!(s_numNew % 0x400))
        cache.sessionFlush();

    iDataLen = i2d_SSL_SESSION(pSess, &pAsn1);
    assert((unsigned int)iDataLen <= sizeof(data) - sizeof(SslSessData_t));
    pObj->x_iValueLen = iDataLen;
    pObj->x_iExpireTime = DateTime::s_curTime + cache.getExpireSec();

    return cache.addSession(pSess->session_id, pSess->session_id_length,
                            data, iDataLen + sizeof(*pObj));
}


/**
 * getSessionCb() is the callback that openssl will use to get the session id.
 * This function will go into shm to look for the ID and if found,
 * will convert it to, and return as a SSL_SESSION object.
 */
static SSL_SESSION *getSessionCb(SSL *pSSL, unsigned char *id, int len,
                                 int *ref)
{
    SslSessCache &cache = SslSessCache::getInstance();

#ifdef DEBUG_SHOW_MORE
    printId("Lookup Session", id, len);
#endif
    //*ref = 0;
    const unsigned char *cp;
    SSL_SESSION *pSess = NULL;
    SslSessData_t *pObj = cache.getLockedSessionData(id, len);
    if (pObj)
    {
        cp = (const unsigned char *) pObj->x_sessionData;
        pSess = d2i_SSL_SESSION(NULL, &cp, pObj->x_iValueLen);
        cache.unlock();
        if (pSess)
        {
            printId("Create Session from cache succeed", id, len);
            SslConnection *pConn = (SslConnection *)SSL_get_ex_data(pSSL,
                                   SslConnection::getConnIdx());
            pConn->setFreeSess();
        }
        else
            printId("d2i_SSL_SESSION failed", id, len);
    }

//     else
//     {
//         // Failed to allocated SSL SESSION
// //         printId("SESS GET-FAILED TO FIND SSL SESSION", id, len);
//         SSL_CTX *pCtx = SSL_get_SSL_CTX(pSSL);
//         LS_DBG_L("GET FAILED: Accept %ld, Accept Good %ld, Accept Reneg %ld, "
//                  "Hits %ld, cb hits %ld, misses %ld",
//                  SSL_CTX_sess_accept(pCtx), SSL_CTX_sess_accept_good(pCtx),
//                  SSL_CTX_sess_accept_renegotiate(pCtx), SSL_CTX_sess_hits(pCtx),
//                  SSL_CTX_sess_cb_hits(pCtx), SSL_CTX_sess_misses(pCtx));
//     }

    return pSess;
}


/**
 * removeCb() is the callback that openssl will use to remove the session id.
 * It will simply call the cache's remove function on the session passed in.
 * When finished, it will call flush on the cache to remove any easily
 * found expired sessions.
 */
static void removeCb(SSL_CTX *pCtx, SSL_SESSION *pSess)
{
    SslSessCache &cache = SslSessCache::getInstance();
#ifdef DEBUG_SHOW_MORE
    printId("Remove Session", pSess->session_id, pSess->session_id_length);
#endif
    LsShmHash *pStore = cache.getSessStore();

    pStore->lock();
    pStore->remove(pSess->session_id, pSess->session_id_length);
    pStore->unlock();

    cache.sessionFlush(); // flush out the SHM expired sessions
}


/**
 * watchCtx sets the callback functions for pCtx.  Any time OpenSSL needs
 * to create, get, or remove a ssl session, it will call these functions.
 */
int SslSessCache::watchCtx(SSL_CTX *pCtx)
{
    SSL_CTX_sess_set_new_cb(pCtx, newSessionCb);
    SSL_CTX_sess_set_remove_cb(pCtx, removeCb);
    SSL_CTX_sess_set_get_cb(pCtx, getSessionCb);
    SSL_CTX_set_timeout(pCtx, SslSessCache::getInstance().m_expireSec);
    return LS_OK;
}


/**
 * addSession() will try to insert a session into the hash.
 */
int SslSessCache::addSession(unsigned char *pId, int idLen,
                             unsigned char *pData, int iDataLen)
{
    LsShmOffset_t iObjOff;

    m_pSessStore->lock();
    iObjOff = m_pSessStore->insert(pId, idLen, pData, iDataLen);
    if (iObjOff != 0)
    {
#ifdef DEBUG_SHOW_MORE
        printId("New Session", pId, idLen);
#endif
    }
    else
        printId("Failed to add to SHM hashtable", pId, idLen);
    m_pSessStore->unlock();

    return (iObjOff != 0); //session will be cached
}


void SslSessCache::unlock()
{
    m_pSessStore->unlock();
}


/**
 * getLockedSessionData() will attempt to get the session data from
 * the hash given the id and length.
 *
 * NOTICE: if this function succeeds, the hash table \b must be unlocked
 * afterwards.
 */
SslSessData_t *SslSessCache::getLockedSessionData(unsigned char *id,
        int len)
{
    int valLen;
    LsShmOffset_t iObjOff;
    SslSessData_t *pObj;

    m_pSessStore->lock();
    iObjOff = m_pSessStore->find(id, len, &valLen);
    if (iObjOff != 0)
    {
        pObj = (SslSessData_t *)m_pSessStore->offset2ptr(iObjOff);
        if (!isExpired(pObj))
            return pObj;      //m_pSessStore need to be locked
        else
            printId("Cached Session expired", id, len);
    }
    m_pSessStore->unlock();
    return NULL;
}


/**
 * sessionFlush() will check the least recently used sessions and remove the
 * ones that are expired.
 */
int SslSessCache::sessionFlush()
{
    int num;

    m_pSessStore->lock();
    num = m_pSessStore->trim(DateTime::s_curTime - m_expireSec, NULL, NULL);
    m_pSessStore->unlock();

    return num;
}


/**
 * stat() prints the cache's statistics.
 */
int SslSessCache::stat()
{
    LsHashStat stat;

    // lock
    m_pSessStore->lock();
    m_pSessStore->stat(&stat, checkStatElem, m_pSessStore);
    LS_DBG_L("NEWSESSION STATISTIC <%p> " , this);
    LS_DBG_L("HASH STATISTIC NUM %3d DUP %3d EXPIRED %d IDX [%d %d %d]",
             stat.num, stat.numDup, stat.numExpired, stat.numIdx,
             stat.numIdxOccupied, stat.maxLink);
    LS_DBG_L("HASH STATISTIC TOP %d %d %d %d %d [%d %d %d %d %d]",
             stat.top[0], stat.top[1], stat.top[2], stat.top[3], stat.top[4],
             stat.top[5], stat.top[6], stat.top[7], stat.top[8], stat.top[9]);
    // unlock
    m_pSessStore->unlock();
    return 0;
}


/**
 * checkStatElem() is the callback function that checks the actual data
 * to update any statistic that the hash wouldn't know about.
 */
int checkStatElem(LsShmHash::iteroffset iIterOff, void *pData)
{
    LsHashStat *pHashStat = (LsHashStat *)pData;
    LsShmHash *pHash = (LsShmHash *)pHashStat->userData;
    SslSessData_t *pObj = (SslSessData_t *)pHash->offset2iteratorData(
                              iIterOff);
    if (isExpired(pObj))
        pHashStat->numExpired++;
    return 0;
}


void printId(const char *tag, unsigned char *pId, int iIdLen)
{
    if (LS_LOG_ENABLED(log4cxx::Level::DBG_LOW))
    {
        char buf[0x100];
        int len;

        len = StringTool::hexEncode((const char *)pId, iIdLen, buf);
        LS_DBG_L("[SSL SESS] [PID:%6d] %s: ID [%s] size %d", getpid(), tag,
                 buf, len);
    }
}


// int printAll(LsShmHash::iteroffset iIterOff, void *pUData)
// {
//     SSL_SESSION *pSess;
//     LsShmHash *pHash = (LsShmHash *)pUData;
//     SslSessData_t *pObj = (SslSessData_t *)pHash->offset2iteratorData(iIterOff);
//     const unsigned char *cp = (const unsigned char *) pObj->x_sessionData;
//
//     pSess = d2i_SSL_SESSION(NULL, &cp, pObj->x_iValueLen);
//     if ( pSess == NULL )
//     {
//         LS_DBG_L("printAll missing session");
//         return 0;
//     }
//     printId("printAll check", pSess->session_id, pSess->session_id_length);
//
//     return 0;
// }

