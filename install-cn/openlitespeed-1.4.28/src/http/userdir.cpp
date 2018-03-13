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
#include "userdir.h"

#include <http/htpasswd.h>
#include <http/httpstatuscode.h>
#include <util/datetime.h>
#include <util/pool.h>

#if !defined( __FreeBSD__ ) && \
    !defined(macintosh) && !defined(__APPLE__) && !defined(__APPLE_CC__)

#include <crypt.h>
#else
#include <unistd.h>
#endif
#include <openssl/md5.h>
#include <openssl/sha.h>
#include <string.h>



UserDir::~UserDir()
{
    if (m_pCacheUser)
    {
        m_pCacheUser->release_objects();
        delete m_pCacheUser;
    }
    if (m_pCacheGroup)
    {
        m_pCacheGroup->release_objects();
        delete m_pCacheGroup;
    }
    if (m_pName)
        Pool::deallocate2(m_pName);
}


void UserDir::setName(const char *pName)
{
    if (m_pName)
        Pool::deallocate2(m_pName);
    m_pName = Pool::dupstr(pName);
}


const AuthUser *UserDir::getUserIfMatchGroup(HttpSession *pSession,
        const char *pUser,
        int userLen, const StringList *pReqGroups, int *ready)
{
    if (!pReqGroups)
        return NULL;
    AuthUser *pData = (AuthUser *)getUser(pSession, pUser, userLen, ready);
    if (pData && pData->getGroups())
    {
        StringList::const_iterator iter = pReqGroups->begin();
        while (iter != pReqGroups->end())
        {
            if (pData->getGroups()->bfind((*iter)->c_str()))
                return pData;
            ++iter;
        }
    }
    if (m_pCacheGroup)
    {
        const StringList *pGroup;
        StringList::const_iterator iter = pReqGroups->begin();
        while (iter != pReqGroups->end())
        {
            pGroup = (const AuthGroup *)(getGroup(pSession,
                                                  (*iter)->c_str(), (*iter)->len(), ready));
            if (pGroup)
            {
                if (pGroup->bfind(pUser))
                    return pData;
            }
            ++iter;
        }
    }
    return NULL;
}


void UserDir::setUserCache(HashDataCache *pCache)
{
    if (m_pCacheUser)
    {
        if (pCache != m_pCacheUser)
            delete m_pCacheUser;
    }
    m_pCacheUser = pCache;

}


void UserDir::setGroupCache(HashDataCache *pCache)
{
    if (m_pCacheGroup)
    {
        if (pCache != m_pCacheGroup)
            delete m_pCacheGroup;
    }
    m_pCacheGroup = pCache;
}


const AuthUser *UserDir::getRequiredUser(HttpSession *pSession,
        const char  *pUser, int userLen,
        const AuthRequired *pRequired, int *ready)
{
    int type = AuthRequired::REQ_DEFAULT;
    if (pRequired)
        type = pRequired->getType();

    switch (type)
    {
    case AuthRequired::REQ_USER:
        if (pRequired->find(pUser) == NULL)
            return NULL;
    //fall through
    case AuthRequired::REQ_DEFAULT:
        return getUser(pSession, pUser, userLen, ready);
    case AuthRequired::REQ_GROUP:
        return getUserIfMatchGroup(pSession, pUser, userLen,
                                   pRequired->getList(), ready);

    case AuthRequired::REQ_FILE_OWNER:
    case AuthRequired::REQ_FILE_GROUP:
    default:
        break;
    }
    return NULL;
}


const AuthUser *UserDir::getUser(HttpSession *pSession,
                                 HashDataCache *pCache,
                                 const char *pKey, int len, int *ready)
{
    AuthUser *pUser;
    HashDataCache::const_iterator iter;
    iter = pCache->find(pKey);
    if (iter != pCache->end())
    {
        pUser = (AuthUser *)iter.second();
        if (pUser)
        {
            if (pUser->getTimestamp() + pCache->getExpire() > DateTime::s_curTime)
                return pUser;
            if (!isUserStoreChanged(pUser->getTimestamp()))
            {
                pUser->setTimestamp(DateTime::s_curTime);
                return pUser;
            }
            else
            {
                pCache->erase(iter);
                delete pUser;
            }
        }
    }
    pUser = getUserFromStore(pSession, pCache, pKey, len, ready);
    if (*ready == -1)
        return NULL;
    if (*ready > 0)
        return NULL;
    if (!pUser)
    {
        pUser = new AuthUser();
        if (!pUser)
            return NULL;
        pUser->setKey(pKey, len);
        pUser->setExist(0);
    }
    else
    {
        if (pUser->getEncMethod() == ENCRYPT_PLAIN)
            pUser->updatePasswdEncMethod();
    }
    pUser->setTimestamp(DateTime::s_curTime);
    if (pCache->insert(pUser->getKey(), pUser) == pCache->end())
    {
        delete pUser;
        pUser = NULL;
    }
    return pUser;

}


