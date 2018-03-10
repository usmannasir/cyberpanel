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
#ifndef HTTPREQ_H
#define HTTPREQ_H

class SslConnection;
enum
{
    REQ_BODY_UNKNOWN,
    REQ_BODY_FORM,
    REQ_BODY_MULTIPART
};


#include <http/httpheader.h>
#include "httpvhost.h"
#include <lsr/ls_str.h>
#include <lsr/ls_types.h>
#include <util/autobuf.h>
#include <util/autostr.h>
#include <log4cxx/logsession.h>
#include <util/objarray.h>

#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>

#define CHUNKED                 -1
#define MAX_REDIRECTS           10

#define PROCESS_CONTEXT         (1<<0)
#define CONTEXT_AUTH_CHECKED    (1<<1)
#define REDIR_CONTEXT           (1<<2)
#define KEEP_AUTH_INFO          (1<<5)
#define REWRITE_REDIR           (1<<6)
#define SKIP_REWRITE            (1<<7)
#define REWRITE_PERDIR          (1<<8)
#define REWRITE_QSD             (1<<9)
#define REWRITE_CACHE_CONF      (1<<10)
#define CACHE_DECOMPRESS        (1<<11)
#define NO_RESP_BODY            (1<<12)
#define IS_ERROR_PAGE           (1<<13)
#define STAGE_V1                (1<<14)
#define AUTH_DIGEST_STALE       (1<<15)
#define VERIFY_SIG              (1<<16)
#define CACHE_KEY               (1<<17)
#define CACHE_PRIVATE_KEY       (1<<18)
#define AP_USER_DIR             (1<<19)
#define X_FORWARD_HTTPS         (1<<20)
#define LOG_ACCESS_404          (1<<21)
#define RESP_CONT_LEN_SET       (1<<22)

#define COOKIE_PARSED           (1<<24)
#define LITEMAGE_CROWLER        (1<<25)
#define DUM_BENCHMARK_TOOL      (1<<26)
#define EXEC_EXT_CMD            (1<<27)
#define MP4_SEEK                (1<<28)
#define EXEC_CMD_PARSE_RES      (1<<29)

#define GZIP_ENABLED            1
#define REQ_GZIP_ACCEPT         2
#define GZIP_REQUIRED           (GZIP_ENABLED | REQ_GZIP_ACCEPT)
#define UPSTREAM_GZIP           4
#define GZIP_ADD_ENCODING       8
#define GZIP_OFF                16
#define UPSTREAM_DEFLATE        32

#define BR_ENABLED              1
#define REQ_BR_ACCEPT           2
#define BR_REQUIRED             (BR_ENABLED | REQ_BR_ACCEPT)
#define UPSTREAM_BR             4

struct AAAData;
class AuthRequired;
class ClientInfo;
class ExpiresCtrl;
class HotlinkCtrl;
class HTAuth;
class HttpContext;
class HttpHandler;
class HttpRange;
class HttpRespHeaders;
class HttpSession;
class HttpVHost;
class IOVec;
class MimeSetting;
class RadixNode;
class SSIConfig;
class SSIRuntime;
class StaticFileCacheData;
class VHostMap;
class VMemBuf;
typedef struct ls_hash_s ls_hash_t;


typedef struct
{
    int keyOff;
    int keyLen;
    int valOff;
    int valLen;
} key_value_pair;


typedef struct
{
    int keyOff;
    int flag: 8;
    int keyLen: 24;
    int valOff;
    int valLen;
} cookieval_t;

#define COOKIE_FLAG_PHPSESSID       1
#define COOKIE_FLAG_FRONTEND        2
#define COOKIE_FLAG_XF_SESSID       4
#define COOKIE_FLAG_RESP_UPDATE     8


