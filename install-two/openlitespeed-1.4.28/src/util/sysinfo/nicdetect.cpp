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
#include "nicdetect.h"

#include    <errno.h>
#include    <net/if.h>
#include    <net/if_arp.h>
#include    <netinet/in.h>
#include    <sys/ioctl.h>
#include    <arpa/inet.h>

#if defined(sun) || defined(__sun)
#include    <sys/socket.h>
#include    <sys/sockio.h>
#endif

#include    <stdio.h>
#include    <stdlib.h>
#include    <string.h>
//#include    <stropts.h>
#include    <unistd.h>

#if defined(__FreeBSD__ ) || defined(__NetBSD__) || defined(__OpenBSD__) \
    || defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)

#include "bsd_nicdetect.cpp"

#elif defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)

// Linux, solaris use SIOCGIFCONF

#include "linux_nicdetect.cpp"

#else

#include "siocglif_nicdetect.cpp"

#endif


void
NICDetect::free_ifi_info(struct ifi_info *ifihead)
{
    struct ifi_info    *ifi, *ifinext;

    for (ifi = ifihead; ifi != NULL; ifi = ifinext)
    {
        if (ifi->ifi_addr != NULL)
            free(ifi->ifi_addr);
        if (ifi->ifi_brdaddr != NULL)
            free(ifi->ifi_brdaddr);
        if (ifi->ifi_dstaddr != NULL)
            free(ifi->ifi_dstaddr);
        ifinext = ifi->ifi_next;    /* can't fetch ifi_next after free() */
        free(ifi);                    /* the ifi_info{} itself */
    }
}