const StringList *UserDir::getGroup(HttpSession *pSession,
                                    HashDataCache *pCache, const char *pKey,
                                    int len, int *ready)
{
    AuthGroup *pGroup;
    HashDataCache::const_iterator iter;
    iter = pCache->find(pKey);
    if (iter != pCache->end())
    {
        pGroup = (AuthGroup *)iter.second();
        if (pGroup)
        {
            if (pGroup->getTimestamp() + pCache->getExpire() > DateTime::s_curTime)
                return pGroup;
            if (!isGroupStoreChanged(pGroup->getTimestamp()))
            {
                pGroup->setTimestamp(DateTime::s_curTime);
                return pGroup;
            }
            else
            {
                pCache->erase(iter);
                delete pGroup;
            }
        }
    }
    pGroup = getGroupFromStore(pSession, pCache, pKey, len, ready);
    if (*ready == -1)
        return NULL;
    if (*ready > 0)
        return NULL;
    if (!pGroup)
    {
        pGroup = new AuthGroup();
        if (!pGroup)
            return NULL;
        pGroup->setKey(pKey, len);
        pGroup->setExist(0);
    }
    pGroup->setTimestamp(DateTime::s_curTime);
    if (pCache->insert(pGroup->getKey(), pGroup) == pCache->end())
    {
        delete pGroup;
        pGroup = NULL;
    }
    return pGroup;

}


static int verifyMD5(const char *pStored, const char *pPasswd, int seeded)
{
    unsigned char achHash[MD5_DIGEST_LENGTH];
    MD5_CTX ctx;

    MD5_Init(&ctx);
    MD5_Update(&ctx, pPasswd, strlen(pPasswd));
    if (seeded)
        MD5_Update(&ctx, pStored + MD5_DIGEST_LENGTH, 4);
    MD5_Final(achHash, &ctx);
    return memcmp(achHash, pStored, MD5_DIGEST_LENGTH);
}


static int verifySHA(const char *pStored, const char *pPasswd, int seeded)
{
    SHA_CTX c;
    unsigned char m[SHA_DIGEST_LENGTH];

    SHA1_Init(&c);
    SHA1_Update(&c, pPasswd, strlen(pPasswd));
    if (seeded)
        SHA1_Update(&c, pStored + SHA_DIGEST_LENGTH, 4);
    SHA1_Final(m, &c);
    return memcmp(m, pStored, SHA_DIGEST_LENGTH);
}


void ApTo64(char *s, unsigned long v, int n)
{
    static unsigned char itoa64[] =         /* 0 ... 63 => ASCII - 64 */
        "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";

    while (--n >= 0)
    {
        *s++ = itoa64[v & 0x3f];
        v >>= 6;
    }
}


void ApMD5Encode(const unsigned char *pw,
                 const unsigned char *sp, int sl,
                 char *result)
{

    char *p;
    unsigned char final[16];
    int i;
    int pl;
    unsigned int pwlen;
    MD5_CTX ctx, ctx1;
    unsigned long l;

    MD5_Init(&ctx);

    pwlen = strlen((char *)pw);
    MD5_Update(&ctx, pw, pwlen);
    MD5_Update(&ctx, sp, sl);

    MD5_Init(&ctx1);
    MD5_Update(&ctx1, pw, pwlen);
    MD5_Update(&ctx1, sp + 6, sl - 6);
    MD5_Update(&ctx1, pw, pwlen);
    MD5_Final(final, &ctx1);
    for (pl = pwlen; pl > 0; pl -= 16)
        MD5_Update(&ctx, final, (pl > 16) ? 16 : (unsigned int) pl);

    /*
     * Don't leave anything around in vm they could use.
     */
    memset(final, 0, sizeof(final));

    /*
     * Then something really weird...
     */
    for (i = pwlen; i != 0; i >>= 1)
    {
        if (i & 1)
            MD5_Update(&ctx, final, 1);
        else
            MD5_Update(&ctx, pw, 1);
    }

    MD5_Final(final, &ctx);

    for (i = 0; i < 1000; i++)
    {
        MD5_Init(&ctx1);
        if (i & 1)
            MD5_Update(&ctx1, pw, pwlen);
        else
            MD5_Update(&ctx1, final, 16);
        if (i % 3)
            MD5_Update(&ctx1, sp + 6, sl - 6);

        if (i % 7)
            MD5_Update(&ctx1, pw, pwlen);

        if (i & 1)
            MD5_Update(&ctx1, final, 16);
        else
            MD5_Update(&ctx1, pw, pwlen);
        MD5_Final(final, &ctx1);
    }

    p = result;

    l = (final[ 0] << 16) | (final[ 6] << 8) | final[12];
    ApTo64(p, l, 4);
    p += 4;
    l = (final[ 1] << 16) | (final[ 7] << 8) | final[13];
    ApTo64(p, l, 4);
    p += 4;
    l = (final[ 2] << 16) | (final[ 8] << 8) | final[14];
    ApTo64(p, l, 4);
    p += 4;
    l = (final[ 3] << 16) | (final[ 9] << 8) | final[15];
    ApTo64(p, l, 4);
    p += 4;
    l = (final[ 4] << 16) | (final[10] << 8) | final[ 5];
    ApTo64(p, l, 4);
    p += 4;
    l =                    final[11]                ;
    ApTo64(p, l, 2);
    p += 2;
    *p = '\0';

    /*
     * Don't leave anything around in vm they could use.
     */
    memset(final, 0, sizeof(final));

}


