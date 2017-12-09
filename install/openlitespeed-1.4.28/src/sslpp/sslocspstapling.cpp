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

#include <sslpp/sslocspstapling.h>
#include <sslpp/sslerror.h>

#include <lsr/ls_base64.h>
#include <main/configctx.h>
#include <util/httpfetch.h>
#include <util/stringtool.h>
#include <util/xmlnode.h>
#include <util/datetime.h>

#include <openssl/crypto.h>
#include <openssl/err.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/rand.h>
#include <openssl/ssl.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>
#include <openssl/x509_vfy.h>

#ifndef OPENSSL_IS_BORINGSSL
#include <openssl/ocsp.h>
#else
#include <sslpp/ocsp/ocsp.h>
#endif

#include <assert.h>
#include <ctype.h>
#include <fcntl.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>



const char *SslOcspStapling::s_pRespTempPath = "/tmp/ocspcache/";
int   SslOcspStapling::s_iRespTempPathLen = 15;

static AutoStr2 s_ErrMsg = "";
const char *getStaplingErrMsg() { return s_ErrMsg.c_str(); }


static void setLastErrMsg(const char *format, ...)
{
    const unsigned int MAX_LINE_LENGTH = 1024;
    char s[MAX_LINE_LENGTH] = {0};
    va_list ap;
    va_start(ap, format);
    int ret = vsnprintf(s, MAX_LINE_LENGTH, format, ap);
    va_end(ap);

    if ((unsigned int)ret > MAX_LINE_LENGTH)
        ret = MAX_LINE_LENGTH;
    s_ErrMsg.setLen(0);
    s_ErrMsg.setStr(s, ret);
}


static X509 *load_cert(const char *pPath)
{
    X509 *pCert;
    BIO *bio = BIO_new_file(pPath, "r");
    if (bio == NULL)
        return NULL;
    pCert = PEM_read_bio_X509_AUX(bio, NULL, NULL, NULL);
    BIO_free(bio);
    return pCert;
}


static int OcspRespCb(void *pArg, HttpFetch *pHttpFetch)
{
    SslOcspStapling *pSslOcspStapling = (SslOcspStapling *)pArg;
    pSslOcspStapling->processResponse(pHttpFetch);
    return 0;
}


int SslOcspStapling::callback(SSL *ssl)
{
    int     iResult;
    iResult = SSL_TLSEXT_ERR_NOACK;
    update();
    if (m_iDataLen > 0)
    {
#ifndef OPENSSL_IS_BORINGSSL
        unsigned char *pbuff;
        /*OpenSSL will free pbuff by itself */
        pbuff = (unsigned char *)malloc(m_iDataLen);
        if (pbuff == NULL)
            return SSL_TLSEXT_ERR_NOACK;
        memcpy(pbuff, m_pRespData, m_iDataLen);
        SSL_set_tlsext_status_ocsp_resp(ssl, pbuff, m_iDataLen);
//#else
//        SSL_set_ocsp_response(ssl, m_pRespData, m_iDataLen);
#endif
        iResult = SSL_TLSEXT_ERR_OK;

    }
    return iResult;
}


int SslOcspStapling::processResponse(HttpFetch *pHttpFetch)
{
    struct stat        st;
    const char          *pRespContentType;
    //assert( pHttpFetch == m_pHttpFetch );
    int istatusCode = m_pHttpFetch->getStatusCode() ;
    pRespContentType = m_pHttpFetch->getRespContentType();
    if ((istatusCode == 200)
        && (strcasecmp(pRespContentType, "application/ocsp-response") == 0))
        verifyRespFile();
    else
    {
        setLastErrMsg("Received bad OCSP response. ReponderUrl=%s, StatusCode=%d, ContentType=%s\n",
                      m_sOcspResponder.c_str(), istatusCode,
                      ((pRespContentType) ? (pRespContentType) : ("")));
        //printf("%s\n", s_ErrMsg.c_str());
        m_pHttpFetch->writeLog(s_ErrMsg.c_str());
    }

    if (::stat(m_sRespfileTmp.c_str(), &st) == 0)
        unlink(m_sRespfileTmp.c_str());
    return 0;
}


SslOcspStapling::SslOcspStapling()
    : m_pHttpFetch(NULL)
    , m_pReqData(NULL)
    , m_iDataLen(0)
    , m_pRespData(NULL)
    , m_RespTime(0)
    , m_pCertId(NULL)
{
}


SslOcspStapling::~SslOcspStapling()
{
    if (m_pRespData != NULL)
        delete []m_pRespData;
    if (m_pHttpFetch != NULL)
        delete m_pHttpFetch;
    if (m_pReqData)
        free(m_pReqData);
    if (m_pCertId != NULL)
        OCSP_CERTID_free(m_pCertId);
}


