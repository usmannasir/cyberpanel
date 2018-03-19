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
#include "sslcontext.h"

#include <log4cxx/logger.h>
#include <main/configctx.h>
#include <sslpp/sslconnection.h>
#include <sslpp/sslerror.h>
#include <sslpp/sslocspstapling.h>
#include <sslpp/sslsesscache.h>
#include <sslpp/sslticket.h>
#include <util/xmlnode.h>

#include <openssl/err.h>
#include <openssl/rand.h>
#include <openssl/ssl.h>

#ifdef OPENSSL_IS_BORINGSSL
#include <openssl/internal.h>
#endif

#include <ctype.h>
#include <fcntl.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>
#include <limits.h>

int     SslContext::s_iEnableMultiCerts = 0;
static char         s_iUseStrongDH = 0;
void SslContext::setUseStrongDH(int use)
{
    s_iUseStrongDH = use;
}

static DH *s_pDHs[3] = {   NULL, NULL, NULL    };


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
        s_pDHs[index]->p = BN_bin2bn(s_dh_p[index], s_dh_p_size[index], NULL);
        s_pDHs[index]->g = BN_bin2bn(dh_g, sizeof(dh_g), NULL);
        if ((s_pDHs[index]->p == NULL) || (s_pDHs[index]->g == NULL))
        {
            DH_free(s_pDHs[index]);
            s_pDHs[index] = NULL;
        }
    }
    return s_pDHs[index];
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
    setOptions(SSL_OP_NO_SSLv2);
    if (!(method & SSL_v3))
        setOptions(SSL_OP_NO_SSLv3);
    if (!(method & SSL_TLSv1))
        setOptions(SSL_OP_NO_TLSv1);
#ifdef SSL_OP_NO_TLSv1_1
    if (!(method & SSL_TLSv11))
        setOptions(SSL_OP_NO_TLSv1_1);
#endif
#ifdef SSL_OP_NO_TLSv1_2
    if (!(method & SSL_TLSv12))
        setOptions(SSL_OP_NO_TLSv1_2);
#endif

#ifdef TLS1_3_VERSION
    if (method & SSL_TLSv13)
#ifdef OPENSSL_IS_BORINGSSL
        SSL_CTX_set_max_proto_version(m_pCtx, TLS1_3_VERSION);
#else
        SSL_CTX_set_max_version(m_pCtx, TLS1_3_VERSION);
#endif
#endif

#ifdef SSL_OP_NO_TLSv1_3
    if (!(method & SSL_TLSv13))
        setOptions(SSL_OP_NO_TLSv1_3);
#endif
    
    
}


int SslContext::initDH(const char *pFile)
{
    DH *pDH = NULL;
    if (pFile)
    {
        BIO *bio;
        if ((bio = BIO_new_file(pFile, "r")) != NULL)
        {
            pDH = PEM_read_bio_DHparams(bio, NULL, NULL, NULL);
            BIO_free(bio);
            SSL_CTX_set_tmp_dh(m_pCtx, pDH);
        }
    }
    if (!pDH)
    {
        if (m_iKeyLen < 1024 || !s_iUseStrongDH)
            m_iKeyLen = 1024;
        pDH = getTmpDhParam(m_iKeyLen);
        if (!pDH)
            return -1;
        SSL_CTX_set_tmp_dh(m_pCtx, pDH);
    }

    SSL_CTX_set_options(m_pCtx, SSL_OP_SINGLE_DH_USE);
    return 0;
}


int SslContext::initECDH()
{
#if OPENSSL_VERSION_NUMBER >= 0x10001000L
#ifndef OPENSSL_NO_ECDH
    EC_KEY *ecdh;
    ecdh = EC_KEY_new_by_curve_name(NID_X9_62_prime256v1);
    if (ecdh == NULL)
        return LS_FAIL;
    SSL_CTX_set_tmp_ecdh(m_pCtx, ecdh);
    EC_KEY_free(ecdh);

    SSL_CTX_set_options(m_pCtx, SSL_OP_SINGLE_ECDH_USE);

#endif
#endif
    return 0;
}

