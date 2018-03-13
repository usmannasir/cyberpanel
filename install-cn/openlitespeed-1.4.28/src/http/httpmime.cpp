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
#include "httpmime.h"

#include <http/handlerfactory.h>
#include <http/httphandler.h>
#include <http/httplog.h>
#include <log4cxx/logger.h>
#include <main/configctx.h>
#include <util/autostr.h>
#include <util/hashstringmap.h>
#include <util/stringlist.h>
#include <util/stringtool.h>
#include <util/xmlnode.h>

#include <assert.h>
#include <ctype.h>
#include <errno.h>
#include <string.h>
#include <stdio.h>

static char DEFAULT_MIME_TYPE[] = "application/octet-stream";

static StringList *s_pMIMEList = NULL;

HttpMime *HttpMime::s_pMime = NULL;

//class MimeSettingList : public TPointerList<MimeSetting>{};


static StringList *getMIMEList()
{
    if (!s_pMIMEList)
        s_pMIMEList = new StringList();
    return s_pMIMEList;
}


void HttpMime::releaseMIMEList()
{
    if (s_pMIMEList)
    {
        delete s_pMIMEList;
        s_pMIMEList = NULL;
    }
}


static AutoStr2 *getMIME(const char *pMIME)
{
    AutoStr2 *pStr = getMIMEList()->bfind(pMIME);
    if (!pStr)
    {
        pStr = new AutoStr2(pMIME);
        if (!pStr)
            return NULL;
        getMIMEList()->insert(pStr);
    }
    return pStr;
}


//static MimeSettingList * s_pOldSettings = NULL;
//static MimeSettingList* getOldSettings()
//{
//    if ( !s_pOldSettings )
//    {
//        s_pOldSettings = new MimeSettingList();
//    }
//    return s_pOldSettings;
//}


static const char SEPARATORS[] =
{
    '(', ')', '<', '>', '@', ',', ';', ':', '\\', '"', '/', '[', ']', '?', '=',
    '{', '}', ' ', '\t'
};


static bool isValidToken(const char *pToken, int len)
{
    const char *pTemp = pToken;
    while (*pTemp && len)
    {
        if ((!isalnum(*pTemp)) && (*pTemp != '.') && (*pTemp != '+') &&
            (*pTemp != '-') && (*pTemp != '_'))
            return false;
        pTemp ++;
        len --;
    }
    return true;

}


static bool isValidType(const char *pType)
{
    int len = strlen(pType) ;
    if (len == 0)
        return false;
    return isValidToken(pType, len);
}


int HttpMime::isValidMimeType(const char *pDescr)
{
    char *pTemp = (char *) strchr(pDescr, '/');
    if (pTemp == NULL)
        return 0;
    int len = pTemp - pDescr ;
    if (len == 0 || ! isValidToken(pDescr, len))
        return 0;
    ++pTemp;
//    char* pTemp1;
//    pTemp1 = strchr( pTemp, ';' );
//
//    if ( pTemp1 )
//    {
//        while( isspace( *(pTemp1 - 1) ))
//            --pTemp1;
//        len = pTemp1 - pTemp;
//    }
//    else
    len = strlen(pTemp);
    if (len <= 0 || ! isValidToken(pTemp, len))
        return 0;
    return 1;
}


MimeSetting::MimeSetting()
    : m_psMIME(NULL)
    , m_pHandler(HandlerFactory::getInstance(0, NULL))
{}


MimeSetting::MimeSetting(const MimeSetting &rhs)
    : m_psMIME(rhs.m_psMIME)
    , m_expires(rhs.m_expires)
    , m_pHandler(rhs.m_pHandler)
{
}


MimeSetting::~MimeSetting()
{
}


void MimeSetting::setHandler(const HttpHandler *pHdlr)
{
    m_pHandler = pHdlr;
}


void MimeSetting::inherit(const MimeSetting *pParent, int updateOnly)
{
    if (!m_expires.cfgHandler() && (!m_pHandler->getType()
                                    || !updateOnly))
        m_pHandler = (HttpHandler *)pParent->getHandler();
    if (!m_expires.cfgCompress())
        m_expires.setCompressible(pParent->m_expires.compressible());
    if (!m_expires.cfgExpires())
        m_expires.copyExpires(pParent->m_expires);
}


