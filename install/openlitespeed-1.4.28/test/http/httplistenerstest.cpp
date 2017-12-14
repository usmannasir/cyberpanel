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

#include "httplistenerstest.h"
#include <http/httplistener.h>
#include <edio/multiplexer.h>
#include <edio/multiplexerfactory.h>
#include <socket/tcpserversocket.h>
#include "unittest-cpp/UnitTest++.h"

TEST(HttpListenersTest_testHttpSockListener)
{
    HttpListener listener("*:3880", "*:3880");
    //listener.setIpAddr( INADDR_ANY );
    //listener.setPort( 3880 );

    //CHECK( listener.getPort() == 3880 );
    //CHECK( ((sockaddr_in *)listener.getIpAddr().get())->sin_addr.s_addr == INADDR_ANY );
    CHECK(strcmp(listener.getAddrStr(), "*:3880") == 0);
    CHECK(listener.getfd() == -1);

    CHECK(listener.suspend() != 0);
    CHECK(listener.resume() != 0);

    Multiplexer *pOld = MultiplexerFactory::getMultiplexer();
    Multiplexer *pMultiplexer =
        MultiplexerFactory::getNew(
            MultiplexerFactory::getType("poll"));
    if (pMultiplexer != NULL)
    {
        pMultiplexer->init(1024);
        MultiplexerFactory::setMultiplexer(pMultiplexer);
    }

    CHECK(listener.start() == 0);
    CHECK(listener.getfd() != -1);

    /*    TcpServerSocket serverSock;
        CHECK( serverSock.listen( 3880, 10, INADDR_ANY ) != 0 );

        CHECK( listener.suspend() == 0 );
        CHECK( listener.resume() == 0 );
        CHECK( listener.stop() == 0 );
        CHECK( serverSock.listen( 3880, 10, INADDR_ANY ) == 0 );*/
    MultiplexerFactory::setMultiplexer(pOld);
    MultiplexerFactory::recycle(pMultiplexer);
}

#endif
