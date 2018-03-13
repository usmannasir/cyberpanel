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
/*

#include <log4cxx/logger.h>
#include <log4cxx/layout_type_plain.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>


typedef long long int usec_t;

static inline usec_t utime(void)
{
struct timeval tv;

gettimeofday(&tv, NULL);

return (usec_t) (tv.tv_sec * 1000000 + tv.tv_usec);
}

#define timed_loop(name, count, expr) \
{ \
int i; \
usec_t u = utime(); \
for (i = 0; i < count; i++) (expr); \
u -= utime(); \
fprintf(stderr, name ": elapsed %lld us - average %lld us\n", -u, - u / count); \
}

static LOG4CXX_NS::Logger* stream = LOG4CXX_NS::Logger::getLogger( "stream" );
static LOG4CXX_NS::Logger* mmaped = LOG4CXX_NS::Logger::getLogger( "mmap" );

extern void log4cxx_bench( int count = 100, int size = 128 )
{
LOG4CXX_NS::Appender* appenderMmap
    = LOG4CXX_NS::Appender::getAppender( "bench.mmap", "mmap" );
LOG4CXX_NS::Appender* appenderStream
    = LOG4CXX_NS::Appender::getAppender( "bench.log", "log4cxx.stream" );
mmaped.setAppender( appenderMmap );
stream.setAppender( appenderStream );
LOG4CXX_NS::Logger root = LOG4CXX_NS::Logger::getRootLogger();
root.setLevel( LOG4CXX_NS::Level::ERROR );
//root.setAppender( LOG4CXX_NS::Appender::getAppender( "stdout" ));
LOG4CXX_NS::Layout layout = LOG4CXX_NS::Layout::getLayout("log4cxx.pattern" );
layout.setUData( (void *)"%d %p %c - %m" );
appenderStream.setLayout( layout );

char * buffer;
buffer = (char *)malloc( size + 1 );
memset( buffer, 'X', size );
buffer[ size ] = 0;

fprintf( stderr, "   loop: %d\n", count );
fprintf( stderr, " buffer: %d\n", size );

timed_loop( "stream",   count, (stream.error( "%s", buffer )));
timed_loop( "mmap",     count, (mmaped.error( "%s", buffer )));
timed_loop( "fprintf",  count, (fprintf( stdout, "%s\n", buffer )));
free( buffer );
}
*/