class MIMESubMap : public HashStringMap<MimeSetting *>
{
    AutoStr2        m_sMainType;


    void operator=(const MIMESubMap &rhs);
public:
    MIMESubMap()
        : HashStringMap<MimeSetting * >(10)
    {}
    MIMESubMap(const MIMESubMap &rhs);
    ~MIMESubMap()
    {   release_objects();  }

    MimeSetting *addMIME(char *pMIME);
    const char *setMainType(const char *pType, int len);
    const char *getMainType() const    {   return m_sMainType.c_str(); }
    void updateMIME(FnUpdate fpUpdate, void *pValue);
    int inherit(const MIMESubMap *pParent, int existedOnly);
    int inherit(iterator iter, int existedOnly);
    MIMESubMap::iterator findMimeIgnoreCharset(char *pMIME);

};


MIMESubMap::MIMESubMap(const MIMESubMap &rhs)
    : HashStringMap<MimeSetting * >(10), m_sMainType(rhs.m_sMainType)
{
    iterator iter;
    for (iter = rhs.begin(); iter != rhs.end(); iter = rhs.next(iter))
    {
        MimeSetting *pSetting = new MimeSetting(*iter.second());
        if (pSetting)
            insert(iter.first(), pSetting);
    }

}


int MIMESubMap::inherit(iterator iter, int existedOnly)
{
    iterator iter2 = find(iter.first());
    if (iter2 == end())
    {
        if (!existedOnly)
        {
            MimeSetting *pSetting = new MimeSetting(*iter.second());
            if (pSetting)
                insert(iter.first(), pSetting);
            else
                return LS_FAIL;
        }
    }
    else
        iter2.second()->inherit(iter.second(), existedOnly);
    return 0;
}


int MIMESubMap::inherit(const MIMESubMap *pParent, int existedOnly)
{
    iterator iter;
    for (iter = pParent->begin();
         iter != pParent->end();
         iter = pParent->next(iter))
        inherit(iter, existedOnly);
    return 0;
}


const char *MIMESubMap::setMainType(const char *pType, int len)
{
    m_sMainType.setStr(pType, len);
    return m_sMainType.c_str();
}


void MIMESubMap::updateMIME(FnUpdate fpUpdate, void *pValue)
{
    iterator iter;
    for (iter = begin(); iter != end(); iter = next(iter))
        (*fpUpdate)(iter.second(), pValue);
}


MimeSetting *MIMESubMap::addMIME(char *pMIME)
{
    const char *p = strchr(pMIME, '/');
    if (!p)
        return NULL;
    ++p;
    if (!*p)
        return NULL;
    AutoStr2 *pStr = ::getMIME(pMIME);
    if (!pStr)
        return NULL;
    p = pStr->c_str() + (p - pMIME);
    MimeSetting *pSetting = new MimeSetting();
    if (!pSetting)
        return NULL;
    pSetting->setMIME(pStr);
    if (strncasecmp(pStr->c_str(), "image/", 6) == 0)
        pSetting->getExpires()->setBit(CONFIG_IMAGE);
    insert(p, pSetting);
    return pSetting;
}


MIMESubMap::iterator MIMESubMap::findMimeIgnoreCharset(char *pMIME)
{
    char *p1 = strchr(pMIME, ';');
    char ch;
    if (p1)
    {
        while (isspace(*(p1 - 1)))
            --p1;
        ch = *p1;
        *p1 = '\0';
    }
    MIMESubMap::iterator iterSub = find(pMIME);
    if (p1)
        *p1 = ch;
    return iterSub;
}


class MIMEMap : public HashStringMap<MIMESubMap *>
{

    void operator=(const MIMEMap &rhs);
public:
    MIMEMap()
        : HashStringMap<MIMESubMap * >(10)
    {}
    MIMEMap(const MIMEMap &rhs);
    ~MIMEMap()
    {   release_objects();  }
    iterator findSubMap(const char *pMIME, char *&p) const;
    MIMESubMap *addSubMap(char *pMIME, int len);

    MimeSetting *addMIME(char *pMIME);
    MimeSetting *findMimeIgnoreCharset(char *pMIME) const;
    void removeMIME(MimeSetting *pMIME);
    int updateMIME(char *pMIME, FnUpdate fpUpdate, void *pValue);
    int inherit(const MIMEMap *pParent, int existedOnly, char *pFilter);
    int inherit(iterator iter, int existedOnly);
};


