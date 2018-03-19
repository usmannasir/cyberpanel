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

// #include "extensions/fcgi/fcgistarter.h"
// #include "extensions/fcgi/fcgiapp.h"
// #include "extensions/fcgi/fcgiappconfig.h"
// #include "extensions/fcgi/fcgiconnection.h"
// #include "extensions/fcgi/fcgirequest.h"
// #include "extensions/fcgi/samplefcgiextconn.h"
// #include "socket/coresocket.h"
// #include "edio/poller.h"
// #include <lsr/ls_time.h>
// #include <stdio.h>
// #include <signal.h>
// #include <sys/types.h>
// #include <sys/wait.h>
// #include "unittest-cpp/UnitTest++.h"
//
// // int testStart( const char * pURI, const char * pPathFcgiApp )
// // {
// //     int fd = -1;
// //     int ret;
// //     //ret = CoreSocket::connect( pURI, false, &fd );
// //     //CPPUNIT_ASSERT( ret != 0 );
// //     FcgiApp app( pURI );
// //     FcgiAppConfig &config = app.getConfig();
// //     config.setAppPath( pPathFcgiApp );
// //     config.setBackLog( 10 );
// //     config.setMaxConns( 1 );
// //     int pid = FcgiStarter::start( app );
// //     if ( pid <= 0  )
// //     {
// //         printf( "failed to start fast CGI application!\n" );
// //         return LS_FAIL;
// //     }
// //     printf( "fast cgi app PID=%d\n", pid );
// //     ls_sleep( 1000 );
// //     ret = CoreSocket::connect( pURI, false, &fd );
// //     if (( ret == 0 )&&( fd != -1 ))
// //     {
// //         printf( "connect to fast cgi app successfully!\n" );
// //     }
// //     else
// //     {
// //         printf( "Failed to connect to fast cgi app!\n" );
// //         return -2;
// //     }
// //     kill( pid, SIGKILL );
// //     /*
// //     waitpid( pid, NULL, 0 );
// //     ret = CoreSocket::connect( pURI, false, &fd );
// //     if ( fd == -1 )
// //     {
// //         printf( "shutdown fast cgi app successfully!\n" );
// //     }
// //     */
// //     return 0;
// // }
//
// void testProtocol(const char *pURI, const char *pAppPath)
// {
// //    FcgiApp * pApp = new FcgiApp( pURI );
// //    pApp->setURL( pURI );
// //    pApp->getConfig().setAppPath( pAppPath );
// //    pApp->getConfig().setBackLog( 10 );
// //    pApp->getConfig().setMaxConns( 1 );
// //    //CPPUNIT_ASSERT( pApp->start() == 0 );
// //    Poller mplx( 10 );
// //    pApp->setMultiplexer( &mplx );
// //    SampleFcgiExtConn* pExtConn = new SampleFcgiExtConn();
// //    pExtConn->setID( "test" );
// //    FcgiRequest * pReq = new FcgiRequest( pExtConn );
// //    if ( pApp->addNewRequest( pReq ) != -1 )
// //    {
// //        long lMax = time(NULL) + 2;
// //        while(( (pExtConn->getState()&(HEC_COMPLETE | HEC_ERROR )) == 0 )
// //            &&( time( NULL ) < lMax ))
// //        {
// //            mplx.waitAndProcessEvents( 100 );
// //        }
// //    }
// //    delete pReq;
// //    delete pExtConn;
// //
// //    //CPPUNIT_ASSERT( pApp->stop() == 0 );
// //    delete pApp;
//
//
//
// }
//
// TEST(FcgiStarterTesttest)
// {
//     const char *pURI = "localhost:5555";
//     const char *pApp =
//         "/home/gwang/projects/httpd/httpd/serverroot/fcgi-bin/lt-echo-cpp";
//     //CPPUNIT_ASSERT( testStart( pURI, pApp ) == 0 );
//     testProtocol(pURI, pApp);
//     //printf( "fast cgi app PID=%d\n", pApp->getPid() );
//     //ret = CoreSocket::connect( "localhost:5555", false, &fd );
//     //assert( ret == -1 );
//
// }
//

#endif
