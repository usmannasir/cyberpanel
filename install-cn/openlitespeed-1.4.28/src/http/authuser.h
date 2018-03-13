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
#ifndef AUTHUSER_H
#define AUTHUSER_H


#include <lsdef.h>
#include <util/autostr.h>
#include <util/stringlist.h>
#include <util/keydata.h>

class StringList;

enum
{
    ENCRYPT_UNKNOWN,
    ENCRYPT_PLAIN,
    ENCRYPT_CRYPT,
    ENCRYPT_MD5,
    ENCRYPT_APMD5,
    ENCRYPT_SHA,
    ENCRYPT_SMD5,
    ENCRYPT_SSHA
};

class AuthData : public KeyData
{
    long        m_lTimestamp;
    short       m_exist;
    short       m_encMethod;
public:
    AuthData()
        : m_exist(1)
        , m_encMethod(ENCRYPT_PLAIN)
    {}
    virtual ~AuthData() {}


    long getTimestamp() const           {   return m_lTimestamp;    }
    void setTimestamp(long stamp)     {   m_lTimestamp = stamp;   }

    short isExist()  const              {   return m_exist;         }
    void  setExist(short exist)       {   m_exist = exist;        }

    short getEncMethod() const          {   return m_encMethod;     }
    void  setEncMethod(short m)       {   m_encMethod = m;        }
    LS_NO_COPY_ASSIGN(AuthData);
};

class AuthUser : public AuthData
{
private:
    AutoStr      m_passwd;
    StringList *m_pGroups;


public:


    AuthUser();
    ~AuthUser();
    void setPasswd(const char *pPasswd, int len) {   m_passwd.setStr(pPasswd, len); }
    int  setGroups(const char *pGroups, const char *pEnd);
    int  addGroup(const char *pGroup);
    void updatePasswdEncMethod();

    void setPasswd(const char *pPasswd)  {   m_passwd = pPasswd;     }

    const char *getPasswd() const          {   return m_passwd.c_str();}
    const StringList *getGroups() const    {   return m_pGroups;       }
    LS_NO_COPY_ASSIGN(AuthUser);
};

class AuthGroup : public AuthData, public StringList
{
public:
    AuthGroup() {}
    ~AuthGroup() {}
    int add(const char *pUser);
};

#endif
