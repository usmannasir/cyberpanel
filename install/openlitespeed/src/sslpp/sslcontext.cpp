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
#include "sslcontext.h"

#include <log4cxx/logger.h>
#include <main/configctx.h>
#include <sslpp/sslconnection.h>
#include <sslpp/sslerror.h>
#include <sslpp/sslocspstapling.h>
#include <sslpp/sslsesscache.h>
#include <sslpp/sslticket.h>
#include <sslpp/sslutil.h>
#include <util/xmlnode.h>

#include <openssl/err.h>
#include <openssl/rand.h>
#include <openssl/ssl.h>

#include <openssl/evp.h>

#include <ctype.h>
#include <fcntl.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>
#include <limits.h>

int     SslContext::s_iEnableMultiCerts = 0;
void SslContext::setUseStrongDH(int use)
{
    SslUtil::setUseStrongDH(use);
}


long SslContext::getOptions()
{
    return SSL_CTX_get_options(m_pCtx);
}


long SslContext::setOptions(long options)
{
    return SSL_CTX_set_options(m_pCtx, options);
}


int SslContext::seedRand(int len)
{
    static int fd = open("/dev/urandom", O_RDONLY | O_NONBLOCK);
    char achBuf[2048];
    int ret;
    if (fd >= 0)
    {
        int toRead;
        do
        {
            toRead = sizeof(achBuf);
            if (len < toRead)
                toRead = len;
            ret = read(fd, achBuf, toRead);
            if (ret > 0)
            {
                RAND_seed(achBuf, ret);
                len -= ret;
            }
        }
        while ((len > 0) && (ret == toRead));
        fcntl(fd, F_SETFD, FD_CLOEXEC);
        //close( fd );
    }
    else
    {
#ifdef DEVRANDOM_EGD
        /* Use an EGD socket to read entropy from an EGD or PRNGD entropy
         * collecting daemon. */
        static const char *egdsockets[] = { "/var/run/egd-pool", "/dev/egd-pool", "/etc/egd-pool" };
        for (egdsocket = egdsockets; *egdsocket && n < len; egdsocket++)
        {

            ret = RAND_egd_bytes(*egdsocket, len);
            if (ret > 0)
                len -= ret;
        }
#endif
    }
    if (len == 0)
        return 0;
    if (len > (int)sizeof(achBuf))
        len = (int)sizeof(achBuf);
    gettimeofday((timeval *)achBuf, NULL);
    ret = sizeof(timeval);
    *(pid_t *)(achBuf + ret) = getpid();
    ret += sizeof(pid_t);
    *(uid_t *)(achBuf + ret) = getuid();
    ret += sizeof(uid_t);
    if (len > ret)
        memmove(achBuf + ret, achBuf + sizeof(achBuf) - len + ret, len - ret);
    RAND_seed(achBuf, len);
    return 0;
}


void SslContext::setProtocol(int method)
{
    if (method == m_iMethod)
        return;
    if ((method & SSL_ALL) == 0)
        return;
    m_iMethod = method;
    updateProtocol(method);
}


void SslContext::updateProtocol(int method)
{
    SslUtil::updateProtocol(m_pCtx, method);
}


int SslContext::initDH(const char *pFile)
{
    return SslUtil::initDH(m_pCtx, pFile, m_iKeyLen);
}


int SslContext::initECDH()
{
    return SslUtil::initECDH(m_pCtx);
}

static int s_ctx_ex_index = -1;

void SslContext::linkSslContext()
{
    if (s_ctx_ex_index == -1)
    {
        s_ctx_ex_index = SSL_CTX_get_ex_new_index(0, NULL, NULL, NULL, NULL);
    }
    SSL_CTX_set_ex_data(m_pCtx, s_ctx_ex_index, this);
}


SslContext *SslContext::getSslContext(SSL_CTX *ctx)
{
    return (SslContext *)SSL_CTX_get_ex_data(ctx, s_ctx_ex_index);
}


int SslContext::init(int iMethod)
{
    if (m_pCtx != NULL)
        return 0;
    SSL_METHOD *meth;
    if (initSSL())
        return LS_FAIL;
    m_iMethod = iMethod;
    m_iEnableSpdy = 0;
    m_iEnableOcsp = 0;
    meth = (SSL_METHOD *)SSLv23_method();
    m_pCtx = SSL_CTX_new(meth);
    if (m_pCtx)
    {
        SslUtil::initCtx(m_pCtx, iMethod, m_iRenegProtect);
        //initDH( NULL );
        //initECDH();
        linkSslContext();
        return 0;
    }
    else
    {
        //TODO: log ssl error
        return LS_FAIL;
    }
}


