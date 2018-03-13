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
#ifndef SSLCONNECTION_H
#define SSLCONNECTION_H
#include <lsdef.h>



typedef struct x509_st X509;
typedef struct ssl_cipher_st SSL_CIPHER;
typedef struct ssl_st SSL;
typedef struct ssl_ctx_st SSL_CTX;
typedef struct ssl_session_st SSL_SESSION;

class SslConnection
{
    SSL    *m_ssl;
    int     m_iStatus;
    int     m_iWant;
    int     m_iFlag;
    char    m_iFreeCtx;
    char    m_iFreeSess;
    static int32_t s_iConnIdx;

public:
    enum
    {
        DISCONNECTED,
        CONNECTING,
        ACCEPTING,
        CONNECTED,
        SHUTDOWN
    };
    enum
    {
        READ = 1,
        WRITE = 2,
        LAST_READ = 4,
        LAST_WRITE = 8
    };

    int wantRead() const    {   return m_iWant & READ;  }
    int wantWrite() const   {   return m_iWant & WRITE; }
    int lastRead() const    {   return m_iWant & LAST_READ; }
    int lastWrite() const   {   return m_iWant & LAST_WRITE; }

    char getFlag() const    {   return m_iFlag;     }
    void setFlag(int flag) {   m_iFlag = flag;     }

    char getFreeCtx() const {   return m_iFreeCtx;      }
    void setFreeCtx()       {   m_iFreeCtx = 1;         }

    char getFreeSess() const    {   return m_iFreeSess;     }
    void setFreeSess()          {   m_iFreeSess = 1;        }

    SslConnection();
    explicit SslConnection(SSL *ssl);
    SslConnection(SSL *ssl, int fd);
    SslConnection(SSL *ssl, int rfd, int wfd);
    ~SslConnection();

    void setSSL(SSL *ssl);
    SSL *getSSL() const    {   return m_ssl;   }

    void release();
    int setfd(int fd);
    int setfd(int rfd, int wfd);

    void toAccept();
    int accept();
    int connect();
    int read(char *pBuf, int len);
    int wpending();
    int write(const char *pBuf, int len);
    int writev(const struct iovec *vect, int count, int *finished);
    int flush();
    int shutdown(int bidirectional);
    int checkError(int ret);
    bool isConnected()      {   return m_iStatus == CONNECTED;  }
    int tryagain();

    int getStatus() const   {   return m_iStatus;   }

    X509 *getPeerCertificate() const;
    long getVerifyResult() const;
    int  getVerifyMode() const;
    int  isVerifyOk() const;
    int  buildVerifyErrorString(char *pBuf, int len) const;

    const char *getCipherName() const;

    const SSL_CIPHER *getCurrentCipher() const;

    SSL_SESSION *getSession() const;

    const char *getVersion() const;

    int setTlsExtHostName(const char *pName);

    int getSpdyVersion();

    static void initConnIdx();
    static int getConnIdx()         {   return s_iConnIdx;   }
    static int getSessionIdLen(SSL_SESSION *s);
    static const unsigned char *getSessionId(SSL_SESSION *s);
    static int getCipherBits(const SSL_CIPHER *pCipher, int *algkeysize);
    static int isClientVerifyOptional(int i);

    LS_NO_COPY_ASSIGN(SslConnection);
};

#endif
