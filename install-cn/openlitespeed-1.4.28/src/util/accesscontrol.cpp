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
#include <util/accesscontrol.h>

#include <util/accessdef.h>
#include <util/gpointerlist.h>
#include <util/pool.h>
#include <util/poolalloc.h>
#include <util/stringtool.h>
#include <util/xmlnode.h>
#include <util/sysinfo/systeminfo.h>

#include <assert.h>
#include <ctype.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

typedef union
{
    in6_addr    m_addr6;
    in_addr_t   m_addrs[4];
} Addr6;


AccessControl *AccessControl::s_pAccessCtrl = NULL;


static int isIPv6(const char *ip_mask)
{
    return (('[' == *ip_mask) || (strchr(ip_mask, ':')));
}


static int strToIPv6(char *ip, in6_addr *pAddr)
{
    if ('[' == *ip)
    {
        ++ip;
        char *pEnd = ip + strlen(ip) - 1;
        if (*pEnd != ']')
            return 0;
        *pEnd = 0;
    }
    return inet_pton(AF_INET6, ip, pAddr);
}


class IP6Acc
{
    in6_addr    m_addr;
    int         m_allowed;
public:
    IP6Acc(const in6_addr &addr, int allow)
        : m_addr(addr)
        , m_allowed(allow)
    {}
    void setAccess(int allow)
    {   m_allowed = allow;   }
    int getAccess() const
    {   return m_allowed;   }
    const in6_addr &getAddr() const
    {   return m_addr;      }

    static hash_key_t hf(const void *pKey)
    {
        hash_key_t key;
        if (sizeof(hash_key_t) == 4)
        {
            key = *((const hash_key_t *)pKey) +
                  *(((const hash_key_t *)pKey) + 1) +
                  *(((const hash_key_t *)pKey) + 2) +
                  *(((const hash_key_t *)pKey) + 3);
        }
        else
        {
            key = *((const hash_key_t *)pKey) +
                  *(((const hash_key_t *)pKey) + 1);
        }
        return key;
    }

    static int  cmp(const void *pVal1, const void *pVal2)
    {
        return memcmp(pVal1, pVal2, 16);
    }



    LS_NO_COPY_ASSIGN(IP6Acc);
};


class IP6AccessControl : public THash< IP6Acc * >
{
    typedef THash< IP6Acc * > IP6Hash;
public:
    explicit IP6AccessControl(int initSize)
        : IP6Hash(initSize, IP6Acc::hf, IP6Acc::cmp)
    {}

    ~IP6AccessControl() { release_objects();  };

    int addUpdate(const in6_addr &ip, long allow);

    void remove(const in6_addr &ip)
    {
        IP6Hash::iterator iter = IP6Hash::find(&ip);
        if (iter != end())
        {
            delete iter.second();
            IP6Hash::erase(iter);
        }
    }
    void clear()    {   release_objects(); IP6Hash::clear();  }
    size_t size() const {   return IP6Hash::size();   }


    LS_NO_COPY_ASSIGN(IP6AccessControl);
};


int IP6AccessControl::addUpdate(const in6_addr &ip, long allow)
{
    iterator iter = find(&ip);
    if (iter == end())
    {
        IP6Acc *pAcc = new IP6Acc(ip, allow);
        if (pAcc)
            insert(&pAcc->getAddr(), pAcc);

    }
    else
        iter.second()->setAccess(allow);
    return 0;
}


class SubNetNode
{
    typedef TPointerList<SubNetNode> NodeList;
    NodeList  m_children;
    in_addr_t m_id;
    in_addr_t m_mask;
    int       m_iAllowed;
public:
    SubNetNode(in_addr_t id, in_addr_t mask, int allowed)
        : m_id(id), m_mask(mask), m_iAllowed(allowed)
    {}
    ~SubNetNode();

    int hasAccess() const           {   return m_iAllowed;   }
    unsigned int getId() const      {   return m_id;        }
    const in_addr_t &getMask() const {   return m_mask;      }
    void setMask(in_addr_t mask)  {   m_mask = mask;      }
    void setAccess(int allow)       {   m_iAllowed = allow; }