SslContext::SslContext(int iMethod)
    : m_pCtx(NULL)
    , m_iMethod(iMethod)
    , m_iRenegProtect(1)
    , m_iEnableSpdy(0)
    , m_iEnableOcsp(0)
    , m_iKeyLen(1024)
    , m_pStapling(NULL)
{
}


SslContext::~SslContext()
{
    release();
}


void SslContext::release()
{
    if (m_pCtx != NULL)
    {
        SSL_CTX *pCtx = m_pCtx;
        m_pCtx = NULL;
        SSL_CTX_free(pCtx);
    }
    if (m_pStapling)
        delete m_pStapling;
}


SSL *SslContext::newSSL()
{
    init(m_iMethod);
    return SSL_new(m_pCtx);
}


static int isFileChanged(const char *pFile, const struct stat &stOld)
{
    struct stat st;
    if (::stat(pFile, &st) == -1)
        return 0;
    return ((st.st_size != stOld.st_size) ||
            (st.st_ino != stOld.st_ino) ||
            (st.st_mtime != stOld.st_mtime));
}


int SslContext::isKeyFileChanged(const char *pKeyFile) const
{
    return isFileChanged(pKeyFile, m_stKey);
}


int SslContext::isCertFileChanged(const char *pCertFile) const
{
    return isFileChanged(pCertFile, m_stCert);
}


int SslContext::setKeyCertificateFile(const char *pFile, int iType,
                                      int chained)
{
    return setKeyCertificateFile(pFile, iType, pFile, iType, chained);
}


int SslContext::setKeyCertificateFile(const char *pKeyFile, int iKeyType,
                                      const char *pCertFile, int iCertType,
                                      int chained)
{
    if (!setCertificateFile(pCertFile, iCertType, chained))
        return 0;
    if (!setPrivateKeyFile(pKeyFile, iKeyType))
        return 0;
    return  SSL_CTX_check_private_key(m_pCtx);
}


static const int max_certs = 4;
static const int max_path_len = 512;
int SslContext::setMultiKeyCertFile(const char *pKeyFile, int iKeyType,
                                    const char *pCertFile, int iCertType,
                                    int chained)
{
    int i, iCertLen, iKeyLen, iLoaded = 0;
    char achCert[max_path_len], achKey[max_path_len];
    const char *apExt[max_certs] = {"", ".rsa", ".dsa", ".ecc"};
    char *pCertCur, *pKeyCur;

    iCertLen = snprintf(achCert, max_path_len, "%s", pCertFile);
    pCertCur = achCert + iCertLen;
    iKeyLen = snprintf(achKey, max_path_len, "%s", pKeyFile);
    pKeyCur = achKey + iKeyLen;
    for (i = 0; i < max_certs; ++i)
    {
        snprintf(pCertCur, max_path_len - iCertLen, "%s", apExt[i]);
        snprintf(pKeyCur, max_path_len - iKeyLen, "%s", apExt[i]);
        if ((access(achCert, F_OK) == 0) && (access(achKey, F_OK) == 0))
        {
            if (setKeyCertificateFile(achKey, iKeyType, achCert, iCertType,
                                      chained) == false)
            {
                LS_ERROR("Failed to load key file %s and cert file %s",
                         achKey, achCert);
                return false;
            }
            iLoaded = 1;
        }
    }
    return (iLoaded == 1);
}


int SslContext::setCertificateFile(const char *pFile, int type,
                                   int chained)
{
    if (!pFile)
        return 0;
    ::stat(pFile, &m_stCert);
    if (init(m_iMethod))
        return 0;
    if (chained)
        return SSL_CTX_use_certificate_chain_file(m_pCtx, pFile);
    else
    {
        int ret = SslUtil::loadCertFile(m_pCtx, pFile, type);
        if (ret == -1)
            return SSL_CTX_use_certificate_file(m_pCtx, pFile,
                                                SslUtil::translateType(type));
        return ret;
    }
}


int SslContext::setCertificateChainFile(const char *pFile)
{
    BIO *bio;
    if ((bio = BIO_new_file(pFile, "r")) == NULL)
        return -1;
    int ret =  SslUtil::setCertificateChain(m_pCtx, bio);
    BIO_free(bio);
    return ret;
}


int SslContext::setCALocation(const char *pCAFile, const char *pCAPath,
                              int cv)
{
    if (init(m_iMethod))
        return LS_FAIL;
    return SslUtil::loadCA(m_pCtx, pCAFile, pCAPath, cv);
}