int SslOcspStapling::init(SSL_CTX *pSslCtx)
{
    int             iResult;
    X509           *pCert;
    struct stat     st;
    m_pCtx = pSslCtx;
    pCert = NULL;
    iResult = -1;

    if (::stat(m_sRespfileTmp.c_str(), &st) == 0)
    {
        if ((st.st_mtime + 30) <= time(NULL))
            unlink(m_sRespfileTmp.c_str());
    }
    //SSL_CTX_set_default_verify_paths( m_pCtx );

    pCert = load_cert(m_sCertfile.c_str());
    if (pCert == NULL)
    {
        setLastErrMsg("Failed to load file: %s!\n", m_sCertfile.c_str());
        return LS_FAIL;
    }

    if ((getCertId(pCert) == 0) && (getResponder(pCert) == 0))
    {
//         m_addrResponder.setHttpUrl(m_sOcspResponder.c_str(),
//                                    m_sOcspResponder.len());
        iResult = 0;
        //update();

    }
    X509_free(pCert);
    return iResult;
}


int SslOcspStapling::update()
{

    struct stat st;
    if (m_RespTime != 0 && m_RespTime + m_iocspRespMaxAge < DateTime::s_curTime)
    {
        return 0;
    }

    if (::stat(m_sRespfile.c_str(), &st) == 0)
    {
        if (m_RespTime != st.st_mtime)
        {
            verifyRespFile(0);
            m_RespTime = st.st_mtime;
        }
    }
    if (::stat(m_sRespfileTmp.c_str(), &st) != 0
        || st.st_mtime + 10 < DateTime::s_curTime)
        createRequest();
    return 0;
}


int SslOcspStapling::getResponder(X509 *pCert)
{
    char                    *pUrl;
    X509                    *pCAt;
    STACK_OF(X509)          *pXchain;
    int                     i;
    int                     n;

#if OPENSSL_VERSION_NUMBER >= 0x10000003L
    STACK_OF(OPENSSL_STRING)  *strResp;
#else
    STACK                    *strResp;
#endif
    if (m_sOcspResponder.c_str())
        return 0;
    strResp = X509_get1_ocsp(pCert);
    if (strResp == NULL)
    {
#ifndef OPENSSL_IS_BORINGSSL
        pXchain = m_pCtx->extra_certs;
#else
        SSL_CTX_get0_chain_certs(m_pCtx, &pXchain);
#endif
        n = sk_X509_num(pXchain);
        for (i = 0; i < n; i++)
        {
            pCert = sk_X509_value(pXchain, i);
            strResp = X509_get1_ocsp(pCert);
            if (strResp)
                break;
        }
    }
    if (strResp == NULL)
    {
        if (m_sCAfile.c_str() == NULL)
            return LS_FAIL;
        pCAt = load_cert(m_sCAfile.c_str());
        if (pCAt == NULL)
        {
            setLastErrMsg("Failed to load file: %s!\n", m_sCAfile.c_str());
            return LS_FAIL;
        }

        strResp = X509_get1_ocsp(pCAt);
        X509_free(pCAt);
        if (strResp == NULL)
        {
            setLastErrMsg("Failed to get responder!\n");
            return LS_FAIL;
        }
    }
#if OPENSSL_VERSION_NUMBER >= 0x1000004fL
    pUrl = sk_OPENSSL_STRING_value(strResp, 0);
#elif OPENSSL_VERSION_NUMBER >= 0x10000003L
    pUrl = (char *)sk_value((const _STACK *) strResp, 0);
#else
    pUrl = (char *)sk_value((const STACK *) strResp, 0);
#endif
    if (pUrl)
    {
        m_sOcspResponder.setStr(pUrl);
        return 0;
    }
    X509_email_free(strResp);
    setLastErrMsg("Failed to get responder Url!\n");
    return LS_FAIL;
}


int SslOcspStapling::getRequestData(unsigned char **pReqData)
{
    int             len = -1;
    OCSP_REQUEST    *ocsp;
    OCSP_CERTID     *id;

    if (m_pCertId == NULL)
        return LS_FAIL;
    ocsp = OCSP_REQUEST_new();
    if (ocsp == NULL)
        return LS_FAIL;

    id = OCSP_CERTID_dup(m_pCertId);
    if (OCSP_request_add0_id(ocsp, id) != NULL)
    {
        len = i2d_OCSP_REQUEST(ocsp, pReqData);
    }
    OCSP_REQUEST_free(ocsp);
    return  len;
}