    SubNetNode *insertChild(in_addr_t ip, in_addr_t mask, int allowed);
    SubNetNode *insertChild(SubNetNode *pNode);
    SubNetNode *matchNode(in_addr_t ip);
    void clear();

    void *operator new(size_t sz)
    {   return Pool::allocate(sizeof(SubNetNode));   }
    void operator delete(void *p)
    {   return Pool::deallocate(p, sizeof(SubNetNode));    }


    LS_NO_COPY_ASSIGN(SubNetNode);
};


SubNetNode::~SubNetNode()
{
    clear();
}


void SubNetNode::clear()
{
    NodeList::iterator iter;
    for (iter = m_children.begin(); iter != m_children.end(); ++iter)
        delete *iter;
    m_children.clear();
}


SubNetNode *SubNetNode::insertChild(in_addr_t ip, in_addr_t mask,
                                    int allowed)
{
    in_addr_t id = ip & mask;
    SubNetNode *pNewChild = new SubNetNode(id, mask, allowed);
    return insertChild(pNewChild);

}


SubNetNode *SubNetNode::insertChild(SubNetNode *pNode)
{
    //new( pNewChild )

    // the newly inserted one may be parent of other siblings

    NodeList::iterator iter;
    for (iter = m_children.begin(); iter != m_children.end();)
    {
        if (((*iter)->m_id & pNode->m_mask) == pNode->m_id)
        {
            if ((*iter)->m_mask == pNode->m_mask)
            {
                (*iter)->m_iAllowed = pNode->m_iAllowed;
                delete pNode;
                return *iter;
            }
            else if (((*iter)->m_mask & pNode->m_mask) == pNode->m_mask)
            {
                pNode->m_children.push_back(*iter);
                m_children.erase(iter);
            }
            else
                return (*iter)->insertChild(pNode);
        }
        else if ((pNode->m_id & (*iter)->m_mask) == (*iter)->m_id)
            return (*iter)->insertChild(pNode);
        else
            ++iter;
    }

    m_children.push_back(pNode);

    return pNode;
}


SubNetNode *SubNetNode::matchNode(in_addr_t ip)
{
    NodeList::const_iterator pos;

    NodeList::const_iterator pEnd = m_children.end();
    for (pos = m_children.begin(); pos != pEnd; ++pos)
    {
        if ((ip & (*pos)->m_mask) == (*pos)->m_id)
            return *pos;
    }
    return NULL;
}


class SubNet6Node
{
    typedef TPointerList<SubNet6Node> NodeList;
    NodeList  m_children;
    Addr6     m_id;
    Addr6     m_mask;
    int       m_allowed;
public:
    SubNet6Node(const in6_addr &id, const in6_addr &mask, int allowed)
        : m_allowed(allowed)
    {
        m_id.m_addr6 = id;
        m_mask.m_addr6 = mask;
    }
    ~SubNet6Node();

    void andMask(Addr6 &dest, const Addr6 &ip, const Addr6 &mask)
    {
        dest.m_addrs[0] = ip.m_addrs[0] & mask.m_addrs[0];
        dest.m_addrs[1] = ip.m_addrs[1] & mask.m_addrs[1];
        dest.m_addrs[2] = ip.m_addrs[2] & mask.m_addrs[2];
        dest.m_addrs[3] = ip.m_addrs[3] & mask.m_addrs[3];
    }
    int hasAccess() const           {   return m_allowed;   }
    const Addr6 &getId() const      {   return m_id;        }
    const Addr6 &getMask() const    {   return m_mask;      }
    void setMask(in6_addr &mask)  {   m_mask.m_addr6 = mask;      }
    void setAccess(int allow)       {   m_allowed = allow; }

    SubNet6Node *insertChild(const in6_addr &ip, const in6_addr &mask,
                             int allowed);
    SubNet6Node *insertChild(SubNet6Node *pNode);
    SubNet6Node *matchNode(const in6_addr &ip);
    void clear();

