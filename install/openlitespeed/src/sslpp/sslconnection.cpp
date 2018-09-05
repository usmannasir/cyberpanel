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
#include "sslconnection.h"
// #include "sslerror.h"
#include "sslsesscache.h"
#include <log4cxx/logger.h>

#include <lsdef.h>

#include <errno.h>
#include <string.h>
#include <assert.h>
#include <config.h>
#include <sys/uio.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <poll.h>
#include <lsr/ls_pool.h>

//#define DEBUGGING

#ifdef DEBUGGING

#define DEBUG_MESSAGE( ...)  LS_LOG(log4cxx::Level::DEBUG, __VA_ARGS__);

#else

#define DEBUG_MESSAGE(...)

#endif


const int RBIO_BUF_SIZE = 1024;
int32_t SslConnection::s_iConnIdx = -1;

//static const char * s_pErrInvldSSL = "Invalid Parameter, SSL* ssl is null\n";

SslConnection::SslConnection()
    : m_ssl(NULL)
    , m_iStatus(DISCONNECTED)
    , m_iWant(0)
    , m_iFlag(0)
    , m_iFreeCtx(0)
    , m_iFreeSess(0)
    , m_iUseRbio(0)
    , m_rbioBuf(NULL)
    , m_rbioBuffered(0)
{
}


SslConnection::SslConnection(SSL *ssl)
    : m_ssl(ssl)
    , m_iStatus(DISCONNECTED)
    , m_iWant(0)
    , m_iFlag(0)
    , m_iFreeCtx(0)
    , m_iFreeSess(0)
    , m_iUseRbio(0)
    , m_rbioBuf(NULL)
    , m_rbioBuffered(0)
{
    SSL_set_ex_data(ssl, s_iConnIdx, (void *)this);
}


SslConnection::SslConnection(SSL *ssl, int fd)
    : m_ssl(ssl)
    , m_iStatus(DISCONNECTED)
    , m_iWant(0)
    , m_iFlag(0)
    , m_iFreeCtx(0)
    , m_iFreeSess(0)
    , m_iUseRbio(0)
    , m_rbioBuf(NULL)
    , m_rbioBuffered(0)
{
    m_iRFd = fd;
    SSL_set_wfd(m_ssl, fd);
    SSL_set_ex_data(ssl, s_iConnIdx, (void *)this);
}


SslConnection::SslConnection(SSL *ssl, int rfd, int wfd)
    : m_ssl(ssl)
    , m_iStatus(DISCONNECTED)
    , m_iWant(0)
    , m_iFlag(0)
    , m_iFreeCtx(0)
    , m_iFreeSess(0)
    , m_rbioBuf(NULL)
    , m_rbioBuffered(0)
{
    m_iRFd = rfd;
    SSL_set_wfd(m_ssl, wfd);
    SSL_set_ex_data(ssl, s_iConnIdx, (void *)this);
}


SslConnection::~SslConnection()
{
    if (m_rbioBuf)
        ls_pfree(m_rbioBuf);
    if (m_ssl)
        release();
}


void SslConnection::setSSL(SSL *ssl)
{
    assert(!m_ssl);
    //m_iWant = 0;
    m_ssl = ssl;
    m_iFlag = 0;
    SSL_set_ex_data(ssl, s_iConnIdx, (void *)this);
}

void SslConnection::release()
{
    assert(m_ssl);
    if (m_iStatus != DISCONNECTED)
        shutdown(0);
    if (m_iFreeSess != 0)
        SSL_SESSION_free(SSL_get_session(m_ssl));
    if (m_iFreeCtx != 0)
        SSL_CTX_free(SSL_get_SSL_CTX(m_ssl));

    SSL_free(m_ssl); // This frees the bound BIOs
    // All buffer counters must be set to 0 to reset everything.
    m_rbioBuffered = 0;
    m_iRFd = -1;
    m_ssl = NULL;
    
    if (m_rbioBuf)
    {
        ls_pfree(m_rbioBuf);
        m_rbioBuf = NULL;
    }
}


