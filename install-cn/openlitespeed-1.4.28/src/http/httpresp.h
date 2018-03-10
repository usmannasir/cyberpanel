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
#ifndef HTTPRESP_H
#define HTTPRESP_H


#include <http/httprespheaders.h>

#define RANGE_HEADER_LEN    22
#define LSI_RSP_BODY_SIZE_CHUNKED (-1)
#define LSI_RSP_BODY_SIZE_UNKNOWN (-2)

class HttpReq;
typedef struct ls_xpool_s ls_xpool_t;

class HttpResp
{
public:


private:
    HttpRespHeaders m_respHeaders;
    off_t           m_lEntityLength;
    off_t           m_lEntityFinished;

    HttpResp(const HttpResp &rhs);
    void operator=(const HttpResp &rhs);


    void addWWWAuthHeader(const HttpReq *pReq);
public:
    explicit HttpResp(ls_xpool_t *pool);
    HttpResp();
    ~HttpResp();

    void reset();
//    {
//        m_outputBuf.clear();
//        m_iovec.clear();
//        memset( &m_iGotDate, 0,
//                (char *)((&m_iHeaderLeft) + 1) - (char*)&m_iGotDate );
//    }


    int appendHeader(const char *pName, int nameLen,
                     const char *pValue, int valLen);
    void addLocationHeader(const HttpReq *pReq);

    void prepareHeaders(const HttpReq *pReq, int addAcceptRange = 0);
    void appendContentLenHeader();

    HttpRespHeaders &getRespHeaders()
    {   return m_respHeaders;  }

    void setContentLen(off_t len)     {   m_lEntityLength = len;  }
    off_t getContentLen() const         {   return m_lEntityLength; }

    void written(long len)            {   m_lEntityFinished += len;    }
    off_t getBodySent() const           {   return m_lEntityFinished; }

    bool isChunked() const
    {   return (m_lEntityLength == -1); }

    //IOVec& getIov()    {   return m_respHeaders.getIOVec();  }
    int parseAdd(const char *pBuf, int len)
    {   return m_respHeaders.parseAdd(pBuf, len, LSI_HEADEROP_ADD);    }

    void addGzipEncodingHeader()
    {
        m_respHeaders.addGzipEncodingHeader();
    }

    void addBrotliEncodingHeader()
    {
        m_respHeaders.addBrotliEncodingHeader();
    }

    void appendChunked()
    {
        m_respHeaders.appendChunked();
    }



    off_t getTotalLen()    {   return m_lEntityFinished + m_respHeaders.getTotalLen();   }
    //int  isRespHeaderBuilt()      {   return m_respHeaders.isRespHeadersBuilt();   }
    const char *getContentTypeHeader(int &len)  {    return m_respHeaders.getContentTypeHeader(len);  }

    int  appendLastMod(long tmMod);
    int addCookie(const char *pName, const char *pVal,
                  const char *path, const char *domain, int expires,
                  int secure, int httponly);

};

#endif
