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

#ifndef OPENSSL_IS_BORINGSSL
#include <openssl/err.h>
#endif
#include "sslutil.h"
#include <sslpp/sslcontext.h>
#include <sslpp/sslconnection.h>
#include <sslpp/sslsesscache.h>
#include <sslpp/sslticket.h>

#include <lsdef.h>
#include <log4cxx/logger.h>
#include <util/autobuf.h>

#include <ctype.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>


const int SSLUTIL_MAX_CERT_LENGTH = 40960;

static char         s_iUseStrongDH = 0;
void SslUtil::setUseStrongDH(int use)
{
    s_iUseStrongDH = use;
}

static DH *s_pDHs[3] = {   NULL, NULL, NULL    };

const char *SslUtil::s_pDefaultCAFile = NULL;
const char *SslUtil::s_pDefaultCAPath = NULL;

static const int s_iSystems = 4;
static const char *s_aSystemFiles[] =
{
    "/etc/ssl/certs/ca-certificates.crt",       // Debian/Ubuntu
    "/etc/pki/tls/certs/ca-bundle.crt",         // Centos/Red Hat/Fedora
    "/usr/local/share/certs/ca-root-nss.crt",   // FreeBSD
    "/etc/ssl/ca-bundle.pem",                   // OpenSUSE
};
static const char *s_aSystemDirs[] =
{
    "/etc/ssl/certs/",                  // Debian/Ubuntu
    "/etc/pki/tls/certs/",              // Centos/Red Hat/Fedora
    "/usr/local/share/certs/",          // FreeBSD
    "/etc/ssl/",                        // OpenSUSE
};

/* 1024bits dh
-----BEGIN DH PARAMETERS-----
MIGHAoGBAIKf6/zj7gQ0hi0zZKYr3ntl8MdKOlO1VSkUFPyuXobXNLFtvcyVKxxe
tEOxVLO0ZmLoEeEdi8cxNAGKXqe1tqlyDYS8KLdIIsWvJMkE5bta2r+P8qXte0Vm
iNbKuC+K8BiKRWw+1i0v6s9r0/1HM32ITfoJ8KPWlnXjWAbjrpWTAgEC
-----END DH PARAMETERS-----
*/
static unsigned char dh1024_p[] =
{
    0x82, 0x9F, 0xEB, 0xFC, 0xE3, 0xEE, 0x04, 0x34, 0x86, 0x2D, 0x33, 0x64,
    0xA6, 0x2B, 0xDE, 0x7B, 0x65, 0xF0, 0xC7, 0x4A, 0x3A, 0x53, 0xB5, 0x55,
    0x29, 0x14, 0x14, 0xFC, 0xAE, 0x5E, 0x86, 0xD7, 0x34, 0xB1, 0x6D, 0xBD,
    0xCC, 0x95, 0x2B, 0x1C, 0x5E, 0xB4, 0x43, 0xB1, 0x54, 0xB3, 0xB4, 0x66,
    0x62, 0xE8, 0x11, 0xE1, 0x1D, 0x8B, 0xC7, 0x31, 0x34, 0x01, 0x8A, 0x5E,
    0xA7, 0xB5, 0xB6, 0xA9, 0x72, 0x0D, 0x84, 0xBC, 0x28, 0xB7, 0x48, 0x22,
    0xC5, 0xAF, 0x24, 0xC9, 0x04, 0xE5, 0xBB, 0x5A, 0xDA, 0xBF, 0x8F, 0xF2,
    0xA5, 0xED, 0x7B, 0x45, 0x66, 0x88, 0xD6, 0xCA, 0xB8, 0x2F, 0x8A, 0xF0,
    0x18, 0x8A, 0x45, 0x6C, 0x3E, 0xD6, 0x2D, 0x2F, 0xEA, 0xCF, 0x6B, 0xD3,
    0xFD, 0x47, 0x33, 0x7D, 0x88, 0x4D, 0xFA, 0x09, 0xF0, 0xA3, 0xD6, 0x96,
    0x75, 0xE3, 0x58, 0x06, 0xE3, 0xAE, 0x95, 0x93
};


