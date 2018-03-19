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

#ifndef MULTIPLEXERTEST_H
#define MULTIPLEXERTEST_H
#include "unittest-cpp/UnitTest++.h"

#include <edio/eventreactor.h>

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <string.h>
#include <unistd.h>




template<class T>
class MultiplexerTest : public CppUnit::TestFixture
{
    CPPUNIT_TEST_SUITE(MultiplexerTest);
    CPPUNIT_TEST(testAll);
    CPPUNIT_TEST_SUITE_END();
private:
    T  m_test;
    //Poller m_test;
    static int m_fds[2];
    static int m_eventBitsCount[8];
public:
    MultiplexerTest() {};
    ~MultiplexerTest() {};
    class TestHandler : public EventReactor
    {
        int handleEvents(short revent)
        {
            printf("handleEvents, fd = %d  revent = %d\n", getfd(), revent);
            for (int i = 0; i < 8; i++)
            {
                if (revent & (1 << i))
                {
                    m_eventBitsCount[i]++;
                    //printf( "handleEvents: m_eventBitsCount[%d] = %d\n",
                    //        i, m_eventBitsCount[i] );
                }
            }
            return 0;
        }
    };
    static int log2(int val)
    {
        int i;
        for (i = 0; i < 16; i++)
            if (val == (1 << i))
                return i;
        return LS_FAIL;
    }

    void testAll()
    {
        TestHandler h1, h2;
        CHECK(0 == m_test.init(16));
        memset(m_eventBitsCount, 0, 8 * sizeof(int));
        CHECK(0 == socketpair(AF_UNIX, SOCK_STREAM, 0,  m_fds));
        //CHECK( 0 == pipe( m_fds ));
        h1.setfd(m_fds[0]);
        h2.setfd(m_fds[1]);
        CHECK(0 == fcntl(m_fds[0], F_SETFL, m_test.getFLTag()));
        CHECK(0 == fcntl(m_fds[1], F_SETFL, m_test.getFLTag()));
        CHECK(0 == m_test.add(&h1, POLLOUT));
        CHECK(0 == m_test.add(&h2, POLLIN | POLLPRI));
        //CHECK( 0 == m_test.remove( 0 ) );

        CHECK(0 == m_test.waitAndProcessEvents(0));
        CHECK(0 == m_eventBitsCount[log2(POLLIN)]);
        CHECK(0 == m_eventBitsCount[log2(POLLPRI)]);
        CHECK(1 == m_eventBitsCount[log2(POLLOUT)]);
        CHECK(0 == m_eventBitsCount[log2(POLLERR)]);
        CHECK(0 == m_eventBitsCount[log2(POLLHUP)]);
        CHECK(0 == m_eventBitsCount[log2(POLLNVAL)]);

        CHECK(0 == m_test.waitAndProcessEvents(0));
        CHECK(2 == m_eventBitsCount[log2(POLLOUT)]);
        memset(m_eventBitsCount, 0, 8 * sizeof(int));
        h1.andMask2(0);
        h2.andMask2(0);
        int ret = m_test.waitAndProcessEvents(0);
        printf("ret=%d\n", ret);
        CHECK(EWOULDBLOCK == ret);
        CHECK(0 == m_eventBitsCount[log2(POLLOUT)]);

        //CHECK( EEXIST == m_test.add( h1, POLLOUT ) );
        //CHECK( EEXIST == m_test.add( h2, POLLIN|POLLPRI ));
        h2.setMask2(POLLOUT | POLLHUP | POLLERR);
        h1.setMask2(POLLIN | POLLPRI | POLLHUP | POLLERR);
//        write( m_fds[1], "hello", 5 );
//        write( m_fds[1], "hello", 5 );
        while (write(m_fds[1], "hello", 5) == 5)
            ;
        CHECK(EWOULDBLOCK == errno);
        h2.resetRevent(POLLOUT);
        m_test.testEvents(&h1);
        m_test.testEvents(&h2);
        CHECK(0 == m_test.waitAndProcessEvents(0));
        CHECK(1 == m_eventBitsCount[log2(POLLIN)]);
        CHECK(0 == m_eventBitsCount[log2(POLLPRI)]);
        CHECK(0 == m_eventBitsCount[log2(POLLOUT)]);
        CHECK(0 == m_eventBitsCount[log2(POLLERR)]);
        CHECK(0 == m_eventBitsCount[log2(POLLHUP)]);
        CHECK(0 == m_eventBitsCount[log2(POLLNVAL)]);

        char achBuf[10];
        while (read(m_fds[0], achBuf, 5) == 5)
            ;
        CHECK(EWOULDBLOCK == errno);
        h1.resetRevent(POLLIN);

        memset(m_eventBitsCount, 0, 8 * sizeof(int));
        CHECK(0 == m_test.waitAndProcessEvents(0));
        CHECK(0 == m_eventBitsCount[log2(POLLIN)]);
        CHECK(0 == m_eventBitsCount[log2(POLLPRI)]);
        CHECK(1 == m_eventBitsCount[log2(POLLOUT)]);
        CHECK(0 == m_eventBitsCount[log2(POLLERR)]);
        CHECK(0 == m_eventBitsCount[log2(POLLHUP)]);
        CHECK(0 == m_eventBitsCount[log2(POLLNVAL)]);

        memset(m_eventBitsCount, 0, 8 * sizeof(int));
        CHECK(0 == close(m_fds[0]));
        CHECK(0 == m_test.waitAndProcessEvents(0));
        CHECK(0 == m_eventBitsCount[log2(POLLIN)]);
        CHECK(0 == m_eventBitsCount[log2(POLLPRI)]);

        // Not true under Solris 8 sparc platform
        //CPPUNIT_ASSERT( 1 == m_eventBitsCount[log2(POLLOUT)] );

        CHECK(1 <= m_eventBitsCount[log2(POLLERR)] + m_eventBitsCount[log2(
                    POLLHUP)]);
        //CPPUNIT_ASSERT( 1 == m_eventBitsCount[log2(POLLNVAL)] );


    }
};
template< class T>
int MultiplexerTest<T>::m_fds[2];
template< class T>
int MultiplexerTest<T>::m_eventBitsCount[8];


#endif

#endif