class CookieList : public TObjArray< cookieval_t >
{
public:
    CookieList()
        : m_iSessIdx(0)
    {}
    ~CookieList()
    {}
    void setSessIdx(int idx)
    {   m_iSessIdx = idx + 1;   }
    int getSessIdx() const
    {   return m_iSessIdx - 1;  }
    int isSessIdxSet() const
    {   return m_iSessIdx != 0; }
    void reset()
    {   clear(); m_iSessIdx = 0;    }

    void cookieClassify(cookieval_t *pCookieEntry,
                        const char *pCookies, int nameLen,
                        const char *pVal, int valLen);

    cookieval_t *insertCookieIndex(ls_xpool_t *pool, AutoBuf *pData,
                                   const char *pName, int nameLen);
    void copy(CookieList &rhs, ls_xpool_t *pool)
    {
        m_iSessIdx = rhs.m_iSessIdx;
        TObjArray<cookieval_t>::copy(rhs, pool);
    }


private:
    int  m_iSessIdx;
};

typedef TObjArray< key_value_pair > KVPairArray;

class HttpReq
{
private:
    const VHostMap     *m_pVHostMap;
    SslConnection      *m_pSslConn;
    AutoBuf             m_headerBuf;

    int                 m_iReqHeaderBufFinished;
    int                 m_iReqHeaderBufRead;

    const MimeSetting  *m_pMimeType;

    ls_xpool_t         *m_pPool;
    ls_strpair_t        m_curUrl;
    ls_strpair_t       *m_pUrls;
    char               *m_pAuthUser;
    RadixNode          *m_pEnv;
    KVPairArray         m_unknHeaders;

    //Comment:The order of the below 3 varibles should NOT be changed!!!
    short               m_commonHeaderLen[HttpHeader::H_TE];
    int                 m_commonHeaderOffset[HttpHeader::H_TE];
    int                 m_headerIdxOff;
    int                 m_reqLineOff;
    int                 m_reqLineLen;
    int                 m_reqURLOff;
    int                 m_reqURLLen;
    ls_str_t            m_location;
    ls_str_t            m_pathInfo;
    ls_str_t            m_newHost;
    ls_str_t            m_redirHdrs;
    unsigned char       m_iHeaderStatus;
    unsigned char       m_iHS1;
    unsigned char       m_iHS3;
    unsigned char       m_iLeadingWWW;
    int                 m_iHS2;
    short               m_iCfIpHeader;
    short               m_method;
    int                 m_iEnvCount;
    unsigned short      m_ver;
    short               m_iRedirects;
    int                 m_iAcceptGzip:8;
    int                 m_iAcceptBr:8;
    int                 m_iKeepAlive:8;
    int                 m_iNoRespBody:8;
    off_t               m_lEntityLength;
    off_t               m_lEntityFinished;
    int                 m_iContextState;
    const HttpHandler  *m_pHttpHandler;

    int                 m_iHttpHeaderEnd;

    const HttpContext  *m_pContext;
    //const HttpContext * m_pHTAContext;
    const HttpContext  *m_pFMContext;
    VMemBuf            *m_pReqBodyBuf;
    HttpRange          *m_pRange;
    HttpVHost          *m_pVHost;
    const char         *m_pForcedType;
    const HTAuth       *m_pHTAuth;
    const AuthRequired *m_pAuthRequired;
    SSIRuntime         *m_pSSIRuntime;
    int                 m_iHostOff;
    int                 m_iHostLen;
    const AutoStr2     *m_pRealPath;
    int                 m_iMatchedLen;

    int                 m_upgradeProto;
    int                 m_code;

    // The following member do not need to be initialized
    AutoStr2            m_sRealPathStore;
    int                 m_fdReqFile;
    struct stat         m_fileStat;
    int                 m_iScriptNameLen;
    short               m_iBodyType;
    LogSession         *m_pILog;
    CookieList          m_cookies;

    static_file_data_t *m_pUrlStaticFileData;



    HttpReq(const HttpReq &rhs) ;
    void operator=(const HttpReq &rhs);

    int setQS(const char *qs, int qsLen);
    void uSetURI(char *pURI, int uriLen);

