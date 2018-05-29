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
#include <fcntl.h>
#include <lsr/ls_fileio.h>
#include <util/stringtool.h>

#define IFRSIZE   ((int)(sizeof (struct ifreq)))

// For Linux, need to get IPv6 address info from /proc/net/if_inet6
//    sample: 00000000000000000000000000000001 01 80 10 80 lo
//
//    fields: address, index, prefix length, scope
//    (net/ipv6.h), interface flags (linux/rtnetlink.h), interface name.

struct ifi_info *parse_proc_net()
{
    struct ifi_info   *ifi, *ifihead, **ifipnext;
    int fd;
    char achBuf[8192];
    fd = ls_fio_open("/proc/net/if_inet6", O_RDONLY, 0644);
    if (fd == -1)
        return NULL;
    int ret, total = 0;
    while ((ret = ls_fio_read(fd, &achBuf[total],
                              sizeof(achBuf) - total - 1)) > 0)
    {
        total += ret;
        if (total >= (int)sizeof(achBuf) - 1)
            break;
    }
    ls_fio_close(fd);

    struct sockaddr_in6 addr;
    char *pEnd = &achBuf[total];
    char *pLineEnd;
    char *p = achBuf;
    *pEnd = 0;
    addr.sin6_family = AF_INET6;

    ifihead = NULL;
    ifipnext = &ifihead;
    while (p < pEnd)
    {
        pLineEnd = strchr(p, '\n');
        if (!pLineEnd)
            pLineEnd = pEnd;
        *pLineEnd = 0;
        if (pLineEnd - p > 45)
        {
            int index, prefix, scope, flag;
            char achName[256];
            StringTool::hexDecode(p, 32, (char *)&addr.sin6_addr);
            if (sscanf(p + 32, " %x %x %x %x %s", &index, &prefix,
                       &scope, &flag, achName) == 5)
            {
                if (scope != 32)
                {
                    ifi = (struct ifi_info *)calloc(1, sizeof(struct ifi_info));
                    *ifipnext = ifi;            /* prev points to this new one */
                    ifipnext = &ifi->ifi_next;    /* pointer to next one goes here */

                    ifi->ifi_flags = flag;        /* IFF_xxx values */
                    memmove(ifi->ifi_name, achName, IFI_NAME);
                    ifi->ifi_name[IFI_NAME - 1] = '\0';
                    if (ifi->ifi_addr == NULL)
                    {
                        ifi->ifi_addr = (sockaddr *)calloc(1, sizeof(struct sockaddr_in6));
                        memmove(ifi->ifi_addr, &addr, sizeof(struct sockaddr_in6));
                    }

                }
            }
        }

        p = pLineEnd + 1;
    }
    return ifihead;

}