int SslContext::setPrivateKeyFile(const char *pFile, int type)
{
    int ret;
    if (!pFile)
        return -1;
    ::stat(pFile, &m_stKey);
    if (init(m_iMethod))
        return -1;
//     if (loadPrivateKeyFile(pFile, type) == -1)
    if ((ret = SslUtil::loadPrivateKeyFile(m_pCtx, pFile, type)) <= 1)
    {
        return SSL_CTX_use_PrivateKey_file(m_pCtx, pFile,
                                           SslUtil::translateType(type)) == 1;
    }
    m_iKeyLen = ret;
    return 1;
}


int SslContext::checkPrivateKey()
{
    if (m_pCtx)
        return SSL_CTX_check_private_key(m_pCtx);
    else
        return 0;
}


int SslContext::setCipherList(const char *pList)
{
    if (!m_pCtx)
        return false;
    return SslUtil::setCipherList(m_pCtx, pList);
}



/*
SL_CTX_set_verify(ctx, nVerify,  ssl_callback_SSLVerify);
    SSL_CTX_sess_set_new_cb(ctx,      ssl_callback_NewSessionCacheEntry);
    SSL_CTX_sess_set_get_cb(ctx,      ssl_callback_GetSessionCacheEntry);
    SSL_CTX_sess_set_remove_cb(ctx,   ssl_callback_DelSessionCacheEntry);
    SSL_CTX_set_tmp_rsa_callback(ctx, ssl_callback_TmpRSA);
    SSL_CTX_set_tmp_dh_callback(ctx,  ssl_callback_TmpDH);
    SSL_CTX_set_info_callback(ctx,    ssl_callback_LogTracingState);
*/


int SslContext::initSSL()
{
    SSL_load_error_strings();
    SSL_library_init();
#ifndef SSL_OP_NO_COMPRESSION
    /* workaround for OpenSSL 0.9.8 */
    sk_SSL_COMP_zero(SSL_COMP_get_compression_methods());
#endif

    SslConnection::initConnIdx();

    return seedRand(512);
}


/*
static RSA *load_key(const char *file, char *pass, int isPrivate )
{
    BIO * bio_err = BIO_new_fp( stderr, BIO_NOCLOSE );
    BIO *bp = NULL;
    EVP_PKEY *pKey = NULL;
    RSA *pRSA = NULL;

    bp=BIO_new(BIO_s_file());
    if (bp == NULL)
    {
        return NULL;
    }
    if (BIO_read_filename(bp,file) <= 0)
    {
        BIO_free( bp );
        return NULL;
    }
    if ( !isPrivate )
        pKey = PEM_read_bio_PUBKEY( bp, NULL, NULL, pass);
    else
        pKey = PEM_read_bio_PrivateKey( bp, NULL, NULL, pass );
    if ( !pKey )
    {
        ERR_print_errors( bio_err );
    }
    else
    {
        pRSA = EVP_PKEY_get1_RSA( pKey );
        EVP_PKEY_free( pKey );
    }
    if (bp != NULL)
        BIO_free(bp);
    if ( bio_err )
        BIO_free( bio_err );
    return(pRSA);
}
*/


static RSA *load_key(const unsigned char *key, int keyLen, char *pass,
                     int isPrivate)
{
    BIO *bio_err = BIO_new_fp(stderr, BIO_NOCLOSE);
    BIO *bp = NULL;
    EVP_PKEY *pKey = NULL;
    RSA *pRSA = NULL;

    bp = BIO_new_mem_buf((void *)key, keyLen);
    if (bp == NULL)
        return NULL;
    if (!isPrivate)
        pKey = PEM_read_bio_PUBKEY(bp, NULL, NULL, pass);
    else
        pKey = PEM_read_bio_PrivateKey(bp, NULL, NULL, pass);
    if (!pKey)
        ERR_print_errors(bio_err);
    else
    {
        pRSA = EVP_PKEY_get1_RSA(pKey);
        EVP_PKEY_free(pKey);
    }
    if (bp != NULL)
        BIO_free(bp);
    if (bio_err)
        BIO_free(bio_err);
    return (pRSA);
}


int  SslContext::publickey_encrypt(const unsigned char *pPubKey,
                                   int keylen,
                                   const char *content, int len, char *encrypted, unsigned int bufLen)
{
    int ret;
    initSSL();
    RSA *pRSA = load_key(pPubKey, keylen, NULL, 0);
    if (pRSA)
    {
        if (bufLen < RSA_size(pRSA))
            return LS_FAIL;
        ret = RSA_public_encrypt(len, (unsigned char *)content,
                                 (unsigned char *)encrypted, pRSA, RSA_PKCS1_OAEP_PADDING);
        RSA_free(pRSA);
        return ret;
    }
    else
        return LS_FAIL;

}


