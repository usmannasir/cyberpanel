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
#ifndef SSLCERT_H
#define SSLCERT_H

#include <lsdef.h>


typedef struct x509_st X509;

class SslCert
{
private:
    X509 *m_cert;
    char *m_pSubjectName;
    char *m_pIssuer;
    void release();

public:
    SslCert();
    explicit SslCert(X509 *pCert);

    ~SslCert();
    void operator=(X509 *pCert);
    bool operator==(X509 *pCert) const
    {   return m_cert == pCert ;    }
    bool operator!=(X509 *pCert) const
    {   return m_cert != pCert ;    }
    X509 *get() const
    {   return m_cert;  }
    const char *getSubjectName();
    const char *getIssuer();
    static int PEMWriteCert(X509 *pCert, char *pBuf, int len);

    LS_NO_COPY_ASSIGN(SslCert);
};

#endif