    void *operator new(size_t sz)
    {   return Pool::allocate(sizeof(SubNet6Node));   }
    void operator delete(void *p)
    {   return Pool::deallocate(p, sizeof(SubNet6Node));    }


    LS_NO_COPY_ASSIGN(SubNet6Node);
};


SubNet6Node::~SubNet6Node()
{
    clear();
}


void SubNet6Node::clear()
{
    NodeList::iterator iter;
    for (iter = m_children.begin(); iter != m_children.end(); ++iter)
        delete *iter;
    m_children.clear();
}


SubNet6Node *SubNet6Node::insertChild(const in6_addr &ip,
                                      const in6_addr &mask, int allowed)
{
    Addr6 id;
    andMask(id, (const Addr6 &)ip, (const Addr6 &)mask);
    SubNet6Node *pNewChild = new SubNet6Node(id.m_addr6, mask, allowed);
    return insertChild(pNewChild);

}


SubNet6Node *SubNet6Node::insertChild(SubNet6Node *pNode)
{

    // the newly inserted one may be parent of other siblings
    NodeList::iterator iter;
    for (iter = m_children.begin(); iter != m_children.end();)
    {
        Addr6 id1;
        andMask(id1, (*iter)->m_id, (const Addr6 &)pNode->m_mask);
        if (GHash::cmpIpv6(&id1, &pNode->m_id) == 0)
        {
            if (GHash::cmpIpv6(&(*iter)->m_mask, &pNode->m_mask) == 0)
            {
                (*iter)->m_allowed = pNode->m_allowed;
                delete pNode;
                return *iter;
            }
            else
            {
                pNode->m_children.push_back(*iter);
                m_children.erase(iter);
            }
        }
        else
        {
            Addr6 id2;
            andMask(id2, pNode->m_id, (const Addr6 &)((*iter)->m_mask));
            if (GHash::cmpIpv6(&id2, &(*iter)->m_id) == 0)
                return (*iter)->insertChild(pNode);
            else
                ++iter;
        }
    }

    m_children.push_back(pNode);

    return pNode;
}


SubNet6Node *SubNet6Node::matchNode(const in6_addr &ip)
{
    NodeList::const_iterator pos;

    NodeList::const_iterator pEnd = m_children.end();
    for (pos = m_children.begin(); pos != pEnd; ++pos)
    {
        Addr6 id;
        andMask(id, (const Addr6 &)ip, (*pos)->m_mask);
        if (GHash::cmpIpv6(&id, &(*pos)->m_id) == 0)
            return *pos;
    }
    return NULL;
}


AccessControl::AccessControl()
    : m_ipCtrl(13)
    , m_pIp6Ctrl(NULL)
{
    m_pRoot = new SubNetNode(0, 0, true);
    in6_addr addr;
    memset(&addr, 0, sizeof(addr));
    m_pRoot6 = new SubNet6Node(addr, addr, true);
}


AccessControl::~AccessControl()
{
    delete m_pRoot;
    delete m_pRoot6;
    if (m_pIp6Ctrl)
        delete m_pIp6Ctrl;
}


int AccessControl::hasAccess(const struct sockaddr *pAddr) const
{
    switch (pAddr->sa_family)
    {
    case AF_UNSPEC:
        assert(false);
    case AF_INET:
        {
            return hasAccess((((const sockaddr_in *)pAddr)->sin_addr).s_addr);
        }
    case AF_INET6:
        return hasAccess(((const sockaddr_in6 *)pAddr)->sin6_addr);
        assert(false);
    case AF_UNIX:
        assert(false);
    }
    return false;
}


int AccessControl::hasAccess(in_addr_t ip) const
{
    if (m_ipCtrl.size())
    {
        IPAcc pos = m_ipCtrl.find(ip);
        if (!pos.isNull())
            return pos.getAccess();
    }

    SubNetNode *pCurNode = m_pRoot;
    SubNetNode *pNextNode;

    while ((pNextNode = pCurNode->matchNode(ip)) != NULL)
        pCurNode = pNextNode;

    return pCurNode->hasAccess();
}