    int redirectDir(const char *pURI);
    int processPath(const char *pURI, int uriLen, char *pBuf,
                    char *pBegin, char *pEnd,  int &cacheable);
    int processURIEx(const char *pURI, int uriLen, int &cacheable);
    int processMatchList(const HttpContext *pContext, const char *pURI,
                         int iURILen);
    int processMatchedURI(const char *pURI, int uriLen, char *pMatched,
                          int len);
    int processSuffix(const char *pURI, const char *pURIEnd, int &cacheable);
    int filesMatch(const char *pEnd);

    int checkSuffixHandler(const char *pURI, int len, int &cacheable);



    //parse headers
    int processRequestLine();
    int processHeaderLines();

    int translate(const char *pURI, int uriLen,
                  const HttpContext *pContext, char *pReal, int len) const;
    int internalRedirect(const char *pURL, int len, int alloc = 0);
    //int internalRedirectURI( const char * pURI, int len );

    int contextRedirect(const HttpContext *pContext, int matchLen);
    int tryExtractHostFromUrl(const char *&pURL, int &len);

    void addHeader(size_t index, int off, int len)
    {
        m_commonHeaderOffset[index] = off;
        m_commonHeaderLen[index] = len;
    }
    key_value_pair *getCurHeaderIdx()
    {   return m_unknHeaders.getObj(m_unknHeaders.getSize() - 1);   }
    key_value_pair *newUnknownHeader();

    key_value_pair *newKeyValueBuf();
    key_value_pair *getUnknHeaderByKey(const AutoBuf &buf, const char *pName,
                                       int namelen) const;

    key_value_pair *getUnknHeaderPair(int index)
    {   return m_unknHeaders.getObj(index); }

    int appendIndexToUri(const char *pIndex, int indexLen);

    int checkHotlink(const HotlinkCtrl *pHLC, const char *pSuffix);

protected:
    //this function is for testing purpose,
    // should only be called from a test program
    int appendTestHeaderData(const char *pBuf, int len)
    {
        m_headerBuf.append(pBuf, len);
        return processHeader();
    }

public:

    enum
    {
        HEADER_REQUEST_LINE = 0,
        HEADER_REQUSET_LINE_DONE = 1,
        HEADER_HEADER = HEADER_REQUSET_LINE_DONE,
        HEADER_HEADER_LINE_END,
        HEADER_OK,
        HEADER_SKIP,
        HEADER_ERROR_TOLONG,
        HEADER_ERROR_INVALID
    };

    enum
    {
        UPD_PROTO_NONE = 0,
        UPD_PROTO_WEBSOCKET = 1,
        UPD_PROTO_HTTP2 = 2,
    };

    explicit HttpReq();
    ~HttpReq();

    int processHeader();
    int processNewReqData(const struct sockaddr *pAddr);
    void reset();
    void reset2();

    void setILog(LogSession *pILog)         {   m_pILog = pILog;            }
    LOG4CXX_NS::Logger *getLogger() const   {   return m_pILog->getLogger();}
    const char   *getLogId()                {   return m_pILog->getLogId(); }
    LogSession *getLogSession() const       {   return m_pILog;             }

    void setVHostMap(const VHostMap *pMap)  {   m_pVHostMap = pMap;         }
    const VHostMap *getVHostMap() const     {   return m_pVHostMap;         }
    const HttpVHost *matchVHost(const VHostMap *pVHostMap);
    const HttpVHost *matchVHost();

    char getStatus() const                  {   return m_iHeaderStatus;     }
    int getMethod() const                   {   return m_method;            }

    unsigned int getVersion() const         {   return m_ver;               }

    AutoBuf &getHeaderBuf()                 {   return m_headerBuf;         }

    const HttpVHost *getVHost() const       {   return m_pVHost;            }
    HttpVHost *getVHost()                   {   return m_pVHost;            }

    void setVHost(HttpVHost *pVHost)        {   m_pVHost = pVHost;          }

