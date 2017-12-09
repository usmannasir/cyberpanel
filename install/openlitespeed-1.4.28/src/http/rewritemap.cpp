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
#include "rewritemap.h"
#include <util/stringtool.h>
#include <util/httputil.h>
#include <log4cxx/logger.h>

#include <stdlib.h>
#include <string.h>
#include <time.h>


KeyData *RewriteMapFile::parseLine(char *pLine, char *pLineEnd)
{
    char ch = *pLine;
    if ((ch == '#') || (ch == ' ') || (ch == '\t') || (ch == '\r')
        || (ch == '\n'))
        return NULL;
    int keyLen = strcspn(pLine, " \t\r\n");
    return parseLine(pLine, keyLen, pLine + keyLen + 1, pLineEnd);
}
KeyData *RewriteMapFile::parseLine(const char *pKey, int keyLen,
                                   char *pLine, char *pLineEnd)
{
    RewriteMapData *pData;
    pData = new RewriteMapData();
    if (pData)
    {
        pData->setKey(pKey, keyLen);
        int skip = strspn(pLine,  " \t\r\n");
        pLine += skip;
        if ((*pLine == '#') || (pLine == pLineEnd))
            pData->setValue("", 0);
        else
        {
            skip = strcspn(pLine, " #\t\r\n");
            pData->setValue(pLine, skip);
        }
    }
    return pData;

}

KeyData *RewriteMapFile::newEmptyData(const char *pKey, int len)
{
    KeyData *pData = new RewriteMapData();
    if (pData)
        pData->setKey(pKey, len);
    return pData;
}



RewriteMap::RewriteMap()
    : m_type(0)
    , m_loadTime(0)
    , m_pStore(NULL)
{
}
RewriteMap::~RewriteMap()
{
    if (m_pStore)
        delete m_pStore;
    release_objects();
}

int RewriteMap::parseType_Source(const char *pSource)
{
    static const char *s_types[8] =
    {
        "txt:", "rnd:", "int:toupper", "int:tolower",
        "int:escape", "int:unescape", "dbm:", "prg:"
    };
    static int s_type_len[8] = { 4, 4, 11, 11, 10, 12, 4, 4 };
    int i;
    for (i = 0; i < 8; ++i)
    {
        if (strncasecmp(s_types[i], pSource, s_type_len[i]) == 0)
            break;
    }
    if (i >= TYPE_DBM)
    {
        //error unknow or unsupported map type
        return -2;
    }
    m_type = i;
    pSource += s_type_len[i];
    if (m_type <= TYPE_RND)
    {
        m_pStore = new RewriteMapFile();
        if (m_pStore)
            m_pStore->setDataStoreURI(pSource);
        else
            return LS_FAIL;
    }
    return 0;
}

int RewriteMap::reloadFromStore()
{
    release_objects();
    if (m_pStore->open())
    {
        LS_ERROR("Failed to open rewrite map file: %s",
                 m_pStore->getDataStoreURI());
        return LS_FAIL;
    }
    KeyData *pData;
    while ((pData = m_pStore->getNext()) != NULL)
        insert(pData->getKey(), pData);
    m_pStore->close();
    m_loadTime = time(NULL);
    return 0;
}

static void initRand()
{
    static int s_inited = 0;
    if (!s_inited)
    {
        srand(time(NULL));
        s_inited = 1;
    }
}


int RewriteMap::lookup(const char *pKey, int keyLen, char *pValue,
                       int valLen)
{
    if (m_type <= TYPE_RND)
    {
        if (m_pStore->isStoreChanged(m_loadTime))
            reloadFromStore();
        RewriteMapData *pData = (RewriteMapData *)getData(pKey);
        if (!pData)
            return LS_FAIL;
        const char *pTxt = pData->getValue()->c_str();
        int len = pData->getValue()->len();
        if (m_type == TYPE_RND)
        {
            const char *part_begin[257];
            int parts = 1;
            part_begin[0] = pTxt;
            const char *p = pTxt;
            while (parts < 256)
            {
                p = strchr(p, '|');
                if (p)
                {
                    p++;
                    part_begin[parts++] = p;
                }
                else
                {
                    part_begin[parts] = pTxt + len + 1;
                    break;
                }
            }
            if (parts > 1)
            {
                initRand();
                parts = (int)((double)rand() / ((double)RAND_MAX + 1) * parts);
                pTxt = part_begin[parts];
                len = part_begin[parts + 1] - pTxt - 1;
            }
        }
        if (len > valLen)
            len = valLen;
        memmove(pValue, pTxt, len);
        valLen = len;
    }
    else
    {
        switch (m_type)
        {
        case TYPE_INT_UPPER:
            if (StringTool::strUpper(pKey, pValue, valLen) == NULL)
                valLen = 0;
            break;
        case TYPE_INT_LOWER:
            if (StringTool::strLower(pKey, pValue, valLen) == NULL)
                valLen = 0;
            break;
        case TYPE_INT_ESCAPE:
            valLen = HttpUtil::escape(pKey, keyLen, pValue, valLen);
            break;
        case TYPE_INT_UNESC:
            valLen = HttpUtil::unescape(pKey, keyLen, pValue, valLen);
            break;
        case TYPE_DBM:
        case TYPE_PRG:
        default:
            valLen = 0;
            break;
        }
    }
    return valLen;
}


RewriteMapList::RewriteMapList()
{}

RewriteMapList::~RewriteMapList()
{   release_objects();  }