int SslConnection::installRbio(int rfd, int wfd)
{
    DEBUG_MESSAGE("beginBIO, this: %p\n", this);
    assert(m_ssl);
    /**
     * Even though this is only used for the first read, we're setting and 
     * creating a BIO for both sides.  As it's necessary for negotiation. */
    
    BIO *rbio = BIO_new(BIO_s_mem());
    if (!rbio)
    {
        DEBUG_MESSAGE("beginBIO - first BIO_new failed!\n");
        errno = ENOMEM;
        m_iUseRbio = 0;
        return -1;
    }
    if (!(m_rbioBuf = (char *)ls_palloc(RBIO_BUF_SIZE)))
    {
        DEBUG_MESSAGE("Insufficient memory allocating %d bytes\n",
                        RBIO_BUF_SIZE);
        BIO_free(rbio);
        errno = ENOMEM;
        m_iUseRbio = 0;
        return -1;
    }

    m_iRFd = rfd;
#ifndef OPENSSL_IS_BORINGSSL
    SSL_set_fd(m_ssl, rfd);
    m_saved_rbio = SSL_get_rbio(m_ssl);
#if OPENSSL_VERSION_NUMBER >= 0x10100000L
    BIO_up_ref(m_saved_rbio);
    SSL_set0_rbio(m_ssl, rbio);
#else
    m_ssl->rbio = rbio;
#endif //OPENSSL_VERSION_NUMBER >= 0x10100000L
#else
    SSL_set_bio(m_ssl, rbio, NULL);
    SSL_set_wfd(m_ssl, wfd);
#endif
    return 0;
}


int SslConnection::setfd(int fd)
{
    m_iWant = 0;

    if (m_iUseRbio && installRbio(fd,fd) == 0)
        return 1;
    if (SSL_set_fd(m_ssl, fd) == -1)
        ;
    return 1;
}


int SslConnection::setfd(int rfd, int wfd)
{
    m_iWant = 0;
    if (m_iUseRbio && installRbio(rfd,wfd) == 0)
        return 1;
    if (SSL_set_rfd(m_ssl, rfd) == -1 || SSL_set_wfd(m_ssl, wfd) == -1)
    {
        m_iStatus = DISCONNECTED;
        return 0;
    }
    return 1;
}


int SslConnection::readRbioClientHello()
{
    int ret;

    // Go through the state machine...
    DEBUG_MESSAGE("readBIO state: 0x%x\n", SSL_get_state(m_ssl));
    
    ssize_t dataRead;
    DEBUG_MESSAGE("readBIO buffered: %d\n", m_rbioBuffered);
    // Return if no data to service the next request.
    dataRead = recv(m_iRFd, &m_rbioBuf[m_rbioBuffered],
                    RBIO_BUF_SIZE - m_rbioBuffered, 0);
    if (dataRead == -1)
    {
        if ((errno == EAGAIN) || (errno == EWOULDBLOCK))
        {
            DEBUG_MESSAGE("readBIO retry recv\n");
            return 0; 
        }
        DEBUG_MESSAGE("recv failed, errno: %d\n", errno);
        return -1;    
    }
    else if (dataRead == 0)
    {
        DEBUG_MESSAGE("recv closed.  Handle it as an error\n");
        errno = ECONNRESET; // Just something somewhat descriptive
        return -1;    
    }
    DEBUG_MESSAGE("readBIO received %d bytes\n", (int)dataRead);
    
    ERR_clear_error();
    ret = BIO_write(SSL_get_rbio(m_ssl), &m_rbioBuf[m_rbioBuffered], dataRead);
    m_rbioBuffered += (int)dataRead;
     
    if (ret <= 0) 
    {
        DEBUG_MESSAGE("readBIO BIO_write FAILED (unrecoverable)!\n");
        return -1;
    }
    return 1;
}


