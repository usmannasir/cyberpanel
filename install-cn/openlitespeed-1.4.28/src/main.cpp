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
#ifdef HAVE_CONFIG_H
#include <config.h>
#endif


#include <main/lshttpdmain.h>

#include <sys/stat.h>
#include <stdio.h>
#include <stdlib.h>


/*
#include <sys/mman.h>
void test_mmap()
{
    int fd;
    fd = open( "mmap_test", O_RDWR | O_CREAT | O_TRUNC, 0600 );
    assert( fd != -1 );
    assert( ftruncate( fd, 4096 ) != -1 );
    char * pBuf =( char*) mmap( NULL, 4096, PROT_READ | PROT_WRITE,
                MAP_SHARED , fd, 0 );
    //munmap( pBuf2, 4096 );
    assert( pBuf );
    memset( pBuf, 'A', 4096 );
    ftruncate( fd, 8192 );
    memset( pBuf, 'B', 2048 );
    char * pBuf1 =( char*) mmap( NULL, 4096, PROT_READ | PROT_WRITE,
                MAP_SHARED , fd, 4096 );
    assert( pBuf1 );
    memset( pBuf1, 'C', 4096 );
    memset( pBuf, 'D', 1024 );
    munmap( pBuf1, 4096 );
    munmap( pBuf, 4096 );
    close( fd );

}
*/
//static int testExec()
//{
//    int ret = fork();
//    if ( ret )
//        return ret;
//    ret = execlp( "ls", "ls -la", NULL );
//    printf( "execle error!" );
//    exit( -1 );
//    return ret;
//}
//#include <util/emailsender.h>

//#include <sys/types.h>
//#include <sys/socket.h>
//#include <netinet/in.h>
//#include <arpa/inet.h>
//#include <util/sysinfo/nicdetect.h>
//static int testNICDetect( )
//{
//    struct ifi_info * pHead = NICDetect::get_ifi_info( AF_INET, 1 );
//    struct ifi_info * iter;
//    char temp[40];
//    for( iter = pHead; iter != NULL; iter = iter->ifi_next )
//    {
//        //if ( iter->ifi_hlen > 0 )
//        {
//            printf( "%s-%s-%X:%X:%X:%X:%X:%X\n", iter->ifi_name,
//                    inet_ntop( iter->ifi_addr->sa_family,
//                        &(((sockaddr_in *)iter->ifi_addr)->sin_addr),
//                        temp, 40 ),
//
//                    iter->ifi_haddr[0], iter->ifi_haddr[1],
//                    iter->ifi_haddr[2], iter->ifi_haddr[3],
//                    iter->ifi_haddr[4], iter->ifi_haddr[5] );
//        }
//    }
//    if ( pHead )
//        NICDetect::free_ifi_info( pHead );
//    return 0;
//}

static LshttpdMain *s_pLshttpd = NULL;
int main(int argc, char *argv[])
{
    //test_mmap();
    //testExec();
//    testNICDetect();
    s_pLshttpd = new LshttpdMain();
    if (!s_pLshttpd)
    {
        perror("new LshttpdMain()");
        exit(1);
    }
    int ret = s_pLshttpd->main(argc, argv);
    delete s_pLshttpd;
    exit(ret);
}

