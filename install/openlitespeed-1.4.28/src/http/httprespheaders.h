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
#ifndef HTTPRESPHEADERS_H
#define HTTPRESPHEADERS_H

#include <util/autobuf.h>
#include <util/objarray.h>
#include <util/iovec.h>
#include <ls.h>

// namespace RespHeader {
//     enum ADD_METHOD {
//         REPLACE = LSI_ADD_RESPHEADER_REPLACE,
//         APPEND = LSI_ADD_RESPHEADER_APPEND, //Add with a comma to seperate
//         MERGE = LSI_ADD_RESPHEADER_MERGE,   //append unless exist
//         ADD = LSI_ADD_RESPHEADER_ADD,       //add a new line
//     };
// };

typedef struct
{
    int     keyOff;
    int     valOff;
    short   keyLen;
    short   valLen;
    int32_t next_index;  //For the multiple line case, this will indicate the next KVPair index, first valid value is 1 since default is 0
} resp_kvpair;


struct http_header_t;
struct iovec;
class IOVec;

#define HRH_F_HAS_HOLE  1
#define HRH_F_HAS_PUSH  2


class HttpRespHeaders
{
public:
    enum INDEX
    {
        // most common response-header
        H_ACCEPT_RANGES = 0,
        H_CONNECTION,
        H_CONTENT_TYPE,
        H_CONTENT_LENGTH,
        H_CONTENT_ENCODING,
        H_CONTENT_RANGE,
        H_CONTENT_DISPOSITION,
        H_CACHE_CTRL,
        H_DATE,
        H_ETAG,
        H_EXPIRES,
        H_KEEP_ALIVE,
        H_LAST_MODIFIED,
        H_LOCATION,
        H_LITESPEED_LOCATION,
        H_LITESPEED_CACHE_CONTROL,
        H_PRAGMA,
        H_PROXY_CONNECTION,
        H_SERVER,
        H_SET_COOKIE,
        H_CGI_STATUS,
        H_TRANSFER_ENCODING,
        H_VARY,
        H_WWW_AUTHENTICATE,
        H_X_LITESPEED_CACHE,
        H_X_LITESPEED_PURGE,
        H_X_LITESPEED_TAG,
        H_X_LITESPEED_VARY,
        H_LSC_COOKIE,
        H_X_POWERED_BY,
        H_LINK,

//        H_HTTP_VERSION,
        H_HEADER_END,
        H_UNKNOWN = H_HEADER_END,

        //not commonly used headers.
//         H_AGE,
//         H_PROXY_AUTHENTICATE,
//         H_RETRY_AFTER,
//         H_SET_COOKIE2,
//
//
//         // general-header
//         H_TRAILER,
//         H_UPGRADE,
//         H_WARNING,
//
//         // entity-header
//         H_ALLOW,
//         H_CONTENT_LANGUAGE,
//         H_CONTENT_LOCATION,
//         H_CONTENT_MD5,
    };

public:
    HttpRespHeaders(ls_xpool_t *pool);
    ~HttpRespHeaders() {};

    void reset();

    int add(INDEX headerIndex, const char *pVal, unsigned int valLen,
            int method = LSI_HEADEROP_SET);
    int add(const char *pName, int nameLen, const char *pVal,
            unsigned int valLen, int method = LSI_HEADEROP_SET);

    int appendLastVal(const char *pVal, int valLen);
    int add(http_header_t *headerArray, int size,
            int method = LSI_HEADEROP_SET);
    int parseAdd(const char *pStr, int len, int method = LSI_HEADEROP_SET);


    //Special case
    void addStatusLine(int ver, int code, short iKeepAlive) {  m_iHttpVersion = ver; m_iHttpCode = code; m_iKeepAlive = iKeepAlive; }
    short getHttpVersion()  { return m_iHttpVersion; }
    short getHttpCode()     { return m_iHttpCode;   }

    int del(const char *pName, int nameLen);
    int del(INDEX headerIndex);

    int getUniqueCnt() const    {   return m_iHeaderUniqueCount;    }

    int  getCount() const
    {
        return m_aKVPairs.getSize() - m_iHeaderRemovedCount;
    }

    int  getTotalCount() const                       {   return m_aKVPairs.getSize();   }

    char *getContentTypeHeader(int &len);

    //return number of header appended to iov
    int  getHeader(const char *pName, int nameLen, struct iovec *iov,
                   int maxIovCount);
    int  getHeader(INDEX index, struct iovec *iov, int maxIovCount);

    int  getFirstHeader(const char *pName, int nameLen, const char **val,
                        int &valLen);
    const char *getHeader(INDEX index, int *valLen) const;

    int  isHeaderSet(INDEX index) const
    {   return m_KVPairindex[index] != 0xff;    }