MIMEMap::MIMEMap(const MIMEMap &rhs)
    : HashStringMap<MIMESubMap * >(10)
{
    iterator iter;
    for (iter = rhs.begin(); iter != rhs.end(); iter = rhs.next(iter))
    {
        MIMESubMap *pMap = new MIMESubMap(*iter.second());
        if (pMap)
            insert(pMap->getMainType(), pMap);
    }

}


int MIMEMap::inherit(iterator iter, int existedOnly)
{
    iterator iter2;
    iter2 = find(iter.first());
    if (iter2 == end())
    {
        if (!existedOnly)
        {
            MIMESubMap *pMap = new MIMESubMap(*iter.second());
            if (pMap)
                insert(pMap->getMainType(), pMap);
        }
    }
    else
        iter2.second()->inherit(iter.second(), existedOnly);
    return 0;
}


int MIMEMap::inherit(const MIMEMap *pParent, int existedOnly,
                     char *pFilter)
{
    iterator iter;
    if ((pFilter == NULL) || (*pFilter == '*'))
    {
        for (iter = pParent->begin();
             iter != pParent->end();
             iter = pParent->next(iter))
            inherit(iter, existedOnly);
    }
    else
    {

        char *p;
        iter = pParent->findSubMap(pFilter, p);
        if (iter != pParent->end())
        {
            MIMESubMap *pMap;
            iterator iter2;
            iter2 = find(iter.first());
            if (iter2 == end())
            {
                if (!existedOnly)
                    pMap = addSubMap(pFilter, p - pFilter);
                else
                    return 0;
            }
            else
                pMap = iter2.second();

            ++p;
            if (*p == '*')
                pMap->inherit(iter.second(), existedOnly);
            else
            {
                MIMESubMap::iterator iterSub = iter.second()->find(p);
                if (iterSub == iter.second()->end())
                    return 0;
                else
                    pMap->inherit(iterSub, existedOnly);
            }
        }

    }

    return 0;
}


MIMEMap::iterator MIMEMap::findSubMap(const char *pMIME, char *&p) const
{
    p = (char *) strchr(pMIME, '/');
    if (!p)
        return end();
    *p = 0;
    iterator iter = find(pMIME);
    *p = '/';
    return iter;
}


MIMESubMap *MIMEMap::addSubMap(char *pMIME, int len)
{
    MIMESubMap *pMap = new MIMESubMap();
    if (!pMap)
        return NULL;
    const char *pKey = pMap->setMainType(pMIME, len);
    insert(pKey, pMap);
    return pMap;
}


MimeSetting *MIMEMap::addMIME(char *pMIME)
{
    char *p;
    iterator iter = findSubMap(pMIME, p);
    MIMESubMap *pMap;
    if (iter == end())
    {
        pMap = new MIMESubMap();
        if (!pMap)
            return NULL;
        const char *pKey = pMap->setMainType(pMIME, p - pMIME);
        insert(pKey, pMap);
    }
    else
        pMap = iter.second();
    MIMESubMap::iterator iterSub = pMap->find(p + 1);

    if (iterSub == pMap->end())
        return pMap->addMIME(pMIME);
    else
        return iterSub.second();

}


MimeSetting *MIMEMap::findMimeIgnoreCharset(char *pMIME) const
{
    char *p;
    iterator iter = findSubMap(pMIME, p);
    MIMESubMap *pMap;
    if (iter == end())
        return NULL;
    pMap = iter.second();
    ++p;
    MIMESubMap::iterator iterSub = pMap->findMimeIgnoreCharset(p);
    if (iterSub == end())
        return NULL;
    else
        return iterSub.second();

}


void MIMEMap::removeMIME(MimeSetting *pMIME)
{
    char *p;
    iterator iter = findSubMap((char *)pMIME->getMIME()->c_str(), p);
    if (iter == end())
        return;
    iter.second()->remove(p + 1);
}


