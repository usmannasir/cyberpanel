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
#ifndef HTAUTH_H
#define HTAUTH_H



#define AUTH_USER_SIZE       64

class AuthUser;
class AuthRequired;
class AutoBuf;
class HttpSession;
class StringList;
class UserDir;
class HttpRespHeaders;

class HTAuth
{
    char       *m_pName;
    char       *m_authHeader;
    int         m_authHeaderLen;
    UserDir    *m_pUserDir;
    short       m_iAuthType;
    short       m_iAuthTypeUsed;

    HTAuth(const HTAuth &rhs);
    void operator=(const HTAuth &rhs);
    int buildWWWAuthHeader(const char *pName);
public:
    enum
    {
        AUTH_BASIC = 1,
        AUTH_DIGEST = 2,
        AUTH_DEFAULT = AUTH_BASIC
    };

    HTAuth();
    HTAuth(const char *pRealm);
    ~HTAuth();

    void setName(const char *pName);
    const char *getName() const        {   return m_pName;                 }

    void setAuthType(int iType)       {   m_iAuthType = iType;            }
    void setUserDir(UserDir *pDir)   {   m_pUserDir = pDir;              }

    int  getAuthType() const            {   return m_iAuthType;             }
    const UserDir *getUserDir() const   {   return m_pUserDir;              }

    //const AuthUser * getUser( const char * pUser, int userLen ) const;
    int addWWWAuthHeader(HttpRespHeaders &buf) const ;
    int basicAuth(HttpSession *pSession, const char *pAuthorization,
                  int headerLen, char *pAuthUser, int bufLen,
                  const AuthRequired *pRequired) const;
    int digestAuth(HttpSession *pSession, const char *pAuthorization,
                   int size, char *pAuthUser, int bufLen,
                   const AuthRequired *pRequired) const ;
//    int checkAuth(  const char * pAuthorization, int headerLen,
//                char * pAuthUser, int bufLen  ) const;
    int authenticate(HttpSession *pSession, const char *pAuthHeader,
                     int authHeaderLen, char *pAuthUser, int userBufLen,
                     const AuthRequired *pRequired) const;
};

#endif