int AccessControl::hasAccess(const char *pchIP) const
{
    if (!isIPv6(pchIP))
    {
        in_addr ip;
        if (0 >= inet_pton(AF_INET, pchIP, &ip))
            return false; //err in conversion
        return hasAccess(ip.s_addr);
    }
    else
    {
        char achTemp[128];
        memccpy(achTemp, pchIP, 0, 127);
        achTemp[127] = 0;
        in6_addr ip;
        if (0 >= strToIPv6(achTemp, &ip))
            return false;
        return hasAccess(ip);
    }
}


static int checkTrust(char *ip_mask, int allowed)
{
    int len = strlen(ip_mask);
    char ch = *(ip_mask + len - 1);
    if ((ch == 't') || (ch == 'T'))
    {
        if (allowed)
            allowed = AC_TRUST;
        *(ip_mask + len - 1) = 0;
    }
    return allowed;
}


int AccessControl::addIPControl(const char *pchIP, int allowed)
{
    char achTemp[128];
    memccpy(achTemp, pchIP, 0, 127);
    achTemp[127] = 0;
    allowed = checkTrust(achTemp, allowed);
    if (!isIPv6(achTemp))
    {
        in_addr ip;
        if (0 >= inet_pton(AF_INET, achTemp, &ip))
            return LS_FAIL; //err in conversion
        return addIPControl(ip.s_addr, allowed);
    }
    else
    {
        in6_addr ip;
        if (0 >= strToIPv6(achTemp, &ip))
            return false;
        return addIPControl(ip, allowed);
    }
}


void AccessControl::removeIPControl(const char *pchIP)
{
    if (!isIPv6(pchIP))
    {
        in_addr ip;
        if (0 >= inet_pton(AF_INET, pchIP, &ip))
            return; //err in conversion
        return removeIPControl(ip.s_addr);
    }
    else
    {
        char achTemp[128];
        memccpy(achTemp, pchIP, 0, 127);
        achTemp[127] = 0;
        in6_addr ip;
        if (0 >= strToIPv6(achTemp, &ip))
            return;
        if (IN6_IS_ADDR_V4MAPPED(&ip))
            return removeIPControl(((Addr6 *)&ip)->m_addrs[3]);
        if (m_pIp6Ctrl)
            return m_pIp6Ctrl->remove(ip);
    }
}


int AccessControl::addSubNetControl(in_addr_t subNet,
                                    in_addr_t mask,
                                    int allowed)
{
    if (mask == 0xffffffff)
        return addIPControl(subNet, allowed);
    if (mask == 0)
    {
        m_pRoot->setAccess(allowed);
        return 0;
    }

    return insSubNetControl(subNet, mask, allowed);
}


int AccessControl::insSubNetControl(in_addr_t subNet,
                                    in_addr_t mask,
                                    int allowed)
{
    SubNetNode *pCur = m_pRoot;
    /*
        while ( ( pNext = pCur->matchNode( subNet ) ) != NULL )
        {
            if ( pNext->getMask() == mask )
            {
                pNext->setAccess( allowed );
                return 1; // confict with previous
            }
            pCur = pNext;
        }
    */

    pCur->insertChild(subNet, mask, allowed);
    return 0;
}


static unsigned char s_maskbits[8] = { 0x00, 0x80, 0xC0, 0xE0, 0xF0, 0xF8, 0xFC, 0xFE };
int AccessControl::parseNetmask(const char *netMask, int maxbits,
                                void *pMask)
{
    char *pEnd;
    if (!isdigit(*netMask))
        return LS_FAIL;
    int bits = strtol(netMask, &pEnd, 10);
    if ((*pEnd == 0) && (bits >= 0) && (bits < maxbits))
    {
        memset(pMask, 0xff, bits / 8);
        memset(((char *)pMask) + (bits + 7) / 8, 0, (maxbits - bits) / 8);
        if (bits % 8)
            *(((char *)pMask) + bits / 8) = s_maskbits[ bits % 8 ];
        return 0;
    }
    else
        return ((maxbits != 32) || (0 >= inet_pton(AF_INET, netMask, pMask)));
}