/* 2048bits dh
-----BEGIN DH PARAMETERS-----
MIIBCAKCAQEAztPVTfK9Q44nL9BeVY9Q7MtGY7RWOuoIkFedjNo0pceQ6wwgzsyq
m0BoXl9qQPAVtmLwIqNw6NraceLyXcAWW0CENq78PbjpIqFOJvyVLD3XtYTfENGj
PrH0UQDgOAl9B5ae49HHb5EMMMqDhUV3MV4OVMUjH/QbI5Py1CHw383xUikeDHj/
ox7NuR98ucbh3esu90hV5jQf/5bLHdiJ0MipGOrhLuR0ehi7CJ63eChOhqRRldJF
2YQyYoV+k7uiHQH9Ufno/yUdvTMhTriug+iJFfLJq28w9inwnk9HsteoKDUFLKtC
eezPfyukmt9MBkarmRyP5XAsT+zr2GTnSwIBAg==
-----END DH PARAMETERS-----
*/
static unsigned char dh2048_p[] =
{
    0xCE, 0xD3, 0xD5, 0x4D, 0xF2, 0xBD, 0x43, 0x8E, 0x27, 0x2F, 0xD0, 0x5E,
    0x55, 0x8F, 0x50, 0xEC, 0xCB, 0x46, 0x63, 0xB4, 0x56, 0x3A, 0xEA, 0x08,
    0x90, 0x57, 0x9D, 0x8C, 0xDA, 0x34, 0xA5, 0xC7, 0x90, 0xEB, 0x0C, 0x20,
    0xCE, 0xCC, 0xAA, 0x9B, 0x40, 0x68, 0x5E, 0x5F, 0x6A, 0x40, 0xF0, 0x15,
    0xB6, 0x62, 0xF0, 0x22, 0xA3, 0x70, 0xE8, 0xDA, 0xDA, 0x71, 0xE2, 0xF2,
    0x5D, 0xC0, 0x16, 0x5B, 0x40, 0x84, 0x36, 0xAE, 0xFC, 0x3D, 0xB8, 0xE9,
    0x22, 0xA1, 0x4E, 0x26, 0xFC, 0x95, 0x2C, 0x3D, 0xD7, 0xB5, 0x84, 0xDF,
    0x10, 0xD1, 0xA3, 0x3E, 0xB1, 0xF4, 0x51, 0x00, 0xE0, 0x38, 0x09, 0x7D,
    0x07, 0x96, 0x9E, 0xE3, 0xD1, 0xC7, 0x6F, 0x91, 0x0C, 0x30, 0xCA, 0x83,
    0x85, 0x45, 0x77, 0x31, 0x5E, 0x0E, 0x54, 0xC5, 0x23, 0x1F, 0xF4, 0x1B,
    0x23, 0x93, 0xF2, 0xD4, 0x21, 0xF0, 0xDF, 0xCD, 0xF1, 0x52, 0x29, 0x1E,
    0x0C, 0x78, 0xFF, 0xA3, 0x1E, 0xCD, 0xB9, 0x1F, 0x7C, 0xB9, 0xC6, 0xE1,
    0xDD, 0xEB, 0x2E, 0xF7, 0x48, 0x55, 0xE6, 0x34, 0x1F, 0xFF, 0x96, 0xCB,
    0x1D, 0xD8, 0x89, 0xD0, 0xC8, 0xA9, 0x18, 0xEA, 0xE1, 0x2E, 0xE4, 0x74,
    0x7A, 0x18, 0xBB, 0x08, 0x9E, 0xB7, 0x78, 0x28, 0x4E, 0x86, 0xA4, 0x51,
    0x95, 0xD2, 0x45, 0xD9, 0x84, 0x32, 0x62, 0x85, 0x7E, 0x93, 0xBB, 0xA2,
    0x1D, 0x01, 0xFD, 0x51, 0xF9, 0xE8, 0xFF, 0x25, 0x1D, 0xBD, 0x33, 0x21,
    0x4E, 0xB8, 0xAE, 0x83, 0xE8, 0x89, 0x15, 0xF2, 0xC9, 0xAB, 0x6F, 0x30,
    0xF6, 0x29, 0xF0, 0x9E, 0x4F, 0x47, 0xB2, 0xD7, 0xA8, 0x28, 0x35, 0x05,
    0x2C, 0xAB, 0x42, 0x79, 0xEC, 0xCF, 0x7F, 0x2B, 0xA4, 0x9A, 0xDF, 0x4C,
    0x06, 0x46, 0xAB, 0x99, 0x1C, 0x8F, 0xE5, 0x70, 0x2C, 0x4F, 0xEC, 0xEB,
    0xD8, 0x64, 0xE7, 0x4B
};


/* 4096bits dh
-----BEGIN DH PARAMETERS-----
MIICCAKCAgEAi0qVV8+TVb2GssoA7oTXYkEU2CqdT1baVgHxSBBlsLnFEgCWibNI
9n5Q4joQrPE986MvhQI0QGd4+CF7ELcL3OKw0P4GRRXKQhuw2KBpbWR6irdvxl3G
avQTSqvZxyXWqgVtMD3/s8WgW/yJ/OdaEcabY/sJ9mfhN1Luv1kRE56zXEhapdTr
w3Si9u9UyHLOZM4cgRQ+aTRIuoOuFBtqWmBrZ1E9JCYLa2R7sxqhPvT9/25cz/Ti
NSZfIb/WgO6bCybhaCcSSbkd9imlq6PzeM+EuJollCslpJqzqj3ZbcdJjU1I+MGi
shgJj+SOiw2laK7YhWnvj9n5MPb7sED9hOtmvWDXyl//BzLXY6k583Su882mzBjO
NreJXxoVQuMOqn9YHWlNE6u2FvLE7XMob6QsWkiGE+MZKqVKgzdirnTbV0TdPuKd
rbY/eRJzsk4rKg6ZYrRMaiI/hZsAvT5ZUXy6Pw2TU8rFon9fw1ygdjKjubj154X8
i70ve9mhZApVv2+QABtFBzpyB+eAICK8I6b8dmp7fUnwJY4p1vFCIhjUlcFQQVvd
hjv3yHF2x35olftn8z2vXb1NVcQYO9ODVu+3fZIdhBrF8Ol6ZL/XH9g0CGjt57Hx
GGA+kgVcve9ly4AWiZOnCQuSdT4JGJpcGdnsq7wjRLyFY0AatT8i8psCAQI=
-----END DH PARAMETERS-----
*/