    //For LSIAPI using//return number of header appended to iov
    int getAllHeaders(struct iovec *iov_key, struct iovec *iov_val,
                      int maxIovCount);

    int  HeaderBeginPos()  {   return nextHeaderPos(-1); }
    int  HeaderEndPos()    {    return -1; }
    int  nextHeaderPos(int pos);

    int  getHeader(int pos, char **pName, int *nameLen, struct iovec *iov,
                   int maxIovCount)
    {   return _getHeader(pos, pName, nameLen, iov, maxIovCount); }

public:

    //0: REGULAR, 1:SPDY2 2, SPDY3, 3, SPDY 4, .....
    int outputNonSpdyHeaders(IOVec *iovec);
    int isRespHeadersBuilt()    {   return m_iHeaderBuilt;  }
    int getTotalLen()       { return m_iHeadersTotalLen; }
    int appendToIov(IOVec *iovec, int &addCrlf);
    int appendToIovExclude(IOVec *iovec, const char *pName, int nameLen) const;

    static INDEX getIndex(const char *pHeader);
    static int getHeaderStringLen(INDEX index)  {    return s_iHeaderLen[(int)index];  }

    static void buildCommonHeaders();
    static void updateDateHeader();
    static void hideServerSignature(int hide);

    void addGzipEncodingHeader()
    {
        add(s_gzipHeaders, 2);
    }

    void addBrotliEncodingHeader()
    {
        add(s_brHeaders, 2);
    }

    void appendChunked()
    {
        add(&s_chunkedHeader, 1);
    }

    void appendAcceptRange()
    {
        add(&s_acceptRangeHeader, 1);
    }

    void addCommonHeaders()
    {   add(s_commonHeaders, s_commonHeadersCount);     }

    void dropConnectionHeaders();

    unsigned char hasPush() const   {   return m_flags & HRH_F_HAS_PUSH;    }

public:
    static const char *m_sPresetHeaders[H_HEADER_END];
    static int m_iPresetHeaderLen[H_HEADER_END];


private:
    ls_xpool_t     *m_pool;
    AutoBuf         m_buf;
    TObjArray< resp_kvpair > m_aKVPairs;
    unsigned char   m_KVPairindex[H_HEADER_END];
    short           m_iHttpCode;
    char            m_flags;
    char            m_iHeaderBuilt;
    short           m_iHeaderRemovedCount;
    short           m_iHeaderUniqueCount;
    short           m_hLastHeaderKVPairIndex;
    int             m_iHeadersTotalLen;

    char            m_iHttpVersion;
    char            m_iKeepAlive;

    static int      s_iHeaderLen[H_HEADER_END + 1];

    int             getFreeSpaceCount() const {    return m_aKVPairs.getCapacity() - m_aKVPairs.getSize();   };
    void            incKVPairs(int num);
    resp_kvpair    *getKV(int index) const;
    resp_kvpair    *getNewKV();
    char           *getHeaderStr(int offset)        { return m_buf.begin() + offset;  }
    const char     *getHeaderStr(int offset) const  { return m_buf.begin() + offset;  }
    char           *getName(resp_kvpair *pKv)   { return getHeaderStr(pKv->keyOff); }
    char           *getVal(resp_kvpair *pKv)   { return getHeaderStr(pKv->valOff); }
    const char     *getVal(resp_kvpair *pKv) const   { return getHeaderStr(pKv->valOff); }
    int  _getHeader(int kvOrderNum, char **pName, int *nameLen,
                    struct iovec *iov, int maxIovCount);

    int _add(int kvOrderNum, const char *pName, int nameLen, const char *pVal,
             unsigned int valLen, int method);

    void            _del(int kvOrderNum);
    void            replaceHeader(resp_kvpair *pKv, const char *pVal,
                                  unsigned int valLen);
    int             appendHeader(resp_kvpair *pKv, const char *pName,
                                 unsigned int nameLen, const char *pVal, unsigned int valLen, int);
    int             getHeaderKvOrder(const char *pName, unsigned int nameLen);
    void            verifyHeaderLength(INDEX headerIndex,
                                       const char *pName, unsigned int nameLen);
    int             mergeAll();

    HttpRespHeaders(const HttpRespHeaders &other);
    void operator=(const HttpRespHeaders &rhs);

    static char s_sDateHeaders[30];
    static http_header_t   s_commonHeaders[2];
    static http_header_t   s_gzipHeaders[2];
    static http_header_t   s_brHeaders[2];
    static http_header_t   s_keepaliveHeader;
    static http_header_t   s_chunkedHeader;
    static http_header_t   s_concloseHeader;
    static http_header_t   s_acceptRangeHeader;
    static int             s_commonHeadersCount;

};

struct http_header_t
{
    HttpRespHeaders::INDEX index;
    const char *val;
    unsigned int valLen;
};

#endif // HTTPRESPHEADERS_H