int AccessControl::addSubNetControl(const char *ip, const char *netMask,
                                    int allowed)
{
    //FIXME:no validation of string
    if (!isIPv6(ip))
    {
        in_addr subNet, mask;
        if (0 >= inet_pton(AF_INET, ip, &subNet))
            return LS_FAIL;
        if (0 != parseNetmask(netMask, 32, &mask))
            return LS_FAIL;
        return addSubNetControl(subNet.s_addr, mask.s_addr, allowed);
    }
    in6_addr addr, mask;
    char achTemp[128];
    memccpy(achTemp, ip, 0, 127);
    achTemp[127] = 0;
    if (0 >= strToIPv6(achTemp, &addr))
        return LS_FAIL;
    if (0 != parseNetmask(netMask, 128, &mask))
        return LS_FAIL;
    return addSubNetControl(addr, mask, allowed);
}


int AccessControl::addIPv4(const char *ip_mask, int allowed)
{
    char ip[256], mask[256];
    const char *p0;

    mask[0] = 0;
    p0 = strchr(ip_mask, '*');
    if (p0 == NULL)
        p0 = (char *)ip_mask + strlen(ip_mask) + 1;
    if (p0 <= ip_mask)
        return 0;
    memccpy(ip, ip_mask, 0, p0 - ip_mask);
    ip[p0 - ip_mask - 1] = 0;

    int c = 0;
    p0 = (char *)ip_mask;
    while (*p0)
    {
        if (*p0 == '.')
            ++c;
        else if (*p0 == '*')
            break;
        ++p0;
    }
    if (*p0 != '*')
        ++c;
    if (c == 4)
        return addIPControl(ip, allowed);
    int i = 0;
    for (; i < c; ++ i)
    {
        if (i == 0)
            strcat(mask, "255");
        else
            strcat(mask, ".255");
    }
    for (i = 0; i < 4 - c; ++ i)
    {
        strcat(ip, ".0");
        strcat(mask, ".0");
    }
    in_addr subNet, netmask;
    if (0 >= inet_pton(AF_INET, ip, &subNet))
        return LS_FAIL;
    if (0 >= inet_pton(AF_INET, mask, &netmask))
        return LS_FAIL;

    return addSubNetControl(subNet.s_addr, netmask.s_addr, allowed);
}


int AccessControl::addSubNetControl(const char *ip_mask, int allowed)
{
    //IPv4 formats: "192.168.1.*", "192.168.128.5/255.255.128.0", "192.168.128", "192.168.128.0/24"
    //IPv6: "::", "::1", "[::1]", "fdab:78a3:3487::1/120"
    const char *p0;
    char ip[256], mask[256];
    char achTemp[128];
    memccpy(achTemp, ip_mask, 0, 127);
    achTemp[127] = 0;
    allowed = checkTrust(achTemp, allowed);
    ip_mask = achTemp;
    p0 = strchr(ip_mask, '/');
    if (p0 != NULL)
    {
        memccpy(ip, ip_mask, 0, p0 - ip_mask);
        ip[p0 - ip_mask] = 0;
        strcpy(mask, p0 + 1);
        return addSubNetControl(ip, mask, allowed);
    }
    if ((strcmp(ip_mask, "*") == 0) || (strcasecmp(ip_mask, "ALL") == 0))
    {
        m_pRoot->setAccess(allowed);
        m_pRoot6->setAccess(allowed);
        return 0;
    }
    else
    {
        if (!isIPv6(achTemp))
            return addIPv4(achTemp, allowed);
        else
            return addIPControl(achTemp, allowed);
    }

}


void AccessControl::clear()
{
    m_pRoot->clear();
    m_pRoot6->clear();
    m_ipCtrl.clear();
}