    const char *getURI()
    {   return ls_str_cstr(&m_curUrl.key);  }
    int   getURILen()
    {   return ls_str_len(&m_curUrl.key);   }

    void setNewHost(const char *pInfo, int len)
    {   ls_str_xsetstr(&m_newHost, pInfo, len, m_pPool);   }
    int getNewHostLen()
    {   return ls_str_len(&m_newHost);  }
    const char *getNewHost()
    {   return ls_str_cstr(&m_newHost); }

    const char *getPathInfo()
    {   return ls_str_cstr(&m_pathInfo);    }
    int   getPathInfoLen()
    {   return ls_str_len(&m_pathInfo); }

    const char *getQueryString()
    {   return ls_str_cstr(&m_curUrl.val);    }
    int   getQueryStringLen()
    {   return ls_str_len(&m_curUrl.val); }

    int   isWebsocket() const
    {   return ((UPD_PROTO_WEBSOCKET == m_upgradeProto) ? 1 : 0);   }
    int   isHttp2Upgrade() const
    {   return ((UPD_PROTO_HTTP2 == m_upgradeProto) ? 1 : 0);   }
    //request header

    const char *getHeader(size_t index) const
    {   return m_headerBuf.begin() + m_commonHeaderOffset[ index];  }

    const char *getHeader(const char *pName, int namelen, int &valLen) const
    {
        key_value_pair *pIdx = getUnknHeaderByKey(m_headerBuf, pName, namelen);
        if (pIdx)
        {
            valLen = pIdx->valLen;
            return m_headerBuf.getp(pIdx->valOff);
        }
        return NULL;
    }

    int isHeaderSet(size_t index) const
    {   return m_commonHeaderOffset[index];     }
    int getHeaderLen(size_t index) const
    {   return m_commonHeaderLen[ index ];      }

    const char *getHostStr()
    {   return m_headerBuf.getp(m_iHostOff);    }
    const char *getOrgReqLine() const
    {   return m_headerBuf.getp(m_reqLineOff);  }
    const char *getOrgReqURL() const
    {   return m_headerBuf.getp(m_reqURLOff);   }
    int getHttpHeaderLen() const
    {   return m_iHttpHeaderEnd - m_reqLineOff;         }
    int getHttpHeaderEnd() const            {   return m_iHttpHeaderEnd;    }

    int getOrgReqLineLen() const            {   return m_reqLineLen;        }
    int getOrgReqURLLen() const             {   return m_reqURLLen;         }

    const char *encodeReqLine(int &len);

    const char *getAuthUser() const         {   return m_pAuthUser;         }

    bool isChunked() const
    {   return m_lEntityLength == CHUNKED;  }
    off_t getBodyRemain() const
    {   return m_lEntityLength - m_lEntityFinished; }

    off_t getContentFinished() const        {   return m_lEntityFinished;   }
    void contentRead(off_t lLen)            {   m_lEntityFinished += lLen;  }


    const   char *getContentType() const
    {   return getHeader(HttpHeader::H_CONTENT_TYPE);     }

    void setContentLength(off_t len)
    {
        m_lEntityLength = len;

    }
    off_t getContentLength() const          {   return m_lEntityLength;     }
    int  getHostStrLen()                    {   return m_iHostLen;          }
    int  getScriptNameLen() const           {   return m_iScriptNameLen;    }
    void setScriptNameLen(int n);

    const HttpHandler *getHttpHandler() const
    {   return m_pHttpHandler;  }

    int  translatePath(const char *pURI, int uriLen,
                       char *pReal, int len) const;
    int  setCurrentURL(const char *pURL, int len, int alloc = 0);
    int  redirect(const char *pURL, int len, int alloc = 0);
    int  postRewriteProcess(const char *pURI, int len);
    int  processContextPath();
    int  processContext(const HttpContext *&pOldCtx);
    int  checkPathInfo(const char *pURI, int iURILen, int &pathLen,
                       short &scriptLen, short &pathInfoLen,
                       const HttpContext *pContext);
    void saveMatchedResult();
    void restoreMatchedResult();
    char *allocateAuthUser();

