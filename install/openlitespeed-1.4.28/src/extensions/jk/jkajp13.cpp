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
#include "jkajp13.h"
#include "jworker.h"
#include "jworkerconfig.h"

#include <http/httpreq.h>
#include <http/httpsession.h>
#include <http/httpver.h>
#include <lsr/ls_strtool.h>
#include <sslpp/sslconnection.h>
#include <sslpp/sslcert.h>

//#include <openssl/ssl.h>
#include <stdio.h>

JkAjp13::JkAjp13()
{
}


JkAjp13::~JkAjp13()
{
}


static const char *s_pForwardHeaderName[9] =
{
    "cache-control",
    "if-modified-since",
    "if-match",
    "if-none-match",
    "if-unmodified-since",
    "if-range",
    "keep-alive",
    "range",
    "transfer-encoding"
};


static int s_iForwardHeaderLen[9] =
{
    13, 17, 8, 13, 19, 8, 10, 5, 17
};


const char *JkAjp13::s_pRespHeaders[AJP_RESP_HEADERS_NUM + 1] =
{
    "",
    "Content-Type",
    "Content-Language",
    "Content-Length",
    "Date",
    "Last-Modified",
    "Location",
    "Set-Cookie",
    "Set-Cookie2",
    "Servlet-Engine",
    "Status",
    "WWW-Authenticate"
};


int JkAjp13::s_iRespHeaderLen[AJP_RESP_HEADERS_NUM + 1] =
{
    0, 12, 16, 14, 4, 13, 8, 10, 11, 14, 6, 16
};


/*
For messages from the server to the container of type "Forward Request":

AJP13_FORWARD_REQUEST :=
    prefix_code      (byte) 0x02 = JK_AJP13_FORWARD_REQUEST
    method           (byte)
    protocol         (string)
    req_uri          (string)
    remote_addr      (string)
    remote_host      (string)
    server_name      (string)
    server_port      (integer)
    is_ssl           (boolean)
    num_headers      (integer)
    request_headers *(req_header_name req_header_value)
    attributes      *(attribut_name attribute_value)
    request_terminator (byte) OxFF

The request_headers have the following structure:

req_header_name :=
    sc_req_header_name | (string)  [see below for how this is parsed]

sc_req_header_name := 0xA0xx (integer)

req_header_value := (string)

The attributes are optional and have the following structure:

attribute_name := (string)

attribute_value := (string)


Not that the all-important header is "content-length', because it determines whether or not the container looks for another packet immediately.
*/


inline void appendInt(char *&p, int n)
{
    *p++ = (unsigned char)((n >> 8) & 0xff);
    *p++ = (unsigned char)(n & 0xff);
}


inline void appendLong(char *&p, int n)
{
    *p++ = (unsigned char)((n >> 24) & 0xff);
    *p++ = (unsigned char)((n >> 16) & 0xff);
    *p++ = (unsigned char)((n >> 8) & 0xff);
    *p++ = (unsigned char)(n & 0xff);
}


inline void appendString(char *&p, const char *s, int n)
{
    appendInt(p, n);
    ::memcpy(p, s, n);
    p += n;
    *p++ = 0;
}


void JkAjp13::buildAjpHeader(char *pBuf, int size)
{
    *pBuf++ = AJP_REQ_PREFIX_B1;
    *pBuf++ = AJP_REQ_PREFIX_B2;
    appendInt(pBuf, size);
}


void JkAjp13::buildAjpReqBodyHeader(char *pBuf, int size)
{
    *pBuf++ = AJP_REQ_PREFIX_B1;
    *pBuf++ = AJP_REQ_PREFIX_B2;
    appendInt(pBuf, size + 2);
    appendInt(pBuf, size);
}


