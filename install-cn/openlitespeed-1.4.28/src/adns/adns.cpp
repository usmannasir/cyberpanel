/*
 * Copyright 2002 Lite Speed Technologies Inc, All Rights Reserved.
 * LITE SPEED PROPRIETARY/CONFIDENTIAL.
 */

#include "adns.h"

#include <log4cxx/logger.h>
#include <shm/lsshmhash.h>
#include <util/datetime.h>

#include <udns.h>

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>

#define DNS_CACHE_TTL           (12 * 3600)

static int s_inited = 0;


Adns::Adns()
    :m_pCtx( NULL )
    , m_iCounter(0)
    , m_pShmHash(NULL)
    , m_tmLastTrim(0)
{
}


Adns::~Adns()
{
    shutdown();
    s_inited = 0;
}


void Adns::trimCache()
{
    if (!m_pShmHash)
        return;
    if (DateTime::s_curTime - m_tmLastTrim > 60)
    {
        m_tmLastTrim = DateTime::s_curTime;
        m_pShmHash->trim(DateTime::s_curTime - DNS_CACHE_TTL, NULL, 0);
    }
}


const char *Adns::getCacheValue( const char * pName, int nameLen, int &valLen )
{
    if (!m_pShmHash)
        return NULL;
    LsShmOffset_t offset = m_pShmHash->find(pName, nameLen, &valLen);
    if (offset)
    {
        if (valLen <= 0)
            return "";
        return (char *)m_pShmHash->offset2ptr(offset);
    }
    else
        return NULL;
}


int Adns::deleteCache()
{
    return LsShm::deleteFile("adns_cache", NULL);
}


int Adns::init()
{
    if (!s_inited)
    {
        if (dns_init(NULL, 1) < 0)
            return -1;
        s_inited = 1;
        dns_set_opt(NULL, DNS_OPT_NTRIES, 1);
    }
    if ( m_pCtx )
        return 0;
    m_pCtx = dns_new( NULL );
    if ( !m_pCtx )
        return -1;
    if ( dns_open( m_pCtx ) < 0 )
        return -1;
    setfd( dns_sock( m_pCtx ) );

    return 0;
}


int Adns::initShm(int uid, int gid)
{
    if ( m_pShmHash )
        return 0;
    if ((m_pShmHash = LsShmHash::open(
        "adns_cache", "dns_cache", 1000, LSSHM_FLAG_LRU)) != NULL)
    {
        m_pShmHash->getPool()->getShm()->chperm(uid, gid, 0600);
    }
    return 0;
}

int Adns::shutdown()
{
      dns_close( m_pCtx );
//    if ( m_pCtx )
//    {
//        dns_free( m_pCtx );
//        m_pCtx = NULL;
//    }
    return 0;
}


void Adns::printLookupError(struct dns_ctx *ctx, AdnsReq *pAdnsReq)
{
    const char *pError;
    switch(dns_status(ctx))
    {
    case DNS_E_TEMPFAIL:
        pError = "DNS_E_TEMPFAIL";
        break;
    case DNS_E_PROTOCOL:
        pError = "DNS_E_PROTOCOL";
        break;
    case DNS_E_NXDOMAIN:
        pError = "DNS_E_NXDOMAIN";
        break;
    case DNS_E_NODATA:
        pError = "DNS_E_NODATA";
        break;
    case DNS_E_NOMEM:
        pError = "DNS_E_NOMEM";
        break;
    case DNS_E_BADQUERY:
        pError = "DNS_E_BADQUERY";
        break;
    default:
        pError = "Unknown status";
        break;
    }
    LS_DBG_L("[DNSLOOKUP] (%s), "
            "AdnsReq Dump: Type %d, Name %s, Arg %p, Start time %ld",
             pError, pAdnsReq->type, pAdnsReq->name, pAdnsReq->arg,
             pAdnsReq->start_time);
}


