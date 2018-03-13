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

#include "tcpsockettest.h"

#include <socket/tcpsockopt.h>

#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include "unittest-cpp/UnitTest++.h"


inline  int     setNonBlock(int fd, int nonblock = 1)
{
    int val = fcntl(fd, F_GETFL, 0);
    if (nonblock)
        return fcntl(fd, F_SETFL, val | O_NONBLOCK);
    else
        return fcntl(fd, F_SETFL, val & (~O_NONBLOCK));
}

inline int      isSet(int fd, int arg)
{
    int val = fcntl(fd, F_GETFL, 0);
    return (val != -1)
           ? ((val & arg) == arg)
           : val;
}


TEST(TcpSocketTest_testAll)
{

//     CHECK( -1 != m_client.getfd() );
//
//     CHECK( 0 == setNonBlock( m_listener.getfd() ) );
//     CHECK( 0 == m_listener.listen( 3452, 15 ) );
//     TcpConnection conn( INVALID_FD );
//     CHECK( NULL == m_listener.acceptConn(conn) );
//     CHECK( EWOULDBLOCK == errno );
//     //CHECK( 0 == m_client.connect( "192.168.0.10", 3452 ) );
//     CHECK( 0 == m_client.connect( "127.0.0.1:3452" ) );
//     CHECK( 5 == m_client.write( "hello", 5 ) );
//     CHECK( 0 == setNonBlock( m_client.getfd() ));
//     CHECK( 1 == isSet(
//                         m_client.getfd(), O_NONBLOCK ));
//     CHECK( NULL != ( m_pConnection = m_listener.acceptConn( conn ) ));
//     //ErrorNo Errno;
//     //Errno.freezeErrno();
//     //std::cout << Errno.getErrStr() << std::endl;
//     CHECK( 0 == setNonBlock( m_pConnection->getfd() ));
//     CHECK( 1 == isSet(
//                         m_pConnection->getfd(), O_NONBLOCK ));
//     char achBuf[81920];
//     CHECK( 5 == m_pConnection->read( achBuf, 256 ));
//     CHECK( -1 == m_pConnection->read( achBuf, 256 ));
//     CHECK( EWOULDBLOCK == errno );
//     CHECK( 0 == TcpSockOpt::setTcpCork( m_client, 1));
//     int iSize = 0;
//     while( (iSize = m_client.write( achBuf, 81920 )) == 81920 )
//         ;
//     //printf( "TCP send buffer size is %d\n", iSize );
//     CHECK( EWOULDBLOCK == errno );
//     while( -1 != (iSize = m_pConnection->read( achBuf, 81920 )))
//         //printf( "Receive %d Bytes!\n", iSize )
//         ;
//     CHECK( EWOULDBLOCK == errno );

}

#endif
