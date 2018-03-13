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
#ifndef NICDETECT_H
#define NICDETECT_H


#include    <sys/types.h>
#include    <sys/socket.h>

#define    IFI_NAME    16           /* same as IFNAMSIZ in <net/if.h> */
#define    IFI_HADDR   8            /* allow for 64-bit EUI-64 in future */

struct ifi_info
{
    char    ifi_name[IFI_NAME];       /* interface name, null terminated */
    u_char  ifi_haddr[IFI_HADDR];     /* hardware address */
    u_short ifi_hlen;                 /* #bytes in hardware address: 0, 6, 8 */
    short   ifi_flags;                /* IFF_xxx constants from <net/if.h> */
    short   ifi_myflags;              /* our own IFI_xxx flags */
    struct sockaddr  *ifi_addr;       /* primary address */
    struct sockaddr  *ifi_brdaddr;    /* broadcast address */
    struct sockaddr  *ifi_dstaddr;    /* destination address */
    struct ifi_info  *ifi_next;       /* next of these structures */
};

#define    IFI_ALIAS    1           /* ifi_addr is an alias */


class NICDetect
{
    NICDetect();
    ~NICDetect();
public:
    static struct ifi_info *get_ifi_info(int family, int doaliases);
    static void             free_ifi_info(struct ifi_info *pHead);

};

#endif