int SslOcspStapling::createRequest()
{
    int             len;
    struct stat     st;
    if (::stat(m_sRespfileTmp.c_str(), &st) == 0)
        return 0;
    if (m_pHttpFetch != NULL )
    {
        if (-1 != m_pHttpFetch->getHttpFd())
            return 0;
        delete m_pHttpFetch;
        m_pHttpFetch = NULL;
    }
    if (m_pReqData)
    {
        free(m_pReqData);
        m_pReqData = NULL;
    }
    len = getRequestData(&m_pReqData);
    if (len <= 0)
        return LS_FAIL;

    if (*(m_sOcspResponder.c_str() + m_sOcspResponder.len() - 1) != '/')
    {
        m_sOcspResponder.append("/", 1);
    }

    m_pHttpFetch = new HttpFetch();
    m_pHttpFetch->setResProcessor(OcspRespCb, this);
    m_pHttpFetch->setTimeout(30);  //Set Req timeout as 30 seconds
    m_pHttpFetch->startReq(m_sOcspResponder.c_str(), 1, 1,
                           (const char *)m_pReqData, len,
                           m_sRespfileTmp.c_str(), "application/ocsp-request",
                           NULL);
    setLastErrMsg("%lu, len = %d\n\n", m_pHttpFetch, len);
    //printf("%s\n", s_ErrMsg.c_str());
    return 0;
}


void SslOcspStapling::updateRespData(OCSP_RESPONSE *pResponse)
{
    unsigned char *pbuff;
    m_iDataLen = i2d_OCSP_RESPONSE(pResponse, NULL);
    if (m_iDataLen > 0)
    {
        if (m_pRespData != NULL)
            delete [] m_pRespData;

        m_pRespData = new unsigned char[m_iDataLen];
        pbuff = m_pRespData;
        m_iDataLen = i2d_OCSP_RESPONSE(pResponse, &(pbuff));
        if (m_iDataLen <= 0)
        {
            m_iDataLen = 0;
            delete [] m_pRespData;
            m_pRespData = NULL;
        }
#ifdef OPENSSL_IS_BORINGSSL
        if (m_pCtx)
            SSL_CTX_set_ocsp_response(m_pCtx, m_pRespData, m_iDataLen);
#endif
    }
}


int SslOcspStapling::certVerify(OCSP_RESPONSE *pResponse,
                                OCSP_BASICRESP *pBasicResp, X509_STORE *pXstore)
{
    int                 n, iResult = -1;
    STACK_OF(X509)      *pXchain;
    ASN1_GENERALIZEDTIME  *pThisupdate, *pNextupdate;
    struct stat         st;

#ifndef OPENSSL_IS_BORINGSSL
    pXchain = m_pCtx->extra_certs;
#else
    SSL_CTX_get0_chain_certs(m_pCtx, &pXchain);
#endif
    if (OCSP_basic_verify(pBasicResp, pXchain, pXstore, OCSP_NOVERIFY) == 1)
    {
        if ((m_pCertId != NULL)
            && (OCSP_resp_find_status(pBasicResp, m_pCertId, &n,
                                      NULL, NULL, &pThisupdate, &pNextupdate) == 1)
            && (n == V_OCSP_CERTSTATUS_GOOD)
            && (OCSP_check_validity(pThisupdate, pNextupdate, 300, -1) == 1))
        {
            iResult = 0;
            updateRespData(pResponse);
            unlink(m_sRespfile.c_str());
            rename(m_sRespfileTmp.c_str(), m_sRespfile.c_str());
            if (::stat(m_sRespfile.c_str(), &st) == 0)
                m_RespTime = st.st_mtime;
        }
    }
    else
        Logger::getRootLogger()->error("OCSP_basic_verify() failed: %s\n",
                                       SslError().what());
    if (iResult)
    {
        setLastErrMsg("%s", SslError().what());
        ERR_clear_error();
        if (m_pHttpFetch)
            m_pHttpFetch->writeLog(s_ErrMsg.c_str());

    }
    return iResult;
}