static void SslConnection_ssl_info_cb(const SSL *pSSL, int where, int ret)
{
    SslConnection *pConnection = (SslConnection *)SSL_get_ex_data(pSSL,
                                 SslConnection::getConnIdx());
    if ((where & SSL_CB_HANDSHAKE_START) && pConnection->getFlag() == 1)
    {
        close(SSL_get_fd(pSSL));
#ifndef OPENSSL_IS_BORINGSSL
        ((SSL *)pSSL)->error_code = SSL_R_SSL_HANDSHAKE_FAILURE;
#else
        OPENSSL_PUT_ERROR(SSL, SSL_R_SSL_HANDSHAKE_FAILURE);
#endif
        return ;
    }

    if ((where & SSL_CB_HANDSHAKE_DONE) != 0)
    {
#ifdef SSL3_FLAGS_NO_RENEGOTIATE_CIPHERS
        pSSL->s3->flags |= SSL3_FLAGS_NO_RENEGOTIATE_CIPHERS;
#endif
        pConnection->setFlag(1);
    }
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
    meth = (SSL_METHOD *)SSLv23_method();
    m_pCtx = SSL_CTX_new(meth);
    if (m_pCtx)
    {
#ifdef SSL_OP_NO_COMPRESSION
        /* OpenSSL >= 1.0 only */
        SSL_CTX_set_options(m_pCtx, SSL_OP_NO_COMPRESSION);
#endif
        setOptions(SSL_OP_SINGLE_DH_USE | SSL_OP_ALL);
        //setOptions( SSL_OP_NO_SSLv2 );
        updateProtocol(iMethod);

        setOptions(SSL_OP_CIPHER_SERVER_PREFERENCE);

        SSL_CTX_set_mode(m_pCtx, SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER
#ifdef SSL_MODE_RELEASE_BUFFERS
                         | SSL_MODE_RELEASE_BUFFERS
#endif
                        );
        if (m_iRenegProtect)
        {
            setOptions(SSL_OP_NO_SESSION_RESUMPTION_ON_RENEGOTIATION);
            SSL_CTX_set_info_callback(m_pCtx, SslConnection_ssl_info_cb);
        }

        //initECDH();
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
    seedRand(128);
    return SSL_new(m_pCtx);
}


static int translateType(int type)
{
    switch (type)
    {
    case SslContext::FILETYPE_PEM:
        return SSL_FILETYPE_PEM;
    case SslContext::FILETYPE_ASN1:
        return SSL_FILETYPE_ASN1;
    default:
        return -1;
    }
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


const int MAX_CERT_LENGTH = 40960;


static int loadPemWithMissingDash(const char *pFile, char *buf, int bufLen,
                                  char **pBegin)
{
    int i = 0, fd, iLen;
    char *pEnd, *p;
    struct stat st;

    fd = open(pFile, O_RDONLY);
    if (fd < 0)
        return LS_FAIL;

    if (fstat(fd, &st) < 0)
    {
        close(fd);
        return LS_FAIL;
    }

    iLen = st.st_size;
    if (iLen <= MAX_CERT_LENGTH - 10)
        i = read(fd, buf + 5, iLen);
    close(fd);
    if (i < iLen)
        return LS_FAIL;
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


static int loadCertFile(SSL_CTX *pCtx, const char *pFile, int type)
{
    char *pBegin,  buf[MAX_CERT_LENGTH];
    BIO *in;
    X509 *cert = NULL;
    int len;
    int ret;
    unsigned int digestlen;
    unsigned char digest[EVP_MAX_MD_SIZE];

    /* THIS FILE TYPE WILL NOT BE HANDLED HERE.
     * Just left this here in case of future implementation.*/
    if (translateType(type) == SSL_FILETYPE_ASN1)
        return LS_FAIL;

    len = loadPemWithMissingDash(pFile, buf, MAX_CERT_LENGTH, &pBegin);
    if (len == -1)
        return LS_FAIL;

    in = BIO_new_mem_buf((void *)pBegin, len);
    cert = PEM_read_bio_X509(in, NULL, 0, NULL);
    BIO_free(in);
    if (!cert)
        return LS_FAIL;
    if ((ret = SSL_CTX_use_certificate(pCtx, cert)) == 1)
    {
        if (X509_digest(cert, EVP_sha1(), digest, &digestlen) == 0)
            LS_DBG_L("Creating cert digest failed");
        else if (SslContext::setupIdContext(pCtx, digest, digestlen) != LS_OK)
            LS_DBG_L("Digest id context failed");
    }
    X509_free(cert);
    return ret;
}


int SslContext::setCertificateFile(const char *pFile, int type,
                                   int chained)
{
    int ret;
    if (!pFile)
        return 0;
    ::stat(pFile, &m_stCert);
    if (init(m_iMethod))
        return 0;
    if (chained)
        return SSL_CTX_use_certificate_chain_file(m_pCtx, pFile);
    else
    {
        ret = loadCertFile(m_pCtx, pFile, type);
        if (ret == -1)
            return SSL_CTX_use_certificate_file(m_pCtx, pFile,
                                                translateType(type));
        return ret;
    }
}


int SslContext::setCertificateChainFile(const char *pFile)
{
    BIO *bio;
    X509 *x509;
#ifndef OPENSSL_IS_BORINGSSL
    STACK_OF(X509) * pExtraCerts;
#endif
    unsigned long err;
    int n;

    if ((bio = BIO_new_file(pFile, "r")) == NULL)
        return LS_FAIL;
#ifndef OPENSSL_IS_BORINGSSL
    pExtraCerts = m_pCtx->extra_certs;
    if (pExtraCerts != NULL)
    {
        sk_X509_pop_free((STACK_OF(X509) *)pExtraCerts, X509_free);
        m_pCtx->extra_certs = NULL;
    }
#else
    SSL_CTX_clear_extra_chain_certs(m_pCtx);
#endif
    n = 0;
    while ((x509 = PEM_read_bio_X509(bio, NULL, NULL, NULL)) != NULL)
    {
        if (!SSL_CTX_add_extra_chain_cert(m_pCtx, x509))
        {
            X509_free(x509);
            BIO_free(bio);
            return LS_FAIL;
        }
        n++;
    }
    if ((err = ERR_peek_error()) > 0)
    {
        if (!(ERR_GET_LIB(err) == ERR_LIB_PEM
              && ERR_GET_REASON(err) == PEM_R_NO_START_LINE))
        {
            BIO_free(bio);
            return LS_FAIL;
        }
        while (ERR_get_error() > 0) ;
    }
    //m_sCertfile.setStr( pFile );
    BIO_free(bio);
    return n > 0;
}


int SslContext::setCALocation(const char *pCAFile, const char *pCAPath,
                              int cv)
{
    int ret;
    if (init(m_iMethod))
        return LS_FAIL;
    ret = SSL_CTX_load_verify_locations(m_pCtx, pCAFile, pCAPath);
    if ((ret != 0) && cv)
    {

        //m_sCAfile.setStr( pCAFile );

        ret = SSL_CTX_set_default_verify_paths(m_pCtx);
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
            SSL_CTX_set_client_CA_list(m_pCtx, pCAList);
    }

    return ret;
}


int SslContext::setPrivateKeyFile(const char *pFile, int type)
{
    char *pBegin,  buf[MAX_CERT_LENGTH];
    BIO *in;
    EVP_PKEY *key = NULL;
    int len;
    int ret;

    /* THIS FILE TYPE WILL NOT BE HANDLED HERE.
     * Just left this here in case of future implementation.*/
    if (translateType(type) == SSL_FILETYPE_ASN1)
        return -1;

    len = loadPemWithMissingDash(pFile, buf, MAX_CERT_LENGTH, &pBegin);
    if (len == -1)
        return -1;

    in = BIO_new_mem_buf((void *)pBegin, len);
    key = PEM_read_bio_PrivateKey(in, NULL, 0, NULL);
    BIO_free(in);
    if (!key)
        return -1;
    m_iKeyLen = EVP_PKEY_bits(key);
    ret = SSL_CTX_use_PrivateKey(m_pCtx, key);
    EVP_PKEY_free(key);
    return ret;
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
    char cipher[4096] = {0};

    if (!pList || !*pList || (strncasecmp(pList, "ALL:", 4) == 0)
        || (strncasecmp(pList, "SSLv3:", 6) == 0)
        || (strncasecmp(pList, "TLSv1:", 6) == 0))
    {
        //snprintf( cipher, 4095, "RC4:%s", pList );
        //strcpy( cipher, "ALL:HIGH:!aNULL:!SSLV2:!eNULL" );
#if OPENSSL_VERSION_NUMBER >= 0x10001000L
// #ifdef OPENSSL_IS_BORINGSSL
//         strcpy(cipher, "AES128-GCM-SHA256:CHACHA20-POLY1305-SHA256:X25519-AES128-GCM-SHA256:AES-256-CTR-HMAC-SHA256:ECDHE-RSA-CHACHA20-POLY1305:"
//                  "AES128-SHA256:AES256-SHA256");
//         SSL_CTX_set_max_version(m_pCtx, TLS1_3_VERSION);//  
// #endif //OPENSSL_IS_BORINGSSL
        
        strcat(cipher, "ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:"
               "ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:"
               "DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:"
               "kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:"
               "ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:"
               "ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:"
               "ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:"
               "ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:"
               "DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:"
               "DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:"
               "DHE-RSA-AES256-SHA:"
               "AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:"
               "CAMELLIA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:"
               "!MD5:!PSK:!aECDH"
              );

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
        while ((p = strpbrk(pBegin, ": ")) != NULL
               && ((memmem(pBegin, p - pBegin, "CHACHA", 6) != NULL)
                   || (memmem(pBegin, p - pBegin, "chacha", 6) != NULL)))
            pBegin = p + 1;
        if (!p || strncasecmp(pList, "ECDHE", 5) != 0
            || memmem(pList, p - pList, "GCM", 3) == NULL
            || memmem(pList, p - pList, "SHA384", 6) != NULL)
        {
            if (!p)
                p = ":";
            snprintf(cipher, 4095, "%.*sECDHE-ECDSA-AES128-GCM-SHA256%c"
                     "ECDHE-RSA-AES128-GCM-SHA256%c%s",
                     (int)(pBegin - pList), pList, *p, *p, pBegin);
            pList = cipher;
        }
    }

    
    return SSL_CTX_set_cipher_list(m_pCtx, pList);
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


extern SslContext *VHostMapFindSslContext(void *arg, const char *pName);
static int SslConnection_ssl_servername_cb(SSL *pSSL, int *ad, void *arg)
{
    SSL_CTX *pOldCtx, *pNewCtx;
    const char *servername = SSL_get_servername(pSSL,
                             TLSEXT_NAMETYPE_host_name);
    if (!servername || !*servername)
        return SSL_TLSEXT_ERR_NOACK;
    SslContext *pCtx = VHostMapFindSslContext(arg, servername);
    if (!pCtx)
        return SSL_TLSEXT_ERR_NOACK;
#ifdef OPENSSL_IS_BORINGSSL
    // Check OCSP again when the context needs to be changed.
    pCtx->initOCSP();
#endif
    pOldCtx = SSL_get_SSL_CTX(pSSL);
    pNewCtx = pCtx->get();
    if (pOldCtx == pNewCtx)
        return SSL_TLSEXT_ERR_OK;
    SSL_set_SSL_CTX(pSSL, pNewCtx);
    SSL_set_verify(pSSL, SSL_CTX_get_verify_mode(pNewCtx), NULL);
    SSL_set_verify_depth(pSSL, SSL_CTX_get_verify_depth(pNewCtx));

    SSL_clear_options(pSSL,
                      SSL_get_options(pSSL) & ~SSL_CTX_get_options(pNewCtx));
    // remark: VHost is guaranteed to have NO_TICKET set.
    // If listener has it set, set will not affect it.
    // If listener does not have it set, set will not set it.
    SSL_set_options(pSSL, SSL_CTX_get_options(pNewCtx) & ~SSL_OP_NO_TICKET);

    return SSL_TLSEXT_ERR_OK;
}


int SslContext::initSNI(void *param)
{
#ifdef SSL_TLSEXT_ERR_OK
    SSL_CTX_set_tlsext_servername_callback(m_pCtx,
                                           SslConnection_ssl_servername_cb);
    SSL_CTX_set_tlsext_servername_arg(m_pCtx, param);

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
               1, 31, 30);
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
    EVP_MD_CTX md;
    unsigned int len;
    unsigned char buf[EVP_MAX_MD_SIZE];

    EVP_MD_CTX_init(&md);

    if (EVP_DigestInit_ex(&md, EVP_sha1(), NULL) != 1)
    {
        LS_DBG_L("Init EVP Digest failed.");
        return LS_FAIL;
    }
    else if (EVP_DigestUpdate(&md, pDigest, iDigestLen) != 1)
    {
        LS_DBG_L("Update EVP Digest failed");
        return LS_FAIL;
    }
    else if (EVP_DigestFinal_ex(&md, buf, &len) != 1)
    {
        LS_DBG_L("EVP Digest Final failed.");
        return LS_FAIL;
    }
    else if (EVP_MD_CTX_cleanup(&md) != 1)
    {
        LS_DBG_L("EVP Digest Cleanup failed.");
        return LS_FAIL;
    }
    else if (SSL_CTX_set_session_id_context(pCtx, buf, len) != 1)
    {
        LS_DBG_L("Set Session Id Context failed.");
        return LS_FAIL;
    }
    return LS_OK;
}


int  SslContext::enableShmSessionCache()
{
    if (!SslSessCache::getInstance().isReady())
    {
        LS_WARN("FAILED TO ENABLE SHM SSL CACHE. SERVER DID NOT INITIALIZE");
        return LS_FAIL;
    }

    SSL_CTX_set_session_cache_mode(m_pCtx, SSL_SESS_CACHE_SERVER
                                   | SSL_SESS_CACHE_NO_INTERNAL);
    /* enable external cache configuration check */
    SslSessCache::watchCtx(m_pCtx);
    LS_DBG_L("EXTERNAL SHM SSL CACHE ENABLED");
    return LS_OK;
}


int SslContext::enableSessionTickets()
{
    return SslTicket::getInstance().enableCtx(m_pCtx);
}


void SslContext::disableSessionTickets()
{
    SslTicket::getInstance().disableCtx(m_pCtx);
}