int MIMEMap::updateMIME(char *pMIME, FnUpdate fnUpdate, void *pValue)
{
    if (*pMIME == '*')
    {
        iterator iter;
        for (iter = begin(); iter != end(); iter = next(iter))
            iter.second()->updateMIME(fnUpdate, pValue);
    }
    else
    {
        char *p;
        iterator iter = findSubMap(pMIME, p);
        MIMESubMap *pMap = NULL;

        if (iter == end())
        {
            if (!p)
                return -1;
            pMap = addSubMap(pMIME, p - pMIME);
            if (!pMap)
                return -1;
        }
        else
            pMap = iter.second();
        ++p;
        if (*p == '*')
            pMap->updateMIME(fnUpdate, pValue);
        else
        {
            MIMESubMap::iterator iterSub = pMap->find(p);
            if (iterSub == pMap->end())
            {
                MimeSetting *pM = pMap->addMIME(pMIME);
                if (!pM)
                    return -1;
                (*fnUpdate)(pM, pValue);
            }
            else
                (*fnUpdate)(iterSub.second(), pValue);
        }

    }
    return 0;
}


class MIMESuffix
{
    MIMESuffix(const MIMESuffix &rhs);
    void operator=(const MIMESuffix &rhs);
public:
    MIMESuffix(const char *pSuffix, MimeSetting *pSetting);
    ~MIMESuffix() {}

    const char     *getSuffix() const   {   return m_sSuffix.c_str();   }
    MimeSetting    *getSetting() const  {   return m_pSetting;  }

    void            setSetting(MimeSetting *pSetting)
    {   m_pSetting = pSetting;  }

private:
    AutoStr       m_sSuffix;
    MimeSetting *m_pSetting;

};


MIMESuffix::MIMESuffix(const char *pSuffix, MimeSetting *pSetting)
    : m_sSuffix(pSuffix)
    , m_pSetting(pSetting)
{}


class MIMESuffixMap : public HashStringMap<MIMESuffix *>
{
    MIMESuffixMap(const MIMESuffixMap &rhs);
    void operator=(const MIMESuffixMap &rhs);
public:
    MIMESuffixMap()
        : HashStringMap<MIMESuffix * >(10)
    {}
    ~MIMESuffixMap() {   release_objects();   }
    MIMESuffixMap(int n) : HashStringMap<MIMESuffix * >(n) {}
    MIMESuffix *addMapping(const char *pSuffix, MimeSetting *pSetting)
    {   return addUpdateMapping(pSuffix, pSetting, 0);    }
    MIMESuffix *addUpdateMapping(const char *pSuffix, MimeSetting *pSetting,
                                 int update = 1);

};


MIMESuffix *MIMESuffixMap::addUpdateMapping(
    const char *pSuffix, MimeSetting *pSetting, int update)
{
    iterator iter = find(pSuffix);
    if (iter != end())
    {
        if (update)
        {
            MIMESuffix *pOld = iter.second();
            pOld->setSetting(pSetting);
            //pSetting->addSuffix(pSuffix);
            return pOld;
        }
        else
            return NULL;
    }
    MIMESuffix *pSuffixMap = new MIMESuffix(pSuffix, pSetting);
    insert(pSuffixMap->getSuffix(), pSuffixMap);
    return pSuffixMap;
}


HttpMime::HttpMime()
    : m_pDefault(NULL)
{
    m_pMIMEMap = new MIMEMap();
    m_pSuffixMap = new MIMESuffixMap();

}


HttpMime::HttpMime(const HttpMime &rhs)
{
    m_pMIMEMap = new MIMEMap(*rhs.m_pMIMEMap);
    if (rhs.m_pDefault)
        m_pDefault = m_pMIMEMap->findMimeIgnoreCharset((char *)
                     rhs.m_pDefault->getMIME()->c_str());
    else
        m_pDefault = NULL;
    m_pSuffixMap = new MIMESuffixMap();
    inheritSuffix(&rhs, 1);
}


