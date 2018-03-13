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
#ifndef REWRITEMAP_H
#define REWRITEMAP_H


#include <lsdef.h>
#include <util/autostr.h>
#include <util/hashdatacache.h>
#include <util/hashstringmap.h>
#include <util/keydata.h>

class RewriteMapData : public KeyData
{
    AutoStr2    m_value;
public:
    RewriteMapData() {}
    ~RewriteMapData() {}
    const AutoStr2 *getValue() const       {   return &m_value;    }
    void setValue(const char *pValue, int len)
    {   m_value.setStr(pValue, len);      }

    LS_NO_COPY_ASSIGN(RewriteMapData);
};

class RewriteMapFile : public FileStore
{

protected:
    virtual KeyData *parseLine(char *pLine, char *pLineEnd);
    virtual KeyData *parseLine(const char *pKey, int keyLen,
                               char *pLine, char *pLineEnd);
    virtual KeyData *newEmptyData(const char *pKey, int len);

public:
    RewriteMapFile() {}
    ~RewriteMapFile() {}

};


class RewriteMap : public HashDataCache
{

    AutoStr             m_sName;
    int                 m_type;
    long                m_loadTime;
    RewriteMapFile     *m_pStore;

    int reloadFromStore();

public:

    enum
    {
        TYPE_TXT,
        TYPE_RND,
        TYPE_INT_UPPER,
        TYPE_INT_LOWER,
        TYPE_INT_ESCAPE,
        TYPE_INT_UNESC,
        TYPE_DBM,
        TYPE_PRG
    };

    RewriteMap();
    ~RewriteMap();

    void setName(const char *pName)  {   m_sName.setStr(pName);    }
    const char *getName() const        {   return m_sName.c_str();     }

    int parseType_Source(const char *pSource);
    int lookup(const char *pKey, int keyLen, char *pValue, int valLen);
    LS_NO_COPY_ASSIGN(RewriteMap);
};

class RewriteMapList : public HashStringMap<RewriteMap *>
{
public:
    RewriteMapList();
    ~RewriteMapList();
};

#endif
