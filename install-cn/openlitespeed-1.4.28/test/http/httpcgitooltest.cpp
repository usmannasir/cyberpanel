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

// #include "httpcgitooltest.h"
// #include <http/httpsession.h>
// #include <http/httpextconnector.h>
// #include <http/httpcgitool.h>
// #include "unittest-cpp/UnitTest++.h"
//
// TEST( HttpCgiToolTest_test)
// {
//     HttpSession session;
//     HttpExtConnector connector;
//     connector.setHttpSession( &session );
//     session.getReq()->reset();
//     char test1[] =
//     "staTus: 404 not found   \t \r \n"
//     "Content-Type: \tapplication/x-testcgi \n"
//     "Script-Control: no-abort \n"
//     "Http-eXtended:my-extension\n"
//     "MultiLineHeader: line1\n"
//     " line2\r\n"
//     "\n"
//     "this is the resp body";
//     char * pEnd = test1 + strlen( test1 );
//     char * pCur = test1;
//     char * pBuf = test1;
//     int status = 0;
//     while( pCur < pEnd )
//     {
//         pCur++;
//         int ret = HttpCgiTool::parseRespHeader( &connector, pBuf, pCur - pBuf, status );
//         if ( ret > 0 )
//             pBuf += ret;
//         if ( status == HttpReq::HEADER_OK )
//             break;
//     }
//
//     CHECK( strncmp( pBuf, "this is the resp body", 21 ) == 0 );
//     CHECK( session.getReq()->getStatusCode() == SC_404 );
//     session.getResp()->getOutputBuf().append( '\0' );
//     const char * pOutput = session.getResp()->getOutputBuf().begin();
//     CHECK( strstr( pOutput,
//                     "Content-Type: \tapplication/x-testcgi\r\n" ) != NULL );
//     CHECK( strstr( pOutput,
//                     "Http-eXtended:my-extension\r\n" ) != NULL );
//     CHECK( strstr( pOutput,     "MultiLineHeader: line1\r\n"
//                                          " line2\r\n" ) != NULL );
//     CHECK( *session.getReq()->getLocation() == 0 );
//
//     char test2[] = "Location: http://www.somewhere.com/\n\n";
//     status = 0;
//     session.getResp()->reset();
//     session.getReq()->setStatusCode( SC_200 );
//     int ret = HttpCgiTool::parseRespHeader( &connector, test2, strlen( test2 ), status );
//     CHECK( ret == (int)strlen( test2 ) );
//     CHECK( status == HttpReq::HEADER_OK );
//     CHECK( session.getReq()->getStatusCode() == SC_302 );
//     session.getResp()->getOutputBuf().append( '\0' );
//     pOutput = session.getResp()->getOutputBuf().begin();
//
//     CHECK( strstr( pOutput,
//                     "Location: http://www.somewhere.com/\r\n" ) != NULL );
//     CHECK( *session.getReq()->getLocation() == 0 );
//
//     char test3[] = "Location: /internal/redirect/url\n\n";
//     status = 0;
//     session.getResp()->reset();
//     session.getReq()->setStatusCode( SC_200 );
//     ret = HttpCgiTool::parseRespHeader( &connector, test3, strlen( test3 ), status );
//     CHECK( ret == (int)strlen( test3 ) );
//     CHECK( status == HttpReq::HEADER_OK );
//     CHECK( session.getReq()->getStatusCode() == SC_200 );
//     session.getResp()->getOutputBuf().append( '\0' );
//     pOutput = session.getResp()->getOutputBuf().begin();
//
//     CHECK( strstr( pOutput,
//                     "/internal/redirect/url" ) == NULL );
//     CHECK( strcmp( "/internal/redirect/url",
//                             session.getReq()->getLocation()) == 0 );
//
//
// }

#endif