static unsigned char dh4096_p[] =
{
    0x8B, 0x4A, 0x95, 0x57, 0xCF, 0x93, 0x55, 0xBD, 0x86, 0xB2, 0xCA, 0x00,
    0xEE, 0x84, 0xD7, 0x62, 0x41, 0x14, 0xD8, 0x2A, 0x9D, 0x4F, 0x56, 0xDA,
    0x56, 0x01, 0xF1, 0x48, 0x10, 0x65, 0xB0, 0xB9, 0xC5, 0x12, 0x00, 0x96,
    0x89, 0xB3, 0x48, 0xF6, 0x7E, 0x50, 0xE2, 0x3A, 0x10, 0xAC, 0xF1, 0x3D,
    0xF3, 0xA3, 0x2F, 0x85, 0x02, 0x34, 0x40, 0x67, 0x78, 0xF8, 0x21, 0x7B,
    0x10, 0xB7, 0x0B, 0xDC, 0xE2, 0xB0, 0xD0, 0xFE, 0x06, 0x45, 0x15, 0xCA,
    0x42, 0x1B, 0xB0, 0xD8, 0xA0, 0x69, 0x6D, 0x64, 0x7A, 0x8A, 0xB7, 0x6F,
    0xC6, 0x5D, 0xC6, 0x6A, 0xF4, 0x13, 0x4A, 0xAB, 0xD9, 0xC7, 0x25, 0xD6,
    0xAA, 0x05, 0x6D, 0x30, 0x3D, 0xFF, 0xB3, 0xC5, 0xA0, 0x5B, 0xFC, 0x89,
    0xFC, 0xE7, 0x5A, 0x11, 0xC6, 0x9B, 0x63, 0xFB, 0x09, 0xF6, 0x67, 0xE1,
    0x37, 0x52, 0xEE, 0xBF, 0x59, 0x11, 0x13, 0x9E, 0xB3, 0x5C, 0x48, 0x5A,
    0xA5, 0xD4, 0xEB, 0xC3, 0x74, 0xA2, 0xF6, 0xEF, 0x54, 0xC8, 0x72, 0xCE,
    0x64, 0xCE, 0x1C, 0x81, 0x14, 0x3E, 0x69, 0x34, 0x48, 0xBA, 0x83, 0xAE,
    0x14, 0x1B, 0x6A, 0x5A, 0x60, 0x6B, 0x67, 0x51, 0x3D, 0x24, 0x26, 0x0B,
    0x6B, 0x64, 0x7B, 0xB3, 0x1A, 0xA1, 0x3E, 0xF4, 0xFD, 0xFF, 0x6E, 0x5C,
    0xCF, 0xF4, 0xE2, 0x35, 0x26, 0x5F, 0x21, 0xBF, 0xD6, 0x80, 0xEE, 0x9B,
    0x0B, 0x26, 0xE1, 0x68, 0x27, 0x12, 0x49, 0xB9, 0x1D, 0xF6, 0x29, 0xA5,
    0xAB, 0xA3, 0xF3, 0x78, 0xCF, 0x84, 0xB8, 0x9A, 0x25, 0x94, 0x2B, 0x25,
    0xA4, 0x9A, 0xB3, 0xAA, 0x3D, 0xD9, 0x6D, 0xC7, 0x49, 0x8D, 0x4D, 0x48,
    0xF8, 0xC1, 0xA2, 0xB2, 0x18, 0x09, 0x8F, 0xE4, 0x8E, 0x8B, 0x0D, 0xA5,
    0x68, 0xAE, 0xD8, 0x85, 0x69, 0xEF, 0x8F, 0xD9, 0xF9, 0x30, 0xF6, 0xFB,
    0xB0, 0x40, 0xFD, 0x84, 0xEB, 0x66, 0xBD, 0x60, 0xD7, 0xCA, 0x5F, 0xFF,
    0x07, 0x32, 0xD7, 0x63, 0xA9, 0x39, 0xF3, 0x74, 0xAE, 0xF3, 0xCD, 0xA6,
    0xCC, 0x18, 0xCE, 0x36, 0xB7, 0x89, 0x5F, 0x1A, 0x15, 0x42, 0xE3, 0x0E,
    0xAA, 0x7F, 0x58, 0x1D, 0x69, 0x4D, 0x13, 0xAB, 0xB6, 0x16, 0xF2, 0xC4,
    0xED, 0x73, 0x28, 0x6F, 0xA4, 0x2C, 0x5A, 0x48, 0x86, 0x13, 0xE3, 0x19,
    0x2A, 0xA5, 0x4A, 0x83, 0x37, 0x62, 0xAE, 0x74, 0xDB, 0x57, 0x44, 0xDD,
    0x3E, 0xE2, 0x9D, 0xAD, 0xB6, 0x3F, 0x79, 0x12, 0x73, 0xB2, 0x4E, 0x2B,
    0x2A, 0x0E, 0x99, 0x62, 0xB4, 0x4C, 0x6A, 0x22, 0x3F, 0x85, 0x9B, 0x00,
    0xBD, 0x3E, 0x59, 0x51, 0x7C, 0xBA, 0x3F, 0x0D, 0x93, 0x53, 0xCA, 0xC5,
    0xA2, 0x7F, 0x5F, 0xC3, 0x5C, 0xA0, 0x76, 0x32, 0xA3, 0xB9, 0xB8, 0xF5,
    0xE7, 0x85, 0xFC, 0x8B, 0xBD, 0x2F, 0x7B, 0xD9, 0xA1, 0x64, 0x0A, 0x55,
    0xBF, 0x6F, 0x90, 0x00, 0x1B, 0x45, 0x07, 0x3A, 0x72, 0x07, 0xE7, 0x80,
    0x20, 0x22, 0xBC, 0x23, 0xA6, 0xFC, 0x76, 0x6A, 0x7B, 0x7D, 0x49, 0xF0,
    0x25, 0x8E, 0x29, 0xD6, 0xF1, 0x42, 0x22, 0x18, 0xD4, 0x95, 0xC1, 0x50,
    0x41, 0x5B, 0xDD, 0x86, 0x3B, 0xF7, 0xC8, 0x71, 0x76, 0xC7, 0x7E, 0x68,
    0x95, 0xFB, 0x67, 0xF3, 0x3D, 0xAF, 0x5D, 0xBD, 0x4D, 0x55, 0xC4, 0x18,
    0x3B, 0xD3, 0x83, 0x56, 0xEF, 0xB7, 0x7D, 0x92, 0x1D, 0x84, 0x1A, 0xC5,
    0xF0, 0xE9, 0x7A, 0x64, 0xBF, 0xD7, 0x1F, 0xD8, 0x34, 0x08, 0x68, 0xED,
    0xE7, 0xB1, 0xF1, 0x18, 0x60, 0x3E, 0x92, 0x05, 0x5C, 0xBD, 0xEF, 0x65,
    0xCB, 0x80, 0x16, 0x89, 0x93, 0xA7, 0x09, 0x0B, 0x92, 0x75, 0x3E, 0x09,
    0x18, 0x9A, 0x5C, 0x19, 0xD9, 0xEC, 0xAB, 0xBC, 0x23, 0x44, 0xBC, 0x85,
    0x63, 0x40, 0x1A, 0xB5, 0x3F, 0x22, 0xF2, 0x9B
};