int HttpMime::inheritSuffix(const HttpMime *pParent, int force)
{
//*
    MIMESuffixMap::iterator iter;
    for (iter = pParent->m_pSuffixMap->begin();
         iter != pParent->m_pSuffixMap->end();
         iter = pParent->m_pSuffixMap->next(iter))
    {
        MIMESuffixMap::iterator iterSelf = m_pSuffixMap->
                                           find(iter.first());
        if (iterSelf != m_pSuffixMap->end())
            continue;
        MimeSetting *pSetting = m_pMIMEMap->findMimeIgnoreCharset((char *)
                                iter.second()->getSetting()->getMIME()->c_str());
        if (!pSetting && force)
            pSetting = iter.second()->getSetting();
        if (pSetting)
            m_pSuffixMap->addUpdateMapping(iter.first(), pSetting, force);
    }
// */
    /*
        MIMEMap::iterator iter;
        for( iter = m_pMIMEMap->begin();
             iter != m_pMIMEMap->end();
             iter = m_pMIMEMap->next( iter ) )
        {
            MIMESubMap::iterator iterSub;
            for( iterSub = iter.second()->begin();
                 iterSub != iter.second()->end();
                 iterSub = iter.second()->next( iterSub ) )
            {
                MimeSetting * pSetting = pParent->m_pMIMEMap->findMimeIgnoreCharset( (char *)
                    iterSub.second()->getMIME()->c_str() );
                if ( pSetting && pSetting->getSuffixes() )
                {
                    StringList * pSuffixes = pSetting->getSuffixes();
                    StringList::iterator suffixIter;
                    for( suffixIter = pSuffixes->begin();
                        suffixIter != pSuffixes->end();
                        ++suffixIter )
                        m_pSuffixMap->addUpdateMapping( (*suffixIter)->c_str(), iterSub.second(), 0 );
                }
            }
        }
    // */
    return 0;
}


int HttpMime::updateMIME(char *pMIME, FnUpdate fn, void *pValue,
                         const HttpMime *pParent)
{
    if (pParent)
        m_pMIMEMap->inherit(pParent->m_pMIMEMap, 0, pMIME);
    return m_pMIMEMap->updateMIME(pMIME, fn, pValue);
}


MimeSetting *HttpMime::initDefault(char *pMIME)
{
    if (!pMIME)
        pMIME = DEFAULT_MIME_TYPE;
    if (!m_pDefault)
        m_pDefault = m_pMIMEMap->addMIME(pMIME);
    else
    {
        if (!m_pDefault->getMIME() ||
            (strcmp(pMIME, m_pDefault->getMIME()->c_str()) != 0))
            m_pDefault->setMIME(::getMIME(pMIME));
    }
    return m_pDefault;
}


const MimeSetting *HttpMime::getMimeSetting(char *pMime) const
{
    return m_pMIMEMap->findMimeIgnoreCharset(pMime);
}

const MimeSetting *HttpMime::getMIMESettingLowerCase(char *pMime) const
{
    return m_pMIMEMap->findMimeIgnoreCharset(pMime);
}


HttpMime::~HttpMime()
{
    if (m_pSuffixMap)
    {
        delete m_pSuffixMap;
        m_pSuffixMap = NULL;
    }
    if (m_pMIMEMap)
    {
        delete m_pMIMEMap;
        m_pMIMEMap = NULL;
    }
}


const MimeSetting *HttpMime::getFileMime(const char *pPath, int len) const
{
    const char *p = pPath + len;
    while (p > pPath)
    {
        if (*(p - 1) == '.')
            break;
        if (*(p - 1) == '/')
            return NULL;
        --p;
    }
    return getFileMimeBySuffix(p);
}


const MimeSetting *HttpMime::getFileMime(const char *pPath) const
{
    const char *pSuffix = strrchr(pPath, '.');
    if (pSuffix)
    {
        ++pSuffix;
        return getFileMimeBySuffix(pSuffix);
    }
    return NULL;
}


const MimeSetting *HttpMime::getFileMimeBySuffix(const char *pType) const
{
    if (pType)
    {
        MIMESuffixMap::iterator pos = m_pSuffixMap->find(pType);
        if (pos != m_pSuffixMap->end())
            return pos.second()->getSetting();
    }
    return NULL;
}


char HttpMime::compressible(const char *pMIME) const
{
    const MimeSetting *pSetting = m_pMIMEMap->findMimeIgnoreCharset((
                                      char *)pMIME);
    if (!pSetting)
        if (m_pDefault)
            return m_pDefault->getExpires()->compressible();
        else
            return 0;
    else
        return pSetting->getExpires()->compressible();
}


int HttpMime::inherit(HttpMime *pParent, int existedOnly)
{
    if (!pParent)
        return 0;
    if (m_pMIMEMap->inherit(pParent->m_pMIMEMap, existedOnly, NULL))
        return LS_FAIL;
    //inheritSuffix(pParent);
    if (!existedOnly)
    {
        if (pParent->m_pDefault)
            initDefault((char *)pParent->getDefault()->getMIME()->c_str());
    }
    return 0;
}


