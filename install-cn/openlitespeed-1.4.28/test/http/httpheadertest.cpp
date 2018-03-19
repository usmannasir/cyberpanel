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

/*****************************************************************************
 * Notable findings
 * h.add(HttpRespHeaders::H_HEADER_END, "unknown", 7, "My_Server", 9); triggers an abort - is considered acceptable behavior
 * h.add(HttpRespHeaders::H_UNKNOWN, "unknown", -7, "My_Server", 9); triggers a crash - is considered acceptable behavior
 * header values are limited to 10 in Spdy Header
*****************************************************************************/



#ifdef RUN_TEST
#include <stdio.h>
#include "httpheadertest.h"
#include <http/httpheader.h>
#include <http/httprespheaders.h>
#include <http/httpstatuscode.h>
#include <lsr/ls_xpool.h>
#include <util/iovec.h>

#include <stdlib.h>
#include "unittest-cpp/UnitTest++.h"
#include <util/misc/profiletime.h>

static const char *const s_pHeaders[] =
{
    //most common headers
    "Accept",
    "Accept-charset",
    "Accept-EncodinG",
    "accept-language",
    "authorIzation",
    "connection",
    "coNtent-type",
    "content-Length",
    "cookiE",
    "coOkie2",
    "hoSt",
    "pRagma",
    "reFerer",
    "user-agEnt",
    "cache-control",
    "if-ModifIed-siNce",
    "if-mAtch",
    "if-none-match",
    "if-range",
    "if-unmoDified-since",
    "kEep-alIve",
    "rAnge",
    "x-Forwarded-For",
    "via",
    "transfer-encoding",

    // request-header
    "te",
    "expect",
    "max-forwards",
    "proxy-authorization",

    // general-header
    "date",
    "trailer",
    "upgrade",
    "warning",

    // entity-header
    "allow",
    "content-encoding",
    "content-language",
    "content-location",
    "content-md5",
    "content-range",
    "expires",
    "last-modified",

    // response-header
    "accept-ranges",
    "age",
    "etag",
    "location",
    "proxy-authenticate",
    "proxy-connection",
    "retry-after",
    "server",
    "vary",
    "www-authenticate",
    "status",

    //invalid headers
    "accepted",
    "age ",
    " location ",
    "\thost"

};