static unsigned char *s_dh_p[3] =
{   dh1024_p, dh2048_p, dh4096_p  };

static int  s_dh_p_size[3] =
{   sizeof(dh1024_p), sizeof(dh2048_p), sizeof(dh4096_p) };

static DH *getTmpDhParam(int size)
{
    unsigned char dh_g[] = { 0x02 };
    int index = (size + 1023) / 1024 - 1;
    if (index > 2)
        index = 2;

    if (s_pDHs[index])
        return s_pDHs[index];

    if ((s_pDHs[index] = DH_new()) != NULL)
    {
#if OPENSSL_VERSION_NUMBER >= 0x10100000L
        BIGNUM *p, *q, *g;
        DH_set0_pqg(s_pDHs[index], 
                    BN_bin2bn(s_dh_p[index], s_dh_p_size[index], NULL), //p
                    NULL,                                               //q
                    BN_bin2bn(dh_g, sizeof(dh_g), NULL));               //g
        DH_get0_pqg(s_pDHs[index], (const BIGNUM **)&p, (const BIGNUM **)&q, 
                    (const BIGNUM **)&g);
        if ((p == NULL) || (g == NULL))
#else        
        s_pDHs[index]->p = BN_bin2bn(s_dh_p[index], s_dh_p_size[index], NULL);
        s_pDHs[index]->g = BN_bin2bn(dh_g, sizeof(dh_g), NULL);
        if ((s_pDHs[index]->p == NULL) || (s_pDHs[index]->g == NULL))
#endif            
        {
            DH_free(s_pDHs[index]);
            s_pDHs[index] = NULL;
        }
    }
    return s_pDHs[index];
}


static void freeDH(void *parent, void *ptr, CRYPTO_EX_DATA *ad,
                int idx, long argl, void *argp)
{
    DH *pDH = (DH *)ptr;
    int i;
    for (i = 0; i < 3; ++i)
    {
        if (pDH == s_pDHs[i])
            return;
    }
    DH_free(pDH);
}


static long s_iDHParamIdx = -1;
int SslUtil::initDH(SSL_CTX *pCtx, const char *pFile, int iKeyLen)
{
    DH *pDH = NULL;
    if (pFile)
    {
        BIO *bio;
        if ((bio = BIO_new_file(pFile, "r")) != NULL)
        {
            pDH = PEM_read_bio_DHparams(bio, NULL, NULL, NULL);
            BIO_free(bio);
            SSL_CTX_set_tmp_dh(pCtx, pDH);
        }
    }
    if (!pDH)
    {
        if (iKeyLen < 1024 || !s_iUseStrongDH)
            iKeyLen = 1024;
        pDH = getTmpDhParam(iKeyLen);
        if (!pDH)
            return -1;
        SSL_CTX_set_tmp_dh(pCtx, pDH);
    }
    if (s_iDHParamIdx == -1)
        s_iDHParamIdx = SSL_CTX_get_ex_new_index(0, NULL, NULL, NULL, freeDH);
    SSL_CTX_set_ex_data(pCtx, s_iDHParamIdx, pDH);

    SSL_CTX_set_options(pCtx, SSL_OP_SINGLE_DH_USE);
    return 0;
}


int SslUtil::copyDH(SSL_CTX* pCtx, SSL_CTX* pSrcCtx)
{
    DH *pDH;
    if (s_iDHParamIdx == -1)
        return LS_FAIL;
    pDH = (DH *)SSL_CTX_get_ex_data(pSrcCtx, s_iDHParamIdx);
    if (pDH == NULL)
        return LS_FAIL;
    SSL_CTX_set_tmp_dh(pCtx, pDH);
    return LS_OK;
}


int SslUtil::initECDH(SSL_CTX *pCtx)
{
#if OPENSSL_VERSION_NUMBER >= 0x10001000L
#ifndef OPENSSL_NO_ECDH
    EC_KEY *ecdh;
    ecdh = EC_KEY_new_by_curve_name(NID_X9_62_prime256v1);
    if (ecdh == NULL)
        return -1;
    SSL_CTX_set_tmp_ecdh(pCtx, ecdh);
    EC_KEY_free(ecdh);

    SSL_CTX_set_options(pCtx, SSL_OP_SINGLE_ECDH_USE);

#endif
#endif
    return 0;
}

