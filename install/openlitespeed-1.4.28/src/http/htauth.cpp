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
#include "htauth.h"

#include <http/authuser.h>
#include <http/httprespheaders.h>
#include <http/httpstatuscode.h>
#include <http/userdir.h>
#include <lsr/ls_base64.h>
#include <lsr/ls_strtool.h>
#include <util/pool.h>
#include <util/stringlist.h>
#include <util/stringtool.h>

#include <openssl/md5.h>

#include <assert.h>
#include <ctype.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

HTAuth::HTAuth()
    : m_pName(NULL)
    , m_authHeader(NULL)
    , m_authHeaderLen(0)
    , m_pUserDir(NULL)
    , m_iAuthType(AUTH_DEFAULT)
{
}


HTAuth::HTAuth(const char *pRealm)
    : m_pName(NULL)
    , m_authHeader(NULL)
    , m_authHeaderLen(0)
    , m_pUserDir(NULL)
    , m_iAuthType(AUTH_DEFAULT)
{}


HTAuth::~HTAuth()
{
    if (m_pName)
        Pool::deallocate2(m_pName);
    if (m_authHeader)
        Pool::deallocate2(m_authHeader);
}


void HTAuth::setName(const char *pName)
{
    m_pName = (char *)Pool::dupstr(pName);
    buildWWWAuthHeader(pName);
}


int HTAuth::buildWWWAuthHeader(const char *pName)
{
    if (m_iAuthType & AUTH_DIGEST)
    {
        m_authHeader = (char *)Pool::dupstr(pName);
        return 0;
    }
    else if (m_iAuthType & AUTH_BASIC)
    {
        int len = strlen(pName) + 40;

        m_authHeader = (char *)Pool::reallocate2(m_authHeader, len);
        if (m_authHeader)
        {
            m_authHeaderLen = ls_snprintf(m_authHeader, len,
                                          "Basic realm=\"%s\"", pName);
            return 0;
        }
    }
    return LS_FAIL;
}


int HTAuth::addWWWAuthHeader(HttpRespHeaders &buf) const
{
    if (m_iAuthType & AUTH_BASIC)
        buf.add(HttpRespHeaders::H_WWW_AUTHENTICATE, m_authHeader,
                m_authHeaderLen);
    else if (m_iAuthType & AUTH_DIGEST)
    {
        char sTemp[256] = {0};
        int n = ls_snprintf(sTemp, 255, "Digest realm=\"%s\" nonce=\"%lu\"\r\n",
                            m_authHeader, time(NULL));

        buf.add(HttpRespHeaders::H_WWW_AUTHENTICATE, sTemp, n);
    }
    return 0;
}


#define MAX_PASSWD_LEN      128
#define MAX_BASIC_AUTH_LEN  256
#define MAX_DIGEST_AUTH_LEN  4096


int HTAuth::basicAuth(HttpSession *pSession, const char *pAuthorization,
                      int size,
                      char *pAuthUser, int bufLen,
                      const AuthRequired *pRequired) const
{

    char buf[MAX_BASIC_AUTH_LEN];
    char *pUser = buf;
    int ret = ls_base64_decode(pAuthorization, size, pUser);
    if (ret == -1)
        return SC_401;
    while (isspace(*pUser))
        ++pUser;
    if (*pUser == ':')
        return SC_401;
    char *passReq = strchr(pUser + 1, ':');
    if (passReq == NULL)
        return SC_401;
    char *p = passReq++;
    while (isspace(p[-1]))
        --p;
    *p = 0;
    int userLen = p - pUser;
    memccpy(pAuthUser, pUser, 0, bufLen - 1);
    *(pAuthUser + bufLen - 1) = 0;

    while (isspace(*passReq))
        ++passReq;
    p = (char *)buf + ret;
    if (passReq >= p)
        return SC_401;
    while ((p > passReq) && isspace(p[-1]))
        --p;
    *p = 0;
    ret = m_pUserDir->authenticate(pSession, pUser, userLen, passReq,
                                   ENCRYPT_PLAIN,
                                   pRequired);
    return ret;
}


//enum
//{
//    DIGEST_USERNAME,
//    DIGEST_REALM,
//    DIGEST_NONCE,
//    DIGEST_URI,
//    DIGEST_QOP,
//    DIGEST_NC,
//    DIGEST_CNONCE,
//    DIGEST_RESPONSE,
//    DIGEST_OPAQUE,
//    DIGEST_ALGORITHM,
//};


