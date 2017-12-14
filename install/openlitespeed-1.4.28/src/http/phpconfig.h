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
#ifndef PHPCONFIG_H
#define PHPCONFIG_H



#include <util/autobuf.h>
#include <util/autostr.h>
#include <util/hashstringmap.h>

#define PHP_CONF_PERDIR 1
#define PHP_CONF_SYSTEM 4

#define PHP_CONFIG_ENV  1

class PHPValue
{
    AutoStr m_sKey;
    AutoStr m_sVal;
    int     m_iType;

    void operator=(const PHPValue &rhs);
public:
    PHPValue()  {}
    PHPValue(const PHPValue &rhs)
        : m_sKey(rhs.m_sKey)
        , m_sVal(rhs.m_sVal)
        , m_iType(rhs.m_iType)
    {}

    ~PHPValue() {}
    int setValue(const char *pKey, const char *pValue,
                 short iType);
    const char *getKey() const     {   return m_sKey.c_str();  }
    const char *getValue() const   {   return m_sVal.c_str();  }
    void setValue(const char *v)  {   m_sVal = v;             }

    void setType(short t)         {   m_iType = t;            }
    short getType() const           {   return m_iType;         }

};

class PHPConfig
{
    HashStringMap<PHPValue *>   m_config;
    AutoBuf                     m_lsapiEnv;

    void operator=(const PHPConfig &rhs);
public:
    PHPConfig();
    ~PHPConfig();

    PHPConfig(const PHPConfig &rhs);

    int merge(const PHPConfig *pParent);
    int parse(int id, const char *pArgs,
              char *pErr, int errBufLen);
    int buildLsapiEnv();
    const AutoBuf &getLsapiEnv()    {   return m_lsapiEnv;  }
    int getCount() const        {   return m_config.size(); }
};

#endif