int SslUtil::translateType(int type)
{
    switch (type)
    {
    case SslUtil::FILETYPE_PEM:
        return SSL_FILETYPE_PEM;
    case SslUtil::FILETYPE_ASN1:
        return SSL_FILETYPE_ASN1;
    default:
        return -1;
    }
}


int SslUtil::loadPemWithMissingDash(const char *pFile, char *buf, int bufLen,
                                    char **pBegin)
{
    int i = 0, fd, iLen;
    char *pEnd, *p;
    struct stat st;

    fd = open(pFile, O_RDONLY);
    if (fd < 0)
        return -1;

    if (fstat(fd, &st) < 0)
    {
        close(fd);
        return -1;
    }

    iLen = st.st_size;
    if (iLen <= bufLen - 10)
        i = read(fd, buf + 5, iLen);
    close(fd);
    if (i < iLen)
        return -1;
    *pBegin = buf + 5;
    pEnd = *pBegin + iLen;

    p = *pBegin;
    while (*p == '-')
        ++p;
    while (p < *pBegin + 5)
    {
        /** Do not use *(-- to avoid trigger compiler bug */
        --*pBegin;
        *(*pBegin) = '-';
    }

    while (isspace(pEnd[-1]))
        pEnd--;
    p = pEnd;

    while (p[-1] == '-')
        --p;
    while (p + 5 > pEnd)
        *pEnd++ = '-';
    *pEnd++ = '\n';
    *pEnd = 0;

    return pEnd - *pBegin;
}