    void setErrorPage()
    {   m_iContextState |= IS_ERROR_PAGE;       }
    int  isErrorPage() const
    {   return m_iContextState & IS_ERROR_PAGE; }

    short isKeepAlive() const               {   return m_iKeepAlive;        }
    void keepAlive(short keepalive)         {   m_iKeepAlive = keepalive;   }

    int getPort() const;
    const AutoStr2 &getPortStr() const;

    const AutoStr2 *getLocalAddrStr() const;

    const AutoStr2 *getRealPath() const     {   return m_pRealPath;         }

    int  getLocationLen()
    {   return ls_str_len(&m_location); }
    int  setLocation(const char *pLoc, int len);
    const char *getLocation()
    {   return ls_str_cstr(&m_location);    }
    void clearLocation()
    {   ls_str_set(&m_location, NULL, 0); }

    int  appendRedirHdr(const char *pDisp, int len);
    int  getRedirHdrsLen() const      
    {   return ls_str_len(&m_redirHdrs);   }
    const char *getRedirHdrs() const
    {  return ls_str_cstr(&m_redirHdrs);   }
    
    int  addWWWAuthHeader(HttpRespHeaders &buf) const;
    const AuthRequired *getAuthRequired() const
    {   return m_pAuthRequired; }

    //void matchContext();
    void updateKeepAlive();
    struct stat &getFileStat()              {   return m_fileStat;          }
    const struct stat &getFileStat() const  {   return m_fileStat;          }

    int transferReqFileFd()
    {
        int fd = m_fdReqFile;
        m_fdReqFile = -1;
        return fd;
    }

    HttpRange *getRange() const             {   return m_pRange;            }
    void setRange(HttpRange *pRange)        {   m_pRange = pRange;          }

    VMemBuf *getBodyBuf() const             {   return m_pReqBodyBuf;       }
    short getBodyType() const               {   return m_iBodyType;  }

    int prepareReqBodyBuf();
    void replaceBodyBuf(VMemBuf *pBuf);
    void updateBodyType(const char *buf);
    

    char gzipAcceptable() const             {   return m_iAcceptGzip;       }
    void andGzip(char b)                    {   m_iAcceptGzip &= b;         }
    void orGzip(char b)                     {   m_iAcceptGzip |= b;         }

    char brAcceptable() const               {   return m_iAcceptBr;       }
    void andBr(char b)                      {   m_iAcceptBr &= b;         }
    void orBr(char b)                       {   m_iAcceptBr |= b;         }

    char noRespBody() const                 {   return m_iNoRespBody;       }
    void setNoRespBody()                    {   m_iNoRespBody = 1;          }
    void updateNoRespBodyByStatus(int code);
//     {
//         if (!(m_iContextState & KEEP_AUTH_INFO))
//         {
//             switch (m_code = code)
//             {
//             case SC_100:
//             case SC_101:
//             case SC_204:
//             case SC_205:
//             case SC_304:
//                 m_iNoRespBody = 1;
//             }
//         }
//     }


    void processReqBodyInReqHeaderBuf();
    void resetHeaderBuf();
    int  pendingHeaderDataLen() const
    {   return m_iReqHeaderBufRead - m_iReqHeaderBufFinished;  }

    void rewindPendingHeaderData(int len)
    {   m_iReqHeaderBufFinished -= len; }
    int  appendPendingHeaderData(const char *pBuf, int len);
    void compactHeaderBuf()
    {
        m_headerBuf.resize(m_iHttpHeaderEnd);
        m_iReqHeaderBufRead = m_iReqHeaderBufFinished = m_iHttpHeaderEnd;
    }

    int getCurPos() const
    {   return  m_iReqHeaderBufFinished;    }
    void setHeaderEnd()
    {   m_iHttpHeaderEnd = m_iReqHeaderBufFinished; }
    void pendingDataProcessed(int len)
    {   m_iReqHeaderBufFinished += len; }

