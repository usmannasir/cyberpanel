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

#ifndef SSLTICKET_H
#define SSLTICKET_H

#include <util/tsingleton.h>
#include <stdint.h>

#define SSLTICKET_NUMKEYS 3

class LsShmHash;
class AutoStr2;
typedef struct STShmData_s STShmData_t;
typedef uint32_t LsShmOffset_t;
typedef struct ssl_st SSL;
typedef struct ssl_ctx_st SSL_CTX;
typedef struct evp_cipher_ctx_st EVP_CIPHER_CTX;
typedef struct hmac_ctx_st HMAC_CTX;

typedef struct STKey_s
{
    unsigned char aName[16];
    unsigned char aAes[16];
    unsigned char aHmac[16];
    long          expireSec;
} STKey_t;

class SslTicket : public TSingleton<SslTicket>
{
    friend class TSingleton<SslTicket>;
    LsShmHash      *m_pKeyStore;
    AutoStr2       *m_pFile;
    LsShmOffset_t   m_iOff;
    STKey_t         m_aKeys[SSLTICKET_NUMKEYS];
    short           m_idxPrev;
    short           m_idxCur;
    short           m_idxNext;
    long            m_iLifetime;

    SslTicket();
    SslTicket(const SslTicket &rhs);
    void *operator=(const SslTicket &rhs);

    int         initShm();
    int         checkShmExpire(STShmData_t *pShmData);
    int         doCb(SSL *pSSL, unsigned char aName[16], unsigned char *iv,
                     EVP_CIPHER_CTX *ectx, HMAC_CTX *hctx, int enc);
    static int  ticketCb(SSL *pSSL, unsigned char aName[16], unsigned char *iv,
                         EVP_CIPHER_CTX *ectx, HMAC_CTX *hctx, int enc)
    {   return getInstance().doCb(pSSL, aName, iv, ectx, hctx, enc);    }
public:
    ~SslTicket();

    int         init(const char *pFileName, long timeout);
    int         onTimer();

    void        disableCtx(SSL_CTX *pCtx);
    int         enableCtx(SSL_CTX *pCtx);
};

#endif