void HttpMime::updateSuffixMimeHandler()
{
    MIMESuffixMap::iterator iter;
    for (iter = m_pSuffixMap->begin();
         iter != m_pSuffixMap->end();
         iter = m_pSuffixMap->next(iter))
    {
        MimeSetting *pSetting = m_pMIMEMap->findMimeIgnoreCharset(
                                    (char *)iter.second()->getSetting()->getMIME()->c_str());
        if (pSetting && pSetting != iter.second()->getSetting())
            iter.second()->setSetting(pSetting);
    }
}


#define TEMP_BUF_LEN 1024

int HttpMime::loadMime(const char *pPropertyPath)
{
    FILE *fpMime = fopen(pPropertyPath, "r");
    if (fpMime == NULL)
    {
        LS_ERROR("[MIME] Cannot load property file: %s", pPropertyPath);
        return errno;
    }

    char pBuf[TEMP_BUF_LEN];
    int lineNo = 0;
    m_pSuffixMap->release_objects();

    while (! feof(fpMime))
    {
        lineNo ++ ;
        if (fgets(pBuf, TEMP_BUF_LEN, fpMime))
        {
            char *p = strchr(pBuf, '#');
            if (p)
                *p = 0;
            processOneLine(pPropertyPath, pBuf, lineNo);
        }
    }

    fclose(fpMime);
    return 0;
}


MimeSetting *HttpMime::addUpdateMIME(char *pSuffixes, char *pDesc,
                                     const char *&reason,
                                     int update)
{
    pSuffixes = StringTool::strTrim(pSuffixes);
    pDesc = StringTool::strTrim(pDesc);
    if (!isValidMimeType(pDesc))
    {
        reason = "invalid MIME description";
        return NULL;
    }
    if (strlen(pDesc) > MAX_MIME_LEN)
    {
        reason = "MIME description is too long";
        return NULL;
    }

    pSuffixes = StringTool::strLower(pSuffixes, pSuffixes);
    pDesc = StringTool::strLower(pDesc, pDesc);
    MimeSetting *pSetting = m_pMIMEMap->findMimeIgnoreCharset(pDesc);
    if (pSetting)
    {
        if (strcmp(pDesc, pSetting->getMIME()->c_str()) != 0)
        {
//            LS_WARN("[MIME] File %s line %d: MIME type with different parameter"
//                    " is not allowed, current: \"%s\" new: \"%s\", new one is used.",
//                            pFilePath, lineNo, pSetting->getMIME()->c_str(), pDesc));
            AutoStr2 *pMime = ::getMIME(pDesc);
            pSetting->setMIME(pMime);
        }
    }
    else
    {
        pSetting = m_pMIMEMap->addMIME(pDesc);
        if (!pSetting)
        {
            reason = "invalid MIME type";
            return NULL;
        }
    }
    addUpdateSuffixMimeMap(pSetting, pSuffixes, update);
    return pSetting;
}


int HttpMime::processOneLine(const char *pFilePath, char *pLine,
                             int lineNo)
{
    pLine = StringTool::strTrim(pLine);
    if (strlen(pLine) == 0)
        return 0;

    char *pType = pLine ;
    char *pDesc ;
    const char *reason;
    while (1)
    {
        if ((pDesc = strchr(pLine, '=')) == NULL)
        {
            reason = "missing '='";
            break;
        }

        *pDesc = '\0';
        ++ pDesc;


        if (!addUpdateMIME(pType, pDesc, reason, 0))
            break;
        else
            return 0;

    }

    LS_ERROR("[MIME] File %s line %d: (%s) - \"%s\"",
             pFilePath, lineNo, reason, pLine);
    return LS_FAIL;
}


void HttpMime::setCompressible(MimeSetting *pSetting, void *pValue)
{
    pSetting->getExpires()->setCompressible((long)pValue);
    pSetting->getExpires()->setBit(CONFIG_COMPRESS);
}


