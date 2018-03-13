/*
 * Copyright 2002 Lite Speed Technologies Inc, All Rights Reserved.
 * LITE SPEED PROPRIETARY/CONFIDENTIAL.
 */


#ifndef ADNS_H
#define ADNS_H

#include <lsdef.h>
#include <time.h>
#include <arpa/inet.h>
#include <netinet/in.h>


/**
  *@author Gang Wang
  */
struct sockaddr;
class LsShmHash;
class Adns;

#include <edio/eventreactor.h>
#include <util/tsingleton.h>

typedef void (* addrLookupCbV4)(struct dns_ctx *, struct dns_rr_a4 *, void *);
typedef void (* addrLookupCbV6)(struct dns_ctx *, struct dns_rr_a6 *, void *);
typedef int (* lookup_pf)(void *arg, const long lParam, void *pParam);
typedef void (* unknownCb)();

class AdnsReq
{
    friend class Adns;
public:
    AdnsReq()
       : type(0)
       , cb(NULL)
       , name(NULL)
       , arg(NULL)
       , start_time(0)
       {}

    ~AdnsReq()
    {
        if (name)
            free(name);
    }

    void **getArgAddr()                     {   return &arg;        }
    time_t getStartTime()                   {   return start_time;  }

    void setCallback(lookup_pf callback)    {   cb = callback;      }

private:
    int              type;//PF_INET, PF_INET6
    lookup_pf        cb;
    struct sockaddr *result;
    char            *name;
    void            *arg;
    long             start_time;
};


class Adns : public EventReactor, public TSingleton<Adns>
{
    friend class TSingleton<Adns>;

public:

    int  init();
    int  shutdown();
    int  initShm(int uid, int gid);


    static int  deleteCache();
    void        trimCache();
    
    char *getCacheName(const char *pName, int type);
    const char *getCacheValue( const char * pName, int nameLen, int &valLen );

    //Sync mode, return the ip
    const char *getHostByNameInCache( const char * pName, int &length, int type );
    //Async mode, when done will call the cb
    AdnsReq *getHostByName(const char * pName, int type, struct sockaddr *result,
                           lookup_pf cb, void *arg);

    const char *getHostByAddrInCache( const struct sockaddr * pAddr, int &length );
    AdnsReq *getHostByAddr( const struct sockaddr * pAddr, void *arg, lookup_pf cb );

    int  handleEvents( short events );
    void onTimer();
    void setTimeOut(int tmSec);

    static int getHostByNameSync(const char *pName, in_addr_t *addr);
    static int getHostByNameV6Sync(const char *pName, in6_addr *addr);

    LsShmHash  *getShmHash()    {   return m_pShmHash;  }
    void       checkCacheTTL();
private:
    Adns();
    ~Adns();

    static void getHostByNameCb(struct dns_ctx *ctx, void *rr_unknown, void *param);
    static void getHostByAddrCb(struct dns_ctx *ctx, struct dns_rr_ptr *rr, void *param);
    static void printLookupError(struct dns_ctx *ctx, AdnsReq *pAdnsReq);

    void checkDnsEvents();


    struct dns_ctx *    m_pCtx;
    int                 m_iCounter;
    LsShmHash          *m_pShmHash;
    time_t              m_tmLastTrim;

    LS_NO_COPY_ASSIGN(Adns);
};


#endif