int AccessControl::addList(const char *pList, int allow)
{
    char achBuf[128];
    int added = 0;
    while (pList)
    {
        const char *p = strpbrk(pList, ", \r\n");
        const char *pEnd;
        if (p)
            pEnd = p++;
        else
            pEnd = pList + strlen(pList);
        int len = StringTool::strTrim(pList, pEnd);
        if ((len > 0) && (len < (int)sizeof(achBuf)))
        {
            memccpy(achBuf, pList, 0, len);
            achBuf[len] = 0;
            //if ( strchr( achBuf, '*' )||( strchr( achBuf, '/' ))
            //    || (achBuf[len-1] == '.' )
            //    || (strcasecmp( achBuf, "ALL") == 0 ))
            if (achBuf[len - 1] == '.')
                achBuf[len - 1] = 0;
            added += (addSubNetControl(achBuf, allow) == 0);
            //else
            //    added += ( addIPControl( achBuf, allow ) == 0 );

        }
        pList = p;
    }
    return added;
}


int AccessControl::hasAccess(const in6_addr &ip) const
{
    if (m_pIp6Ctrl)
    {
        IP6AccessControl::iterator iter = m_pIp6Ctrl->find(&ip);
        if (iter != m_pIp6Ctrl->end())
            return iter.second()->getAccess();
    }
    SubNet6Node *pCurNode = m_pRoot6;
    SubNet6Node *pNextNode;

    while ((pNextNode = pCurNode->matchNode(ip)) != NULL)
        pCurNode = pNextNode;

    return pCurNode->hasAccess();
}


int AccessControl::addIPControl(const in6_addr &ip, int allowed)
{
    if (IN6_IS_ADDR_V4MAPPED(&ip))
        return addIPControl(((Addr6 *)&ip)->m_addrs[3], allowed);
    Addr6 *p = (Addr6 *)&ip;
    if ((!p->m_addrs[0]) && (!p->m_addrs[1]) && (!p->m_addrs[2])
        && (!p->m_addrs[3]))
    {
        m_pRoot6->setAccess(allowed);
        return 0;
    }
    if (!m_pIp6Ctrl)
        m_pIp6Ctrl = new IP6AccessControl(13);
    if (m_pIp6Ctrl)
        return m_pIp6Ctrl->addUpdate(ip, allowed);
    return LS_FAIL;
}


int AccessControl::addSubNetControl(const in6_addr &subNet,
                                    const in6_addr &mask,
                                    int allowed)
{
    Addr6 *p = (Addr6 *)&mask;
    if (IN6_IS_ADDR_V4MAPPED(&subNet))
    {
        if (p->m_addrs[3])
            return addSubNetControl(((Addr6 *)&subNet)->m_addrs[3], p->m_addrs[3],
                                    allowed);
        return LS_FAIL;
    }
    if ((0xffffffff == p->m_addrs[3]) &&
        (0xffffffff == p->m_addrs[2]) &&
        (0xffffffff == p->m_addrs[1]) &&
        (0xffffffff == p->m_addrs[0]))
        return addIPControl(subNet, allowed);
    if ((!p->m_addrs[0]) && (!p->m_addrs[1]) && (!p->m_addrs[2])
        && (!p->m_addrs[3]))
    {
        m_pRoot6->setAccess(allowed);
        return 0;
    }

    return insSubNetControl(subNet, mask, allowed);
}


int AccessControl::insSubNetControl(const in6_addr &subNet,
                                    const in6_addr &mask,
                                    int allowed)
{
    SubNet6Node *pCur = m_pRoot6;
    SubNet6Node *pNext;
    while ((pNext = pCur->matchNode(subNet)) != NULL)
    {
        if (GHash::cmpIpv6(&pNext->getMask(), &mask) == 0)
        {
            pNext->setAccess(allowed);
            return 1; // confict with previous
        }
        pCur = pNext;
    }

    pCur->insertChild(subNet, mask, allowed);
    return 0;
}


int AccessControl::isAvailable(const XmlNode *pNode)
{
    const XmlNode *pNode1 = pNode->getChild("accessControl");

    if (pNode1)
    {
        const char *pAllow = pNode1->getChildValue("allow");

        if (((pAllow) && strcasestr(pAllow, "T"))
            || (pNode1->getChildValue("deny")))
            return 1;
    }

    return 0;
}