int HttpMime::setCompressibleByType(const char *pValue,
                                    const HttpMime *pParent,
                                    const char *pLogId)
{
    if (!pValue)
        return 0;
    StringList list;
    list.split(pValue, strlen(pValue) + pValue, ",");
    StringList::iterator iter;
    for (iter = list.begin(); iter != list.end(); ++iter)
    {
        char *pType = (*iter)->buf();
        long compressible = 1;
        if (*pType == '!')
        {
            compressible = 0;
            ++pType;
        }
        if (updateMIME(pType, HttpMime::setCompressible,
                       (void *)compressible, pParent) == -1)
        {
            LS_NOTICE("[%s] Can not find compressible MIME type: %s, add it!",
                      pLogId, pType);
            const char *pReason;
            char achTmp[] = "";
            addUpdateMIME(achTmp, pType, pReason, 0);
            updateMIME(pType, HttpMime::setCompressible,
                       (void *)compressible, pParent);
        }
    }
    return 0;
}


void HttpMime::setExpire(MimeSetting *pSetting, void *pValue)
{
    pSetting->getExpires()->parse((const char *)pValue);
}


int HttpMime::setExpiresByType(const char *pValue, const HttpMime *pParent,
                               const char *pLogId)
{
    if (!pValue)
        return 0;
    StringList list;
    list.split(pValue, strlen(pValue) + pValue, ",");
    StringList::iterator iter;
    for (iter = list.begin(); iter != list.end(); ++iter)
    {
        char *pType = (*iter)->buf();
        char *pExpiresTime = strchr(pType, '=');
        if (!pExpiresTime)
        {
            pExpiresTime = strchr(pType, ' ');
            if (!pExpiresTime)
            {
                LS_WARN("[%s] Invalid Expires setting: %s, ignore!", pLogId, pType);
                continue;
            }
        }
        *pExpiresTime++ = 0;
        if (updateMIME(pType, HttpMime::setExpire,
                       pExpiresTime, pParent) == -1)
        {
            LS_WARN("[%s] Can not find MIME type: %s, "
                    "ignore Expires setting %s!",
                    pLogId, pType, pExpiresTime);
        }
    }
    return 0;
}


int HttpMime::addUpdateSuffixMimeMap(MimeSetting *pSetting,
                                     char *pSuffixes, int update)
{
    pSuffixes = StringTool::strTrim(pSuffixes);
    pSuffixes = StringTool::strLower(pSuffixes, pSuffixes);
    char *p = pSuffixes;
    while (1)
    {
        p = strtok(pSuffixes, ", \t");
        if (!p)
            return 0;
        pSuffixes = NULL;
        p = StringTool::strTrim(p);
        while (*p == '.')
            ++p;
        if (*p == 0)
            continue;
        if (!isValidType(p))
            continue;
        if (strcmp(p, "default") == 0)
        {
            m_pDefault = pSetting;
            continue;
        }
        if (!m_pSuffixMap->addUpdateMapping(p, pSetting, update))
            continue;
    }

}



int HttpMime::addType(const HttpMime *pDefault, const char *pValue,
                      const char *pLogId)
{
    if (!pValue)
        return 0;
    const char *reason;
//    StringList list;
//    list.split( pValue, strlen( pValue ) + pValue, "," );
//    StringList::iterator iter;
//    for( iter = list.begin(); iter != list.end(); ++iter )
//    {
    AutoStr str(pValue);
    char *pType = str.buf();
    char *pSuffix = strchr(pType, '=');
    if (!pSuffix)
    {
        pSuffix = strchr(pType, ' ');
        if (!pSuffix)
        {
            LS_WARN("[%s] Incomplete MIME type, missing suffix: %s, ignore!", pLogId,
                    pType);
            return LS_FAIL;
        }
    }
    *pSuffix++ = 0;
    m_pMIMEMap->inherit(pDefault->m_pMIMEMap, 0, pType);
    if (addUpdateMIME(pSuffix, pType, reason, 1))
        LS_WARN("[%s] failed to add mime type: %s %s, reason: %s",
                pLogId, pType, pSuffix, reason);
//    }
    return 0;
}


void HttpMime::setHandler(MimeSetting *pSetting, void *pValue)
{
    pSetting->setHandler((HttpHandler *)pValue);
    pSetting->getExpires()->setBit(CONFIG_HANDLER);
}


