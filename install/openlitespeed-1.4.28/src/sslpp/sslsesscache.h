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
#ifndef SSLSESSCACHE_H
#define SSLSESSCACHE_H

#include <lsdef.h>
#include <util/tsingleton.h>

#include <openssl/ssl.h>

#include <stdint.h>
#include <unistd.h>


#define LS_SSLSESSCACHE_DEFAULTSIZE 40*1024

class LsShmHash;
typedef struct SslSessData_s SslSessData_t;

//
//  SslSessCache
//
class SslSessCache : public TSingleton<SslSessCache>
{
    friend class TSingleton<SslSessCache>;

public:
    static int watchCtx(SSL_CTX *pCtx);

    int     init(int32_t iTimeout, int iMaxEntries);
    int     isReady() const              {   return m_pSessStore != NULL;   }
    int32_t getExpireSec() const         {   return m_expireSec;            }
    void    setExpireSec(int32_t iExpire) {   m_expireSec = iExpire;         }

    int     sessionFlush();
    int     stat();
    int     addSession(unsigned char *pId, int idLen,
                       unsigned char *pData, int iDataLen);
    SSL_SESSION *getSession(unsigned char *id, int len);
    SslSessData_t *getLockedSessionData(unsigned char *id, int len);

    void    unlock();
    LsShmHash *getSessStore() const
    {   return m_pSessStore;    }

private:
    SslSessCache();
    ~SslSessCache();

    int     initShm();

private:
    int32_t                 m_expireSec;
    int                     m_maxEntries;
    LsShmHash              *m_pSessStore;

    LS_NO_COPY_ASSIGN(SslSessCache);
};

#endif // SSLSESSCACHE_H

