/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2016  LiteSpeed Technologies, Inc.                 *
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
#ifndef CACHECONFIG_H
#define CACHECONFIG_H


#include <util/autostr.h>
#include <util/aho.h>
#include <http/vhostmap.h>


//Default setting         0000 0010 0111 1100
#define CACHE_ENABLE_PUBLIC                 (1<<0)
#define CACHE_ENABLE_PRIVATE                (1<<1)
#define CACHE_CHECK_PUBLIC                  (1<<2)
#define CACHE_CHECK_PRIVATE                 (1<<3)
#define CACHE_QS_CACHE                      (1<<4)
#define CACHE_REQ_COOKIE_CACHE              (1<<5)
#define CACHE_IGNORE_REQ_CACHE_CTRL_HEADER  (1<<6)
#define CACHE_IGNORE_RESP_CACHE_CTRL_HEADER (1<<7)
#define CACHE_IGNORE_SURROGATE_HEADER       (1<<8)
#define CACHE_RESP_COOKIE_CACHE             (1<<9)
#define CACHE_MAX_AGE_SET                   (1<<10)
#define CACHE_PRIVATE_AGE_SET               (1<<11)
#define CACHE_STALE_AGE_SET                 (1<<12)
#define CACHE_MAX_OBJ_SIZE                  (1<<13)
#define CACHE_NO_VARY                       (1<<14)
#define CACHE_ADD_ETAG                      (1<<15)


class DirHashCacheStore;

class CacheConfig
{
public:

    CacheConfig();

    ~CacheConfig();

    void inherit(const CacheConfig *pParent);
    void setConfigBit(int bit, int enable)
    {
        m_iCacheConfigBits |= bit;
        m_iCacheFlag = (m_iCacheFlag & ~bit) | ((enable) ? bit : 0);
    }

    void setDefaultAge(int age)       {   m_defaultAge = age;     }
    int  getDefaultAge() const          {   return m_defaultAge;    }

    void setPrivateAge(int age)       {   m_privateAge = age;     }
    int  getPrivateAge() const          {   return m_privateAge;    }

    void setMaxStale(int age)         {   m_iMaxStale = age;       }
    int  getMaxStale() const            {   return m_iMaxStale;      }

    int  isPrivateEnabled() const   {   return m_iCacheFlag & CACHE_ENABLE_PRIVATE;    }
    int  isPrivateCheck() const   {   return m_iCacheFlag & CACHE_CHECK_PRIVATE;   }

    int  isEnabled() const          {   return m_iCacheFlag & CACHE_ENABLE_PUBLIC; }
    int  isCheckPublic() const      {   return m_iCacheFlag & CACHE_CHECK_PUBLIC;       }
    int  isSet(int bit) const     {   return m_iCacheFlag & bit;     }
    int  getConfigBits(int bit) const  {   return m_iCacheConfigBits & bit; }
    void apply(const CacheConfig *pParent);
    void setMaxObjSize(long objSize)  {   m_lMaxObjSize = objSize;  }
    long getMaxObjSize() const      {   return m_lMaxObjSize;   }
    void setAddEtagType(int v)      {   m_iAddEtag = v;     }
    int getAddEtagType() const      { return m_iAddEtag;    }
    int  isLitemagReady();
    void setLitemageDefault();

//     void setStoragePath(const char *s, int len)
//     {
//         m_sStoragePath.setStr(s, len);
//     }
//
//     const char *getStoragePath() const
//     {
//         return m_sStoragePath.c_str();
//     }

    // int getBypassPercentage() {   return m_iBypassPercentage; }

    void setLevel(int v)    { m_iLevele = v; }
    void setOnlyUseOwnUrlExclude(int v)    { m_iOnlyUseOwnUrlExclude = v; }
    int isOnlyUseOwnUrlExclude()    { return m_iOnlyUseOwnUrlExclude; }

    void setOwnStore(int v)    { m_iOwnStore = v; }
    //int getOwnStore()    { return m_iOwnStore; }

    Aho *getUrlExclude() const         {   return m_pUrlExclude;     }
    void setUrlExclude(Aho *pExclude)  {   m_pUrlExclude = pExclude; }
    Aho *getParentUrlExclude() const         {   return m_pParentUrlExclude;     }
    void setParentUrlExclude(Aho *pExclude)  {   m_pParentUrlExclude = pExclude; }

    VHostMap *getVHostMapExclude() const         {   return m_pVHostMapExclude;     }
    void setVHostMapExclude(VHostMap *v)  {   m_pVHostMapExclude = v; }

    DirHashCacheStore *getStore() const { return m_pStore; }
    void setStore(DirHashCacheStore *pStore) { m_pStore = pStore; }



private:
    short   m_iCacheConfigBits;
    short   m_iCacheFlag;
    int     m_defaultAge;
    int     m_privateAge;
    int     m_iMaxStale;
    long    m_lMaxObjSize;
    int8_t  m_iLevele;  //SERVER, VHOST or context
    int8_t  m_iOnlyUseOwnUrlExclude;
    int8_t  m_iOwnStore;
    int8_t  m_iAddEtag;  //0, no, 1: add size-mtime; 2: xxhash64


    Aho        *m_pUrlExclude; //server and Vhost level can have it
    Aho        *m_pParentUrlExclude;
    VHostMap   *m_pVHostMapExclude;//Only server level has it
    DirHashCacheStore *m_pStore;
};

#endif
