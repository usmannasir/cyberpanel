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
#ifndef USERDIR_H
#define USERDIR_H



#include <http/authuser.h>
#include <util/hashdatacache.h>

class AutoStr2;
class HttpSession;

class AuthRequired
{
    int         m_iRequiredType;
    StringList *m_pRequired;

    AuthRequired(const AuthRequired &rhs);
    void operator=(const AuthRequired &rhs);

public:

    enum
    {
        REQ_VALID_USER,
        REQ_USER,
        REQ_GROUP,
        REQ_FILE_OWNER,
        REQ_FILE_GROUP,
        REQ_DEFAULT = REQ_VALID_USER
    };

    AuthRequired();
    ~AuthRequired();
    int parse(const char *pRequired);
    const AutoStr2 *find(const char *p) const;
    int         getType() const  {   return m_iRequiredType; }
    StringList *getList() const {   return m_pRequired; }
};


class UserDir
{
    char             *m_pName;
    HashDataCache    *m_pCacheUser;
    HashDataCache    *m_pCacheGroup;
    int               m_encryptMethod;

    UserDir(const UserDir &);
    UserDir &operator=(const UserDir &);


public:
    UserDir()
        : m_pName(NULL)
        , m_pCacheUser(NULL)
        , m_pCacheGroup(NULL)
    {}
    virtual ~UserDir();

    const char *getName() const        {   return m_pName;  }
    void setName(const char *pName);

    void setUserCache(HashDataCache *pCache);
    void setGroupCache(HashDataCache *pCache);

    HashDataCache *getUserCache()  {   return m_pCacheUser;    }
    HashDataCache *getGroupCache() {   return m_pCacheGroup;   }

    virtual int authenticate(HttpSession *pSession, const char *pUser,
                             int nameLen,
                             const char *pPasswd, int encryptMethod,
                             const AuthRequired *pRequired);

    virtual AuthUser *getUserFromStore(HttpSession *pSession,
                                       HashDataCache *pCache,
                                       const char *pUser, int len, int *ready) = 0;
    virtual AuthGroup *getGroupFromStore(HttpSession *pSession,
                                         HashDataCache  *pCache,
                                         const char *pGroup, int len, int *ready) = 0;

    const AuthUser *getRequiredUser(HttpSession *pSession, const char *pUser,
                                    int userLen,
                                    const AuthRequired *pRequired, int *ready);

    const AuthUser *getUserIfMatchGroup(HttpSession *pSession,
                                        const char *pUser, int userLen,
                                        const StringList *m_pReqGroups, int *ready);

    const AuthUser *getUser(HttpSession *pSession,
                            const char *pUser, int len, int *ready)
    {   return getUser(pSession, m_pCacheUser, pUser, len, ready);   }
    const StringList *getGroup(HttpSession *pSession,
                               const char *pGroup, int len, int *ready)
    {   return getGroup(pSession, m_pCacheGroup, pGroup, len, ready);    }
    virtual const AuthUser *getUser(HttpSession *pSession,
                                    HashDataCache *pCache,
                                    const char *pUser, int len, int *ready);
    virtual const StringList *getGroup(HttpSession *pSession,
                                       HashDataCache *pCache,
                                       const char *pGroup, int len, int *ready);

    virtual const char *getUserStoreURI() = 0;
    virtual const char *getGroupStoreURI() = 0;
    virtual int isGroupDBAvail() = 0;
    virtual int isUserStoreChanged(long tm)   {  return 1;    }
    virtual int isGroupStoreChanged(long tm)  {   return 1;   }
    void onTimer();
};

class PlainFileUserDir : public UserDir
{

    DataStore    *m_pUserStore;
    DataStore    *m_pGroupStore;
    PlainFileUserDir(const PlainFileUserDir &rhs);
    void operator=(const PlainFileUserDir &rhs);
public:
    PlainFileUserDir();
    ~PlainFileUserDir();

//    virtual int authenticate( HttpSession * pSession, const char * pUser, int nameLen,
//                      const char * pPasswd, int encryptMethod,
//                      AuthRequired * pRequired );

    AuthUser *getUserFromStore(HttpSession *pSession, HashDataCache *pCache,
                               const char *pUser, int len, int *ready)
    {
        return (AuthUser *)m_pUserStore->getDataFromStore(pUser, len);
    }

    AuthGroup *getGroupFromStore(HttpSession *pSession, HashDataCache *pCache,
                                 const char *pGroup, int len, int *ready)
    {
        if (!m_pGroupStore)
            return NULL;
        return (AuthGroup *)m_pGroupStore->getDataFromStore(pGroup, len);
    }
    virtual const char *getUserStoreURI()
    {   return m_pUserStore->getDataStoreURI();     }
    virtual const char *getGroupStoreURI()
    {   return m_pGroupStore->getDataStoreURI();    }
    virtual int isGroupDBAvail()
    {   return m_pGroupStore != NULL;   }

    int setDataStore(const char *pFile, const char *pGroup);
    int isUserStoreChanged(long tm)   {  return m_pUserStore->isStoreChanged(tm);    }
    int isGroupStoreChanged(long tm)  {  return m_pGroupStore->isStoreChanged(tm);   }

};


#endif
