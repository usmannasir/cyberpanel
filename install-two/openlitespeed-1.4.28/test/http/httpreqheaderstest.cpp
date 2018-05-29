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

#include "httpreqheaderstest.h"
#include "unittest-cpp/UnitTest++.h"



TEST(HttpReqHeadersTest_test)
{
//    const char * pSample[] =
//    {
//        "host","localhost:2080",
//        "user-agent","Mozilla/5.0 (X11; U; Linux i686; en-US; rv:0.9.2.1) Gecko/20010901",
//        "accept","text/xml, application/xml, application/xhtml+xml, text/html;q=0.9, image/png, image/jpeg, image/gif;q=0.2, text/plain;q=0.8, text/css",
//        "accept-language","en-us",
//        "accept-encoding","gzip,deflate,compress,identity",
//        "accept-charset","ISO-8859-1, utf-8;q=0.66, *;q=0.66",
//        "keep-alive","300",
//        "content-type","text/html",
//        "connection","keep-alive"
//    };
//    const char * pVerfiy =
//    "host: LOCALHOST:2080 \t \r\n"
//    "user-agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:0.9.2.1) Gecko/20010901\r\n"
//    "accept: text/xml, application/xml, application/xhtml+xml, text/html;q=0.9, image/png, image/jpeg, image/gif;q=0.2, text/plain;q=0.8, text/css\r\n"
//    "accept-language: en-us\t\t \t\t\r\n"
//    "accept-encoding: gzip,deflate,compress,identity\r\n"
//    "accept-charset: ISO-8859-1, utf-8;q=0.66, *;q=0.66\r\n"
//    "keep-alive: 300\r\n"
//    "content-type: text/html\r\n"
//    "connection: Keep-Alive\r\n";
//
//    HttpBuf httpBuf;
//    HttpHeader header;
//    for( int i = 0; i < (int)(sizeof( pSample ) / sizeof( char *)); i+=2 )
//    {
//        CPPUNIT_ASSERT( header.append( &httpBuf,
//                                pSample[i], pSample[i+1] ) == 0);
//    }
//    //httpBuf.append( "\0", 1 );
//    //printf( "%s\n", httpBuf.begin() );
//    CPPUNIT_ASSERT( 0 == strncmp( pVerfiy, httpBuf.begin(), sizeof( pVerfiy ) ) );
//    for( int i = 0; i < (int)(sizeof( pSample ) / sizeof( char *)); i += 2 )
//    {
//        int index = HttpHeader::getIndex( pSample[i] );
//        CPPUNIT_ASSERT( 0 ==
//            strncmp( header.getHeaderValue( &httpBuf, index ), pSample[i + 1],
//                strlen( pSample[i+1] ) ) );
//        CPPUNIT_ASSERT( 0 ==
//            strncmp( header.getHeaderValue( &httpBuf, pSample[i] ),
//                pSample[i + 1], strlen( pSample[i + 1] ) ) ) ;
//    }

//    HttpReqHeaders reqHeaders;
//    for( int i = 0; i < (int)(sizeof( pSample ) / sizeof( char *)); i += 2 )
//    {
//        int index = HttpHeader::getIndex( pSample[i] );
//        const char * pValue = header.getHeaderValue( &httpBuf, index );
//        const char * pKey = header.getHeaderKey( &httpBuf, index );
//        reqHeaders.addHeader( index, pKey - httpBuf.begin(),
//                pValue - httpBuf.begin(), strlen( pSample[i+1] ) );
//    }
//
//    for( int i = 0; i < (int)(sizeof( pSample ) / sizeof( char *)); i += 2 )
//    {
//        int index = HttpHeader::getIndex( pSample[i] );
//        CPPUNIT_ASSERT( 0 ==
//            strncmp( reqHeaders.getHeaderValue( &httpBuf, index ),
//                    pSample[i + 1],
//                    strlen( pSample[i+1] ) ) );
//    }


}

#endif