void SslConnection::restoreRbio()
{
    DEBUG_MESSAGE("remove recv BIO layer.\n");
#ifdef OPENSSL_IS_BORINGSSL
    SSL_set_rfd(m_ssl, m_iRFd);
#else
#if OPENSSL_VERSION_NUMBER >= 0x10100000L
    SSL_set0_rbio(m_ssl,m_saved_rbio);
    BIO_free(m_saved_rbio);
#else
    BIO_free_all(m_ssl->rbio);
    m_ssl->rbio = m_saved_rbio;
#endif
#endif
    ls_pfree(m_rbioBuf);
    m_rbioBuf = NULL;
    m_iUseRbio = 0;
}


int SslConnection::read(char *pBuf, int len)
{
    int ret;
    assert(m_ssl);
    m_iWant = 0;
  
    ret = SSL_read(m_ssl, pBuf, len);
    if (ret > 0)
    {
        if (ret < len) 
        {
            pBuf[ret] = 0;
        }
        return ret;
    }
    else
    {
        m_iWant = LAST_READ;
        return checkError(ret);
    }
}


#define MAX_SSL_WRITE_SIZE 8192
int SslConnection::write(const char *pBuf, int len)
{
    assert(m_ssl);
    m_iWant = 0;
    if (len <= 0)
        return 0;

    int writeLen, ret = 0;
    do
    {
        writeLen = (len > MAX_SSL_WRITE_SIZE ? MAX_SSL_WRITE_SIZE : len);
        int rc = SSL_write(m_ssl, pBuf, writeLen);
        if (rc > 0)
        {
            ret += rc;
            len -= rc;
            pBuf += rc;
        }
        else
        {
            if (ret == 0)
            {
                m_iWant = LAST_WRITE;
                return checkError(rc);
            }
            else
                return ret; //Do not change the state since not finished
        }
    }
    while (len > 0);

    m_iWant &= ~LAST_WRITE;
    return ret;
}


int SslConnection::writev(const struct iovec *vect, int count,
                          int *finished)
{
    int ret = 0;

    const struct iovec *pEnd = vect + count;
    const char *pBuf;
    int bufSize;
    int written;

    char *pBufEnd;
    char *pCurEnd;
    char achBuf[4096];
    
    pBufEnd = achBuf + 4096;
    pCurEnd = achBuf;
    for (; vect < pEnd ;)
    {
        pBuf = (const char *) vect->iov_base;
        bufSize = vect->iov_len;
        if (bufSize < 1024)
        {
            if (pBufEnd - pCurEnd > bufSize)
            {
                memmove(pCurEnd, pBuf, bufSize);
                pCurEnd += bufSize;
                ++vect;
                if (vect < pEnd)
                    continue;
            }
            pBuf = achBuf;
            bufSize = pCurEnd - pBuf;
            pCurEnd = achBuf;
        }
        else if (pCurEnd != achBuf)
        {
            pBuf = achBuf;
            bufSize = pCurEnd - pBuf;
            pCurEnd = achBuf;
        }
        else
            ++vect;
        written = write(pBuf, bufSize);
        if (written > 0)
        {
            ret += written;
            if (written < bufSize)
                break;
        }
        else if (!written)
            break;
        else
            return LS_FAIL;
    }
    if (finished)
        *finished = (vect == pEnd);
    return ret;
}


int SslConnection::wpending()
{
    BIO *pBIO = SSL_get_wbio(m_ssl); // This should work either way
    return BIO_wpending(pBIO);
}


int SslConnection::flush()
{
    BIO *pBIO = SSL_get_wbio(m_ssl);
    if (!pBIO)
        return 0;
    m_iWant = 0;
    int ret = BIO_flush(pBIO);
    if (ret != 1)
        ret = checkError(ret);

    //1 means BIO_flush succeed.
    switch (ret)
    {
    case 1:
        return LS_DONE;
    case 0:
        return LS_AGAIN;
    case -1:
    default:
        return LS_FAIL;
    }
}


