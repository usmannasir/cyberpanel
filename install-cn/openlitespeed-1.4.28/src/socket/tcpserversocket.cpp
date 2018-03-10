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
// #include "tcpserversocket.h"
// #include <tcpconnection.h>
// #include <tcpsockopt.h>
/*
TcpServerSocket::TcpServerSocket( struct sockaddr *pAddr, int backlog )
    : ServerSocket( PF_INET )
{
    if ( listen( pAddr, backlog ) == CoreSocket::FAIL )
    {
        //TODO: add exceptions or output error message.
    }
}

int TcpServerSocket::listen( struct sockaddr * pAddr, int backlog )
{
    TcpSockOpt::setReuseAddr( *this, 1 );
    TcpSockOpt::setTcpNoDelay( *this, 1 );
    //setDeferAccept( 1 );
    int fd;
    int ret = CoreSocket::listen( pAddr, backlog, fd );
    setfd( fd );
    return CoreSocket::FAIL;
}

TcpConnection* TcpServerSocket::acceptConn(TcpConnection& conn)
{
    GSockAddr addrPeer(AF_UNSPEC) ;
    socklen_t len = addrPeer.len();
    int fd = ServerSocket::accept( addrPeer.get(), &len );
    if ( fd != CoreSocket::FAIL )
    {
        conn.setfd( fd );
        conn.setPeerAddr( &addrPeer );
        return &conn;
    }
    return NULL;
}*/