int  SslContext::publickey_decrypt(const unsigned char *pPubKey,
                                   int keylen,
                                   const char *encrypted, int len, char *decrypted, unsigned int bufLen)
{
    int ret;
    initSSL();
    RSA *pRSA = load_key(pPubKey, keylen, NULL, 0);
    if (pRSA)
    {
        if (bufLen < RSA_size(pRSA))
            return LS_FAIL;
        ret = RSA_public_decrypt(len, (unsigned char *)encrypted,
                                 (unsigned char *)decrypted, pRSA, RSA_PKCS1_PADDING);
        RSA_free(pRSA);
        return ret;
    }
    else
        return LS_FAIL;
}


/*
int  SslContext::privatekey_encrypt( const char * pPrivateKeyFile, const char * content,
                    int len, char * encrypted, int bufLen )
{
    int ret;
    initSSL();
    RSA * pRSA = load_key( pPrivateKeyFile, NULL, 1 );
    if ( pRSA )
    {
        if ( bufLen < RSA_size( pRSA) )
            return LS_FAIL;
        ret = RSA_private_encrypt(len, (unsigned char *)content,
            (unsigned char *)encrypted, pRSA, RSA_PKCS1_PADDING );
        RSA_free( pRSA );
        return ret;
    }
    else
        return LS_FAIL;
}
int  SslContext::privatekey_decrypt( const char * pPrivateKeyFile, const char * encrypted,
                    int len, char * decrypted, int bufLen )
{
    int ret;
    initSSL();
    RSA * pRSA = load_key( pPrivateKeyFile, NULL, 1 );
    if ( pRSA )
    {
        if ( bufLen < RSA_size( pRSA) )
            return LS_FAIL;
        ret = RSA_private_decrypt(len, (unsigned char *)encrypted,
            (unsigned char *)decrypted, pRSA, RSA_PKCS1_OAEP_PADDING );
        RSA_free( pRSA );
        return ret;
    }
    else
        return LS_FAIL;
}
*/


/*
    ASSERT (options->ca_file || options->ca_path);
    if (!SSL_CTX_load_verify_locations (ctx, options->ca_file, options->ca_path))
    msg (M_SSLERR, "Cannot load CA certificate file %s path %s (SSL_CTX_load_verify_locations)", options->ca_file, options->ca_path);

    // * Set a store for certs (CA & CRL) with a lookup on the "capath" hash directory * /
    if (options->ca_path) {
        X509_STORE *store = SSL_CTX_get_cert_store(ctx);

        if (store)
        {
            X509_LOOKUP *lookup = X509_STORE_add_lookup(store, X509_LOOKUP_hash_dir());
            if (!X509_LOOKUP_add_dir(lookup, options->ca_path, X509_FILETYPE_PEM))
                X509_LOOKUP_add_dir(lookup, NULL, X509_FILETYPE_DEFAULT);
            else
                msg(M_WARN, "WARNING: experimental option --capath %s", options->ca_path);
#if OPENSSL_VERSION_NUMBER >= 0x00907000L
            X509_STORE_set_flags(store, X509_V_FLAG_CRL_CHECK | X509_V_FLAG_CRL_CHECK_ALL);
#else
#warn This version of OpenSSL cannot handle CRL files in capath
            msg(M_WARN, "WARNING: this version of OpenSSL cannot handle CRL files in capath");
#endif
        }
        else
            msg(M_SSLERR, "Cannot get certificate store (SSL_CTX_get_cert_store)");
    }
*/


int newClientSessionCb(SSL * ssl, SSL_SESSION * session){
    SslConnection *c = (SslConnection *)SSL_get_ex_data(ssl,SslConnection::getConnIdx());
    c->cacheClientSession(session);
    return 1;
}


void SslContext::enableClientSessionReuse()
{
    init(m_iMethod);
    SSL_CTX_set_session_cache_mode(m_pCtx, SSL_SESS_CACHE_CLIENT);
    SSL_CTX_sess_set_new_cb(m_pCtx, newClientSessionCb);
}


extern SslContext *VHostMapFindSslContext(void *arg, const char *pName);
/**
 * The cert callback is expected to return the following:
 * < 0 If the server needs to look for a certificate
 *  0  On error.
 *  1  If success, regardless of if a certificate was set or not.
 */