int SslConnection::shutdown(int bidirectional)
{
    assert(m_ssl);
    
    m_iFlag = 0;
    if (m_iStatus == ACCEPTING)
    {
        ERR_clear_error();
        m_iStatus = DISCONNECTED;
        return 0;
    }
    if (m_iStatus != DISCONNECTED)
    {
        m_iWant = 0;
        SSL_set_shutdown(m_ssl, SSL_SENT_SHUTDOWN | SSL_RECEIVED_SHUTDOWN);
        //SSL_set_quiet_shutdown( m_ssl, !bidirectional );
        int ret = SSL_shutdown(m_ssl);
        if ((ret) ||
            ((ret == 0) && (!bidirectional)))
        {
            m_iStatus = DISCONNECTED;
            return 0;
        }
        else
            m_iStatus = SHUTDOWN;
        return checkError(ret);
    }
    return 0;
}


void SslConnection::toAccept()
{
    m_iStatus = ACCEPTING;
    m_iWant = READ;
}


int SslConnection::accept()
{
    int ret;
    DEBUG_MESSAGE("accept\n");
    assert(m_ssl);
    if (m_iStatus != ACCEPTING) {
        DEBUG_MESSAGE("In accept but not in ACCEPTING status\n");
        return -1;
    }
    if (m_iUseRbio && (m_iWant & READ))
    {
        DEBUG_MESSAGE("Accept want to read more data, so read and save\n");
        ret = readRbioClientHello();
        if (ret < 0)
            return ret;
    }
    ret = SSL_accept(m_ssl);
    DEBUG_MESSAGE("SSL_accept rc: %d\n",ret);
    if (ret == 1)
    {
        DEBUG_MESSAGE("SSL_accept worked - move to connected status\n");
        m_iStatus = CONNECTED;
        m_iWant = READ;
    }
    else
    {
        ret = checkError(ret);
        if (m_iWant & READ)
        {
            DEBUG_MESSAGE("accept wants read more data\n");
        }
        if (m_iWant & WRITE)
        {
            DEBUG_MESSAGE("accept wants write more data\n");
        }
    }
    if (m_iUseRbio && ret != -1 && m_rbioBuffered > 100)
    {
        restoreRbio();
    }
    return ret;
}


int SslConnection::checkError(int ret)
{
    int err = SSL_get_error(m_ssl, ret);
#ifdef DEBUGGING
    char errorString1[1024];
    char errorString2[1024];
    DEBUG_MESSAGE("checkError returned %d, first error: %s, last error: %s\n",
                  err, ERR_error_string(ERR_peek_error(), errorString1), 
                  ERR_error_string(ERR_peek_last_error(), errorString2));
#endif
    switch (err)
    {
    case SSL_ERROR_NONE:
        ERR_clear_error();
        return 0;
        
    case SSL_ERROR_WANT_READ:
    case SSL_ERROR_WANT_WRITE:
        if (err == SSL_ERROR_WANT_READ)
        {
            m_iWant |= READ;
        }
        else
        {
            m_iWant |= WRITE;
        }
        ERR_clear_error();
        return 0;
    case SSL_ERROR_SYSCALL:
        {
            int ret = ERR_get_error();
            if (ret == 0)
            {
                errno = ECONNRESET;
                break;
            }
        }
    default:
        errno = EIO;
        //printf( "SslError:%s\n", SslError(err).what() );
    }
    return LS_FAIL;
}


int SslConnection::connect()
{
    assert(m_ssl);
    m_iStatus = CONNECTING;
    m_iWant = 0;
    int ret = SSL_connect(m_ssl);
    if (ret == 1)
    {
        m_iStatus = CONNECTED;
        return 1;
    }
    else
        return checkError(ret);
}


int SslConnection::tryagain()
{    
    assert(m_ssl);
    switch (m_iStatus)
    {
    case CONNECTING:
        return connect();
    case ACCEPTING:
        return accept();
    case SHUTDOWN:
        return shutdown(1);
    }
    return 0;
}


X509 *SslConnection::getPeerCertificate() const
{   return SSL_get_peer_certificate(m_ssl);   }


long SslConnection::getVerifyResult() const
{   return SSL_get_verify_result(m_ssl);      }


int SslConnection::getVerifyMode() const
{   return SSL_get_verify_mode(m_ssl);        }


