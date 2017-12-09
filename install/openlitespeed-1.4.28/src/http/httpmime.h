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
#ifndef HTTPMIME_H
#define HTTPMIME_H


#include <http/expiresctrl.h>

#include <stddef.h>

#define MAX_MIME_LEN 256

class AutoStr2;
class HttpHandler;
class MimeMap;
class MIList;
class StringList;
class MIMEMap;
class MIMESuffix;
class MIMESuffixMap;
class MimeSettingList;
class XmlNodeList;
class HttpVHost;
class ConfigCtx;

class MimeSetting
{
    AutoStr2           *m_psMIME;
    ExpiresCtrl         m_expires;
    const HttpHandler *m_pHandler;

    void operator=(const MimeSetting &rhs);
public:
    MimeSetting();
    MimeSetting(const MimeSetting &rhs);
    ~MimeSetting();
    const AutoStr2     *getMIME() const     {   return m_psMIME;    }
    ExpiresCtrl        *getExpires()        {   return &m_expires;  }
    const ExpiresCtrl *getExpires() const  {   return &m_expires;  }
    void  setMIME(AutoStr2 *pMIME)       {   m_psMIME = pMIME;   }
    void  setHandler(const HttpHandler *pHdlr);
    const HttpHandler *getHandler() const  {   return m_pHandler;  }
    void  inherit(const MimeSetting *pParent, int updateOnly);
};

typedef void (*FnUpdate)(MimeSetting *pSetting, void *pValue);

class HttpMime
{
public:
    HttpMime();
    HttpMime(const HttpMime &rhs);
    ~HttpMime();
private:
    MIMEMap          *m_pMIMEMap;
    MIMESuffixMap    *m_pSuffixMap;
    MimeSetting      *m_pDefault;
    static HttpMime  *s_pMime;

    void operator=(const HttpMime &rhs) {}

    int processOneLine(const char *pFilePath, char *pLine, int lineNo);


public:
    MimeSetting *initDefault(char *pMIME = NULL);
    int loadMime(const char *pPropertyPath);
    MimeSetting *addUpdateMIME(char *pType, char *pDesc, const char *&reason,
                               int update = 1);

    const MimeSetting *getFileMime(const char *pPath) const;
    const MimeSetting *getFileMime(const char *pPath, int len) const;
    const MimeSetting *getFileMimeBySuffix(const char *pType) const;
    const MimeSetting *getDefault() const {   return m_pDefault;  }
    const MimeSetting *getMimeSetting(char *pMime) const;
    const MimeSetting *getMIMESettingLowerCase(char *pMime) const;
    int inherit(HttpMime *pParent, int handlerOnly = 1);
    int inheritSuffix(const HttpMime *pParent, int force);

    MimeSetting *getDefault() {   return m_pDefault;  }
    int updateMIME(char *pMIME, FnUpdate fn, void *pValue,
                   const HttpMime *pParent);
    int setCompressibleByType(const char *pValue, const HttpMime *pParent,
                              const char *pLogId);
    int setExpiresByType(const char *pValue, const HttpMime *pParent,
                         const char *pLogId);
    int addType(const HttpMime *pParent, const char *pValue,
                const char *pLogId);
    int addUpdateSuffixMimeMap(MimeSetting *pSetting, char *pSuffixes,
                               int update);
    int addMimeHandler(const char *suffix, char *pMime,
                       const HttpHandler *pHandler,
                       const HttpMime *pParent, const char *pLogId);

    void updateSuffixMimeHandler();

    static void releaseMIMEList();
    char compressible(const char *pMIME) const;
    static void setCompressible(MimeSetting *pSetting, void *pValue);
    static void setExpire(MimeSetting *pSetting, void *pValue);
    static void setHandler(MimeSetting *pSetting, void *pValue);
    static int  needCharset(const char *pMIME);
    static int  isValidMimeType(const char *pDescr);
    static int  shouldKeepAlive(const char *pMIME);
    static int configScriptHandler(const XmlNodeList *pList,
                                   HttpMime *pHttpMime);
    static void addMimeHandler(const HttpHandler *pHdlr, char *pMime,
                               HttpMime *pHttpMime,
                               const char *pSuffix);

    static void setMime(HttpMime *pMime)
    {   s_pMime = pMime;    }
    static HttpMime *getMime()
    {   return s_pMime;     }

};


#endif
