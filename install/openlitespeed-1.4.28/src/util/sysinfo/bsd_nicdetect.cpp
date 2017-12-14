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
#include    <net/if_dl.h>        /* sockaddr_sdl{} */
#include    <net/route.h>        /* RTA_xxx constants */
#include    <sys/param.h>
#include    <sys/sysctl.h>        /* sysctl() */

#include    <lsr/ls_strtool.h>

/*
 * Round up 'a' to next multiple of 'size'
 */
#define ROUNDUP(a, size) (((a) & ((size)-1)) ? (1 + ((a) | ((size)-1))) : (a))

/*
 * Step to next socket address structure;
 * if sa_len is 0, assume it is sizeof(u_long).
 */
#define NEXT_SA(ap)    ap = (struct sockaddr *) \
                            ((caddr_t) ap + (ap->sa_len ? ROUNDUP(ap->sa_len, sizeof (u_long)) : \
                                    sizeof(u_long)))

void
get_rtaddrs(int addrs, struct sockaddr *sa, struct sockaddr **rti_info)
{
    int        i;

    for (i = 0; i < RTAX_MAX; i++)
    {
        if (addrs & (1 << i))
        {
            rti_info[i] = sa;
            NEXT_SA(sa);
        }
        else
            rti_info[i] = NULL;
    }
}

char *
net_rt_iflist(int family, int flags, size_t *lenp)
{
    int        mib[6];
    char    *buf;

    mib[0] = CTL_NET;
    mib[1] = AF_ROUTE;
    mib[2] = 0;
    mib[3] = family;        /* only addresses of this family */
    mib[4] = NET_RT_IFLIST;
    mib[5] = flags;            /* interface index, or 0 */
    if (sysctl(mib, 6, NULL, lenp, NULL, 0) < 0)
        return (NULL);

    if ((buf = (char *)malloc(*lenp)) == NULL)
        return (NULL);
    if (sysctl(mib, 6, buf, lenp, NULL, 0) < 0)
        return (NULL);

    return (buf);
}

/* include get_ifi_info1 */
struct ifi_info *
NICDetect::get_ifi_info(int family, int doaliases)
{
    int                 flags;
    char                *buf, *next, *lim;
    size_t              len;
    struct if_msghdr    *ifm;
    struct ifa_msghdr   *ifam;
    struct sockaddr     *sa, *rti_info[RTAX_MAX];
    struct sockaddr_dl  *sdl;
    struct ifi_info     *ifi, *ifisave, *ifihead, **ifipnext;

    buf = net_rt_iflist(family, 0, &len);
    if (!buf)
        return NULL;
    ifihead = NULL;
    ifipnext = &ifihead;

    lim = buf + len;
    for (next = buf; next < lim; next += ifm->ifm_msglen)
    {
        ifm = (struct if_msghdr *) next;
        if (ifm->ifm_type == RTM_IFINFO)
        {
            if (((flags = ifm->ifm_flags) & IFF_UP) == 0)
                continue;    /* ignore if interface not up */

            sa = (struct sockaddr *)(ifm + 1);
            get_rtaddrs(ifm->ifm_addrs, sa, rti_info);
            if ((sa = rti_info[RTAX_IFP]) != NULL)
            {
                ifi = (struct ifi_info *)calloc(1, sizeof(struct ifi_info));
                *ifipnext = ifi;            /* prev points to this new one */
                ifipnext = &ifi->ifi_next;    /* ptr to next one goes here */

                ifi->ifi_flags = flags;
                if (sa->sa_family == AF_LINK)
                {
                    sdl = (struct sockaddr_dl *) sa;
                    if (sdl->sdl_nlen > 0)
                        ls_snprintf(ifi->ifi_name, IFI_NAME, "%*s",
                                    sdl->sdl_nlen, &sdl->sdl_data[0]);
                    else
                        ls_snprintf(ifi->ifi_name, IFI_NAME, "index %d",
                                    sdl->sdl_index);

                    if ((ifi->ifi_hlen = sdl->sdl_alen) > 0)
                        memcpy(ifi->ifi_haddr, LLADDR(sdl),
                               (IFI_HADDR < sdl->sdl_alen) ? IFI_HADDR : sdl->sdl_alen);
                }
            }

        }
        else if (ifm->ifm_type == RTM_NEWADDR)
        {
            if (ifi->ifi_addr)      /* already have an IP addr for i/f */
            {
                if (doaliases == 0)
                    continue;

                /* 4we have a new IP addr for existing interface */
                ifisave = ifi;
                ifi = (struct ifi_info *)calloc(1, sizeof(struct ifi_info));
                *ifipnext = ifi;            /* prev points to this new one */
                ifipnext = &ifi->ifi_next;    /* ptr to next one goes here */
                ifi->ifi_flags = ifisave->ifi_flags;
                ifi->ifi_hlen = ifisave->ifi_hlen;
                memcpy(ifi->ifi_name, ifisave->ifi_name, IFI_NAME);
                memcpy(ifi->ifi_haddr, ifisave->ifi_haddr, IFI_HADDR);
            }

            ifam = (struct ifa_msghdr *) next;
            sa = (struct sockaddr *)(ifam + 1);
            get_rtaddrs(ifam->ifam_addrs, sa, rti_info);

            if (((sa = rti_info[RTAX_IFA]) != NULL) && (sa->sa_len > 0))
            {
                ifi->ifi_addr = (sockaddr *)calloc(1, sa->sa_len);
                memcpy(ifi->ifi_addr, sa, sa->sa_len);
            }

            if (((flags & IFF_BROADCAST) &&
                 (sa = rti_info[RTAX_BRD]) != NULL) && (sa->sa_len > 0))
            {
                ifi->ifi_brdaddr = (sockaddr *)calloc(1, sa->sa_len);
                memcpy(ifi->ifi_brdaddr, sa, sa->sa_len);
            }

            if (((flags & IFF_POINTOPOINT) &&
                 (sa = rti_info[RTAX_BRD]) != NULL) && (sa->sa_len > 0))
            {
                ifi->ifi_dstaddr = (sockaddr *)calloc(1, sa->sa_len);
                memcpy(ifi->ifi_dstaddr, sa, sa->sa_len);
            }

        }
//        else
//            err_quit("unexpected message type %d", ifm->ifm_type);
    }
    free(buf);
    /* "ifihead" points to the first structure in the linked list */
    return (ifihead);   /* ptr to first structure in linked list */
}
