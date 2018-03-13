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
#ifdef RUN_TEST

#include "httpreqtest.h"

#include <http/httpreq.h>
#include <http/httpmethod.h>
#include <log4cxx/logsession.h>
#include <stdio.h>
#include "unittest-cpp/UnitTest++.h"

#include <http/httpstatuscode.h>

class HttpReqTst : public HttpReq, public LogSession
{
public:
    HttpReqTst()
        : HttpReq()
    {  }
    const char *getLogId()     {   return LogSession::getLogId();  }
    virtual const char *buildLogId() {  return getLogId(); }

    int append(const char *pBuf, int size)
    {   return HttpReq::appendTestHeaderData(pBuf, size); }
};
SUITE(HttpReqTest)
{
    TEST(HttpReqTest_testFragment)
    {
        const char pFrag1[] =
            "POST /serv_admin/wizControl.php HTTP/1.1\r\n"
            "Host: 192.168.0.10:8083\r\n"
            "User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.0.1) Gecko/20020830\r\n"
            "Accept: text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,video/x-mng,image/png,image/jpeg,image/gif;q=0.2,text/css,*/*;q=0.1\r\n"
            "Accept-Language: en-us, en;q=0.50\r\n"
            "Accept-Encoding: gzip, deflate, compress;q=0.9\r\n"
            "Accept-Charset: ISO-8859-1, utf-8;q=0.66, *;q=0.66\r\n"
            "Keep-Alive: 300\r\n"
            "Connection: keep-alive\r\n"
            "Referer: http://192.168.0.10:8083/serv_admin/servGeneral.php?id=1\r\n"
            "Cookie: PHPSESSID=386791a581cda4e5f5c6b4f960f19c33\r\n";

        const char pFrag2[] =
            "Content-Type: application/x-www-form-urlencoded\r\n"
            "Content-Length: 104\r\n"
            "\r\n"
            "parentWin=YB_conf&objName=ESgeneral&objId=&finishPage=servGeneral.php%3Fid%3D1&nextPage=servGeneral1.php\r\n";
        HttpReqTst req;
        req.getIdBuf() = "testFragment" ;
        req.reset();
        req.setVHost((HttpVHost *)
                     1);    //just skip vhost lookup while parsing header
        CHECK(1 == req.append(pFrag1, strlen(pFrag1)));
        CHECK(0 == req.append(pFrag2, strlen(pFrag2)));
        CHECK(req.getOrgReqURLLen() == 26);
    }

    TEST(HttpReqTest_testParseHeader)
    {

        const char *pSample[] =
        {
            "host", "www.example.com:3080",
            "user-agent", "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:0.9.2.1) Gecko/20010901",
            "accept", "text/xml, application/xml, application/xhtml+xml, text/html;q=0.9, image/png, image/jpeg, image/gif;q=0.2, text/plain;q=0.8, text/css",
            "accept-language", "en-us",
            "accept-encoding", "deflate,gzip,compress,identity",
            "accept-charset", "ISO-8859-1, utf-8;q=0.66, *;q=0.66",
            "content-type", "text/html",
            "keep-alive", "300",
            "connection", "keep-alive",
            "range", "bytes=10-20"
        };
        const char *pGarbage =
            " \t   \r\n"
            "\r\n"
            "\t\r\n";

        const char *pURI = "/path/path1/path3 path4";
        const char *pArg = "a=b%20c";
        const char *pInput =
            "GET \t http://WWW.eXample.cOm:2080///path//./path1/path2//..////path3%20path4?a=b%20c \tHTTP/1.0\t \r\n"
            "Host: \n"
            "\twww.example.com:3080\r\n"
            "User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:0.9.2.1) Gecko/20010901\r\n"
            "Accept : text/xml, application/xml, application/xhtml+xml, text/html;q=0.9, image/png, image/jpeg, image/gif;q=0.2, text/plain;q=0.8, text/css\r\n"
            "Accept-Language: en-us\r\n"
            "Accept-Encoding: deflate,gzip,compress,identity\r\n"
            "Accept-Charset: ISO-8859-1, utf-8;q=0.66, *;q=0.66\r\n"
            "Content-Type: text/html\t \r\n"
            "Keep-alive\t: 300 \r\n"
            "Connection: keep-alive\r\n"
            "Range: bytes=10-20\r\r\n"
            "Non-Standard-Header: header1\r\n"
            "  line2\r\n"
            "\t \tline3\r\n"
            "\r\n";
        HttpReqTst req;
        req.getIdBuf() = "testParseHeader";
        req.reset();
        req.setVHost((HttpVHost *)
                     1);    //just skip vhost look while parsing header
        CHECK(1 == req.append(pGarbage, strlen(pGarbage)));

        int len = strlen(pInput);
        int i;
        for (i = 0; i < len; ++i)
        {
            int ret = req.append(pInput + i, 1);
            if ((ret != 1) && (ret != 0))
                printf("test error: ret=%d, i=%d, bufleft=%s\n", ret, i, pInput + i);
            CHECK((ret == 1) || (ret == 0));
        }
        int status = req.getStatus();
        CHECK(HttpReq::HEADER_OK == status);
        CHECK(HttpMethod::HTTP_GET == req.getMethod());
        CHECK(strcmp(req.getURI(), pURI) == 0);
        CHECK(strncmp(req.getQueryString(), pArg, strlen(pArg)) == 0);
        CHECK(req.getOrgReqURLLen() == 51);
        for (int i = 0; i < (int)(sizeof(pSample) / sizeof(char *)); i += 2)
        {
            int index = HttpHeader::getIndex(pSample[i]);
            const char *pHeader = req.getHeader(index);

            if (!*pHeader)
                printf("i=%d\n", i);
            CHECK(*pHeader);
            CHECK(0 ==
                  strncmp(pHeader,
                          pSample[i + 1],
                          strlen(pSample[i + 1])));
        }

        const char *pHost = "www.example.com";
        int hl = req.getHostStrLen();
        CHECK(hl == (int)strlen(pHost));

        CHECK(strncmp(req.getHostStr(), pHost, strlen(pHost)) == 0);
        req.setVHost(NULL);
        CHECK(req.gzipAcceptable());
        CHECK(req.isKeepAlive());
        const char *pNSHKey = "non-standard-header";
        const char *pNSHValue = "header1    line2  \t \tline3";
        const char *pParsed = req.getHeader(pNSHKey, 19, len);
        CHECK(NULL != pParsed);
        CHECK(0 ==
              strncmp(pParsed,
                      pNSHValue,
                      strlen(pNSHValue)));
    }

    TEST(HttpReqTest_testParseHeader1)
    {

        const char *pSample[] =
        {
            "host", "www.example.com:3080",
            "user-agent", "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:0.9.2.1) Gecko/20010901",
            "accept", "text/xml, application/xml, application/xhtml+xml, text/html;q=0.9, image/png, image/jpeg, image/gif;q=0.2, text/plain;q=0.8, text/css",
            "accept-language", "en-us",
            "accept-encoding", "deflate,compress,identity",
            "accept-charset", "ISO-8859-1, utf-8;q=0.66, *;q=0.66",
            "content-type", "text/html",
            "content-length", "1234",
            "keep-alive", "300",
            "connection", "close"
        };

        //const char * pURI = "/path/path1/path3 path4";
        const char *pInput =
            "POST \t ///path//path1////path3%20path4/../../../ \tHTTP/1.1\t \r\n"
            "Host: \n"
            " www.example.com:3080\r\n"
            "User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:0.9.2.1) Gecko/20010901\r\n"
            "Accept : text/xml, application/xml, application/xhtml+xml, text/html;q=0.9, image/png, image/jpeg, image/gif;q=0.2, text/plain;q=0.8, text/css\r\n"
            "Accept-Language: en-us\r\n"
            "Accept-Encoding: deflate,compress,identity\r\n"
            "Accept-Charset: ISO-8859-1, utf-8;q=0.66, *;q=0.66\r\n"
            "Content-Type: text/html\t \r\n"
            "Content-length: 1234 \r\n"
            "Keep-alive\t: 300 \r\n"
            "Connection: \t\n"
            "\t close\r\n"
            "\r\n";
        HttpReqTst req;
        req.getIdBuf() = "testParseHeader1" ;
        req.reset();
        req.setVHost((HttpVHost *)
                     1);    //just skip vhost look while parsing header

        int len = strlen(pInput);
        int i;
        for (i = 0; i < len; ++i)
        {
            int ret = req.append(pInput + i, 1);
            if ((ret != 1) && (ret != 0))
                printf("test error: ret=%d, i=%d, bufleft=%s\n", ret, i, pInput + i);
            CHECK((ret == 1) || (ret == 0));
        }
        int status = req.getStatus();
        CHECK(HttpReq::HEADER_OK == status);
        CHECK(HttpMethod::HTTP_POST == req.getMethod());
        CHECK(strcmp(req.getURI(), "/") == 0);
        CHECK(req.getQueryStringLen() == 0);
        CHECK(req.getOrgReqURLLen() == 41);
        for (int i = 0; i < (int)(sizeof(pSample) / sizeof(char *)); i += 2)
        {
            int index = HttpHeader::getIndex(pSample[i]);
            const char *pHeader = req.getHeader(index);

            if (!*pHeader)
                printf("i=%d\n", i);
            CHECK(*pHeader);
            int cmp = strncmp(pHeader,
                              pSample[i + 1],
                              strlen(pSample[i + 1]));
            if (cmp)
                printf("i=%d\n", i);
            CHECK(0 == cmp);
        }

        const char *pHost = "www.example.com";
        int hl = req.getHostStrLen();
        CHECK(hl == (int)strlen(pHost));
        CHECK(strncmp(req.getHostStr(), pHost, strlen(pHost)) == 0);
        req.setVHost(NULL);
        CHECK(req.getContentLength() == 1234);
        CHECK(!req.gzipAcceptable());
        CHECK(!req.isKeepAlive());
        //const char * pNSHKey = "non-standard-header";
        //const char * pNSHValue = "header1    line2  \t \tline3";
        //const char * pParsed = req.getHeader( pNSHKey );
        //CHECK( NULL != pParsed );
        //printf( "%s\n" ,  pParsed );
        //CHECK( 0 ==
        //        strncmp( pParsed,
        //                pNSHValue,
        //                strlen( pNSHValue ) ) );
    }

    TEST(HttpReqTest_testParseHeader2)
    {
        const char pInput[] =
        {
            "GET / HTTP/1.1\r\n"
            "Host: www.epochtimes.com\r\n"
            "User-Agent: productfinderbot\r\n"
            "From: \r\nReferer: \r\nAccept-Encoding: \r\n"
            "Customize : \r\n"
            "   Customized\r\n"
            "Connection: close\r\n\r\n"
        };
        HttpReqTst req;
        req.getIdBuf() = "testParseHeader1" ;
        req.reset();
        req.setVHost((HttpVHost *)
                     1);    //just skip vhost look while parsing header

        int len = strlen(pInput);
        int i;
        for (i = 0; i < len; ++i)
        {
            int ret = req.append(pInput + i, 1);
            if ((ret != 1) && (ret != 0))
                printf("test error: ret=%d, i=%d, bufleft=%s\n", ret, i, pInput + i);
            CHECK((ret == 1) || (ret == 0));
        }
        int status = req.getStatus();
        CHECK(HttpReq::HEADER_OK == status);
        CHECK(HttpMethod::HTTP_GET == req.getMethod());
        int index = HttpHeader::getIndex("Referer");
        const char *pHeader = req.getHeader(index);
        CHECK(*pHeader);
        CHECK(req.getHeaderLen(index) == 0);
        CHECK(req.getOrgReqURLLen() == 1);
        index = HttpHeader::getIndex("Accept-Encoding");
        pHeader = req.getHeader(index);
        CHECK(*pHeader);
        CHECK(req.getHeaderLen(index) == 0);
        int unknown = req.getUnknownHeaderCount();
        CHECK(unknown == 2);
        const char *pKey;
        const char *pVal;
        int keyLen;
        int valLen;
        pKey = req.getUnknownHeaderByIndex(0, keyLen, pVal, valLen);
        CHECK(keyLen == 4);
        CHECK(valLen == 0);
        CHECK(strncasecmp(pKey, "from", 4) == 0);
        CHECK(pVal > req.getHeaderBuf().begin());
        CHECK(pVal < req.getHeaderBuf().end());

        pKey = req.getUnknownHeaderByIndex(1, keyLen, pVal, valLen);
        CHECK(keyLen == 9);
        CHECK(valLen == 10);
        CHECK(strncasecmp(pKey, "customize", 9) == 0);
        CHECK(strncmp(pVal, "Customized", 9) == 0);
        CHECK(pVal > req.getHeaderBuf().begin());
        CHECK(pVal < req.getHeaderBuf().end());

    }

    TEST(HttpReqTest_testParseHeader3)
    {
        const char pInput[] =
        {
            "GET /asf/../../../ HTTP/1.1\r\n"
            "Host: www.epochtimes.com\r\n"
            "User-Agent: productfinderbot\r\n"
            "From: \r\nReferer: \r\nAccept-Encoding: \r\n"
            "Customize : \r\n"
            "   Customized\r\n"
            "Connection: close\r\n\r\n"
        };
        HttpReqTst req;
        req.getIdBuf() = "testParseHeader1" ;
        req.reset();
        req.setVHost((HttpVHost *)
                     1);    //just skip vhost look while parsing header

        int len = strlen(pInput);
        int i;
        int ret;
        for (i = 0; i < len; ++i)
        {
            ret = req.append(pInput + i, 1);
            if ((ret != 1) && (ret != 0))
                printf("test error: ret=%d, i=%d, bufleft=%s\n", ret, i, pInput + i);
            if (ret == SC_400)
                break;
            CHECK((ret == 1) || (ret == 0));
        }
        CHECK(ret == SC_400);

    }
}


#endif