SUITE(HttpHeaderTest)
{

    TEST(headerIndexMatching)
    {
        const char *p;
        //int l;

        for (int i = 0; i < LSI_RSPHDR_END; ++i)
        {
            p = HttpRespHeaders::m_sPresetHeaders[i];
            //l = HttpRespHeaders::m_iPresetHeaderLen[i];

            HttpRespHeaders::INDEX index = HttpRespHeaders::getIndex(
                    p);
            CHECK(i == index);
        }

        printf("\nFinish checking resp headers indx matching. \n");
    }

    TEST(testLookup)
    {
        int size = sizeof(s_pHeaders) / sizeof(char *);
        int i;
        for (i = 0; i < size; i++)
        {
            if (i < HttpHeader::H_TE)
            {
                //printf( "%s\n", s_pHeaders[i] );
                int index = HttpHeader::getIndex2(s_pHeaders[i]);
                CHECK(i == index);
                CHECK((int)strlen(s_pHeaders[i]) ==
                      HttpHeader::getHeaderStringLen(i));
//            CHECK( 0 == strncasecmp( s_pHeaders[i],
//                                    HttpHeader::getHeader( i ),
//                                    strlen( s_pHeaders[i]) ) );
            }
            else
            {
//            CHECK( NULL == HttpHeader::getHeader( i ));
                CHECK(HttpHeader::H_HEADER_END ==
                      HttpHeader::getIndex2(s_pHeaders[i]));
            }
        }

        static const char *respHeaders[] =
        {
            "content-type",
            "content-length",
            "content-encoding",
            "cache-control",
            "location",
            "pragma",
            "status",
            "transfer-encoding",
            "proxy-connection",
            "server"
        };
        static int respHeaderIndex[] =
        {
            HttpRespHeaders::H_CONTENT_TYPE,
            HttpRespHeaders::H_CONTENT_LENGTH,
            HttpRespHeaders::H_CONTENT_ENCODING,
            HttpRespHeaders::H_CACHE_CTRL,
            HttpRespHeaders::H_LOCATION,
            HttpRespHeaders::H_PRAGMA,
            HttpRespHeaders::H_CGI_STATUS,
            HttpRespHeaders::H_TRANSFER_ENCODING,
            HttpRespHeaders::H_PROXY_CONNECTION,
            HttpRespHeaders::H_SERVER
        };
        size = sizeof(respHeaders) / sizeof(char *);
        for (i = 0; i < size; i++)
        {
            //printf( "%s\n", respHeaders[i] );
            HttpRespHeaders::INDEX index = HttpRespHeaders::getIndex(
                    respHeaders[i]);
            CHECK(index == respHeaderIndex[i]);
            CHECK((int)strlen(respHeaders[i]) ==
                  HttpRespHeaders::getHeaderStringLen(index));
        }
    }

    TEST(testInstance)
    {
//    HttpHeader header;
//    const char * pSample[] =
//    {
//        "host","localhost:2080",
//        "user-agent","Mozilla/5.0 (X11; U; Linux i686; en-US; rv:0.9.2.1) Gecko/20010901",
//        "accept","text/xml, application/xml, application/xhtml+xml, text/html;q=0.9, image/png, image/jpeg, image/gif;q=0.2, text/plain;q=0.8, text/css",
//        "accept-language","en-us",
//        "accept-encoding","gzip,deflate,compress,identity",
//        "accept-charset","ISO-8859-1, utf-8;q=0.66, *;q=0.66",
//        "keep-alive","300",
//        "connection","keep-alive"
//    };
//    const char * pVerfiy =
//    "host: localhost:2080\r\n"
//    "user-agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:0.9.2.1) Gecko/20010901\r\n"
//    "accept: text/xml, application/xml, application/xhtml+xml, text/html;q=0.9, image/png, image/jpeg, image/gif;q=0.2, text/plain;q=0.8, text/css\r\n"
//    "accept-language: en-us\r\n"
//    "accept-encoding: gzip,deflate,compress,identity\r\n"
//    "accept-charset: ISO-8859-1, utf-8;q=0.66, *;q=0.66\r\n"
//    "keep-alive: 300\r\n"
//    "connection: keep-alive\r\n";
//
//    HttpBuf httpBuf;
//    //test HttpHeader::append()
//    for( int i = 0; i < (int)(sizeof( pSample ) / sizeof( char *)); i+=2 )
//    {
//        CHECK( header.append( &httpBuf,
//                                pSample[i], pSample[i+1] ) == 0);
//    }
//    //httpBuf.append( "\0", 1 );
//    //printf( "%s\n", httpBuf.begin() );
//    CHECK( 0 == strncmp( pVerfiy, httpBuf.begin(), sizeof( pVerfiy ) ) );
//    for( int i = 0; i < (int)(sizeof( pSample ) / sizeof( char *)); i += 2 )
//    {
//        int index = HttpHeader::getIndex( pSample[i] );
//        CHECK( 0 ==
//            strncmp( header.getHeaderValue( &httpBuf, index ), pSample[i + 1],
//                strlen( pSample[i+1] ) ) );
//        CHECK( 0 ==
//            strncmp( header.getHeaderKey( &httpBuf, index ), pSample[i],
//                strlen( pSample[i] ) ) );
//        CHECK( 0 ==
//            strncmp( header.getHeaderValue( &httpBuf, pSample[i] ),
//                pSample[i + 1], strlen( pSample[i + 1] ) ) ) ;
//    }
//
//    // test HttpHeader::add()
//    HttpHeader header1;
//    for( int i = 0; i < (int)(sizeof( pSample ) / sizeof( char *)); i += 2 )
//    {
//        int index = HttpHeader::getIndex( pSample[i] );
//        const char * pValue = header.getHeaderValue( &httpBuf, index );
//        const char * pKey = header.getHeaderKey( &httpBuf, index );
//        header1.add( index, pKey - httpBuf.begin(),
//                pValue - httpBuf.begin(), strlen( pSample[i] ) );
//    }
//    for( int i = 0; i < (int)(sizeof( pSample ) / sizeof( char *)); i += 2 )
//    {
//        int index = HttpHeader::getIndex( pSample[i] );
//        CHECK( 0 ==
//            strncmp( header.getHeaderValue( &httpBuf, index ), pSample[i + 1],
//                strlen( pSample[i+1] ) ) );
//        CHECK( 0 ==
//            strncmp( header.getHeaderKey( &httpBuf, index ), pSample[i],
//                strlen( pSample[i] ) ) );
//        CHECK( 0 ==
//            strncmp( header.getHeaderValue( &httpBuf, pSample[i] ),
//                pSample[i + 1], strlen( pSample[i + 1] ) ) ) ;
//    }

    }


    TEST(benchmarkLookup)
    {
        //ProfileTime prof( "HttpHeader lookup benchmark" );
        int size = sizeof(s_pHeaders) / sizeof(char *);
        for (int i = 0; i < 1000000; i++)
            HttpHeader::getIndex(s_pHeaders[ rand() % size ]);
    }


    void displaySpdyHeaders(HttpRespHeaders * pRespHeaders)
    {
        struct iovec iov[10];
        int total = 0;
        char *key;
        int keyLen;

        printf("\r\n*******************************************************************\r\n\r\n");
        for (int pos = pRespHeaders->HeaderBeginPos();
             pos != pRespHeaders->HeaderEndPos();
             pos = pRespHeaders->nextHeaderPos(pos))
        {
            int count = pRespHeaders->getHeader(pos, &key, &keyLen, iov, 10);
            if (count >= 1)
            {
                for (int i = 0; i < keyLen; ++i)
                    printf("%c", *(key + i));

                printf(": ");
                for (int j = 0; j < count; ++j)
                {
                    for (size_t ii = 0; ii < iov[j].iov_len; ++ii)
                        printf("%c", *((char *)iov[j].iov_base + ii));

                    printf("\r\n");
                }
                total ++;
            }
        }

        printf("\r\nspdy totla= %d\r\n*******************************************************************\r\n\r\n",
               total);
    }


    void DisplayBothHeader(IOVec io, int format, short count,
                           HttpRespHeaders * pRespHeaders)
    {
        IOVec::iterator it;
        unsigned char *p = NULL;
        it = io.begin();
        p = (unsigned char *)it->iov_base;
        //return;//comment this out to view header data


        for (it = io.begin(); it != io.end(); ++it)
        {
            p = (unsigned char *)it->iov_base;
            for (unsigned int i = 0; i < it->iov_len; ++i)
            {
                if (format  != 0)
                    printf("%02X ", p[i]);
                else
                    printf("%c", p[i]);
            }
        }
        printf("\r\nplain http Count = %d\r\n======================================================\r\n",
               count);

        displaySpdyHeaders(pRespHeaders);

//     if (format != 0)
//     {
//         AutoBuf buf;
//         for (it = io.begin(); it != io.end(); ++it)
//         {
//             buf.append( (const char *)it->iov_base, it->iov_len);
//         }
//
//         if (format ==  1)
//         {
//             char *p = buf.begin();
//             short *tempNumS;
//             short tempNum;
//
//             for (int j=0; j<count; ++j)
//             {
//                 tempNumS = (short *)p;
//                 tempNum = ntohs(*tempNumS);
//                 p += 2;
//                 for (int n=0; n<tempNum; ++n){
//                     printf("%c", *(p + n));
//                 }
//                 printf(": ");
//                 p += tempNum;
//
//                 tempNumS = (short *)p;
//                 tempNum = ntohs(*tempNumS);
//                 p += 2;
//                 for (int n=0; n<tempNum; ++n){
//                     if (*(p + n) != 0)
//                         printf("%c", *(p + n));
//                     else
//                         printf("\r\n\t");
//                 }
//                 printf("\r\n");
//                 p += tempNum;
//             }
//         }
//         else
//         {
//             char *p = buf.begin();
//             int32_t *tempNumS;
//             int32_t tempNum;
//
//             for (int j=0; j<count; ++j)
//             {
//                 tempNumS = (int32_t *)p;
//                 tempNum = ntohl(*tempNumS);
//                 p += 4;
//                 for (int n=0; n<tempNum; ++n){
//                     printf("%c", *(p + n));
//                 }
//                 printf(": ");
//                 p += tempNum;
//
//                 tempNumS = (int32_t *)p;
//                 tempNum = ntohl(*tempNumS);
//                 p += 4;
//                 for (int n=0; n<tempNum; ++n){
//                     if (*(p + n) != 0)
//                         printf("%c", *(p + n));
//                     else
//                         printf("\r\n\t");
//                 }
//                 printf("\r\n");
//                 p += tempNum;
//             }
//         }
//
//         printf("\r\n*******************************************************************\r\n\r\n");
//
//     }

    }

    void CheckIoHeader(IOVec io, char *phBuf)
    {
        IOVec::iterator it;
        unsigned char *p = NULL;
        char *ph = phBuf;

//printf("->&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&\n");


        for (it = io.begin(); it != io.end(); ++it)
        {
            p = (unsigned char *)it->iov_base;
            printf("Check: %.*s, %.*s\n", (int)it->iov_len, p,
                   (int)it->iov_len, ph);
            CHECK(strncasecmp((const char *)p, ph, it->iov_len) == 0);
            if (strncasecmp((const char *)p, ph, it->iov_len) != 0)
                printf("p:\n%.*s\nph:\n%.*s\n", (int)it->iov_len, p,
                       (int)it->iov_len, ph);
            ph += it->iov_len;
        }

//printf("<-&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&\n");
    }


    TEST(respHeadersCrash)
    {
        char headerData[] =
            "X-Powered-By: PHP/5.3.29\r\n"
            "Set-Cookie: PHPSESSID=us6sr4noanp02s0its2dgv35m1; path=/\r\n"
            "Expires: Thu, 19 Nov 1981 08:52:00 GMT\r\n"
            "X-Pingback: http://www.theeverafterbridal.com/xmlrpc.php\r\n"
            "Content-Type: text/html; charset=UTF-8\r\n"
            "Set-Cookie: wordpress_fa5eb9fde7bf3f7f3fd8640562242bba=+; expires=Fri, 06-Jun-2014 04:43:43 GMT; path=/wp-admin\r\n"
            "Set-Cookie: wordpress_sec_fa5eb9fde7bf3f7f3fd8640562242bba=+; expires=Fri, 06-Jun-2014 04:43:43 GMT; path=/wp-admin\r\n"
            "Set-Cookie: wordpress_fa5eb9fde7bf3f7f3fd8640562242bba=+; expires=Fri, 06-Jun-2014 04:43:43 GMT; path=/wp-content/plugins\r\n"
            "Set-Cookie: wordpress_sec_fa5eb9fde7bf3f7f3fd8640562242bba=+; expires=Fri, 06-Jun-2014 04:43:43 GMT; path=/wp-content/plugins\r\n"
            "Set-Cookie: wordpress_logged_in_fa5eb9fde7bf3f7f3fd8640562242bba=+; expires=Fri, 06-Jun-2014 04:43:43 GMT; path=/\r\n"
            "Set-Cookie: wordpress_logged_in_fa5eb9fde7bf3f7f3fd8640562242bba=+; expires=Fri, 06-Jun-2014 04:43:43 GMT; path=/\r\n"
            "Set-Cookie: wordpress_fa5eb9fde7bf3f7f3fd8640562242bba=+; expires=Fri, 06-Jun-2014 04:43:43 GMT; path=/\r\n"
            "Set-Cookie: wordpress_fa5eb9fde7bf3f7f3fd8640562242bba=+; expires=Fri, 06-Jun-2014 04:43:43 GMT; path=/\r\n"
            "Set-Cookie: wordpress_sec_fa5eb9fde7bf3f7f3fd8640562242bba=+; expires=Fri, 06-Jun-2014 04:43:43 GMT; path=/\r\n"
            "Set-Cookie: wordpress_sec_fa5eb9fde7bf3f7f3fd8640562242bba=+; expires=Fri, 06-Jun-2014 04:43:43 GMT; path=/\r\n"
            "Set-Cookie: wordpressuser_fa5eb9fde7bf3f7f3fd8640562242bba=+; expires=Fri, 06-Jun-2014 04:43:43 GMT; path=/\r\n"
            "Set-Cookie: wordpresspass_fa5eb9fde7bf3f7f3fd8640562242bba=+; expires=Fri, 06-Jun-2014 04:43:43 GMT; path=/\r\n"
            "Set-Cookie: wordpressuser_fa5eb9fde7bf3f7f3fd8640562242bba=+; expires=Fri, 06-Jun-2014 04:43:43 GMT; path=/\r\n"
            "Set-Cookie: wordpresspass_fa5eb9fde7bf3f7f3fd8640562242bba=+; expires=Fri, 06-Jun-2014 04:43:43 GMT; path=/\r\n"
            "Cache-Control: no-store, no-cache, must-revalidate, max-age=0\r\n";

        char headerData1[] =
            "Cache-Control: post-check=0, pre-check=0\r\n";

        char headerData2[] = ":\r\n\r\n";

        ls_xpool_t *pool = ls_xpool_new();
        HttpRespHeaders h(pool);
        h.reset();

        h.parseAdd(headerData, sizeof(headerData) - 1, LSI_HEADEROP_ADD);
        h.parseAdd(headerData1, sizeof(headerData1) - 1, LSI_HEADEROP_ADD);
        h.parseAdd(headerData2, sizeof(headerData2) - 1, LSI_HEADEROP_ADD);
    }


    TEST(respHeaders)
    {
        ls_xpool_t *pool = ls_xpool_new();
        HttpRespHeaders h(pool);
        IOVec io;
        const char *pVal = NULL;
        int valLen = 0;
        char sTestHdr[1500];

        printf("============= Response Header Test ==================\n");



        int kk = 0;// non-spdy case
        //for (int kk=0; kk<1; ++kk)
        {
            h.reset();
            h.add(HttpRespHeaders::H_SERVER, "My_Server", 9);
            h.add(HttpRespHeaders::H_ACCEPT_RANGES, "bytes", 5);
            h.add(HttpRespHeaders::H_DATE, "Thu, 16 May 2013 20:32:23 GMT",
                  strlen("Thu, 16 May 2013 20:32:23 GMT"));
            h.add(HttpRespHeaders::H_X_POWERED_BY, "PHP/5.3.24", strlen("PHP/5.3.24"));
            h.outputNonSpdyHeaders(&io);
            DisplayBothHeader(io, kk, h.getCount(), &h);
            strcpy(sTestHdr,
                   "HTTP/1.1 200 OK\r\nserver: My_Server\r\naccept-ranges: bytes\r\ndate: Thu, 16 May 2013 20:32:23 GMT\r\nx-powered-by: PHP/5.3.24\r\nconnection: close\r\n\r\n");
            CheckIoHeader(io, sTestHdr);
            CHECK(h.getCount() ==
                  5);   //Will add connection: close automatically

            h.reset();
            h.add(HttpRespHeaders::H_SERVER, "My_Server", 9);
            h.add(HttpRespHeaders::H_ACCEPT_RANGES, "bytes", 5);
            h.add(HttpRespHeaders::H_DATE, "Thu, 16 May 2013 20:32:23 GMT",
                  strlen("Thu, 16 May 2013 20:32:23 GMT"));
            h.add(HttpRespHeaders::H_X_POWERED_BY, "PHP/5.3.24", strlen("PHP/5.3.24"));
            h.addStatusLine(0, SC_304,
                            1);   //when ver is 0 and keepalive is 1, Will NOT add connection: close automatically
            h.outputNonSpdyHeaders(&io);
            DisplayBothHeader(io, kk, h.getCount(), &h);
            strcpy(sTestHdr, "HTTP/1.1 304 Not Modified\r\n"
                   "server: My_Server\r\naccept-ranges: bytes\r\ndate: Thu, 16 May 2013 20:32:23 GMT\r\nx-powered-by: PHP/5.3.24\r\n\r\n");
            CheckIoHeader(io, sTestHdr);
            CHECK(h.getCount() == 4);

            h.reset();
            h.add(HttpRespHeaders::H_SERVER,  "My_Server", 9);
            h.add(HttpRespHeaders::H_ACCEPT_RANGES, "bytes", 5);
            h.add(HttpRespHeaders::H_DATE, "Thu, 16 May 2013 20:32:23 GMT",
                  strlen("Thu, 16 May 2013 20:32:23 GMT"));
            h.add(HttpRespHeaders::H_DATE,  "Thu, 16 ", strlen("Thu, 16 "),
                  LSI_HEADEROP_MERGE);
            h.add(HttpRespHeaders::H_DATE,  "XXXX", 4, LSI_HEADEROP_MERGE);
            h.add(HttpRespHeaders::H_X_POWERED_BY, "PHP/5.3.24", strlen("PHP/5.3.24"));
            h.outputNonSpdyHeaders(&io);
            DisplayBothHeader(io, kk, h.getCount(), &h);
            strcpy(sTestHdr,
                   "HTTP/1.1 200 OK\r\nserver: My_Server\r\naccept-ranges: bytes\r\ndate: Thu, 16 May 2013 20:32:23 GMT,Thu, 16 ,XXXX\r\nx-powered-by: PHP/5.3.24\r\nconnection: close\r\n\r\n");
            CheckIoHeader(io, sTestHdr);

            h.add(HttpRespHeaders::H_DATE,  "NEWDATE", 7, LSI_HEADEROP_ADD);
            h.outputNonSpdyHeaders(&io);
            DisplayBothHeader(io, kk, h.getCount(), &h);
            strcpy(sTestHdr,
                   "HTTP/1.1 200 OK\r\nserver: My_Server\r\naccept-ranges: bytes\r\ndate: Thu, 16 May 2013 20:32:23 GMT,Thu, 16 ,XXXX\r\nx-powered-by: PHP/5.3.24\r\nconnection: close\r\ndate: NEWDATE\r\n\r\n");
            CheckIoHeader(io, sTestHdr);

            h.add(HttpRespHeaders::H_DATE,  "NEWDATE2", 8, LSI_HEADEROP_ADD);
            h.outputNonSpdyHeaders(&io);
            DisplayBothHeader(io, kk, h.getCount(), &h);
            strcpy(sTestHdr,
                   "HTTP/1.1 200 OK\r\nserver: My_Server\r\naccept-ranges: bytes\r\ndate: Thu, 16 May 2013 20:32:23 GMT,Thu, 16 ,XXXX\r\nx-powered-by: PHP/5.3.24\r\nconnection: close\r\ndate: NEWDATE\r\ndate: NEWDATE2\r\n\r\n");
            CheckIoHeader(io, sTestHdr);

            h.add(HttpRespHeaders::H_DATE,  "NEWDATE3", 8, LSI_HEADEROP_ADD);
            h.outputNonSpdyHeaders(&io);
            DisplayBothHeader(io, kk, h.getCount(), &h);
            strcpy(sTestHdr,
                   "HTTP/1.1 200 OK\r\nserver: My_Server\r\naccept-ranges: bytes\r\ndate: Thu, 16 May 2013 20:32:23 GMT,Thu, 16 ,XXXX\r\nx-powered-by: PHP/5.3.24\r\nconnection: close\r\ndate: NEWDATE\r\ndate: NEWDATE2\r\ndate: NEWDATE3\r\n\r\n");
            CheckIoHeader(io, sTestHdr);


            h.del(HttpRespHeaders::H_DATE);
            h.outputNonSpdyHeaders(&io);
            DisplayBothHeader(io, kk, h.getCount(), &h);
            CHECK(h.getCount() == 4);
            strcpy(sTestHdr,
                   "HTTP/1.1 200 OK\r\nserver: My_Server\r\naccept-ranges: bytes\r\nx-powered-by: PHP/5.3.24\r\nconnection: close\r\n\r\n");
            CheckIoHeader(io, sTestHdr);


            h.del("X-Powered-By", strlen("X-Powered-By"));
            h.outputNonSpdyHeaders(&io);
            DisplayBothHeader(io, kk, h.getCount(), &h);
            CHECK(h.getCount() == 3);
            strcpy(sTestHdr,
                   "HTTP/1.1 200 OK\r\nserver: My_Server\r\naccept-ranges: bytes\r\nconnection: close\r\n\r\n");
            CheckIoHeader(io, sTestHdr);

            h.add(HttpRespHeaders::H_SERVER,  "YY_Server", 9);
            h.outputNonSpdyHeaders(&io);
            DisplayBothHeader(io, kk, h.getCount(), &h);
            CHECK(h.getCount() == 3);
            strcpy(sTestHdr,
                   "HTTP/1.1 200 OK\r\nserver: YY_Server\r\naccept-ranges: bytes\r\nconnection: close\r\n\r\n");
            CheckIoHeader(io, sTestHdr);


            h.add(HttpRespHeaders::H_SERVER,  "XServer", 7);
            h.outputNonSpdyHeaders(&io);
            DisplayBothHeader(io, kk, h.getCount(), &h);
            CHECK(h.getCount() == 3);
            strcpy(sTestHdr,
                   "HTTP/1.1 200 OK\r\nserver: XServer  \r\naccept-ranges: bytes\r\nconnection: close\r\n\r\n");
            CheckIoHeader(io, sTestHdr);

            h.add(HttpRespHeaders::H_DATE,  "Thu, 16 May 2099 20:32:23 GMT",
                  strlen("Thu, 16 May 2013 20:32:23 GMT"));
            h.add(HttpRespHeaders::H_X_POWERED_BY, "PHP/9.9.99", strlen("PHP/5.3.24"));
            h.outputNonSpdyHeaders(&io);
            DisplayBothHeader(io, kk, h.getCount(), &h);
            CHECK(h.getCount() == 5);
            strcpy(sTestHdr,
                   "HTTP/1.1 200 OK\r\nserver: XServer  \r\naccept-ranges: bytes\r\nconnection: close\r\ndate: Thu, 16 May 2099 20:32:23 GMT\r\nx-powered-by: PHP/9.9.99\r\n\r\n");
            CheckIoHeader(io, sTestHdr);


            h.add("Allow", 5, "*.*", 3);
            h.appendLastVal("; .zip; .rar", strlen("; .zip; .rar"));
            h.appendLastVal("; .exe; .flv", strlen("; .zip; .rar"));
            h.outputNonSpdyHeaders(&io);
            DisplayBothHeader(io, kk, h.getCount(), &h);
            CHECK(h.getCount() == 6);
            strcpy(sTestHdr,
                   "HTTP/1.1 200 OK\r\nserver: XServer  \r\naccept-ranges: bytes\r\nconnection: close\r\ndate: Thu, 16 May 2099 20:32:23 GMT\r\nx-powered-by: PHP/9.9.99\r\nallow: *.*; .zip; .rar; .exe; .flv\r\n\r\n");
            CheckIoHeader(io, sTestHdr);


            h.add(HttpRespHeaders::H_SET_COOKIE,
                  "lsws_uid=a; expires=Mon, 13 May 2013 14:10:51 GMT; path=/",
                  strlen("lsws_uid=a; expires=Mon, 13 May 2013 14:10:51 GMT; path=/"),
                  LSI_HEADEROP_ADD);

            h.add(HttpRespHeaders::H_SET_COOKIE,
                  "lsws_pass=b; expires=Mon, 13 May 2013 14:10:51 GMT; path=/",
                  strlen("lsws_pass=b; expires=Mon, 13 May 2013 14:10:51 GMT; path=/"),
                  LSI_HEADEROP_ADD);

            h.add("testBreak", 9, "----", 4);

            h.add(HttpRespHeaders::H_SET_COOKIE,
                  "lsws_uid=c; expires=Mon, 13 May 2013 14:10:51 GMT; path=/",
                  strlen("lsws_uid=c; expires=Mon, 13 May 2013 14:10:51 GMT; path=/"),
                  LSI_HEADEROP_ADD);
            h.outputNonSpdyHeaders(&io);
            DisplayBothHeader(io, kk, h.getCount(), &h);
            CHECK(h.getUniqueCnt() == 8);
            CHECK(h.getCount() == 10);
            strcpy(sTestHdr,
                   "HTTP/1.1 200 OK\r\nserver: XServer  \r\naccept-ranges: bytes\r\nconnection: close\r\ndate: Thu, 16 May 2099 20:32:23 GMT\r\nx-powered-by: PHP/9.9.99\r\nallow: *.*; .zip; .rar; .exe; .flv\r\n");
            strcat(sTestHdr,
                   "set-cookie: lsws_uid=a; expires=Mon, 13 May 2013 14:10:51 GMT; path=/\r\nset-cookie: lsws_pass=b; expires=Mon, 13 May 2013 14:10:51 GMT; path=/\r\ntestbreak: ----\r\nset-cookie: lsws_uid=c; expires=Mon, 13 May 2013 14:10:51 GMT; path=/\r\n\r\n");
            CheckIoHeader(io, sTestHdr);


            h.getFirstHeader("date", 4, &pVal, valLen);
            CHECK(memcmp(pVal, "Thu, 16 May 2099 20:32:23 GMT", valLen) == 0);

            h.getFirstHeader("Allow", 5, &pVal, valLen);
            CHECK(memcmp(pVal, "*.*; .zip; .rar; .exe; .flv", valLen) == 0);

            h.parseAdd("MytestHeader: TTTTTTTTTTTT\r\nMyTestHeaderii: IIIIIIIIIIIIIIIIIIIII\r\n",
                       strlen("MytestHeader: TTTTTTTTTTTT\r\nMyTestHeaderii: IIIIIIIIIIIIIIIIIIIII\r\n"));

            CHECK(h.getUniqueCnt() == 10);
            CHECK(h.getCount() == 12);
            h.getFirstHeader("MytestHeader", strlen("MytestHeader"), &pVal, valLen);
            CHECK(memcmp(pVal, "TTTTTTTTTTTT", valLen) == 0);

            //Same name, but since no check,  will be appended directly. But SPDY, will check and parse it.
            h.parseAdd("MytestHeader   :    TTTTTTTTTTTT3\r\n",
                       strlen("MytestHeader   :    TTTTTTTTTTTT3\r\n"));

            CHECK(h.getUniqueCnt() == 10);
            CHECK(h.getCount() == 12);
            h.getFirstHeader("MytestHeader", strlen("MytestHeader"), &pVal, valLen);
            CHECK(memcmp(pVal, "TTTTTTTTTTTT3", valLen) == 0);

            h.addStatusLine(0, SC_404, 1);

            h.parseAdd("MytestHeader : XXX\r\n",
                       strlen("MytestHeader : XXX\r\n"), LSI_HEADEROP_MERGE);

            h.parseAdd("Content-Encoding   \t  : GZIP\r\n",
                       strlen("Content-Encoding   \t  : GZIP\r\n"), LSI_HEADEROP_MERGE);
            h.parseAdd("Content-Encoding2 : GZIP\r\n",
                       strlen("Content-Encoding2 : GZIP\r\n"), LSI_HEADEROP_MERGE);
            h.outputNonSpdyHeaders(&io);
            DisplayBothHeader(io, kk, h.getCount(), &h);
            strcpy(sTestHdr,
                   "HTTP/1.1 404 Not Found\r\nServer: XServer  \r\nAccept-Ranges: bytes\r\nConnection: close\r\nDate: Thu, 16 May 2099 20:32:23 GMT\r\nX-Powered-By: PHP/9.9.99\r\nAllow: *.*; .zip; .rar; .exe; .flv\r\n");
            strcat(sTestHdr,
                   "Set-Cookie: lsws_uid=a; expires=Mon, 13 May 2013 14:10:51 GMT; path=/\r\nSet-Cookie: lsws_pass=b; expires=Mon, 13 May 2013 14:10:51 GMT; path=/\r\ntestBreak: ----\r\nSet-Cookie: lsws_uid=c; expires=Mon, 13 May 2013 14:10:51 GMT; path=/\r\n");
            strcat(sTestHdr,
                   "MytestHeader: TTTTTTTTTTTT3,XXX\r\nMyTestHeaderii: IIIIIIIIIIIIIIIIIIIII\r\nContent-Encoding: GZIP\r\nContent-Encoding2: GZIP\r\n\r\n");
            CheckIoHeader(io, sTestHdr);

            h.parseAdd("MytestHeader: XXX\r\n",
                       strlen("MytestHeader: XXX\r\n"), LSI_HEADEROP_MERGE);
            h.outputNonSpdyHeaders(&io);
            DisplayBothHeader(io, kk, h.getCount(), &h);
            strcpy(sTestHdr,
                   "HTTP/1.1 404 Not Found\r\nserver: XServer  \r\naccept-ranges: bytes\r\nconnection: close\r\ndate: Thu, 16 May 2099 20:32:23 GMT\r\nx-powered-by: PHP/9.9.99\r\nallow: *.*; .zip; .rar; .exe; .flv\r\n");
            strcat(sTestHdr,
                   "set-cookie: lsws_uid=a; expires=Mon, 13 May 2013 14:10:51 GMT; path=/\r\nset-cookie: lsws_pass=b; expires=Mon, 13 May 2013 14:10:51 GMT; path=/\r\ntestbreak: ----\r\nset-cookie: lsws_uid=c; expires=Mon, 13 May 2013 14:10:51 GMT; path=/\r\n");
            strcat(sTestHdr,
                   "mytestheader: TTTTTTTTTTTT3,XXX\r\nmytestheaderii: IIIIIIIIIIIIIIIIIIIII\r\nContent-Encoding: GZIP\r\nContent-Encoding2: GZIP\r\n\r\n");
            CheckIoHeader(io, sTestHdr);

            h.parseAdd("MytestHeader: XXX\r\n",
                       strlen("MytestHeader: XXX\r\n"), LSI_HEADEROP_APPEND);
            h.outputNonSpdyHeaders(&io);
            DisplayBothHeader(io, kk, h.getCount(), &h);
            strcpy(sTestHdr,
                   "HTTP/1.1 404 Not Found\r\nServer: XServer  \r\nAccept-Ranges: bytes\r\nConnection: close\r\nDate: Thu, 16 May 2099 20:32:23 GMT\r\nX-Powered-By: PHP/9.9.99\r\nAllow: *.*; .zip; .rar; .exe; .flv\r\n");
            strcat(sTestHdr,
                   "Set-Cookie: lsws_uid=a; expires=Mon, 13 May 2013 14:10:51 GMT; path=/\r\nSet-Cookie: lsws_pass=b; expires=Mon, 13 May 2013 14:10:51 GMT; path=/\r\ntestBreak: ----\r\nSet-Cookie: lsws_uid=c; expires=Mon, 13 May 2013 14:10:51 GMT; path=/\r\n");
            strcat(sTestHdr,
                   "MytestHeader: TTTTTTTTTTTT3,XXX,XXX\r\nMyTestHeaderii: IIIIIIIIIIIIIIIIIIIII\r\nContent-Encoding: GZIP\r\nContent-Encoding2: GZIP\r\n\r\n");
            CheckIoHeader(io, sTestHdr);
        }

        h.reset();
        h.add(HttpRespHeaders::H_SERVER,  "My_Server", 9);
        h.add(HttpRespHeaders::H_ACCEPT_RANGES,  "bytes", 5);
        h.add(HttpRespHeaders::H_DATE,  "Thu, 16 May 2013 20:32:23 GMT",
              strlen("Thu, 16 May 2013 20:32:23 GMT"));
        h.add(HttpRespHeaders::H_DATE,  "AAAA", 4, LSI_HEADEROP_MERGE);
        h.add(HttpRespHeaders::H_X_POWERED_BY, "PHP/5.3.24", strlen("PHP/5.3.24"));
        h.outputNonSpdyHeaders(&io);
        DisplayBothHeader(io, kk, h.getCount(), &h);
        strcpy(sTestHdr,
               "HTTP/1.1 200 OK\r\nserver: My_Server\r\naccept-ranges: bytes\r\ndate: Thu, 16 May 2013 20:32:23 GMT,AAAA\r\nx-powered-by: PHP/5.3.24\r\nconnection: close\r\n\r\n");
        CheckIoHeader(io, sTestHdr);
        h.add(HttpRespHeaders::H_DATE,  "AAA", 3, LSI_HEADEROP_MERGE);
        strcpy(sTestHdr,
               "HTTP/1.1 200 OK\r\nserver: My_Server\r\naccept-ranges: bytes\r\ndate: Thu, 16 May 2013 20:32:23 GMT,AAAA,AAA\r\nx-powered-by: PHP/5.3.24\r\nconnection: close\r\n\r\n");
        h.outputNonSpdyHeaders(&io);
        DisplayBothHeader(io, kk, h.getCount(), &h);
        CheckIoHeader(io, sTestHdr);
        h.add(HttpRespHeaders::H_DATE,  "AAA", 3, LSI_HEADEROP_MERGE);
        strcpy(sTestHdr,
               "HTTP/1.1 200 OK\r\nserver: My_Server\r\naccept-ranges: bytes\r\ndate: Thu, 16 May 2013 20:32:23 GMT,AAAA,AAA\r\nx-powered-by: PHP/5.3.24\r\nconnection: close\r\n\r\n");
        h.outputNonSpdyHeaders(&io);
        DisplayBothHeader(io, kk, h.getCount(), &h);
        CheckIoHeader(io, sTestHdr);
        h.add(HttpRespHeaders::H_DATE,  "AAA", 3, LSI_HEADEROP_APPEND);
        strcpy(sTestHdr,
               "HTTP/1.1 200 OK\r\nserver: My_Server\r\naccept-ranges: bytes\r\ndate: Thu, 16 May 2013 20:32:23 GMT,AAAA,AAA,AAA\r\nx-powered-by: PHP/5.3.24\r\nconnection: close\r\n\r\n");
        h.outputNonSpdyHeaders(&io);
        DisplayBothHeader(io, kk, h.getCount(), &h);
        CheckIoHeader(io, sTestHdr);

        ls_xpool_delete(pool);

        /*

        int temp;
        struct iovec ios[1000];
        int i;
        char *key;
        int keyLen;
        int totalLen = 0;
        IOVec::iterator it;
        char *ph;
        char *p;
        

        static const char * s_pHeaders[HttpRespHeaders::H_HEADER_END] =
        {
            "ACCEPT-RANGES",
            "CONNECTION",
            "CONTENT-TYPE",
            "CONTENT-LENGTH",
            "CONTENT-ENCODING",
            "CONTENT-RANGE",
            "CONTENT-DISPOSITION",
            "CACHE-control",
            "DATE",
            "ETAG",
            "EXPIRES",
            "KEEP-ALIVE",
            "LAST-MODIFIED",
            "LOCATION",
            "x-litespeed-location",
            "X-LITESPEED-CACHE-CONTROL",
            "PRAGMA",
            "PROXY-CONNECTION",
            "SERVER",
            "SET-COOKIE",
            "STATUS",
            "TRANSFER-ENCODING",
            "VARY",
            "WWW-AUTHENTICATE",
            "X-LITESPEED-CACHE",
            "X-LITESPEED-PURGE",
            "X-LITESPEED-TAG",
            "X-LITESPEED-VARY",
            "LSC-COOKIE",
            "X-POWERED-BY",
            "LINK",
        };
        static const char * s_pHeaderVals[HttpRespHeaders::H_HEADER_END] =
        {
            "xACCEPT-RANGES",
            "xCONNECTION",
            "xCONTENT-TYPE",
            "xCONTENT-LENGTH",
            "xCONTENT-ENCODING",
            "xCONTENT-RANGE",
            "xCONTENT-DISPOSITION",
            "xCACHE-control",
            "xDATE",
            "xETAG",
            "xEXPIRES",
            "xKEEP-ALIVE",
            "xLAST-MODIFIED",
            "xLOCATION",
            "xx-litespeed-location",
            "xX-LITESPEED-CACHE-CONTROL",
            "xPRAGMA",
            "xPROXY-CONNECTION",
            "xSERVER",
            "xSET-COOKIE",
            "xSTATUS",
            "xTRANSFER-ENCODING",
            "xVARY",
            "xWWW-AUTHENTICATE",
            "xX-LITESPEED-CACHE",
            "xX-LITESPEED-PURGE",
            "xX-LITESPEED-TAG",
            "xX-LITESPEED-VARY",
            "xLSC-COOKIE",
            "xX-POWERED-BY",
            "xLINK",
        };

        char s_pOutputHdr[] =
        {
            "ACCEPT-RANGES: xACCEPT-RANGES\r\n"
            "CONNECTION: xCONNECTION\r\n"
            "CONTENT-TYPE: xCONTENT-TYPE\r\n"
            "CONTENT-LENGTH: xCONTENT-LENGTH\r\n"
            "CONTENT-ENCODING: xCONTENT-ENCODING\r\n"
            "CONTENT-RANGE: xCONTENT-RANGE\r\n"
            "CONTENT-DISPOSITION: xCONTENT-DISPOSITION\r\n"
            "CACHE-control: xCACHE-control\r\n"
            "DATE: xDATE\r\n"
            "ETAG: xETAG\r\n"
            "EXPIRES: xEXPIRES\r\n"
            "KEEP-ALIVE: xKEEP-ALIVE\r\n"
            "LAST-MODIFIED: xLAST-MODIFIED\r\n"
            "LOCATION: xLOCATION\r\n"
            "x-litespeed-location: xx-litespeed-location\r\n"
            "X-LITESPEED-CACHE-CONTROL: xX-LITESPEED-CACHE-CONTROL\r\n"
            "PRAGMA: xPRAGMA\r\n"
            "PROXY-CONNECTION: xPROXY-CONNECTION\r\n"
            "SERVER: xSERVER\r\n"
            "SET-COOKIE: xSET-COOKIE\r\n"
            "STATUS: xSTATUS\r\n"
            "TRANSFER-ENCODING: xTRANSFER-ENCODING\r\n"
            "VARY: xVARY\r\n"
            "WWW-AUTHENTICATE: xWWW-AUTHENTICATE\r\n"
            "X-LITESPEED-CACHE: xX-LITESPEED-CACHE\r\n"
            "X-LITESPEED-PURGE: xX-LITESPEED-PURGE\r\n"
            "X-LITESPEED-TAG: xX-LITESPEED-TAG\r\n"
            "X-LITESPEED-VARY: xX-LITESPEED-VARY\r\n"
            "LSC-COOKIE: xLSC-COOKIE\r\n"
            "X-POWERED-BY: xX-POWERED-BY\r\n"
            "Link: xLINK\r\n"
        };


        //fill the header array
        http_header_t headerArray1[HttpRespHeaders::H_HEADER_END];
        for (i=0; i<HttpRespHeaders::H_HEADER_END;i++)
        {
            CHECK( i == HttpRespHeaders::getIndex(s_pHeaders[i]));
            headerArray1[i].index = (const HttpRespHeaders::INDEX)(i);
            //headerArray1[i].name = s_pHeaders[i];
            //headerArray1[i].nameLen = strlen(s_pHeaders[i]);
            headerArray1[i].val = s_pHeaderVals[i];
            headerArray1[i].valLen = strlen(s_pHeaderVals[i]);
        }
        h.reset();
        //add using array add and check contents
        temp = h.add(headerArray1, 26);
        CHECK(h.getCount() == 26);
        CHECK(temp == 0);
        for ( i=h.HeaderBeginPos(); i!=h.HeaderEndPos(); i=h.nextHeaderPos(i) )
        {
            temp = h.getHeader(i, &key, &keyLen, ios, 26);
            CHECK(memcmp(key, s_pHeaders[i], keyLen) == 0);
            CHECK(temp == 1);//CTBTODO is this correct
        }

        //add using header index and check counts and contents using getHeader
        h.reset();
        for (i=0; i<HttpRespHeaders::H_HEADER_END;i++)
        {
            temp = h.add((const HttpRespHeaders::INDEX)(i), s_pHeaders[i], strlen(s_pHeaders[i]), s_pHeaderVals[i], strlen(s_pHeaderVals[i]));
            CHECK(temp == 0);
            temp = h.getCount();
            temp = h.getTotalCount();
            CHECK(h.getCount() == i+1);//start at 1 and add 1 for connection close
            CHECK(h.getTotalCount() == i+1);

            temp = h.getHeader(s_pHeaders[i], strlen(s_pHeaders[i]), &pVal, valLen);
            CHECK (memcmp(pVal, s_pHeaderVals[i], strlen(s_pHeaderVals[i])) == 0);
            CHECK (valLen == strlen(s_pHeaderVals[i]));
            CHECK(temp == 0);//CTBTODO check this

            temp = h.getHeader(s_pHeaders[i], strlen(s_pHeaders[i]), ios, 30);
            pVal = (char *)(ios[0].iov_base);
            CHECK(memcmp(pVal, s_pHeaderVals[i], strlen(s_pHeaderVals[i])) == 0);
            CHECK(ios[0].iov_len == strlen(s_pHeaderVals[i]));
            CHECK(temp == 1);

            temp = h.getHeader((const HttpRespHeaders::INDEX)(i), ios, 30);
            CHECK(memcmp((char *)(ios[0].iov_base), s_pHeaderVals[i], strlen(s_pHeaderVals[i])) == 0);
            CHECK(ios[0].iov_len == strlen(s_pHeaderVals[i]));
            //for unknown, it is 0
            if (i==HttpRespHeaders::H_UNKNOWN)
                CHECK(temp == 0);
            else
                CHECK(temp == 1);
        }


        //check using getAllHeaders into io struct
        temp = h.getAllHeaders( ios, 30 );
        CHECK(temp == 26);
        for (i=0; i<HttpRespHeaders::H_HEADER_END;i++)
        {
            pVal = (char *)(ios[i].iov_base);
            CHECK(memcmp((char *)(ios[i].iov_base), s_pHeaders[i], strlen(s_pHeaders[i])) == 0);
            CHECK(ios[i].iov_len == strlen(s_pHeaders[i])+strlen(s_pHeaderVals[i])+4);
        }

        h.reset();
        temp = h.add(headerArray1, 26);
        CHECK(h.getCount() == 26);
        CHECK(temp == 0);
        //check del index
        int count = h.getCount();
        for (i=0; i<HttpRespHeaders::H_HEADER_END;i++)
        {
            temp = h.del((const HttpRespHeaders::INDEX)(i));
            if (i==HttpRespHeaders::H_UNKNOWN)
                CHECK(temp == -1);
            else
                CHECK(temp == 0);
            temp = h.getCount();
            CHECK(h.getCount() == count);//add 1 for connection close
            temp = h.getTotalCount();
            //CHECK(h.getTotalCount() == count);//may be removed always returns 26
            count--;

            temp = h.getHeader(s_pHeaders[i], strlen(s_pHeaders[i]), &pVal, valLen);//should fail - removed
            if (i==HttpRespHeaders::H_UNKNOWN)
                CHECK(temp == 0);
            else
                CHECK(temp == -1);//first pass 0 unknown not removed

        }

        temp = h.outputNonSpdyHeaders(&io);
        CHECK(temp == 0);
        temp = h.getTotalLen();
        CHECK(h.getTotalLen() == 57);
        temp = h.getAllHeaders( ios, 30 );
        CHECK(temp == 2);//unknown not removed and close
        DisplayBothHeader(io, kk, h.getCount(), &h);
        strcpy(sTestHdr, "HTTP/1.1 200 OK\r\nUNKNOWN: xUNKNOWN\r\nConnection: close\r\n\r\n");
        CheckIoHeader(io,sTestHdr);



        h.reset();
        temp = h.add(headerArray1, 26);
        count = h.getCount();
        //check del by name
        for (i=0; i<HttpRespHeaders::H_HEADER_END;i++)
        {
            temp = h.del(s_pHeaders[i], strlen(s_pHeaders[i]));
            count--;
            CHECK(temp == 0);
            temp = h.getCount();
            CHECK(h.getCount() == count);//start at 1 and add 1 for connection close

            temp = h.getHeader(s_pHeaders[i], strlen(s_pHeaders[i]), &pVal, valLen);
            CHECK(temp == -1);
        }

        temp = h.outputNonSpdyHeaders(&io);
        CHECK(temp == 0);
        temp = h.getTotalLen();
        CHECK(h.getTotalLen() == 38);//should be 57 the same as above?
        temp = h.getAllHeaders( ios, 30 );
        CHECK(temp == 1);//unknown was removed and close should be 2?
        DisplayBothHeader(io, kk, h.getCount(), &h);
        strcpy(sTestHdr, "HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n");
        CheckIoHeader(io,sTestHdr);


        //check resest and headers built flag
        h.reset();
        CHECK(h.getCount() == 0);
        CHECK(h.isRespHeadersBuilt() == 0);

        //check del unknown
        h.del(HttpRespHeaders::H_DATE);// it is correct behavior not to remove
        h.del("X", strlen("X"));
        h.add(HttpRespHeaders::H_UNKNOWN, "unknown", 7, "My_Server", 9);
        h.add(HttpRespHeaders::H_ACCEPT_RANGES,  "bytes", 5);
        h.add(HttpRespHeaders::H_DATE,  "Thu, 16 May 2013 20:32:23 GMT", strlen("Thu, 16 May 2013 20:32:23 GMT"));
        h.add(HttpRespHeaders::H_X_POWERED_BY, "PHP/5.3.24", strlen("PHP/5.3.24"));
        h.addStatusLine( 0, 304, 1);  //when ver is 0 and keepalive is 1, Will NOT add connection: close automatically
        h.outputNonSpdyHeaders(&io);

        CHECK(h.isRespHeadersBuilt() == 1);
        CHECK(h.getCount() == 4);
        h.del(HttpRespHeaders::H_UNKNOWN);// it is correct behavior not to remove
        CHECK(h.getCount() == 4);
        h.del(HttpRespHeaders::H_ACCEPT_RANGES);
        CHECK(h.getCount() == 3);
        h.del("X", strlen("X"));
        CHECK(h.getCount() == 3);
        DisplayBothHeader(io, kk, h.getCount(), &h);
        strcpy(sTestHdr, "unknown: My_Server\r\nAccept-Ranges: bytes\r\nDate: Thu, 16 May 2013 20:32:23 GMT\r\nX-Powered-By: PHP/5.3.24\r\n\r\n");
        CheckIoHeader(io,sTestHdr);

        //check content type
        pVal = h.getContentTypeHeader(temp);//
        CHECK(temp == -1);
        h.add(HttpRespHeaders::H_CONTENT_TYPE, "Content-Type", strlen("content-type"), "typeA", strlen("typeA"));
        pVal = h.getContentTypeHeader(temp);//
        CHECK(temp == 5);
        CHECK (memcmp(pVal, "typeA", 5) == 0);


        h.reset();
        http_header_t headerArray[5];
        headerArray[0].index = HttpRespHeaders::H_CONTENT_ENCODING;
        headerArray[0].val = "Hello";
        headerArray[0].valLen = 5;
        headerArray[1].index = HttpRespHeaders::H_ACCEPT_RANGES;
        headerArray[1].val = "val";
        headerArray[1].valLen = 3;
        h.add(headerArray, 2);
        CHECK(h.getCount() == 2);
        h.getHeader("content-encoding", strlen("content-encoding"), &pVal, valLen);
        CHECK (memcmp(pVal, "Hello", valLen) == 0);
        h.getHeader("Accept-Ranges", strlen("Accept-Ranges"), &pVal, valLen);
        CHECK (memcmp(pVal, "val", valLen) == 0);
        h.getHeader("Not_A_Header", strlen("Accept-Ranges"), &pVal, valLen);

        for ( i=h.HeaderBeginPos(); i!=h.HeaderEndPos(); i=h.nextHeaderPos(i) )
        {
            temp = h.getHeader(i, &key, &keyLen, ios, 10);
            CHECK(memcmp(key, headerArray[i].name, keyLen) == 0);
        }

        //check http version and code defaults and set
        temp = h.getHttpVersion();
        CHECK(temp == 0); //default
        temp = h.getHttpCode();
        CHECK(temp == 4); //default
        h.addStatusLine( 1, SC_304, 1);
        temp = h.getHttpVersion();
        CHECK(temp == 1);
        temp = h.getHttpCode();
        CHECK(temp == 17);

        //check total count
        temp = h.getTotalCount();
        CHECK(temp == 2);

        //check string len
        temp = h.getHeaderStringLen( HttpRespHeaders::H_CONTENT_ENCODING );
        CHECK(temp == 16);

        //check total length default and set
        temp = h.getTotalLen();
        CHECK(temp == 0);
        h.outputNonSpdyHeaders(&io);
        temp = h.getTotalLen();
        CHECK(temp == 98);

        temp = h.getHeader("content-encoding", 16, ios, 10);
        pVal = (char *)(ios[0].iov_base);
        CHECK(memcmp((char *)(ios[0].iov_base), "Hello", 5) == 0);
        CHECK(ios[0].iov_len == 5);
        temp = h.getHeader(HttpRespHeaders::H_CONTENT_ENCODING, ios, 10);
        CHECK(memcmp((char *)(ios[0].iov_base), "Hello", 5) == 0);
        CHECK(ios[0].iov_len == 5);

        temp = h.getAllHeaders( ios, 10 );
        pVal = (char *)(ios[0].iov_base);
        CHECK(memcmp((char *)(ios[0].iov_base), "content-encoding", 16) == 0);
        CHECK(ios[0].iov_len == 25);
        CHECK(memcmp((char *)(ios[1].iov_base), "Accept-Ranges", 13) == 0);
        CHECK(ios[1].iov_len == 20);

        //test new functions
        //header len < 64k add 10k header lot of short headers
        h.reset();
        h.addGzipEncodingHeader();
        h.appendChunked();
        //h.appendAcceptRange();
        h.buildCommonHeaders();
        h.addCommonHeaders();
        h.del(HttpRespHeaders::H_DATE);//delete current date for testing
        //h.updateDateHeader();// called in build...
        temp = h.getHeader("server", 6, ios, 10);
        pVal = (char *)(ios[0].iov_base);
        CHECK(memcmp((char *)(ios[0].iov_base), "LiteSpeed", 9) == 0);
        temp = ios[0].iov_len;
        CHECK(ios[0].iov_len == 9);
        DisplayBothHeader(io, kk, h.getCount(), &h);

        h.reset();
        h.hideServerSignature(0);
        h.buildCommonHeaders();
        h.addCommonHeaders();
        h.del(HttpRespHeaders::H_DATE);
        temp = h.getHeader("server", 6, ios, 10);
        pVal = (char *)(ios[0].iov_base);
        CHECK(memcmp((char *)(ios[0].iov_base), "LiteSpeed", 9) == 0);
        CHECK(ios[0].iov_len == 9);
        h.outputNonSpdyHeaders(&io);
        DisplayBothHeader(io, kk, h.getCount(), &h);
        strcpy(sTestHdr, "HTTP/1.1 200 OK\r\nServer: LiteSpeed\r\nConnection: close\r\n\r\n");
        CheckIoHeader(io,sTestHdr);

        h.reset();
        h.hideServerSignature(1);
        h.buildCommonHeaders();
        h.addCommonHeaders();
        h.del(HttpRespHeaders::H_DATE);
        temp = h.getHeader("server", 6, ios, 10);
        pVal = (char *)(ios[0].iov_base);
        CHECK(memcmp((char *)(ios[0].iov_base), "LiteSpeed/1.2.4 Open", 20) == 0);
        CHECK(ios[0].iov_len == 20);
        h.outputNonSpdyHeaders(&io);
        DisplayBothHeader(io, kk, h.getCount(), &h);
        strcpy(sTestHdr, "HTTP/1.1 200 OK\r\nServer: LiteSpeed/1.2.4 Open\r\nConnection: close\r\n\r\n");
        CheckIoHeader(io,sTestHdr);

        h.reset();
        h.hideServerSignature(2);
        h.buildCommonHeaders();
        h.addCommonHeaders();
        h.del(HttpRespHeaders::H_DATE);
        h.outputNonSpdyHeaders(&io);
        DisplayBothHeader(io, kk, h.getCount(), &h);
        strcpy(sTestHdr, "HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n");
        CheckIoHeader(io,sTestHdr);


        //large header test 10k short headers
        static const char * const s_bigStr1[] =
        {"X1111111111111111111111111111111111111111111111111"};//"X"+49 "1"
        static const char * const s_bigStr2[] =
        {"X2222222222222222222222222222222222222222222222222"};//"X"+49 "1"

        h.reset();
        h.buildCommonHeaders();
        h.addStatusLine( 0, 304, 1);  //when ver is 0 and keepalive is 1, Will NOT add connection: close automatically
        for (int j = 0; j<100; j++)
        {
            for (i=HttpRespHeaders::H_UNKNOWN; i<HttpRespHeaders::H_HEADER_END;i++)
            {
                //printf("i = %d j = %d \n",i,j);
                temp = h.add((const HttpRespHeaders::INDEX)(i), s_pHeaders[i], strlen(s_pHeaders[i]),
                             s_pHeaderVals[i], strlen(s_pHeaderVals[i]),LSI_HEADER_ADD);
                CHECK(temp == 0);
                temp = h.getCount();
                temp = h.getTotalCount();
                CHECK(h.getCount() == (i+2)+26*(j));//start at 1 and add 1 for connection close
                CHECK(h.getTotalCount() == (i+2)+26*(j));
            }
        }

        temp = h.getTotalCount();
        temp = h.getCount();


        //check header content
        for ( i=h.HeaderBeginPos(); i!=h.HeaderEndPos(); i=h.nextHeaderPos(i) )
        {
            temp = h.getHeader(i, &key, &keyLen, ios, 1000);
            //CHECK(memcmp(key, headerArray1[i%26].name, keyLen) == 0);//FIXME: CHANGED!!!
            //CHECK(temp == 100);//FIXME this is 100
        }
        //check output
        h.outputNonSpdyHeaders(&io);
        DisplayBothHeader(io, kk, h.getCount(), &h);


        ph = s_pOutputHdr;
        temp = sizeof(s_pOutputHdr);
        it=io.begin();
        p = (char *)it->iov_base;
        for (i=0;i<100;i++)
        {
            CHECK(memcmp(p, s_pOutputHdr, sizeof(s_pOutputHdr)-1) == 0);
            p+=sizeof(s_pOutputHdr)-1;
        }

        //printf("End of response header testing\n");

        */
    }
}

#endif