struct ifi_info *
NICDetect::get_ifi_info(int family, int doaliases)
{
    struct ifi_info     *ifi, *ifihead, **ifipnext;
    int                 sockfd, len, flags, myflags;
    char                *buf, lastname[IFNAMSIZ], *cptr;
    struct ifconf       ifc;
    struct ifreq        *ifr, ifrcopy;
    struct sockaddr_in  *sinptr = NULL;
    if (family == AF_INET6)
        return parse_proc_net();
    sockfd = ::socket(AF_INET, SOCK_DGRAM, 0);

    len = 100 * IFRSIZE;    /* initial buffer size guess */
    for (; ;)
    {
        buf = (char *)malloc(len);
        if (buf)
        {
            ifc.ifc_len = len;
            ifc.ifc_buf = buf;
            if (ioctl(sockfd, SIOCGIFCONF, &ifc) < 0)
            {
                if (errno != EINVAL)
                {
                    close(sockfd);
                    return NULL;
                }
            }
            else
            {
                if (ifc.ifc_len < len)
                    break;                      /* success, len has not changed */
            }
            len += 10 * IFRSIZE;   /* increment */
            free(buf);
        }
        else
        {
            close(sockfd);
            return NULL;
        }
    }
    ifihead = NULL;
    ifipnext = &ifihead;
    lastname[0] = 0;
    ifr = (struct ifreq *)buf;
    for (; (char *)ifr < &buf[ifc.ifc_len]; ++ifr)
    {

        if (ifr->ifr_addr.sa_family != family)
            continue;    /* ignore if not desired address family */

        myflags = 0;
        if ((cptr = strchr(ifr->ifr_name, ':')) != NULL)
            * cptr = 0;       /* replace colon will null */
        if (strncmp(lastname, ifr->ifr_name, IFNAMSIZ) == 0)
        {
            if (doaliases == 0)
                continue;    /* already processed this interface */
            myflags = IFI_ALIAS;
        }
        memmove(lastname, ifr->ifr_name, IFNAMSIZ);

        ifrcopy = *ifr;
        ioctl(sockfd, SIOCGIFFLAGS, &ifrcopy);
        flags = ifrcopy.ifr_flags;
        if ((flags & IFF_UP) == 0)
            continue;    /* ignore if interface not up */

        ifi = (struct ifi_info *)calloc(1, sizeof(struct ifi_info));
        *ifipnext = ifi;            /* prev points to this new one */
        ifipnext = &ifi->ifi_next;    /* pointer to next one goes here */

        ifi->ifi_flags = flags;        /* IFF_xxx values */
        ifi->ifi_myflags = myflags;    /* IFI_xxx values */
        memmove(ifi->ifi_name, ifr->ifr_name, IFI_NAME);
        ifi->ifi_name[IFI_NAME - 1] = '\0';

        switch (ifr->ifr_addr.sa_family)
        {
        case AF_INET:
            sinptr = (struct sockaddr_in *) &ifr->ifr_addr;
            if (ifi->ifi_addr == NULL)
            {
                ifi->ifi_addr = (sockaddr *)calloc(1, sizeof(struct sockaddr_in));
                memmove(ifi->ifi_addr, sinptr, sizeof(struct sockaddr_in));

#ifdef    SIOCGIFBRDADDR
                if (flags & IFF_BROADCAST)
                {
                    ioctl(sockfd, SIOCGIFBRDADDR, &ifrcopy);
                    sinptr = (struct sockaddr_in *) &ifrcopy.ifr_broadaddr;
                    ifi->ifi_brdaddr = (sockaddr *)calloc(1, sizeof(struct sockaddr_in));
                    memmove(ifi->ifi_brdaddr, sinptr, sizeof(struct sockaddr_in));
                }
#endif

#ifdef    SIOCGIFDSTADDR
                if (flags & IFF_POINTOPOINT)
                {
                    ioctl(sockfd, SIOCGIFDSTADDR, &ifrcopy);
                    sinptr = (struct sockaddr_in *) &ifrcopy.ifr_dstaddr;
                    ifi->ifi_dstaddr = (sockaddr *)calloc(1, sizeof(struct sockaddr_in));
                    memmove(ifi->ifi_dstaddr, sinptr, sizeof(struct sockaddr_in));
                }
#endif
            }
            if ((flags & IFF_LOOPBACK) == 0)
            {
                if (!ioctl(sockfd, SIOCGIFHWADDR, &ifrcopy))
                {
                    memmove(ifi->ifi_haddr, ifrcopy.ifr_hwaddr.sa_data, 6);
                    ifi->ifi_hlen = 6;
                }
            }
            break;
        case AF_INET6:
            sinptr = (struct sockaddr_in *) &ifr->ifr_addr;
            if (ifi->ifi_addr == NULL)
            {
                ifi->ifi_addr = (sockaddr *)calloc(1, sizeof(struct sockaddr_in6));
                memmove(ifi->ifi_addr, sinptr, sizeof(struct sockaddr_in6));
            }
            break;
        default:
            break;
        }
    }
    close(sockfd);
    free(buf);
    return (ifihead);   /* pointer to first structure in linked list */
}