void Adns::getHostByNameCb(struct dns_ctx *ctx, void *rr_unknown, void *param)
{
    AdnsReq *pAdnsReq = (AdnsReq *)param;

    char *sIp= (char *)"";
    int ipLen = 0;
    if (rr_unknown)
    {
        if (pAdnsReq->type != PF_INET6)
        {
            struct dns_rr_a4 * rr = (struct dns_rr_a4 *)rr_unknown;
            sIp = (char *)rr->dnsa4_addr;
            ipLen = sizeof(in_addr);
            if (pAdnsReq->result)
                ((sockaddr_in *)pAdnsReq->result)->sin_addr 
                        = *(rr->dnsa4_addr);
        }
        else
        {
            struct dns_rr_a6 * rr = (struct dns_rr_a6 *)rr_unknown;
            sIp = (char *)rr->dnsa6_addr;
            ipLen = sizeof(in6_addr);
            if (pAdnsReq->result)
                memmove(&(((sockaddr_in6 *)pAdnsReq->result)->sin6_addr), 
                        sIp, sizeof(in6_addr));
        }
    }
    else if (LS_LOG_ENABLED(log4cxx::Level::DBG_LESS))
        printLookupError(ctx, pAdnsReq);

    LsShmHash *pCache = Adns::getInstance().getShmHash();
    if (pCache)
        pCache->insert(pAdnsReq->name, strlen(pAdnsReq->name), sIp, ipLen);
    if (pAdnsReq->cb && pAdnsReq->arg)
        pAdnsReq->cb(pAdnsReq->arg, ipLen, sIp);

    if (rr_unknown)
        free(rr_unknown);
    delete pAdnsReq;
}


void Adns::getHostByAddrCb(struct dns_ctx *ctx, struct dns_rr_ptr *rr, void *param)
{
    AdnsReq *pAdnsReq = (AdnsReq *)param;

    int nameLen;
    if (pAdnsReq->type != PF_INET6)
        nameLen = sizeof(in_addr);
    else
        nameLen = sizeof(in6_addr);

    char achBuf[4096];
    char *p = (char *)"";
    int n = 0;
    if (rr)
    {
        if ( rr->dnsptr_nrr == 1 )
        {
            p = rr->dnsptr_ptr[0];
            n = strlen(rr->dnsptr_ptr[0]);
        }
        else
        {
            p = achBuf;
            for(int i = 0; i < rr->dnsptr_nrr; ++i)
            {
                n += snprintf(achBuf + n, 4096 - n, "%s,", rr->dnsptr_ptr[i]);
            }
            achBuf[n -1] = 0;
        }
    }

    LsShmHash *pCache = Adns::getInstance().getShmHash();
    if (pCache)
        pCache->insert(pAdnsReq->name, nameLen, p, n);
    if (pAdnsReq->cb && pAdnsReq->arg)
        pAdnsReq->cb(pAdnsReq->arg, n, p);

    if (rr)
        free(rr);
    delete pAdnsReq;
}


char *Adns::getCacheName(const char *pName, int type)
{
    int len = strlen(pName);
    char *nameWithVer = (char *)malloc(len + 4);
    memcpy(nameWithVer, pName, len);
    memcpy(nameWithVer + len, (type != PF_INET6 ? "_v4" : "_v6"), 3);
    nameWithVer[len + 3] = 0x00;
    return nameWithVer;
}


const char *Adns::getHostByNameInCache( const char * pName, int &length, int type )
{
    char *nameWithVer = getCacheName(pName, type);
    const char *ret = getCacheValue(nameWithVer, strlen(nameWithVer), length);
    free(nameWithVer);
    return ret;
}


AdnsReq *Adns::getHostByName(const char * pName, int type, 
                             struct sockaddr *result,
                             lookup_pf cb, void *arg)
{
    dns_query * pQuery;
    init();
    AdnsReq *pAdnsReq = new AdnsReq;
    if (pAdnsReq)
    {
        pAdnsReq->type = type;
        pAdnsReq->name = getCacheName(pName, type);
        pAdnsReq->result = result;
        pAdnsReq->cb = cb;
        pAdnsReq->arg = arg;
        pAdnsReq->start_time = DateTime::s_curTime;
        if (type != PF_INET6)
            pQuery = dns_submit_a4( m_pCtx, pName, DNS_NOSRCH, (addrLookupCbV4)getHostByNameCb, pAdnsReq);
        else
            pQuery = dns_submit_a6( m_pCtx, pName, DNS_NOSRCH, (addrLookupCbV6)getHostByNameCb, pAdnsReq);
        if (pQuery == NULL)
        {
            delete pAdnsReq;
            pAdnsReq = NULL;
        }
        else
            checkDnsEvents();
        return pAdnsReq;
    }
    else
    {
        ;//ERROR: out of memory
        return NULL;
    }
}