int SslOcspStapling::verifyRespFile(int iNeedVerify)
{
    int                 iResult = -1;
    BIO                 *pBio;
    OCSP_RESPONSE       *pResponse;
    OCSP_BASICRESP      *pBasicResp;
    X509_STORE *pXstore;
    if (iNeedVerify)
        pBio = BIO_new_file(m_sRespfileTmp.c_str(), "r");
    else
        pBio = BIO_new_file(m_sRespfile.c_str(), "r");
    if (pBio == NULL)
        return LS_FAIL;

    pResponse = d2i_OCSP_RESPONSE_bio(pBio, NULL);
    BIO_free(pBio);
    if (pResponse == NULL)
        return LS_FAIL;

    if (OCSP_response_status(pResponse) == OCSP_RESPONSE_STATUS_SUCCESSFUL)
    {
        if (iNeedVerify)
        {
            pBasicResp = OCSP_response_get1_basic(pResponse);
            if (pBasicResp != NULL)
            {
                pXstore = SSL_CTX_get_cert_store(m_pCtx);
                if (pXstore)
                    iResult = certVerify(pResponse, pBasicResp, pXstore);
                OCSP_BASICRESP_free(pBasicResp);
            }
        }
        else
        {
            updateRespData(pResponse);
            iResult = 0;
        }
    }
    OCSP_RESPONSE_free(pResponse);
    return iResult;
}


int SslOcspStapling::getCertId(X509 *pCert)
{
    int     i, n;
    X509                *pXissuer;
    X509_STORE          *pXstore;
    STACK_OF(X509)      *pXchain;
    X509_STORE_CTX      *pXstore_ctx;

#ifndef OPENSSL_IS_BORINGSSL
    pXchain = m_pCtx->extra_certs;
#else
    SSL_CTX_get0_chain_certs(m_pCtx, &pXchain);
#endif
    n = sk_X509_num(pXchain);
    for (i = 0; i < n; i++)
    {
        pXissuer = sk_X509_value(pXchain, i);
        if (X509_check_issued(pXissuer, pCert) == X509_V_OK)
        {
#ifndef OPENSSL_IS_BORINGSSL
            CRYPTO_add(&pXissuer->references, 1, CRYPTO_LOCK_X509);
#else
            X509_up_ref(pXissuer);
#endif
            m_pCertId = OCSP_cert_to_id(NULL, pCert, pXissuer);
            X509_free(pXissuer);
            return 0;
        }
    }
    pXstore = SSL_CTX_get_cert_store(m_pCtx);
    if (pXstore == NULL)
    {
        setLastErrMsg("SSL_CTX_get_cert_store failed!\n");
        return LS_FAIL;
    }
    pXstore_ctx = X509_STORE_CTX_new();
    if (pXstore_ctx == NULL)
    {
        setLastErrMsg("X509_STORE_CTX_new failed!\n");
        return LS_FAIL;
    }
    if (X509_STORE_CTX_init(pXstore_ctx, pXstore, NULL, NULL) == 0)
    {
        setLastErrMsg("X509_STORE_CTX_init failed!\n");
        return LS_FAIL;
    }
    n = X509_STORE_CTX_get1_issuer(&pXissuer, pXstore_ctx, pCert);
    X509_STORE_CTX_free(pXstore_ctx);
    if ((n == -1) || (n == 0))
    {
        setLastErrMsg("X509_STORE_CTX_get1_issuer failed!\n");
        return LS_FAIL;
    }
    m_pCertId = OCSP_cert_to_id(NULL, pCert, pXissuer);
    X509_free(pXissuer);
    return 0;
}


void SslOcspStapling::setCertFile(const char *Certfile)
{
    char RespFile[4096], *pExt;
    unsigned char md5[16];
    char md5Str[35] = {0};
    int iLen;
    m_sCertfile.setStr(Certfile);
    StringTool::getMd5(Certfile, strlen(Certfile), md5);
    StringTool::hexEncode((const char *)md5, 16, md5Str);
    md5Str[32] = 0;
    iLen = snprintf(RespFile, 4095, "%.*sR%s", s_iRespTempPathLen,
                    s_pRespTempPath, md5Str);
    pExt = RespFile + iLen;
    snprintf(pExt, 5, ".rsp");
    m_sRespfile.setStr(RespFile);
    snprintf(pExt, 5, ".tmp");
    m_sRespfileTmp.setStr(RespFile);
}


int SslOcspStapling::config(const XmlNode *pNode, SSL_CTX *pSSL,
                            const char *pCAFile, char *pachCert)
{
    setCertFile(pachCert);

    if (pCAFile)
        setCAFile(pCAFile);

    setRespMaxAge(ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                  "ocspRespMaxAge", 60, 360000, 3600));

    const char *pResponder = pNode->getChildValue("ocspResponder");
    if (pResponder)
        setOcspResponder(pResponder);

    if (init(pSSL) == -1)
    {
        LS_ERROR(ConfigCtx::getCurConfigCtx(),
                 "OCSP Stapling can't be enabled [%s].",
                 getStaplingErrMsg());
        return LS_FAIL;
    }

    return 0;
}