int SslUtil::digestIdContext(SSL_CTX *pCtx, const void *pDigest,
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
    EVP_MD_CTX_init(pmd);

    if ( EVP_DigestInit_ex(pmd, EVP_sha1(), NULL) != 1 )
    {
        LS_DBG_L( "Init EVP Digest failed.");
#if OPENSSL_VERSION_NUMBER >= 0x10100000L
        EVP_MD_CTX_free(pmd);
#endif        
        return LS_FAIL;
    }
    else if ( EVP_DigestUpdate(pmd, pDigest, iDigestLen) != 1 )
    {
        LS_DBG_L( "Update EVP Digest failed");
#if OPENSSL_VERSION_NUMBER >= 0x10100000L
        EVP_MD_CTX_free(pmd);
#endif        
        return LS_FAIL;
    }
    else if ( EVP_DigestFinal_ex(pmd, buf, &len ) != 1 )
    {
        LS_DBG_L( "EVP Digest Final failed.");
#if OPENSSL_VERSION_NUMBER >= 0x10100000L
        EVP_MD_CTX_free(pmd);
#endif        
        return LS_FAIL;
    }
#if OPENSSL_VERSION_NUMBER < 0x10100000L
    else if ( EVP_MD_CTX_cleanup(pmd) != 1 )
    {
        LS_DBG_L( "EVP Digest Cleanup failed.");
        return LS_FAIL;
    }
#endif    
    else if ( SSL_CTX_set_session_id_context(pCtx, buf, len) != 1 )
    {
        LS_DBG_L( "Set Session Id Context failed.");
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


/*
 * return: -1 if cert NULL, 0 on fail, 1 on success
 */
int SslUtil::loadCert(SSL_CTX *pCtx, void *pCert, int iCertLen)
{
    BIO *in;
    X509 *cert = NULL;
    int ret;
    unsigned int digestlen;
    unsigned char digest[EVP_MAX_MD_SIZE];

    in = BIO_new_mem_buf(pCert, iCertLen);
    cert = PEM_read_bio_X509(in, NULL, 0, NULL);
    BIO_free(in);
    if (!cert)
        return -1;
    if (( ret = SSL_CTX_use_certificate(pCtx, cert)) == 1 )
    {
        if ( X509_digest(cert, EVP_sha1(), digest, &digestlen) == 0)
            LS_DBG_L("Creating cert digest failed");
        else if (digestIdContext(pCtx, digest, digestlen) != LS_OK)
            LS_DBG_L("Digest id context failed");
    }
    X509_free(cert);
    return ret;
}

/*
 * return: -1 if key NULL, 0 if SSL_CTX_use_PrivateKey fails, > 1 on success (len per EVP_PKEY_bits)
 */
int SslUtil::loadPrivateKey(SSL_CTX *pCtx, void *pKey, int iKeyLen)
{
    BIO *in;
    EVP_PKEY *key = NULL;
    int ret, len;

    in = BIO_new_mem_buf(pKey, iKeyLen);
    key = PEM_read_bio_PrivateKey(in, NULL, 0, NULL);
    BIO_free(in);
    if (!key)
        return -1;
    len = EVP_PKEY_bits(key);
    ret = SSL_CTX_use_PrivateKey(pCtx, key);
    EVP_PKEY_free(key);
    if (ret != 1)
        return ret;
    return len;
}


int SslUtil::loadCertFile(SSL_CTX *pCtx, const char *pFile, int type)
{
    char *pBegin,  buf[SSLUTIL_MAX_CERT_LENGTH];
    int len;

    /* THIS FILE TYPE WILL NOT BE HANDLED HERE.
     * Just left this here in case of future implementation.*/
    if (translateType(type) == SSL_FILETYPE_ASN1)
        return -1;

    len = loadPemWithMissingDash(pFile, buf, SSLUTIL_MAX_CERT_LENGTH, &pBegin);
    if (len == -1)
        return -1;

    return loadCert(pCtx, pBegin, len);
}

int SslUtil::loadPrivateKeyFile(SSL_CTX *pCtx, const char *pFile, int type)
{
    char *pBegin,  buf[SSLUTIL_MAX_CERT_LENGTH];
    int len;

    /* THIS FILE TYPE WILL NOT BE HANDLED HERE.
     * Just left this here in case of future implementation.*/
    if (translateType(type) == SSL_FILETYPE_ASN1)
        return -1;

    len = loadPemWithMissingDash(pFile, buf, SSLUTIL_MAX_CERT_LENGTH, &pBegin);
    if (len == -1)
        return -1;
    return loadPrivateKey(pCtx, pBegin, len);
}


bool SslUtil::loadCA(SSL_CTX *pCtx, const char *pCAFile, const char *pCAPath,
                     int cv)
{
    int ret = SSL_CTX_load_verify_locations(pCtx, pCAFile, pCAPath);
    if ((ret != 0) && cv)
    {
        ret = SSL_CTX_set_default_verify_paths(pCtx);
        STACK_OF(X509_NAME) *pCAList = NULL;
        if (pCAFile)
            pCAList = SSL_load_client_CA_file(pCAFile);
        if (pCAPath)
        {
            if (!pCAList)
                pCAList = sk_X509_NAME_new_null();
            if (!SSL_add_dir_cert_subjects_to_stack(pCAList, pCAPath))
            {
                sk_X509_NAME_free(pCAList);
                pCAList = NULL;
            }
        }
        if (pCAList)
            SSL_CTX_set_client_CA_list(pCtx, pCAList);
    }

    return ret != 0;
}

int SslUtil::initDefaultCA(const char* pCAFile, const char* pCAPath)
{
    int i;

    if (!pCAFile)
    {
        for (i = 0; i < s_iSystems; ++i)
        {
            if (access(s_aSystemFiles[i], F_OK) == 0)
            {
                s_pDefaultCAFile = s_aSystemFiles[i];
                break;
            }
        }
    }
    else
        s_pDefaultCAFile = pCAFile;

    if (!pCAPath)
    {
        for (i = 0; i < s_iSystems; ++i)
        {
            if (access(s_aSystemDirs[i], F_OK) == 0)
            {
                s_pDefaultCAPath = s_aSystemDirs[i];
                break;
            }
        }
    }
    else
        s_pDefaultCAPath = pCAPath;
    return 0;
}

bool SslUtil::loadCA(SSL_CTX *pCtx, const char *pCAbuf)
{

    int ret = 0;
    BIO *in = NULL;
    // int i, count = 0;
    // X509 *x = NULL;

    if (pCAbuf == NULL)
        return (1);
    in = BIO_new(BIO_s_mem());

    if ((in == NULL) || (BIO_write(in, pCAbuf, strlen(pCAbuf)) <= 0)) {
#ifdef OPENSSL_IS_BORINGSSL
        OPENSSL_PUT_ERROR(X509, ERR_R_SYS_LIB);
#else
        X509err(X509_F_X509_LOAD_CERT_FILE, ERR_R_SYS_LIB);
#endif
        // goto err;
        return -1;
    }

    ret = setCertificateChain(pCtx, in);

    BIO_free(in);
    return ret;
}

int SslUtil::setCertificateChain(SSL_CTX *pCtx, BIO * bio)
{
    X509 *x509;
#ifndef OPENSSL_IS_BORINGSSL
    STACK_OF(X509) * pExtraCerts;
#endif
    unsigned long err;
    int n;

#ifndef OPENSSL_IS_BORINGSSL
#if OPENSSL_VERSION_NUMBER >= 0x10100000L
    SSL_CTX_clear_extra_chain_certs(pCtx);
#else                                                   
    pExtraCerts = pCtx->extra_certs;
    if (pExtraCerts != NULL)
    {
        sk_X509_pop_free((STACK_OF(X509) *)pExtraCerts, X509_free);
        pCtx->extra_certs = NULL;
    }
#endif    
#else
    SSL_CTX_clear_extra_chain_certs(pCtx);
#endif
    n = 0;
    while ((x509 = PEM_read_bio_X509(bio, NULL, NULL, NULL)) != NULL)
    {
        if (!SSL_CTX_add_extra_chain_cert(pCtx, x509))
        {
            X509_free(x509);
            return -1;
        }
        n++;
    }
    if ((err = ERR_peek_error()) > 0)
    {
        if (!(ERR_GET_LIB(err) == ERR_LIB_PEM
              && ERR_GET_REASON(err) == PEM_R_NO_START_LINE))
        {
            return -1;
        }
        while (ERR_get_error() > 0) ;
    }
    return n > 0;
}


static void SslConnection_ssl_info_cb(const SSL *pSSL, int where, int ret)
{
    SslConnection *pConnection = (SslConnection *)SSL_get_ex_data(pSSL,
                                                SslConnection::getConnIdx());
    if ((where & SSL_CB_HANDSHAKE_START) && pConnection->getFlag() == 1)
    {
        close(SSL_get_fd(pSSL));
#ifndef OPENSSL_IS_BORINGSSL
#if OPENSSL_VERSION_NUMBER >= 0x10100000L
        SSLerr(SSL_F_SSL_DO_HANDSHAKE, SSL_R_SSL_HANDSHAKE_FAILURE);
#else
        ((SSL *)pSSL)->error_code = SSL_R_SSL_HANDSHAKE_FAILURE;
#endif        
#else
        OPENSSL_PUT_ERROR(SSL, SSL_R_SSL_HANDSHAKE_FAILURE);
#endif
        return ;
    }

    if ((where & SSL_CB_HANDSHAKE_DONE) != 0)
    {
#ifdef SSL3_FLAGS_NO_RENEGOTIATE_CIPHERS
#if OPENSSL_VERSION_NUMBER >= 0x10100000L
#ifndef SSL_OP_NO_RENEGOTIATION
#define SSL_OP_NO_RENEGOTIATION 0x40000000U /* Requires 1.1.0h or later library */
#endif
        SSL_set_options((SSL *)pSSL, SSL_OP_NO_RENEGOTIATION);
#else        
        pSSL->s3->flags |= SSL3_FLAGS_NO_RENEGOTIATE_CIPHERS;
#endif        
#endif
        pConnection->setFlag(1);
    }
}


void SslUtil::initCtx(SSL_CTX *pCtx, int method, char renegProtect)
{
#ifdef SSL_OP_NO_COMPRESSION
    /* OpenSSL >= 1.0 only */
    SSL_CTX_set_options(pCtx, SSL_OP_NO_COMPRESSION);
#endif
    setOptions(pCtx, SSL_OP_SINGLE_DH_USE | SSL_OP_ALL);
    //setOptions( SSL_OP_NO_SSLv2 );
    updateProtocol(pCtx, method);

    setOptions(pCtx, SSL_OP_CIPHER_SERVER_PREFERENCE);

    SSL_CTX_set_mode(pCtx, SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER
#ifdef SSL_MODE_RELEASE_BUFFERS
                        | SSL_MODE_RELEASE_BUFFERS
#endif
                    );

    if (renegProtect)
    {
        setOptions(pCtx, SSL_OP_NO_SESSION_RESUMPTION_ON_RENEGOTIATION);
        SSL_CTX_set_info_callback(pCtx, SslConnection_ssl_info_cb);
    }
#ifdef OPENSSL_IS_BORINGSSL
    SSL_CTX_set_early_data_enabled(pCtx, 1);
#endif // OPENSSL_IS_BORINGSSL

}


long SslUtil::setOptions(SSL_CTX *pCtx, long options)
{
    return SSL_CTX_set_options(pCtx, options);
}


long SslUtil::getOptions(SSL_CTX *pCtx)
{
    return SSL_CTX_get_options(pCtx);
}


int SslUtil::setCipherList(SSL_CTX *pCtx, const char *pList)
{
    char cipher[4096];

    if (!pList || !*pList || (strncasecmp(pList, "ALL:", 4) == 0)
        || (strncasecmp(pList, "SSLv3:", 6) == 0)
        || (strncasecmp(pList, "TLSv1:", 6) == 0))
    {
        //snprintf( cipher, 4095, "RC4:%s", pList );
        //strcpy( cipher, "ALL:HIGH:!aNULL:!SSLV2:!eNULL" );
#if OPENSSL_VERSION_NUMBER >= 0x10001000L
        strcpy(cipher, "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:"
               "ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:"
               "DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:"
               "kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:"
               "ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:"
               "ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:"
               "ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:"
               "ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:"
               "DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:"
               "DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:"
               "DHE-RSA-AES256-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:"
               "AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:"
               "CAMELLIA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:"
               "!MD5:!PSK:!aECDH"
              );
//         strcpy( cipher, "EECDH+ECDSA+AESGCM EECDH+aRSA+AESGCM EECDH+ECDSA+SHA384 "
//                         "EECDH+ECDSA+SHA256 EECDH+aRSA+SHA384 EECDH+aRSA+SHA256 "
//                         "EECDH+aRSA+RC4 EECDH EDH+aRSA RC4 !aNULL !eNULL !LOW "
//                         "!3DES !MD5 !SSLv2 !EXP !PSK !SRP "
//                         "!DSSTLS_ECDHE_RSA_WITH_AES_128_CBC_SHA:"
//                 );

//             strcpy( cipher, "ECDHE-RSA-AES128-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA128:"
//                             "DHE-RSA-AES128-GCM-SHA384:DHE-RSA-AES128-GCM-SHA128:"
//                             "ECDHE-RSA-AES128-SHA384:ECDHE-RSA-AES128-SHA128:"
//                             "ECDHE-RSA-AES128-SHA:ECDHE-RSA-AES128-SHA:"
//                             "DHE-RSA-AES128-SHA128:DHE-RSA-AES128-SHA128:"
//                             "DHE-RSA-AES128-SHA:DHE-RSA-AES128-SHA:ECDHE-RSA-DES-CBC3-SHA"
//                             ":EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA384:AES128-GCM-SHA128:"
//                             "AES128-SHA128:AES128-SHA128:AES128-SHA:AES128-SHA:"
//                             "DES-CBC3-SHA:HIGH:!aNULL:!eNULL:!EXPORT:!DES:!MD5:!PSK:!RC4"
//                     );
        //strcpy( cipher, "HIGH:!MD5:!aNULL:!EDH@strength" );
#else
        strcpy(cipher,
               "RC4:HIGH:!aNULL:!MD5:!SSLv2:!eNULL:!EDH:!LOW:!EXPORT56:!EXPORT40");

#endif
        //strcpy( cipher, "RC4:-EXP:-SSLv2:-ADH" );
        pList = cipher;
    }
    else
    {
        const char *pBegin = pList;
        const char *p;
        while((p = strpbrk(pBegin, ": ")) != NULL
              && ((memmem(pBegin, p - pBegin, "CHACHA", 6) != NULL)
               || (memmem(pBegin, p - pBegin, "chacha", 6) != NULL)))
        {
            pBegin = p + 1;
        }
        if (!p || strncasecmp(pList, "ECDHE", 5) != 0
            || memmem(pList, p - pList, "GCM", 3) == NULL)
        {
            if (!p)
                p = ":";
            snprintf(cipher, 4095, "%.*sECDHE-ECDSA-AES128-GCM-SHA256%c"
                     "ECDHE-RSA-AES128-GCM-SHA256%c%s",
                     (int)(pBegin - pList), pList, *p, *p, pBegin);
            pList = cipher;
        }
    }

    LS_DBG_L( "[SSL] set ciphers to %s", pList );
    return SSL_CTX_set_cipher_list(pCtx, pList) == 1;
}


void SslUtil::updateProtocol(SSL_CTX *pCtx, int method)
{
    setOptions(pCtx, SSL_OP_NO_SSLv2);
    if (!(method & SslContext::SSL_v3))
        setOptions(pCtx, SSL_OP_NO_SSLv3);
    if (!(method & SslContext::SSL_TLSv1))
        setOptions(pCtx, SSL_OP_NO_TLSv1);
#ifdef SSL_OP_NO_TLSv1_1
    if (!(method & SslContext::SSL_TLSv11))
        setOptions(pCtx, SSL_OP_NO_TLSv1_1);
#endif
#ifdef SSL_OP_NO_TLSv1_2
    if (!(method & SslContext::SSL_TLSv12))
        setOptions(pCtx, SSL_OP_NO_TLSv1_2);
#endif

#ifdef TLS1_3_VERSION
    if (method & SslContext::SSL_TLSv13)
#ifdef OPENSSL_IS_BORINGSSL
        SSL_CTX_set_max_proto_version(pCtx, TLS1_3_VERSION);
#else
        SSL_CTX_set_max_version(pCtx, TLS1_3_VERSION);
#endif
#endif

#ifdef SSL_OP_NO_TLSv1_3
    if (!(method & SslContext::SSL_TLSv13))
        setOptions(pCtx, SSL_OP_NO_TLSv1_3);
#endif
}


int  SslUtil::enableShmSessionCache(SSL_CTX *pCtx)
{
    if (!SslSessCache::getInstance().isReady())
    {
        LS_WARN("FAILED TO ENABLE SHM SSL CACHE. SERVER DID NOT INITIALIZE");
        return LS_OK;
    }

    SSL_CTX_set_session_cache_mode(pCtx, SSL_SESS_CACHE_SERVER
                                            | SSL_SESS_CACHE_NO_INTERNAL);
    /* enable external cache configuration check */
    SslSessCache::watchCtx(pCtx);
    LS_DBG_L("EXTERNAL SHM SSL CACHE ENABLED");
    return LS_OK;
}


/* Note from Kevin: This file was ported from lsr project.
 * Currently only need default CA file/path, but in future will need to change
 * SslTicket so that this works.
int SslUtil::enableSessionTickets(SSL_CTX *pCtx)
{
    if (SslTicket::isKeyStoreEnabled())
        SSL_CTX_set_tlsext_ticket_key_cb(pCtx, SslTicket::ticketCb);
    return 0;
}
*/


void SslUtil::disableSessionTickets(SSL_CTX *pCtx)
{
    long options = SSL_CTX_get_options(pCtx);
    SSL_CTX_set_options(pCtx, options | SSL_OP_NO_TICKET);
}


static int bioToBuf(BIO *pBio, AutoBuf *pBuf)
{
    int len, written;
    len = BIO_number_written(pBio);
    pBuf->reserve(pBuf->size() + len + 1);
    written = BIO_read(pBio, pBuf->end(), len);

    if (written <= 0)
    {
        if (!BIO_should_retry(pBio))
            return -1;
        written = BIO_read(pBio, pBuf->end(), len);
        if (written <= 0)
            return -1;
    }
    if (written != len)
        return -1;

    pBuf->used(written - 1); // - 1 to get rid of extra newline.
    return written;
}

int  SslUtil::getPrivateKeyPem(SSL_CTX *pCtx, AutoBuf *pBuf)
{
    int ret = -1;
    BIO *pOut = BIO_new(BIO_s_mem());
    EVP_PKEY *pKey = SSL_CTX_get0_privatekey(pCtx);

    if (PEM_write_bio_PrivateKey(pOut, pKey, NULL, NULL, 0, NULL, NULL))
        ret = bioToBuf(pOut, pBuf);
    BIO_free(pOut);
    return ret;
}

int  SslUtil::getCertPem(SSL_CTX *pCtx, AutoBuf *pBuf)
{
    int ret = -1;
    BIO *pOut = BIO_new(BIO_s_mem());
    X509 *pCert = SSL_CTX_get0_certificate(pCtx);

    if (PEM_write_bio_X509(pOut, pCert))
        ret = bioToBuf(pOut, pBuf);
    BIO_free(pOut);
    return ret;
}

int  SslUtil::getCertChainPem(SSL_CTX *pCtx, AutoBuf *pBuf)
{
    int i, cnt, ret = -1;
    X509 *pCert;
    STACK_OF(X509) *pChain;
    BIO *pOut = BIO_new(BIO_s_mem());

    if (!SSL_CTX_get_extra_chain_certs(pCtx, &pChain))
    {
        return 0;
    }
    else if (NULL == pChain)
    {
        return 0;
    }
    cnt = sk_X509_num(pChain);

    for (i = 0; i < cnt; ++i)
    {
        pCert = sk_X509_value(pChain, i);
        if (PEM_write_bio_X509(pOut, pCert))
            ret = bioToBuf(pOut, pBuf);
        BIO_free(pOut);
    }
    return ret;
}