#define CERTCB_RET_OK 1
#define CERTCB_RET_ERR 0
#define CERTCB_RET_WAIT -1
static int SslConnection_ssl_servername_cb(SSL *pSSL, void *arg)
{
    SSL_CTX *pOldCtx, *pNewCtx;
    const char *servername = SSL_get_servername(pSSL,
                             TLSEXT_NAMETYPE_host_name);
    if (!servername || !*servername)
        return CERTCB_RET_OK;
    SslContext *pCtx = VHostMapFindSslContext(arg, servername);
    if (!pCtx)
        return CERTCB_RET_OK;
#ifdef OPENSSL_IS_BORINGSSL
    // Check OCSP again when the context needs to be changed.
    pCtx->initOCSP();
#endif
    pOldCtx = SSL_get_SSL_CTX(pSSL);
    pNewCtx = pCtx->get();
    if (pOldCtx == pNewCtx)
        return CERTCB_RET_OK;
    SSL_set_SSL_CTX(pSSL, pNewCtx);
    SSL_set_verify(pSSL, SSL_CTX_get_verify_mode(pNewCtx), NULL);
    SSL_set_verify_depth(pSSL, SSL_CTX_get_verify_depth(pNewCtx));

    SSL_clear_options(pSSL,
                      SSL_get_options(pSSL) & ~SSL_CTX_get_options(pNewCtx));
    // remark: VHost is guaranteed to have NO_TICKET set.
    // If listener has it set, set will not affect it.
    // If listener does not have it set, set will not set it.
    SSL_set_options(pSSL, SSL_CTX_get_options(pNewCtx) & ~SSL_OP_NO_TICKET);

    return CERTCB_RET_OK;
}


int SslContext::initSNI(void *param)
{
#ifdef SSL_TLSEXT_ERR_OK
    SSL_CTX_set_cert_cb(m_pCtx, SslConnection_ssl_servername_cb, param);

    return 0;
#else
    return LS_FAIL;
#endif
}

/*!
    \fn SslContext::setClientVerify( int mode, int depth)
 */
void SslContext::setClientVerify(int mode, int depth)
{
    int req;
    switch (mode)
    {
    case 0:     //none
        req = SSL_VERIFY_NONE;
        break;
    case 1:     //optional
    case 3:     //no_ca
        req = SSL_VERIFY_PEER;
        break;
    case 2:     //required
    default:
        req = SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT |
              SSL_VERIFY_CLIENT_ONCE;
    }
    SSL_CTX_set_verify(m_pCtx, req, NULL);
    SSL_CTX_set_verify_depth(m_pCtx, depth);
}


/*!
    \fn SslContext::addCRL( const char * pCRLFile, const char * pCRLPath)
 */
int SslContext::addCRL(const char *pCRLFile, const char *pCRLPath)
{
    X509_STORE *store = SSL_CTX_get_cert_store(m_pCtx);
    X509_LOOKUP *lookup = X509_STORE_add_lookup(store, X509_LOOKUP_hash_dir());
    if (pCRLFile)
    {
        if (!X509_load_crl_file(lookup, pCRLFile, X509_FILETYPE_PEM))
            return LS_FAIL;
    }
    if (pCRLPath)
    {
        if (!X509_LOOKUP_add_dir(lookup, pCRLPath, X509_FILETYPE_PEM))
            return LS_FAIL;
    }
    X509_STORE_set_flags(store,
                         X509_V_FLAG_CRL_CHECK | X509_V_FLAG_CRL_CHECK_ALL);
    return 0;
}


#ifdef LS_ENABLE_SPDY
static const char *NEXT_PROTO_STRING[8] =
{
    "\x08http/1.1",
    "\x06spdy/2\x08http/1.1",
    "\x08spdy/3.1\x06spdy/3\x08http/1.1",
    "\x08spdy/3.1\x06spdy/3\x06spdy/2\x08http/1.1",
    "\x02h2\x08http/1.1",
    "\x02h2\x06spdy/2\x08http/1.1",
    "\x02h2\x08spdy/3.1\x06spdy/3\x08http/1.1",
    "\x02h2\x08spdy/3.1\x06spdy/3\x06spdy/2\x08http/1.1",
};

static unsigned int NEXT_PROTO_STRING_LEN[8] =
{
    9, 16, 25, 32, 12, 19, 28, 35,
};

static int SslConnection_ssl_npn_advertised_cb(SSL *pSSL,
        const unsigned char **out,
        unsigned int *outlen, void *arg)
{
    SslContext *pCtx = (SslContext *)arg;
    *out = (const unsigned char *)NEXT_PROTO_STRING[ pCtx->getEnableSpdy()];
    *outlen = NEXT_PROTO_STRING_LEN[ pCtx->getEnableSpdy() ];
    return SSL_TLSEXT_ERR_OK;
}

#ifdef TLSEXT_TYPE_application_layer_protocol_negotiation
static int SSLConntext_alpn_select_cb(SSL *pSSL, const unsigned char **out,
                                      unsigned char *outlen, const unsigned char *in,
                                      unsigned int inlen, void *arg)
{
    SslContext *pCtx = (SslContext *)arg;
    if (SSL_select_next_proto((unsigned char **) out, outlen,
                              (const unsigned char *)NEXT_PROTO_STRING[ pCtx->getEnableSpdy() ],
                              NEXT_PROTO_STRING_LEN[ pCtx->getEnableSpdy() ],
                              in, inlen)
        != OPENSSL_NPN_NEGOTIATED)
        return SSL_TLSEXT_ERR_NOACK;
    return SSL_TLSEXT_ERR_OK;
}
#endif

