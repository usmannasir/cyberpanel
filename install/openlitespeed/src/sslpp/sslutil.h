/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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

#ifndef SSLUTIL_H
#define SSLUTIL_H

#include <openssl/ssl.h>

class AutoBuf;
class SslUtil
{
    static const char *s_pDefaultCAFile;
    static const char *s_pDefaultCAPath;

    SslUtil();
    ~SslUtil();
    SslUtil(const SslUtil &rhs);
    void operator=(const SslUtil &rhs);
public:
    enum
    {
        FILETYPE_PEM,
        FILETYPE_ASN1
    };
    static void setUseStrongDH(int use);
    static int initDH(SSL_CTX *pCtx, const char *pFile, int iKeyLen);
    static int copyDH(SSL_CTX *pCtx, SSL_CTX *pSrcCtx);
    static int initECDH(SSL_CTX *pCtx);
    static int translateType(int type);
    static int loadPemWithMissingDash(const char *pFile, char *buf, int bufLen,
                                      char **pBegin);
    static int digestIdContext(SSL_CTX *pCtx, const void *pDigest,
                               size_t iDigestLen);
    static int loadCert(SSL_CTX *pCtx, void *pCert, int iCertLen);
    static int loadPrivateKey(SSL_CTX *pCtx, void *pKey, int iKeyLen);
    static int loadCertFile(SSL_CTX *pCtx, const char *pFile, int type);
    static int loadPrivateKeyFile(SSL_CTX *pCtx, const char *pFile, int type);
    static bool loadCA(SSL_CTX *pCtx, const char *pCAFile, const char *pCAPath,
                       int cv);
    static bool loadCA(SSL_CTX *pCtx, const char *pCAbuf);

    static int initDefaultCA(const char *pCAFile, const char *pCAPath);
    static const char *getDefaultCAFile()
    {
        if (!s_pDefaultCAFile)
            initDefaultCA(NULL, NULL);
        return s_pDefaultCAFile;
    }
    static const char *getDefaultCAPath()
    {
        if (!s_pDefaultCAPath)
            initDefaultCA(NULL, NULL);
        return s_pDefaultCAPath;
    }
    static int setCertificateChain(SSL_CTX *pCtx, BIO * bio);

    static void initCtx(SSL_CTX *pCtx, int method, char renegProtect);
    static long setOptions(SSL_CTX *pCtx, long options);
    static long getOptions(SSL_CTX *pCtx);
    static int setCipherList(SSL_CTX *pCtx, const char *pList);
    static void updateProtocol(SSL_CTX *pCtx, int method);
    static int enableShmSessionCache(SSL_CTX *pCtx);

    static int getPrivateKeyPem(SSL_CTX *pCtx, AutoBuf *pBuf);
    static int getCertPem(SSL_CTX *pCtx, AutoBuf *pBuf);
    static int getCertChainPem(SSL_CTX *pCtx, AutoBuf *pBuf);
    static int enableSessionTickets(SSL_CTX *pCtx);
    static void disableSessionTickets(SSL_CTX *pCtx);
};

#endif