    void setStatusCode(int code)            {   m_code = code;              }
    int  getStatusCode() const              {   return m_code;              }
    void tranEncodeToContentLen();

    const AutoStr2 *getDocRoot() const;
    const ExpiresCtrl *shouldAddExpires();
    void dumpHeader();
    int  getUGidChroot(uid_t *pUid, gid_t *pGid,
                       const AutoStr2 **pChroot);
    const AutoStr2 *getDefaultCharset() const;
    const MimeSetting *getMimeType() const  {   return m_pMimeType;         }
    void  setMimeType(const MimeSetting *mime) {   m_pMimeType = mime;         }

    void  smartKeepAlive(const char *pValue);
    //int setRewriteURI( const char * pURL, int len );
    int setRewriteURI(const char *pURL, int len, int no_escape = 1);
    int setRewriteQueryString(const char *pQS, int len);
    int setRewriteLocation(char *pURI, int uriLen,
                           const char *pQS, int qsLen, int escape);
    void setForcedType(const char *pType)   {   m_pForcedType = pType;      }
    const char *getForcedType() const       {   return m_pForcedType;       }

    int checkSymLink(const char *pPath, int pathLen, const char *pBegin);

    const char *findEnvAlias(const char *pKey, int keyLen, int &aliasKeyLen);
    ls_strpair_t *addEnv(const char *pKey, int keyLen, const char *pValue,
                         int valLen);
    const char *getEnv(const char *pKey, int keyLen, int &valLen);
    const RadixNode *getEnvNode() const;
    int  getEnvCount();
    void unsetEnv(const char *pKey, int keyLen);

    int  getUnknownHeaderCount()
    {
        return m_unknHeaders.getSize();
    }
    const char *getUnknownHeaderByIndex(int idx, int &keyLen,
                                        const char *&pValue, int &valLen);
    char isCfIpSet() const                      {   return m_iCfIpHeader;   }
    const char *getCfIpHeader(int &len);

    void setSsl(SslConnection *p)   {    m_pSslConn = p;        }
    SslConnection *getSsl() const  {   return m_pSslConn;      }
    int isHttps() const
    {   return m_pSslConn || (m_iContextState & X_FORWARD_HTTPS);    }

    char getRewriteLogLevel() const;
    void setHandler(const HttpHandler *pHandler)
    {   m_pHttpHandler = pHandler;      }

//     void setHTAContext( const HttpContext *pCtx)
//     {   m_pHTAContext = pCtx;   }
//     const HttpContext * getHTAContext() const
//     {   return m_pHTAContext;   }
    void setContext(const HttpContext *pCtx) {   m_pContext = pCtx;          }
    const HttpContext *getContext() const   {   return m_pContext;          }
    const HttpContext *getFMContext() const {   return m_pFMContext;        }

    void incRedirects()                     {   ++m_iRedirects;             }
    short getRedirects() const              {   return m_iRedirects;        }

    void orContextState(int s)            {   m_iContextState |= s;       }
    void clearContextState(int s)         {   m_iContextState &= ~s;      }
    int getContextState(int s) const    {   return m_iContextState & s; }
    int detectLoopRedirect(const char *pURI, int uriLen,
                           const char *pArg, int qsLen, int isSSL);
    int detectLoopRedirect();
    int saveCurURL();
    const char *getOrgURI()
    {
        return m_iRedirects ? ls_str_cstr(&(m_pUrls[0].key)) : ls_str_cstr(
                   &m_curUrl.key);
    }

    int  getOrgURILen()
    {
        return m_iRedirects ? ls_str_len(&(m_pUrls[0].key)) : ls_str_len(
                   &m_curUrl.key);
    }

    void appendHeaderIndexes(IOVec *pIOV, int cntUnknown);
    void getAAAData(struct AAAData &aaa, int &satisfyAny);

    off_t getTotalLen() const
    {   return m_lEntityFinished + getHttpHeaderLen();  }

