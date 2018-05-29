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
#include <config.h>


#ifndef SSLOCSPSTAPLING_H
#define SSLOCSPSTAPLING_H

#include <socket/gsockaddr.h>
#include <util/autostr.h>

#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <lsdef.h>

typedef struct ocsp_cert_id_st OCSP_CERTID;
typedef struct ocsp_response_st OCSP_RESPONSE;
typedef struct ocsp_basic_response_st OCSP_BASICRESP;
typedef struct ssl_st SSL;
typedef struct ssl_ctx_st SSL_CTX;
typedef struct x509_st X509;
typedef struct x509_store_st X509_STORE;


class HttpFetch;
class ConfigCtx;
class XmlNode;
class SslOcspStapling
{
public:
    SslOcspStapling();
    ~SslOcspStapling();
    int init(SSL_CTX *pSslCtx);
    int update();
    int getCertId(X509 *pCert);
    int createRequest();
    int getResponder(X509 *pCert);
    int callback(SSL *ssl);
    int processResponse(HttpFetch *pHttpFetch);
    int verifyRespFile(int iNeedVerify = 1);
    int certVerify(OCSP_RESPONSE *pResponse, OCSP_BASICRESP *pBasicResp,
                   X509_STORE *pXstore);
    void updateRespData(OCSP_RESPONSE *pResponse);
    int getRequestData(unsigned char **pReqData);
    void setCertFile(const char *Certfile);
    int config(const XmlNode *pNode, SSL_CTX *pSSL,
               const char *pCAFile, char *pachCert);

    void setOcspResponder(const char *url)    {   m_sOcspResponder.setStr(url);     }
    void setCombineCAfile(const char *CAfile) {   m_sCombineCAfile.setStr(CAfile);  }
    void setCAFile(const char *CAfile)        {   m_sCAfile.setStr(CAfile);         }
    void setRespMaxAge(const int iMaxAge)     {   m_iocspRespMaxAge = iMaxAge;        }
    void setRespfile(const char *Respfile)    {   m_sRespfile.setStr(Respfile);     }

    static void setRespTempPath(const char *pPath)
    {
        if (pPath && (*pPath == '/'))
        {
            s_pRespTempPath = strdup(pPath);
            s_iRespTempPathLen = strlen(pPath);
        }
    }

private:
    HttpFetch      *m_pHttpFetch;

    unsigned char  *m_pReqData;
    uint32_t    m_iDataLen;
    unsigned char     *m_pRespData;
    GSockAddr   m_addrResponder;

    AutoStr2    m_sCertfile;
    AutoStr2    m_sCAfile;
    AutoStr2    m_sOcspResponder;
    AutoStr2    m_sCombineCAfile;
    AutoStr2    m_sRespfile;
    AutoStr2    m_sRespfileTmp;
    int         m_iocspRespMaxAge;
    SSL_CTX    *m_pCtx;
    time_t      m_RespTime;
    OCSP_CERTID *m_pCertId;

    static const char *s_pRespTempPath;
    static int   s_iRespTempPathLen;

    LS_NO_COPY_ASSIGN(SslOcspStapling);
};
const char *getStaplingErrMsg();
#endif // SSLOCSPSTAPLING_H