int HTAuth::digestAuth(HttpSession *pSession, const char *pAuthorization,
                       int size, char *pAuthUser, int bufLen,
                       const AuthRequired *pRequired) const
{
    const char     *username = NULL;
    int             username_len = 0;
    const char     *realm = NULL;
    const char     *nonce = NULL;
    const char     *requri = NULL;
    const char     *resp_digest = NULL;
    const char *p = pAuthorization;
    const char *pEnd = p + size;
    const char *pNameEnd;
    const char *pNameBegin;
    const char *pValueBegin;
    const char *pValueEnd;
    while (p < pEnd)
    {
        pNameEnd = strchr(p, '=');
        if (!pNameEnd)
            break;
        pNameBegin = p;
        p = pNameEnd + 1;
        while (isspace(pNameEnd[-1]))
            --pNameEnd;

        while (isspace(*p))
            ++p;
        pValueBegin = p;
        if (*p == '"')
        {
            ++pValueBegin;
            pValueEnd = strchr(p, '"');
            if (!pValueEnd)
                break;
            p = pValueEnd + 1;
            while (isspace(*p) || (*p == ','))
                ++p;
        }
        else
        {
            pValueEnd = strchr(p, ',');
            if (pValueEnd)
            {
                p = pValueEnd + 1;
                while (isspace(*p))
                    ++p;
            }
            else
                p = pValueEnd = pEnd;
        }
        if (strncasecmp(pNameBegin, "username", 8) == 0)
        {
            username = pValueBegin;
            username_len = pValueEnd - pValueBegin;
        }
        else if (strncasecmp(pNameBegin, "realm", 5) == 0)
            realm = pValueBegin;
        else if (strncasecmp(pNameBegin, "nonce", 5) == 0)
            nonce = pValueBegin;
        else if (strncasecmp(pNameBegin, "uri", 3) == 0)
            requri = pValueBegin;
        else if (strncasecmp(pNameBegin, "response", 8) == 0)
            resp_digest = pValueBegin;
        else if (strncasecmp(pNameBegin, "nc", 2) == 0)
        {

        }
    }
    if ((username) && (username_len < bufLen))
    {
        memccpy(pAuthUser, username, 0, username_len);
        *(pAuthUser + username_len) = 0;

    }
    if ((!username) || (!realm) || (!nonce) || (!requri) || (!resp_digest))
        return SC_401;
//    const AuthUser * pUserData = getUser( pAuthUser, username_len );
//    if ( pUserData )
//    {
//        const char * pPasswd = pUserData->getPasswd();
//        if ( pPasswd )
//        {
//            char achMethod[24];
//            unsigned char achReqHash[16];
//            char achReqHashAsc[33];
//            int methodLen;
//            MD5_CTX md5_request;
//            MD5_Init( &md5_request );
//            MD5_Update( &md5_request, achMethod, methodLen );
//            MD5_Update( &md5_request, requri, requri_len );
//            MD5_Final( achReqHash, &md5_request );
//            StringTool::hex_to_str( (const char *)achReqHash, 16, achReqHashAsc );
//            //fix me
//
//
//        }
//    }
    return SC_401;
}


int HTAuth::authenticate(HttpSession *pSession, const char *pAuthHeader,
                         int authHeaderLen, char *pAuthUser, int userBufLen,
                         const AuthRequired *pRequired) const
{
    if (strncasecmp(pAuthHeader, "Basic ", 6) == 0)
    {
        pAuthHeader += 6;
        authHeaderLen -= 6;
        if (!(m_iAuthType & AUTH_BASIC) || (authHeaderLen > MAX_BASIC_AUTH_LEN))
            return SC_401;
        return basicAuth(pSession, pAuthHeader,
                         authHeaderLen, pAuthUser,
                         AUTH_USER_SIZE - 1, pRequired);
    }
    else if (strncasecmp(pAuthHeader, "Digest ", 7) == 0)
    {
        pAuthHeader += 7;
        authHeaderLen -= 7;
        if (authHeaderLen > MAX_DIGEST_AUTH_LEN)
            return SC_401;
        return digestAuth(pSession, pAuthHeader,
                          authHeaderLen, pAuthUser,
                          AUTH_USER_SIZE - 1, pRequired);
    }
    return SC_401;

}