const char *SslConnection::getCipherName() const
{   return SSL_get_cipher_name(m_ssl);    }


const SSL_CIPHER *SslConnection::getCurrentCipher() const
{   return SSL_get_current_cipher(m_ssl); }


SSL_SESSION *SslConnection::getSession() const
{   return SSL_get_session(m_ssl);        }


int SslConnection::setSession(SSL_SESSION *session) const
{   return SSL_set_session(m_ssl, session);     }


int SslConnection::isSessionReused() const
{   return SSL_session_reused(m_ssl);       }


const char *SslConnection::getVersion() const
{   return SSL_get_version(m_ssl);        }


static const char NPN_SPDY_PREFIX[] = { 's', 'p', 'd', 'y', '/' };
int SslConnection::getSpdyVersion()
{
    int v = 0;

#ifdef LS_ENABLE_SPDY
    unsigned int             len = 0;
    const unsigned char     *data = NULL;

#ifdef TLSEXT_TYPE_application_layer_protocol_negotiation
    SSL_get0_alpn_selected(m_ssl, &data, &len);
#endif

#ifdef TLSEXT_TYPE_next_proto_neg
    if (!data)
        SSL_get0_next_proto_negotiated(m_ssl, &data, &len);
#endif
    if (len > sizeof(NPN_SPDY_PREFIX) &&
        strncasecmp((const char *)data, NPN_SPDY_PREFIX,
                    sizeof(NPN_SPDY_PREFIX)) == 0)
    {
        v = data[ sizeof(NPN_SPDY_PREFIX) ] - '1';
        if ((v == 2) && (len >= 8) && (data[6] == '.') && (data[7] == '1'))
            v = 3;
        return v;
    }

    //h2: http2 version is 4
    if (len >= 2 && data[0] == 'h' && data[1] == '2')
        return 4;
#endif
    return v;
}


void SslConnection::initConnIdx()
{
    if (s_iConnIdx < 0)
        s_iConnIdx = SSL_get_ex_new_index(0, NULL, NULL, NULL, NULL);
}


int SslConnection::getSessionIdLen(SSL_SESSION *s)
//{   return s->session_id_length;     }
{
    unsigned int len;
    SSL_SESSION_get_id((const SSL_SESSION *)s, &len);
    return len;
}


const unsigned char *SslConnection::getSessionId(SSL_SESSION *s)
//{   return s->session_id;           }
{   
    unsigned int len;
    return SSL_SESSION_get_id((const SSL_SESSION *)s, &len);
}


int SslConnection::getCipherBits(const SSL_CIPHER *pCipher,
                                 int *algkeysize)
{
    return SSL_CIPHER_get_bits((SSL_CIPHER *)pCipher, algkeysize);
}


int SslConnection::isClientVerifyOptional(int i)
{   return i == SSL_VERIFY_PEER;    }


int SslConnection::isVerifyOk() const
{   return SSL_get_verify_result(m_ssl) == X509_V_OK;     }


int SslConnection::buildVerifyErrorString(char *pBuf, int len) const
{
    return snprintf(pBuf, len, "FAILED: %s", X509_verify_cert_error_string(
                        SSL_get_verify_result(m_ssl)));
}


int SslConnection::setTlsExtHostName(const char *pName)
{
    if (pName)
        return SSL_set_tlsext_host_name(m_ssl, pName);
    return  0;
}


char* SslConnection::getRawBuffer(int *len)
{
    DEBUG_MESSAGE("getRawBuffer: len: %d\n", m_rbioBuffered);
    *len = m_rbioBuffered;
    return m_rbioBuf;
}



void SslConnection::cacheClientSession(SSL_SESSION* session)
{
    if (m_pSessCache)
        m_pSessCache->saveSession(NULL, 0, session);
}


void SslConnection::tryReuseCachedSession()
{
    if (!m_pSessCache)
        return;
    SSL_SESSION *session = m_pSessCache->getSession(NULL, 0);
    if (session)
        SSL_set_session(m_ssl, session);
}