static int verifyApMD5(const char *pStored, const char *pPasswd)
{
    char result[120];
    const char *pSaltEnd = strchr(pStored + 6, '$');
    if (!pSaltEnd)
        pSaltEnd = pStored + 14;

    ApMD5Encode((const unsigned char *)pPasswd,
                (const unsigned char *)pStored, pSaltEnd - pStored,
                result);

    return memcmp(result, pSaltEnd + 1, 22);
}


int UserDir::authenticate(HttpSession *pSession, const char *pUserName,
                          int len,
                          const char *pPasswd, int encryptMethod,
                          const AuthRequired *pRequired)
{
    int ready = 0;
    const AuthUser *pUser = getRequiredUser(pSession, pUserName, len,
                                            pRequired, &ready);
    if (ready != 0)
        return ready;
    if (!pUser || !pUser->isExist())
        return SC_401;
    const char *pStored = pUser->getPasswd();
//    if (( encryptMethod == m_encryptMethod )||
//        ( m_encryptMethod == AuthUser::ENCRYPT_UNKNOWN ))
    if (pStored)
    {
        switch (pUser->getEncMethod())
        {
        case ENCRYPT_UNKNOWN:
        case ENCRYPT_PLAIN:
            if (strcmp(pPasswd, pUser->getPasswd()) == 0)
                return 0;
        //fall through
        case ENCRYPT_CRYPT:
            if (strcmp(pStored, crypt(pPasswd, pStored)) == 0)
                return 0;
            break;
        case ENCRYPT_MD5:
            if (verifyMD5(pStored, pPasswd, 0) == 0)
                return 0;
            break;
        case ENCRYPT_APMD5:
            if (verifyApMD5(pStored, pPasswd) == 0)
                return 0;
            break;
        case ENCRYPT_SHA:
            if (verifySHA(pStored, pPasswd, 0) == 0)
                return 0;
            break;
        case ENCRYPT_SMD5:
            if (verifyMD5(pStored, pPasswd, 1) == 0)
                return 0;
            break;
        case ENCRYPT_SSHA:
            if (verifySHA(pStored, pPasswd, 1) == 0)
                return 0;
            break;
        }
    }
    return SC_401;
}


void UserDir::onTimer()
{
    //TODO: to be done
}


AuthRequired::AuthRequired()
    : m_iRequiredType(REQ_VALID_USER)
    , m_pRequired(NULL)
{}


AuthRequired::~AuthRequired()
{
    if (m_pRequired)
        delete m_pRequired;
}


int AuthRequired::parse(const char *pRequired)
{
    static const char *keywords[5] = { "valid-user", "user", "group", "file-owner", "file-group" };
    static int          keywordLen[5] = { 10, 4, 5, 10, 10 };
    while ((*pRequired == ' ') || (*pRequired == '\t'))
        ++pRequired;
    const char *pEnd = pRequired + strlen(pRequired);
    if (m_pRequired)
    {
        delete m_pRequired;
        m_pRequired = NULL;
    }
    m_iRequiredType = REQ_DEFAULT;
    for (int i = 0; i < 5; ++i)
    {
        if (strncasecmp(pRequired, keywords[i], keywordLen[i]) == 0)
        {
            char ch;
            pRequired += keywordLen[i];
            if (((ch = *pRequired++) == ' ') || (!ch) || (ch == '\t'))
            {
                m_iRequiredType = i;
                break;
            }
            else
                return LS_FAIL;
        }
    }
    if ((m_iRequiredType == REQ_USER) || (m_iRequiredType == REQ_GROUP))
    {
        m_pRequired = new StringList();
        int size = m_pRequired->split(pRequired, pEnd, " ,");
        if (size > 1)
            m_pRequired->sort();
    }
    return 0;
}


const AutoStr2 *AuthRequired::find(const char *p) const
{
    if (m_pRequired)
        return m_pRequired->bfind(p);
    return NULL;
}


PlainFileUserDir::PlainFileUserDir()
    : m_pUserStore(NULL)
    , m_pGroupStore(NULL)
{
}


PlainFileUserDir::~PlainFileUserDir()
{
    if (m_pUserStore)
        delete m_pUserStore;
    if (m_pGroupStore)
        delete m_pGroupStore;
}


int PlainFileUserDir::setDataStore(const char *pFile, const char *pGroup)
{
    m_pUserStore = new PasswdFile();
    HashDataCache *pCache = new HashDataCache();
    setUserCache(pCache);
    if (!m_pUserStore || !pCache)
        return LS_FAIL;
    m_pUserStore->setDataStoreURI(pFile);
    if (pGroup)
    {
        pCache = new HashDataCache();
        setGroupCache(pCache);
        m_pGroupStore = new GroupFile();
        if (!m_pGroupStore || !pCache)
            return LS_FAIL;
        m_pGroupStore->setDataStoreURI(pGroup);
    }
    return 0;
}