void SslContext::setAlpnCb(SSL_CTX *ctx, void *arg)
{
#ifdef TLSEXT_TYPE_application_layer_protocol_negotiation
    SSL_CTX_set_alpn_select_cb(ctx, SSLConntext_alpn_select_cb, arg);
#endif
}


int SslContext::enableSpdy(int level)
{
    m_iEnableSpdy = (level & 7);
    if (m_iEnableSpdy == 0)
        return 0;
#ifdef TLSEXT_TYPE_application_layer_protocol_negotiation
    SSL_CTX_set_alpn_select_cb(m_pCtx, SSLConntext_alpn_select_cb, this);
#endif
#ifdef TLSEXT_TYPE_next_proto_neg
    SSL_CTX_set_next_protos_advertised_cb(m_pCtx,
                                          SslConnection_ssl_npn_advertised_cb, this);
#else
#error "Openssl version is too low (openssl 1.0.1 or higher is required)!!!"
#endif
    return 0;
}

#else
int SslContext::enableSpdy(int level)
{
    return LS_FAIL;
}

#endif

#ifndef OPENSSL_IS_BORINGSSL
static int sslCertificateStatus_cb(SSL *ssl, void *data)
{
    SslOcspStapling *pStapling = (SslOcspStapling *)data;
    return pStapling->callback(ssl);
}

#else
int SslContext::initOCSP()
{
    if (getpStapling() == NULL) {
        return 0;
    }
    return getpStapling()->update();
}
#endif

SslContext *SslContext::setKeyCertCipher(const char *pCertFile,
        const char *pKeyFile, const char *pCAFile, const char *pCAPath,
        const char *pCiphers, int certChain, int cv, int renegProtect)
{
    int ret;
    LS_DBG_L(ConfigCtx::getCurConfigCtx(), "Create SSL context with"
             " Certificate file: %s and Key File: %s.",
             pCertFile, pKeyFile);
    setRenegProtect(renegProtect);
    if (multiCertsEnabled())
    {
        ret = setMultiKeyCertFile(pKeyFile, SslContext::FILETYPE_PEM,
                                  pCertFile, SslContext::FILETYPE_PEM, certChain);
    }
    else
    {
        ret = setKeyCertificateFile(pKeyFile, SslContext::FILETYPE_PEM,
                                    pCertFile, SslContext::FILETYPE_PEM, certChain);
    }
    if (!ret)
    {
        LS_ERROR("[SSL] Config SSL Context with Certificate File: %s"
                 " and Key File:%s get SSL error: %s",
                 pCertFile, pKeyFile, SslError().what());
        return NULL;
    }

    if ((pCAFile || pCAPath) &&
        !setCALocation(pCAFile, pCAPath, cv))
    {
        LS_ERROR(ConfigCtx::getCurConfigCtx(),
                 "Failed to setup Certificate Authority "
                 "Certificate File: '%s', Path: '%s', SSL error: %s",
                 pCAFile ? pCAFile : "", pCAPath ? pCAPath : "", SslError().what());
        return NULL;
    }
    LS_DBG_L(ConfigCtx::getCurConfigCtx(), "set ciphers to:%s", pCiphers);
    setCipherList(pCiphers);
    return this;
}