static void *getInAddr(const struct sockaddr * pAddr, int& length)
{
    switch( pAddr->sa_family )
    {
    case AF_INET6:
        length = sizeof(in6_addr);
        return &(((sockaddr_in6 *)pAddr)->sin6_addr);
    case AF_INET:
    default:
        length = sizeof(in_addr);
        return &(((sockaddr_in *)pAddr)->sin_addr);
    }
}


const char *Adns::getHostByAddrInCache( const struct sockaddr * pAddr, int &length )
{
    int keyLen;
    const char *key = (const char *)getInAddr(pAddr, keyLen);
    const char *ret = getCacheValue(key, keyLen, length);
    return ret;
}


AdnsReq * Adns::getHostByAddr( const struct sockaddr * pAddr, void *arg, lookup_pf cb)
{
    dns_query * pQuery;
    init();
    AdnsReq *pAdnsReq = new AdnsReq;
    if (!pAdnsReq)
        return NULL;

    int type = pAddr->sa_family;
    pAdnsReq->type = type;
    int length;
    char *pName= (char *)getInAddr(pAddr, length);
    pAdnsReq->name = (char *)malloc(length); //No NULL terminate
    memcpy(pAdnsReq->name, pName, length);
    pAdnsReq->cb = cb;
    pAdnsReq->arg = arg;
    pAdnsReq->start_time = DateTime::s_curTime;

    if (type != PF_INET6)
        pQuery = dns_submit_a4ptr( m_pCtx, (in_addr *)pName, getHostByAddrCb, pAdnsReq);
    else
        pQuery = dns_submit_a6ptr( m_pCtx, (in6_addr *)pName, getHostByAddrCb, pAdnsReq);
    if (pQuery == NULL)
    {
        delete pAdnsReq;
        pAdnsReq = NULL;
    }
    else
        checkDnsEvents();
    return pAdnsReq;
}


int Adns::handleEvents( short events )
{
    if ( events & POLLIN )
        dns_ioevent( m_pCtx, DateTime::s_curTime );

    return 0;
}


void Adns::onTimer()
{
    dns_ioevent( m_pCtx, DateTime::s_curTime );
    if (++m_iCounter >= 10)
    {
        m_iCounter = 0;
        checkDnsEvents();
    }
}


void Adns::setTimeOut(int tmSec)
{
    dns_set_opt(m_pCtx, DNS_OPT_TIMEOUT, tmSec);
}


void Adns::checkDnsEvents()
{
    dns_timeouts( m_pCtx, -1, DateTime::s_curTime );
}


int Adns::getHostByNameSync(const char *pName, in_addr_t *addr)
{
    struct dns_rr_a4 *rr;
    if (!s_inited)
    {
        if (dns_init(NULL, 1) < 0)
            return -1;
        s_inited = 1;
        dns_set_opt(NULL, DNS_OPT_NTRIES, 1);

    }
    rr = dns_resolve_a4(NULL, pName, DNS_NOSRCH);
    if (rr)
    {
        if (rr->dnsa4_nrr > 0)
            memmove(addr, &rr->dnsa4_addr[0], 4);
        free(rr);
        return 0;
    }
    return -1;
}

int Adns::getHostByNameV6Sync(const char *pName, in6_addr *addr)
{
    struct dns_rr_a6 *rr;
    if (!s_inited)
    {
        if (dns_init(NULL, 1) < 0)
            return -1;
        s_inited = 1;
        dns_set_opt(NULL, DNS_OPT_NTRIES, 1);
    }
    rr = dns_resolve_a6(NULL, pName, DNS_NOSRCH);
    if (rr)
    {
        if (rr->dnsa6_nrr > 0)
            memmove(addr, &rr->dnsa6_addr[0], 16);
        free(rr);
        return 0;
    }
    return -1;
}