    const AutoBuf *getExtraHeaders() const;

    int parseMethod(const char *pCur, const char *pBEnd);
    int parseHost(const char *pCur, const char *pBEnd);
    int parseURL(const char *pCur, const char *pBEnd);
    int parseProtocol(const char *pCur, const char *pBEnd);
    int removeSpace(const char **pCur, const char *pBEnd);
    int parseURI(const char *pCur, const char *pBEnd);
    const char *skipSpace(const char *pOrg, const char *pDest);
    int processHeader(int index);
    int postProcessHost(const char *pCur, const char *pBEnd);
    int skipSpaceBothSide(const char *&pHBegin, const char *&pHEnd);
    char isGeoIpOn() const;
    uint32_t isIpToLocOn() const;
    int getDecodedOrgReqURI(char *&pValue);
    SSIRuntime *getSSIRuntime() const       {   return m_pSSIRuntime;       }
    void setSSIRuntime(SSIRuntime *p)       {   m_pSSIRuntime = p;          }
    SSIConfig *getSSIConfig();
    uint32_t isXbitHackFull() const;
    uint32_t isIncludesNoExec() const;
    long getLastMod() const
    {   return m_fileStat.st_mtime;    }
    void backupPathInfo();
    void restorePathInfo();
    void setRealPath(const char *pRealPath, int len)
    {
        m_sRealPathStore.setStr(pRealPath, len);
        m_pRealPath = &m_sRealPathStore;
    }
    int   getOrgReqURILen()
    {
        if (m_iRedirects ? ls_str_cstr(&(m_pUrls[0].val))
            : ls_str_cstr(&m_curUrl.val))
            return m_reqURLLen - 1 - (m_iRedirects
                                      ? ls_str_len(&(m_pUrls[0].val))
                                      : ls_str_len(&m_curUrl.val));
        else
            return m_reqURLLen;
    }

    const char *getRedirectURL(int &len)
    {
        ls_strpair_t &url = (m_iRedirects ? m_pUrls[m_iRedirects - 1] : m_curUrl);
        len = ls_str_len(&(url.key));
        return ls_str_cstr(&(url.key));
    }

    const char *getRedirectQS(int &len)
    {
        ls_strpair_t &url = (m_iRedirects ? m_pUrls[m_iRedirects - 1] : m_curUrl);
        len = ls_str_len(&(url.val));
        return ls_str_cstr(&(url.val));
    }

    int isMatched() const
    {
        return m_iMatchedLen;
    }
    void stripRewriteBase(const HttpContext *pCtx,
                          const char *&m_pSourceURL, int &m_sourceURLLen);

    int locationToUrl(const char *pLocation, int len);

    int internalRedirectURI(const char *pURI, int len, int resetPathInfo = 1,
                            int no_escape = 1);
//     void setErrorPage( )
//     {   m_iContextState |= IS_ERROR_PAGE;       }
//     int  redirect( const char * pURL, int len, int alloc = 0 );
//     int internalRedirect( const char * pURL, int len, int alloc );

    int getETagFlags() const;
    int checkScriptPermission();

    int setMimeBySuffix(const char *pSuffix);
    const char *getMimeBySuffix(const char *pSuffix);

    ls_xpool_t *getPool()
    {   return m_pPool; }

    int removeCookie(const char *pName, int nameLen);
    cookieval_t *setCookie(const char *pName, int nameLen, const char *pValue,
                           int valLen);
    int processSetCookieHeader(const char *pValue, int valLen);
    cookieval_t *getCookie(const char *pName, int nameLen);
    cookieval_t *insertCookieIndex(const char *pName, int nameLen);
    int parseCookies();
    int copyCookieHeaderToBufEnd(int oldOff, const char *pCookie,
                                 int cookieLen);
    CookieList  &getCookieList() { return   m_cookies; }


    int checkUrlStaicFileCache();
    static_file_data_t *getUrlStaticFileData() { return m_pUrlStaticFileData;}
};


#endif
