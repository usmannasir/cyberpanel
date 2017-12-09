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
struct ifi_info *
NICDetect::get_ifi_info(int family, int doaliases)
{
    struct ifi_info     *ifi, *ifihead, **ifipnext;
    int                 sockfd, len, lastlen, flags, myflags;
    char                *buf, lastname[IFNAMSIZ], *cptr;
    struct lifconf       ifc;
    struct lifreq        *ifr, *ifrend, ifrcopy;
    struct sockaddr_in  *sinptr;
    struct sockaddr_in6 *sinptr6;

    sockfd = ::socket(family, SOCK_DGRAM, 0);

    lastlen = len = 100 * sizeof(struct
                                 lifreq);    /* initial buffer size guess */
    memset(&ifc, 0, sizeof(ifc));
    ifc.lifc_family = AF_UNSPEC;
    for (; ;)
    {
        buf = (char *)malloc(len);
        if (buf)
        {
            ifc.lifc_len = len;
            ifc.lifc_buf = buf;
            if (ioctl(sockfd, SIOCGLIFCONF, &ifc) < 0)
            {
                if (errno != EINVAL || lastlen != 0)
                {
                    close(sockfd);
                    return NULL;
                }
            }
            else
            {
                if (ifc.lifc_len == lastlen)
                    break;                      /* success, len has not changed */
                lastlen = ifc.lifc_len;
            }
            len += 10 * sizeof(struct lifreq);   /* increment */
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
    ifrend = (struct lifreq *)(ifc.lifc_buf + ifc.lifc_len);
    for (ifr = ifc.lifc_req; ifr < ifrend; ++ifr)
    {

        if (((struct sockaddr *)&ifr->lifr_addr)->sa_family != family)
            continue;    /* ignore if not desired address family */

        myflags = 0;
        if ((cptr = strchr(ifr->lifr_name, ':')) != NULL)
            * cptr = 0;       /* replace colon will null */
        if (strncmp(lastname, ifr->lifr_name, IFNAMSIZ) == 0)
        {
            if (doaliases == 0)
                continue;    /* already processed this interface */
            myflags = IFI_ALIAS;
        }
        memmove(lastname, ifr->lifr_name, IFNAMSIZ);

        ifrcopy = *ifr;
        ioctl(sockfd, SIOCGLIFFLAGS, &ifrcopy);
        flags = ifrcopy.lifr_flags;
        if ((flags & IFF_UP) == 0)
            continue;    /* ignore if interface not up */

        ifi = (struct ifi_info *)calloc(1, sizeof(struct ifi_info));
        *ifipnext = ifi;            /* prev points to this new one */
        ifipnext = &ifi->ifi_next;    /* pointer to next one goes here */

        ifi->ifi_flags = flags;        /* IFF_xxx values */
        ifi->ifi_myflags = myflags;    /* IFI_xxx values */
        memmove(ifi->ifi_name, ifr->lifr_name, IFI_NAME);
        ifi->ifi_name[IFI_NAME - 1] = '\0';

        switch (((struct sockaddr *)&ifr->lifr_addr)->sa_family)
        {
        case AF_INET:
            sinptr = (struct sockaddr_in *) &ifr->lifr_addr;
            if (ifi->ifi_addr == NULL)
            {
                ifi->ifi_addr = (sockaddr *)calloc(1, sizeof(struct sockaddr_in));
                memmove(ifi->ifi_addr, sinptr, sizeof(struct sockaddr_in));

#ifdef    SIOCGLIFBRDADDR
                if (flags & IFF_BROADCAST)
                {
                    ioctl(sockfd, SIOCGLIFBRDADDR, &ifrcopy);
                    sinptr = (struct sockaddr_in *) &ifrcopy.lifr_broadaddr;
                    ifi->ifi_brdaddr = (sockaddr *)calloc(1, sizeof(struct sockaddr_in));
                    memmove(ifi->ifi_brdaddr, sinptr, sizeof(struct sockaddr_in));
                }
#endif

#ifdef    SIOCGLIFDSTADDR
                if (flags & IFF_POINTOPOINT)
                {
                    ioctl(sockfd, SIOCGLIFDSTADDR, &ifrcopy);
                    sinptr = (struct sockaddr_in *) &ifrcopy.lifr_dstaddr;
                    ifi->ifi_dstaddr = (sockaddr *)calloc(1, sizeof(struct sockaddr_in));
                    memmove(ifi->ifi_dstaddr, sinptr, sizeof(struct sockaddr_in));
                }
#endif
            }
            if ((flags & IFF_LOOPBACK) == 0)
            {

                struct sockaddr_in  *sin;
                struct arpreq       arpreq;
                memset(&arpreq, 0, sizeof(arpreq));
                sin = (struct sockaddr_in *)&arpreq.arp_pa;
                sin->sin_family = AF_INET;
                sinptr = (struct sockaddr_in *) &ifr->lifr_addr;
                //printf( "%s-%s\n", ifi->ifi_name, inet_ntoa( sinptr->sin_addr ) );
                memmove(&sin->sin_addr, &sinptr->sin_addr, sizeof(struct in_addr));
                len = ioctl(sockfd, SIOCGARP, &arpreq);
                if (len == -1)
                    perror("ioctl");
                else
                {
                    ifi->ifi_hlen = 6;
                    memmove(ifi->ifi_haddr, arpreq.arp_ha.sa_data, 6);
                }
            }
            break;
        case AF_INET6:
            sinptr6 = (struct sockaddr_in6 *) &ifr->lifr_addr;
            if (ifi->ifi_addr == NULL)
            {
                ifi->ifi_addr = (sockaddr *)calloc(1, sizeof(struct sockaddr_in6));
                memmove(ifi->ifi_addr, sinptr6, sizeof(struct sockaddr_in6));
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

