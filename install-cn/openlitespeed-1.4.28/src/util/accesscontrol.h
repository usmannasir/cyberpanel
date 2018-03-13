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
#ifndef ACCESSCONTROL_H
#define ACCESSCONTROL_H

#include <lsdef.h>
#include <util/ghash.h>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>


class IPAcc
{
    GHash::const_iterator data;

    void operator=(const IPAcc &rhs);
public:
    IPAcc(GHash::const_iterator iter)
        : data(iter)
    {}
    IPAcc(const IPAcc &rhs)
        : data(rhs.data)
    {}
    int getAccess() const
    {   return (long)(data->second());  }
    const void *key() const
    {   return data->first();           }
    bool isNull() const {   return data == NULL; }
};


class IPAccessControl : private GHash
{
public:
    explicit IPAccessControl(int initSize, GHash::hasher hf = NULL,
                             GHash::value_compare vc = NULL)
        : GHash(initSize, hf, vc)
    {}

    ~IPAccessControl() {};

    int update(in_addr_t ip, long allow)
    {
        return (GHash::update((void *)(unsigned long)ip, (void *)allow) == NULL);
    }

    void remove(in_addr_t ip)
    {
        GHash::iterator iter = GHash::find((void *)(unsigned long)ip);
        if (iter != end())
            GHash::erase(iter);
    }

    IPAcc find(in_addr_t addr) const
    {
        return GHash::find((void *)(unsigned long)addr);
    }


    void clear()    {   GHash::clear();   }
    size_t size() const {   return GHash::size();   }


    LS_NO_COPY_ASSIGN(IPAccessControl);
};




class SubNetNode;
class SubNet6Node;
class IP6AccessControl;
class XmlNode;
class ConfigCtx;
class AccessControl
{
private:
    SubNetNode             *m_pRoot;
    IPAccessControl         m_ipCtrl;

    SubNet6Node            *m_pRoot6;
    IP6AccessControl       *m_pIp6Ctrl;

    static AccessControl   *s_pAccessCtrl;

    int insSubNetControl(in_addr_t subNet,
                         in_addr_t mask,
                         int allowed);

    int addIPControl(in_addr_t ip, int allowed)
    {   return m_ipCtrl.update(ip, allowed);     }
    void removeIPControl(in_addr_t ip)
    {   m_ipCtrl.remove(ip);  }
    int addIPv4(const char *ip, int allowed);
    int parseNetmask(const char *netMask, int max, void *mask);

    int addSubNetControl(in_addr_t ip, in_addr_t netMask, int allowed);

    int addSubNetControl(const in6_addr &subNet,
                         const in6_addr &mask, int allowed);
    int insSubNetControl(const in6_addr &subNet,
                         const in6_addr &mask, int allowed);
    int addIPControl(const in6_addr &ip, int allowed);

public:
    AccessControl();
    ~AccessControl();

    int hasAccess(in_addr_t ip) const;
    int hasAccess(const in6_addr &ip) const;
    int hasAccess(const struct sockaddr *pAddr) const;
    int hasAccess(const char *pchIP) const;
    int addIPControl(const char *pchIP, int allowed);
    void removeIPControl(const char *pchIP);

    int addSubNetControl(const char *ip, const char *netMask, int allowed);
    int addSubNetControl(const char *ip_mask, int allowed);
    void clear();
    int addList(const char *pList, int allow);
    static int isAvailable(const XmlNode *pNode);

    static AccessControl *getAccessCtrl()
    {   return s_pAccessCtrl;   }
    static void setAccessCtrl(AccessControl *pAccessCtrl)
    {   s_pAccessCtrl = pAccessCtrl;    }


    LS_NO_COPY_ASSIGN(AccessControl);
};


#endif