int JkAjp13::buildReq(HttpSession *pSession, char *&p, char *pEnd)
{
    HttpReq *pReq = pSession->getReq();
    //assert( size == AJP_MAX_PKT_BODY_SIZE );
    char *pEnd2 = pEnd - 6;
    int n;
    *p++ = AJP13_FORWARD_REQUEST;
    *p++ = pReq->getMethod();       //method
    n = HttpVer::getVersionStringLen(pReq->getVersion());
    //Protocol string
    appendString(p, HttpVer::getVersionString(pReq->getVersion()), n);
    // request uri
    n = pReq->getURILen();
    if (pEnd2 - p < n)
        return LS_FAIL;
    appendString(p, pReq->getURI(), n);

    n = pSession->getPeerAddrStrLen();
    if (pEnd - p < 2 * (n + 3))
        return LS_FAIL;
    // peer address
    appendString(p, pSession->getPeerAddrString(), n);
    // peer host, use peer address as DNS lookup is too expensive and avoided,
    appendString(p, pSession->getPeerAddrString(), n);
    n = pReq->getHostStrLen();
    if (pEnd2 - p < n)
        return LS_FAIL;
    //host
    appendString(p, pReq->getHostStr(), n);
    if (p >= pEnd2)
        return LS_FAIL;
    //port
    appendInt(p, pReq->getPort());
    //is_ssl
    *p++ = (unsigned char)(pSession->isSSL());
    char *pHeaderCounts = p;
    p += 2;
    int headerCounts = 0;
    size_t i;
    const char *pHeader;
    for (i = HttpHeader::H_ACCEPT; i < HttpHeader::H_CACHE_CTRL; ++i)
    {
        pHeader = pReq->getHeader(i);
        if (*pHeader)
        {
            n = pReq->getHeaderLen(i);
            if (pEnd2 - p < n)
                return LS_FAIL;
            *p++ = 0xA0;
            *p++ = (unsigned char)(i + 1);
            appendString(p, pHeader, n);
            ++headerCounts;
        }
    }
    pHeader = pReq->getHeader(HttpHeader::H_CONTENT_LENGTH);
    if (!*pHeader)
    {
        if (pEnd2 - p < 2)
            return LS_FAIL;
        *p++ = 0xA0;
        *p++ = (unsigned char)(HttpHeader::H_CONTENT_LENGTH + 1);
        appendString(p, "0", 1);
        ++headerCounts;
    }
    for (i = HttpHeader::H_CACHE_CTRL; i < HttpHeader::H_TRANSFER_ENCODING;
         ++i)
    {
        const char *pHeader = pReq->getHeader(i);
        if (*pHeader)
        {
            n = pReq->getHeaderLen(i);
            if (pEnd2 - p < n +
                s_iForwardHeaderLen[ i - HttpHeader::H_CACHE_CTRL])
                return LS_FAIL;
            appendString(p, s_pForwardHeaderName[i - HttpHeader::H_CACHE_CTRL],
                         s_iForwardHeaderLen[ i - HttpHeader::H_CACHE_CTRL]);
            appendString(p, pHeader, n);
            ++headerCounts;
        }
    }
    appendInt(pHeaderCounts, headerCounts);
    const char *pAttr = pReq->getAuthUser();
    if (pAttr)
    {
        n = strlen(pAttr);
        if (pEnd2 - p < n + 8)
            return LS_FAIL;
        *p++ = AJP_A_REMOTE_USER;
        appendString(p, pAttr, n);
        *p++ = AJP_A_AUTH_TYPE;
        appendString(p, "BASIC", 5);
    }

    pAttr = pReq->getQueryString();
    if (pAttr)
    {
        n = pReq->getQueryStringLen();
        if (pEnd2 - p < n)
            return LS_FAIL;
        *p++ = AJP_A_QUERY_STRING;
        appendString(p, pAttr, n);
    }
    if (pSession->isSSL())
    {
        SslConnection *pSSL = pSession->getSSL();
        SSL_SESSION *pSession = pSSL->getSession();
        if (pSession)
        {
            int idLen = SslConnection::getSessionIdLen(pSession);
            n = idLen * 2;
            if (pEnd2 - p < n)
                return LS_FAIL;
            *p++ = AJP_A_SSL_SESSION;
            appendInt(p, n);
            ls_hexencode((char *)SslConnection::getSessionId(pSession),
                         idLen, p);
            p += n;
            *p++ = 0;
        }

        const SSL_CIPHER *pCipher = pSSL->getCurrentCipher();
        if (pCipher)
        {
            const char *pName = pSSL->getCipherName();
            n = strlen(pName);
            if (pEnd2 - p < n)
                return LS_FAIL;
            *p++ = AJP_A_SSL_CIPHER;
            appendString(p, pName, n);
            int algkeysize;
            int keysize = SslConnection::getCipherBits(pCipher, &algkeysize);
            if (pEnd2 - p < 20)
                return LS_FAIL;
            *p++ = AJP_A_SSL_KEY_SIZE;
            n = ls_snprintf(p + 2, 16, "%d", keysize);
            appendInt(p, n);
            p += n + 1;
        }

        X509 *pClientCert = pSSL->getPeerCertificate();
        if (pClientCert)
        {
            n = SslCert::PEMWriteCert(pClientCert, p + 3, pEnd - p);
            if ((n > 0) && (n < pEnd2 - p))
            {
                *p++ = AJP_A_SSL_CERT;
                appendInt(p, n);
                p += n;
                *p++ = 0;
            }
        }
    }

    return 0;
}


int JkAjp13::buildWorkerHeader(JWorker *pWorker, char *&p, char *pEnd)
{
    //TODO: jvm_route
    //pAttr = ???;
    //if (pAttr )
    //{
    //    n = strlen( pAttr );
    //    if ( pEnd - p < n )
    //        return LS_FAIL;
    //    *p++ = AJP_A_JVM_ROUTE;
    //    appendString( p, pAttr, n );
    //}

    //add shared secret between servlet engine and web server
    char *pEnd2 = pEnd - 6;
    int n;
    const char *pSecret = pWorker->getConfig().getSecret();
    n = pWorker->getConfig().getSecretLen();
    if (pSecret)
    {
        if (pEnd2 - p < n)
            return LS_FAIL;
        *p++ = AJP_A_SECRET;
        appendString(p, pSecret, n);
    }

    //add custom environment variables as attributes
    const Env *env = pWorker->getConfig().getEnv();
    int sz = env->size();
    char *const *pEnvs = env->get();
    for (int i = 0 ; i < sz; ++i)
    {
        if (!pEnvs[i])
            continue;
        char *pVal = strchr(pEnvs[i], '=');
        if (pVal == NULL)
            continue;
        n = strlen(pEnvs[i]);
        if (pEnd2 - p < n)
            return LS_FAIL;
        *p++ = AJP_A_REQ_ATTRIBUTE;
        appendString(p, pEnvs[i], pVal - pEnvs[i]);
        appendString(p, pVal, pEnvs[i] + n - pVal);
    }
    *p++ = AJP_A_END;
    return 0;
}