SslContext *SslContext::config(const XmlNode *pNode)
{
    char achCert[MAX_PATH_LEN];
    char achKey [MAX_PATH_LEN];
    char achCAFile[MAX_PATH_LEN];
    char achCAPath[MAX_PATH_LEN];

    const char *pCertFile;
    const char *pKeyFile;
    const char *pCiphers;
    const char *pCAPath;
    const char *pCAFile;
//    const char *pAddr;

    SslContext *pSSL;
    int protocol;
    int certChain;
    int renegProt;
    int enableSpdy = 0;  //Default is disable
    int sessionCache = 0;
    int sessionTicket;

    int cv;

    pCertFile = ConfigCtx::getCurConfigCtx()->getTag(pNode,  "certFile");

    if (!pCertFile)
        return NULL;

    pKeyFile = ConfigCtx::getCurConfigCtx()->getTag(pNode, "keyFile");

    if (!pKeyFile)
        return NULL;

    if (s_iEnableMultiCerts != 0)
    {
        if (ConfigCtx::getCurConfigCtx()->getAbsoluteFile(achCert,
                pCertFile) != 0)
            return NULL;
        else if (ConfigCtx::getCurConfigCtx()->getAbsoluteFile(achKey,
                 pKeyFile) != 0)
            return NULL;
    }
    else
    {
        if (ConfigCtx::getCurConfigCtx()->getValidFile(achCert, pCertFile,
                "certificate file") != 0)
            return NULL;
        if (ConfigCtx::getCurConfigCtx()->getValidFile(achKey, pKeyFile,
                "key file") != 0)
            return NULL;
    }
    pCertFile = achCert;
    pKeyFile = achKey;

    pCiphers = pNode->getChildValue("ciphers");

    if (!pCiphers)
        pCiphers = "ALL:!ADH:!EXPORT56:RC4+RSA:+HIGH:+MEDIUM:!SSLv2:+EXP";

    pCAPath = pNode->getChildValue("CACertPath");
    pCAFile = pNode->getChildValue("CACertFile");

    if (pCAPath)
    {
        if (ConfigCtx::getCurConfigCtx()->getValidPath(achCAPath, pCAPath,
                "CA Certificate path") != 0)
            return NULL;

        pCAPath = achCAPath;
    }

    if (pCAFile)
    {
        if (ConfigCtx::getCurConfigCtx()->getValidFile(achCAFile, pCAFile,
                "CA Certificate file") != 0)
            return NULL;

        pCAFile = achCAFile;
    }

    cv = ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "clientVerify",
            0, 3, 0);
    certChain = ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "certChain",
                0, 1, 0);
    renegProt = ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                "renegprotection", 0, 1, 1);
    pSSL = setKeyCertCipher(pCertFile, pKeyFile, pCAFile, pCAPath, pCiphers,
                            certChain, (cv != 0), renegProt);
    if (pSSL == NULL)
        return NULL;

    protocol = ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "sslProtocol",
               1, 31, 28);
    setProtocol(protocol);

    int enableDH = ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                   "enableECDHE", 0, 1, 1);
    if (enableDH)
        pSSL->initECDH();
    enableDH = ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "enableDHE",
               0, 1, 0);
    if (enableDH)
    {
        const char *pDHParam = pNode->getChildValue("DHParam");
        if (pDHParam)
        {
            if (ConfigCtx::getCurConfigCtx()->getValidFile(achCAPath, pDHParam,
                    "DH Parameter file") != 0)
            {
                LS_WARN(ConfigCtx::getCurConfigCtx(),
                        "invalid path for DH paramter: %s, ignore and use built-in DH parameter!",
                        pDHParam);

                pDHParam = NULL;
            }
            else
                pDHParam = achCAPath;
        }
        pSSL->initDH(pDHParam);
    }


#ifdef LS_ENABLE_SPDY
    enableSpdy = ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                 "enableSpdy", 0, 7, 7);
    if (enableSpdy)
    {
        if (-1 == pSSL->enableSpdy(enableSpdy))
            LS_ERROR(ConfigCtx::getCurConfigCtx(),
                     "SPDY/HTTP2 can't be enabled [try to set to %d].",
                     enableSpdy);
    }
#else
    //Even if no spdy installed, we still need to parse it
    //When user set it and will log an error to user, better than nothing
    enableSpdy = ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                 "enableSpdy", 0, 7, 0);
    if (enableSpdy)
        LS_ERROR(ConfigCtx::getCurConfigCtx(),
                 "SPDY/HTTP2 can't be enabled for not installed.");
#endif

    sessionCache = ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                   "sslSessionCache", 0, 1, 0);
    sessionTicket = ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                    "sslSessionTickets", 0, 1, -1);

    if (sessionCache != 0)
    {
        if (enableShmSessionCache() == LS_FAIL)
            LS_ERROR("Enable session cache failed.");
    }

    if (sessionTicket == 1)
    {
        if (enableSessionTickets() == LS_FAIL)
        {
            LS_ERROR("[SSL] Enable session ticket failed.");
            return NULL;
        }
    }
    else if (sessionTicket == 0)
        disableSessionTickets();

    if (cv)
    {
        setClientVerify(cv, ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                        "verifyDepth", 1, INT_MAX, 1));
        configCRL(pNode, pSSL);
    }

    if ((ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "enableStapling", 0,
            1, 0))
        && (pCertFile != NULL))
    {
        if (getpStapling() == NULL)
        {
            const char *pCombineCAfile = pNode->getChildValue("ocspCACerts");
            char CombineCAfile[MAX_PATH_LEN];
            if (pCombineCAfile)
            {
                if (ConfigCtx::getCurConfigCtx()->getValidFile(CombineCAfile,
                        pCombineCAfile, "Combine CA file") != 0)
                    return 0;
                pSSL->setCertificateChainFile(CombineCAfile);
            }
            if (pSSL->configStapling(pNode, pCAFile, achCert) == 0)
                LS_INFO(ConfigCtx::getCurConfigCtx(), "Enable OCSP Stapling successful!");
        }
    }

    return pSSL;
}


