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
#ifndef CLIENTINFO_H
#define CLIENTINFO_H

#include <lsdef.h>

#include <http/throttlecontrol.h>
#include <lsiapi/lsimoduledata.h>
#include <util/autostr.h>


#define CLIENTINFO_NEED_RESET   (1<<0)
#define CLIENTINFO_GOOG_TEST    (1<<1)
#define CLIENTINFO_GOOG_REAL    (1<<2)
#define CLIENTINFO_GOOG_FAKE    (1<<3)

#if 0
#include <shm/lsshmcache.h>

//
//  Data in the SHM
//
// NOT READY - will continue later
typedef struct lsShmClientInfo_s
{
    lsShm_hCacheData_t  x_cache;
    size_t              x_iConns;
    time_t              x_tmOverLimit;
    short               x_sslNewConn;
    int                 x_iHits;
    time_t              x_lastConnect;
    int                 x_iAccess;
    ThrottleControl     x_ctlThrottle;
} lsShmClientInfo_t ;

typedef struct lsShmClientInfo_s    TShmClient;
typedef LsShmCache                  TShmClientPool;
#endif

struct sockaddr;
class GeoInfo;
class LocInfo;
class ClientInfo
{
    char        m_achSockAddr[24];
    AutoStr2    m_sAddr;
    AutoStr2    m_sHostName;
    uint32_t    m_iFlags;
    int32_t     m_iConns;
    GeoInfo    *m_pGeoInfo;
#ifdef USE_IP2LOCATION
    LocInfo    *m_pLocInfo;
#endif
    LsiModuleData   m_moduleData;

    time_t      m_tmOverLimit;
    short       m_sslNewConn;
    int         m_iHits;
    time_t      m_lastConnect;
    int         m_iAccess;

    ThrottleControl     m_ctlThrottle;
    static int  s_iSoftLimitPC;
    static int  s_iHardLimitPC;
    static int  s_iOverLimitGracePeriod;
    static int  s_iBanPeriod;
    //time_t
    //int       m_iBadReqs;
    //int       m_iGoodReqs;
    //int       m_iTimeoutConn;
    //int       m_iDynReqs;
    //int       m_iBytesReceived;
    //int       m_iBytesSent;
    //int       m_iExcessiveConnAttempts;

#if 0
    // NOT READY
    static TShmClientPool *s_base;
    TShmClient *m_pShmClient;
    LsShmOffset_t m_clientOffset;
    static int shmData_init(lsShm_hCacheData_t *, void *pUParam);
    static int shmData_remove(lsShm_hCacheData_t *, void *pUParam);
#endif

public:
    ClientInfo();
    ~ClientInfo();
    const struct sockaddr *getAddr() const
    {   return (struct sockaddr *)m_achSockAddr;         }

    struct sockaddr * getAddr()
    {   return (struct sockaddr *)m_achSockAddr;                    }
    void setAddr(const struct sockaddr *pAddr);

    void clearFlag( int flag )          {   m_iFlags &= ~flag;          }
    void setFlag( int flag )            {   m_iFlags |= flag;           }
    int isFlagSet( int flag ) const     {   return m_iFlags & flag;     }

    int isNeedTestHost() const
    {   return m_iFlags & CLIENTINFO_GOOG_TEST;         }
    int checkHost();
    void verifyIp(void *ip, const long length);

    const char *getAddrString() const  {   return m_sAddr.c_str();     }
    int          getAddrStrLen() const  {   return m_sAddr.len();       }

    void setHostName(const char *p)
    {
        if (p) m_sHostName.setStr(p);
        else     m_sHostName.setStr("", 0);
    }
    const char *getHostName() const    {   return m_sHostName.c_str(); }
    int getHostNameLen() const          {   return m_sHostName.len();   }

    size_t incConn()                    {   return ++m_iConns;      }
    size_t decConn()                    {   return --m_iConns;      }
    size_t getConns() const             {   return m_iConns;        }

    void hit(time_t t)                 {   ++m_iHits; m_lastConnect = t;    }
    void resetHits()                    {   m_iHits = 0;            }
    int  getHits() const                {   return m_iHits;         }

    void setLastConnTime(time_t t)    {   m_lastConnect = t ;     }
    time_t getLastConnTime() const      {   return m_lastConnect;   }

    void setOverLimitTime(time_t t)   {   m_tmOverLimit = t ;     }
    time_t getOverLimitTime() const     {   return m_tmOverLimit;   }

    void setAccess(int access)        {   m_iAccess = access;     }
    int getAccess() const               {   return m_iAccess;       }

    int checkAccess();

    ThrottleControl &getThrottleCtrl()  {   return m_ctlThrottle;   }

    bool allowRead() const      {   return m_ctlThrottle.allowRead();   }
    bool allowWrite() const     {   return m_ctlThrottle.allowWrite();  }

    short incSslNewConn()   {   return ++m_sslNewConn;  }
    short getSslNewConn()   {   return m_sslNewConn;    }
    void  setSslNewConn(int n)   {   m_sslNewConn = n;    }
    GeoInfo *allocateGeoInfo();
    GeoInfo *getGeoInfo() const        {   return m_pGeoInfo;      }

#ifdef USE_IP2LOCATION
    LocInfo *allocateLocInfo();
    LocInfo *getLocInfo() const        {   return m_pLocInfo;      }
#endif

    LsiModuleData *getModuleData()      {   return &m_moduleData;   }

    static void setPerClientSoftLimit(int val)
    {   s_iSoftLimitPC = val;   }
    static int getPerClientSoftLimit()
    {   return s_iSoftLimitPC;  }

    static void setPerClientHardLimit(int val)
    {   s_iHardLimitPC = val;   }
    static int getPerClientHardLimit()
    {   return s_iHardLimitPC;  }

    static void setOverLimitGracePeriod(int val)
    {   s_iOverLimitGracePeriod = val;  }
    static int getOverLimitGracePeriod()
    {   return s_iOverLimitGracePeriod; }

    static void setBanPeriod(int val)
    {   s_iBanPeriod = val;   }
    static int getBanPeriod()
    {   return s_iBanPeriod;  }
#if 0
    TShmClient *getShmClientInfo()
    {
        return (TShmClient *)
               (s_base ? s_base->offset2ptr(m_clientOffset) : NULL);
    }
#endif
    LS_NO_COPY_ASSIGN(ClientInfo);
};

#endif