int HttpMime::needCharset(const char *pMIME)
{
    if (*pMIME != 't')
        return 0;
    if ((strncmp(pMIME, "text/html", 9) != 0) &&
        (strncmp(pMIME, "text/plain", 10) != 0))
        return 0;
    return 1;
}


int HttpMime::shouldKeepAlive(const char *pMIME)
{
    if (strncmp(pMIME, "image/", 6) == 0)
        return 1;
    if (strncmp(pMIME, "text/css", 8) == 0)
        return 1;
    if (strncmp(pMIME, "application/x-javascript", 24) == 0)
        return 1;
    return 0;
}


int HttpMime::addMimeHandler(const char *pSuffix, char *pMime,
                             const HttpHandler *pHdlr,
                             const HttpMime *pParent, const char *pLogId)
{
    const char *reason;
    char achBuf[256];
    char achSuffix[512];
    if (!pMime)
    {
        strcpy(achBuf, "application/x-httpd-");

        pMime = (char *) strchr(pSuffix, ',');
        if (!pMime)
            pMime = (char *) strchr(pSuffix, ' ');
        if (pMime)
        {
            memccpy(&achBuf[20], pSuffix, 0, pMime - pSuffix);
            achBuf[20 + pMime - pSuffix ] = 0;
        }
        else
            strcpy(&achBuf[20], pSuffix);
        pMime = achBuf;
    }
    memccpy(achSuffix, pSuffix, 0, 511);
    if (!addUpdateMIME(achSuffix, pMime, reason, 1))
    {
        LS_WARN("[%s] failed to add mime type: %s %s, reason: %s",
                pLogId, pMime, pSuffix, reason);
        return LS_FAIL;
    }
    updateMIME(pMime, HttpMime::setHandler, (void *)pHdlr, pParent);
    return 0;
}


int HttpMime::configScriptHandler(const XmlNodeList *pList,
                                  HttpMime *pHttpMime)
{
    ConfigCtx currentCtx("scripthandler", "add");
    XmlNodeList::const_iterator iter;

    for (iter = pList->begin(); iter != pList->end(); ++iter)
    {
        const char *value = (char *)(*iter)->getValue();
        const char *pSuffixByTab = strchr(value, '\t');
        const char *pSuffixBySpace = strchr(value, ' ');
        const char *suffix  = NULL;

        if (pSuffixByTab == NULL && pSuffixBySpace == NULL)
        {
            currentCtx.logErrorInvalTag("ScriptHandler", value);
            continue;
        }
        else if (pSuffixByTab == NULL)
            suffix = pSuffixBySpace;
        else if (pSuffixBySpace == NULL)
            suffix = pSuffixByTab;
        else
            suffix = ((pSuffixByTab > pSuffixBySpace) ? pSuffixBySpace : pSuffixByTab);

        const char *type = strchr(value, ':');

        if (suffix == NULL || type == NULL || strchr(suffix, '.') || type > suffix)
        {
            currentCtx.logErrorInvalTag("suffix", suffix);
            continue;

        }

        ++ suffix; //should all spaces be handled here?? Now only one white space handled.

        char pType[256] = {0};
        memcpy(pType, value, type - value);

        char handler[256] = {0};
        memcpy(handler, type + 1, suffix - type - 2);

        char achHandler[256] = {0};

        if (currentCtx.expandVariable(handler, achHandler, 256) < 0)
        {
            LS_NOTICE(&currentCtx,
                      "add String is too long for scripthandler, value: %s",
                      handler);
            continue;
        }

        const HttpHandler *pHdlr = HandlerFactory::getHandler(pType, achHandler);
        addMimeHandler(pHdlr, NULL, pHttpMime, suffix);
    }

    return 0;
}


void HttpMime::addMimeHandler(const HttpHandler *pHdlr, char *pMime,
                              HttpMime *pHttpMime,
                              const char *pSuffix)
{
    if (!pHdlr)
    {
        LS_ERROR(ConfigCtx::getCurConfigCtx(),
                 "use static file handler for suffix [%s]",
                 pSuffix);
        pHdlr = HandlerFactory::getInstance(0, NULL);
    }
    HttpMime *pParent = NULL;

    if (pHttpMime)
        pParent = HttpMime::getMime();
    else
        pHttpMime = HttpMime::getMime();

    pHttpMime->addMimeHandler(pSuffix, pMime,
                              pHdlr, pParent, TmpLogId::getLogId());
}