int SslContext::configStapling(const XmlNode *pNode,
                               const char *pCAFile, char *pachCert)
{
    SslOcspStapling *pSslOcspStapling = new SslOcspStapling;

    if (pSslOcspStapling->config(pNode, m_pCtx, pCAFile, pachCert) == -1)
    {
        delete pSslOcspStapling;
        return LS_FAIL;
    }
    m_pStapling = pSslOcspStapling;
#ifndef OPENSSL_IS_BORINGSSL
    SSL_CTX_set_tlsext_status_cb(m_pCtx, sslCertificateStatus_cb);
    SSL_CTX_set_tlsext_status_arg(m_pCtx, m_pStapling);
//#else
//    SSL_CTX_enable_ocsp_stapling(m_pCtx);
#endif
    return 0;
}


void SslContext::configCRL(const XmlNode *pNode, SslContext *pSSL)
{
    char achCrlFile[MAX_PATH_LEN];
    char achCrlPath[MAX_PATH_LEN];
    const char *pCrlPath;
    const char *pCrlFile;
    pCrlPath = pNode->getChildValue("crlPath");
    pCrlFile = pNode->getChildValue("crlFile");

    if (pCrlPath)
    {
        if (ConfigCtx::getCurConfigCtx()->getValidPath(achCrlPath, pCrlPath,
                "CRL path") != 0)
            return;
        pCrlPath = achCrlPath;
    }

    if (pCrlFile)
    {
        if (ConfigCtx::getCurConfigCtx()->getValidFile(achCrlFile, pCrlFile,
                "CRL file") != 0)
            return;
        pCrlFile = achCrlFile;
    }

    if (pCrlPath || pCrlFile)
        pSSL->addCRL(achCrlFile, achCrlPath);

}


int SslContext::setupIdContext(SSL_CTX *pCtx, const void *pDigest,
                               size_t iDigestLen)
{
#if OPENSSL_VERSION_NUMBER >= 0x10100000L
    EVP_MD_CTX *pmd;
#else
    EVP_MD_CTX md;    
    EVP_MD_CTX *pmd = &md;
#endif
    unsigned int len;
    unsigned char buf[EVP_MAX_MD_SIZE];

#if OPENSSL_VERSION_NUMBER >= 0x10100000L
    pmd = EVP_MD_CTX_new();
#endif
    
    if (EVP_DigestInit_ex(pmd, EVP_sha1(), NULL) != 1)
    {
        LS_DBG_L("Init EVP Digest failed.");
#if OPENSSL_VERSION_NUMBER >= 0x10100000L
        EVP_MD_CTX_free(pmd);
#endif        
        return LS_FAIL;
    }
    else if (EVP_DigestUpdate(pmd, pDigest, iDigestLen) != 1)
    {
        LS_DBG_L("Update EVP Digest failed");
#if OPENSSL_VERSION_NUMBER >= 0x10100000L
        EVP_MD_CTX_free(pmd);
#endif        
        return LS_FAIL;
    }
    else if (EVP_DigestFinal_ex(pmd, buf, &len) != 1)
    {
        LS_DBG_L("EVP Digest Final failed.");
#if OPENSSL_VERSION_NUMBER >= 0x10100000L
        EVP_MD_CTX_free(pmd);
#endif        
        return LS_FAIL;
    }
#if OPENSSL_VERSION_NUMBER < 0x10100000L
    else if (EVP_MD_CTX_cleanup(pmd) != 1)
    {
        LS_DBG_L("EVP Digest Cleanup failed.");
        return LS_FAIL;
    }
#endif        
    else if (SSL_CTX_set_session_id_context(pCtx, buf, len) != 1)
    {
        LS_DBG_L("Set Session Id Context failed.");
#if OPENSSL_VERSION_NUMBER >= 0x10100000L
        EVP_MD_CTX_free(pmd);
#endif        
        return LS_FAIL;
    }
#if OPENSSL_VERSION_NUMBER >= 0x10100000L
    EVP_MD_CTX_free(pmd);
#endif
    return LS_OK;
}


int  SslContext::enableShmSessionCache()
{
    return SslUtil::enableShmSessionCache(m_pCtx);
}


int SslContext::enableSessionTickets()
{
    return SslTicket::getInstance().enableCtx(m_pCtx);
}


void SslContext::disableSessionTickets()
{
    SslTicket::getInstance().disableCtx(m_pCtx);
}



