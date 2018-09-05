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
typedef int (* lookup_pf)(void *arg, long lParam, void *pParam);
typedef void (* unknownCb)();

class AdnsReq
{
    friend class Adns;
public:
    AdnsReq()
       : cb(NULL)
       , name(NULL)
       , arg(NULL)
       , start_time(0)
       , ref_count(1)
       , type(0)
       {}


    void **getArgAddr()                     {   return &arg;        }
    time_t getStartTime()                   {   return start_time;  }

    void setCallback(lookup_pf callback)    {   cb = callback;      }
    unsigned short getRefCount() const      {   return ref_count;   }
    void incRefCount()                      {   ++ref_count;        }

private:

    ~AdnsReq()
    {
        if (name)
            free(name);
    }

    lookup_pf        cb;
    char            *name;
    void            *arg;
    long             start_time;
    unsigned short   ref_count;
    unsigned short   type;//PF_INET, PF_INET6
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
    AdnsReq *getHostByName(const char * pName, int type, lookup_pf cb, void *arg);

    const char *getHostByAddrInCache( const struct sockaddr * pAddr, int &length );
    AdnsReq *getHostByAddr( const struct sockaddr * pAddr, void *arg, lookup_pf cb );
    
    static int setResult(struct sockaddr *result, const void *ip, int len);
    static void release(AdnsReq *pReq);
    

    int  handleEvents( short events );
    void onTimer();
    void setTimeOut(int tmSec);

    static int getHostByNameSync(const char *pName, in_addr_t *addr);
    static int getHostByNameV6Sync(const char *pName, in6_addr *addr);

    LsShmHash  *getShmHash()    {   return m_pShmHash;  }
    void       checkCacheTTL();
    
    void       processPendingEvt()  
    {
        if (m_iPendingEvt)
        {
            checkDnsEvents();
            m_iPendingEvt = 0;
        }
    }
    
private:
    Adns();
    ~Adns();

    static void getHostByNameCb(struct dns_ctx *ctx, void *rr_unknown, void *param);
    static void getHostByAddrCb(struct dns_ctx *ctx, struct dns_rr_ptr *rr, void *param);
    static void printLookupError(struct dns_ctx *ctx, AdnsReq *pAdnsReq);

    void checkDnsEvents();


    struct dns_ctx *    m_pCtx;
    short               m_iCounter;
    short               m_iPendingEvt;
    LsShmHash          *m_pShmHash;
    time_t              m_tmLastTrim;

    LS_NO_COPY_ASSIGN(Adns);
};


#endif

