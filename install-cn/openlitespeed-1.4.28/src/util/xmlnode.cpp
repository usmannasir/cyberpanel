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
#include <util/xmlnode.h>

#include <assert.h>
#include <ctype.h>
#include <expat.h>
#include <string.h>
#include <lsr/ls_strtool.h>
#include <util/autostr.h>
#include <util/radixtree.h>

#include <limits.h>
#include <fcntl.h>
#include <unistd.h>

#define BUF_SIZE 4096
#define MAX_XML_VALUE_LEN (1024 * 1024 - 2)
const int iXmlNodeRTFlag = RTFLAG_NOCONTEXT | RTFLAG_GLOBALPOOL |
                           RTFLAG_CICMP;

typedef struct xmlouthelper_s
{
    FILE *fd;
    int depth;
} xmlouthelper_t;


class Attr
{
    AutoStr m_name;
    AutoStr m_value;
public:
    Attr(const char *name, const char *value);
    Attr() {};
    ~Attr() {};
    const char *getName() const     {   return m_name.c_str();  }
    const char *getValue() const    {   return m_value.c_str(); }

};


Attr::Attr(const char *name, const char *value)
    : m_name(name), m_value(value)
{}


class XmlNodeImpl
{
    friend class XmlNode;
    friend class XmlTree;

    AutoStr m_name;
    AutoStr2 m_value;
    RadixNode  *m_pNode;
    RadixTree  *m_pAttrMap;

    XmlNodeImpl()
        : m_pNode(NULL)
        , m_pAttrMap(NULL)
    {};


    ~XmlNodeImpl()
    {
        if (m_pAttrMap)
            delete m_pAttrMap;
    };

    int init(const char *el, const char **attr);
    int addChild(const char *name, XmlNode *pChild);
    void initNode(XmlNodeImpl *pParent, XmlNode *pSelf)
    {
        RadixNode *parent = (pParent == NULL ? NULL : pParent->m_pNode);
        if (m_pNode == NULL)
            m_pNode = RadixNode::newNode(NULL, parent, pSelf);
        else
        {
            assert(m_pNode->getParent() == NULL);
            m_pNode->setParent(parent);
        }
    }
    int nodeInited()
    {
        return (m_pNode == NULL ? 0 : 1);
    }
};


int XmlNodeImpl::init(const char *el, const char **attr)
{
    int i;
    m_name = el;
    if ((attr[0]) && (!m_pAttrMap))
    {
        m_pAttrMap = new RadixTree();
        m_pAttrMap->setNoContext();
        m_pAttrMap->setUseGlobalPool();
    }

    for (i = 0; attr[i]; i += 2)
    {
        Attr *pAttr = new Attr(attr[i], attr[i + 1]);
        if (m_pAttrMap->insert(pAttr->getName(), strlen(pAttr->getName()),
                               pAttr) == NULL)
            return LS_FAIL;
    }
    return LS_OK;
}


int XmlNodeImpl::addChild(const char *name, XmlNode *pChild)
{
    XmlNodeList *pList;
    if ((pList = (XmlNodeList *)m_pNode->find(name, strlen(name),
                 iXmlNodeRTFlag)) != NULL)
    {
        pList->push_back(pChild);
        return LS_OK;
    }

    pList = new XmlNodeList(4);
    if (pList == NULL)
        return LS_FAIL;
    pList->push_back(pChild);
    if (m_pNode->insert(NULL, name, strlen(name), pList,
                        iXmlNodeRTFlag) == NULL)
    {
        delete pList;
        return LS_FAIL;
    }
    return LS_OK;
}


XmlNode::XmlNode()
    : m_pImpl(NULL)
{
    m_pImpl = new XmlNodeImpl();
}


XmlNode::~XmlNode()
{
    delete m_pImpl;
}


int XmlNode::init(const char *name, const char **attr)
{
    return m_pImpl->init(name, attr);
}


const char *XmlNode::getName() const
{
    return m_pImpl->m_name.c_str();
}


const char *XmlNode::getValue() const
{
    return m_pImpl->m_value.c_str();
}


int XmlNode::getValueLen() const
{
    return m_pImpl->m_value.len();
}


int XmlNode::addChild(const char *name, XmlNode *pChild)
{
    if (m_pImpl->nodeInited() == 0)
        m_pImpl->initNode(NULL, this);
    if (m_pImpl->addChild(name, pChild) == LS_FAIL)
        return LS_FAIL;
    pChild->m_pImpl->initNode(m_pImpl, pChild);
    return 0;
}


XmlNode *XmlNode::getParent() const
{
    if (m_pImpl->m_pNode == NULL)
        return NULL;
    return (XmlNode *)m_pImpl->m_pNode->getParentObj();
}


int XmlNode::setValue(const char *value, int len)
{
    m_pImpl->m_value.setStr(value, len);
    return 0;
}


const XmlNode *XmlNode::getChild(const char *name, int bOptional) const
{
    XmlNodeList *ptr;
    if (m_pImpl->m_pNode == NULL)
        return NULL;
    if (m_pImpl->m_pNode->getNumChildren() != 0)
    {
        ptr = (XmlNodeList *)m_pImpl->m_pNode->find(name, strlen(name),
                iXmlNodeRTFlag);
        if (ptr != NULL)
            return *(ptr->begin());
    }
    if (bOptional)
        return this;
    return NULL;
}


const char *XmlNode::getChildValue(const char *name, int bKeyName) const
{
    if (bKeyName)
    {
        const char *p = getValue();
        if (p)
            return p;
    }
    const XmlNode *pNode = getChild(name);
    if (pNode)
        return pNode->getValue();
    return NULL;
}


int XmlNode::getChildValueLen(const char *name, int bKeyName) const
{
    if (bKeyName)
        return getValueLen();
    const XmlNode *pNode = getChild(name);
    if (pNode)
        return pNode->getValueLen();
    return 0;
}


static long long getLongValue(const char *pValue, int base = 10)
{
    long long l = strlen(pValue);
    long long m = 1;
    char ch = *(pValue + l - 1);
    if (ch == 'G' || ch == 'g')
        m = 1024 * 1024 * 1024;
    else if (ch == 'M' || ch == 'm')
        m = 1024 * 1024;
    else if (ch == 'K' || ch == 'k')
        m = 1024;
    return strtoll(pValue, (char **)NULL, base) * m;
}


long long XmlNode::getLongValue(const char *pTag,
                                long long min, long long max, long long def, int base) const
{
    const char *pValue = getChildValue(pTag);
    long long val;
    if (!pValue)
        return def;
    val = ::getLongValue(pValue, base);
    if ((max == INT_MAX) && (val > max))
        val = max;
    if (((min != LLONG_MIN) && (val < min)) ||
        ((max != LLONG_MAX) && (val > max)))
    {
        //LS_WARN( "[%s] invalid value of <%s>:%s, use default=%ld",
        //         getLogId(), pTag, pValue, def ));
        return def;
    }
    return val;
}


XmlNode *XmlNode::getChild(const char *name, int bOptional)
{
    return (XmlNode *)((const XmlNode *)this)->getChild(name, bOptional);
}


const XmlNodeList *XmlNode::getChildren(const char *name) const
{
    if (m_pImpl->m_pNode->getNumChildren() == 0)
        return NULL;
    return (XmlNodeList *)m_pImpl->m_pNode->find(name, strlen(name),
            iXmlNodeRTFlag);
}


int XmlNode::hasChild()
{
    if (m_pImpl->m_pNode == NULL)
        return 0;
    return (m_pImpl->m_pNode->getNumChildren() > 0 ? 1 : 0);
}


int XmlNode::getAllChildren(XmlNodeList &list)
{
    return ((const XmlNode *)this)->getAllChildren(list);
}


static int addListToList(void *pObj, void *pUData, const char *pKey,
                         int iKeyLen)
{
    XmlNodeList *pChild = (XmlNodeList *)pObj;
    XmlNodeList *pList = (XmlNodeList *)pUData;
    pList->push_back(*pChild);
    return LS_OK;
}


int XmlNode::getAllChildren(XmlNodeList &list) const
{
    int count = list.size();
    if (m_pImpl->m_pNode == NULL)
        return 0;
    else if (m_pImpl->m_pNode->getNumChildren() == 0)
        return 0;
    else if (m_pImpl->m_pNode->for_each_child2(addListToList, &list) == 0)
        return 0;
    return list.size() - count;
}


const char *XmlNode::getAttr(const char *name) const
{
    Attr *ptr;
    if (m_pImpl->m_pAttrMap == NULL)
        return NULL;
    ptr = (Attr *)m_pImpl->m_pAttrMap->find(name, strlen(name));
    if (ptr != NULL)
        return ptr->getValue();
    return NULL;
}


static int printAttrChild(void *pObj, void *pUData, const char *pKey,
                          int iKeyLen)
{
    Attr *ptr = (Attr *)pObj;
    FILE *fd = (FILE *)pUData;
    fprintf(fd, " %.*s=\"%s\"", iKeyLen, pKey, ptr->getValue());
    return LS_OK;
}


static int printChild(void *pObj, void *pUData, const char *pKey,
                      int iKeyLen)
{
    XmlNodeList::const_iterator iter;
    XmlNodeList *pList = (XmlNodeList *)pObj;
    xmlouthelper_t *pHelper = (xmlouthelper_t *)pUData;
    FILE *fd = pHelper->fd;
    int depth = pHelper->depth;
    for (iter = pList->begin(); iter != pList->end(); ++iter)
        (*iter)->xmlOutput(fd, depth + 1);
    return LS_OK;
}


int XmlNode::xmlOutput(FILE *fd, int depth) const
{
    xmlouthelper_t helper;
    for (int i = 0; i <= depth; ++ i)
        fprintf(fd, " ");
    fprintf(fd, "<%s", getName());
    if (m_pImpl->m_pAttrMap != NULL)
        m_pImpl->m_pAttrMap->for_each2(printAttrChild, fd);

    fprintf(fd, ">");
    if (m_pImpl->m_value.len() != 0)
        fprintf(fd, "%s", getValue());

    if (m_pImpl->m_pNode->getNumChildren() != 0)
    {
        fprintf(fd, "\n");
        helper.depth = depth;
        helper.fd = fd;
        m_pImpl->m_pNode->for_each_child2(printChild, &helper);
        for (int i = 0; i <= depth; ++ i)
            fprintf(fd, " ");
    }
    fprintf(fd, "</%s>\n", getName());
    return 0;
}


class XmlTree
{
public:
    XmlTree()
        : m_pRoot(NULL)
        , m_pCurNode(NULL)
        , m_setValue(false)
    {
        m_curValue.prealloc(MAX_XML_VALUE_LEN);
    }
    ~XmlTree()
    {};

    void startElement(const char *el, const char **attr);
    void endElement(const char *el);
    void charHandler(const char *el, int len);

    XmlNode *m_pRoot;
    XmlNode *m_pCurNode;
    AutoStr2 m_curValue;
    bool    m_setValue;
};


void XmlTree::startElement(const char *el, const char **attr)
{
    XmlNode *pNewNode = new XmlNode();
    pNewNode->init(el, attr);
    if (m_pRoot == NULL)
        m_pRoot = m_pCurNode = pNewNode;
    else
    {
        m_pCurNode->addChild(pNewNode->getName(), pNewNode);
        m_pCurNode = pNewNode;
    }
}


void XmlTree::endElement(const char *el)
{
    if (m_setValue)
    {
        const char *pValue = m_curValue.c_str();
        int len = m_curValue.len();
        int start = 0;
        while ((start < len) && isspace(*(pValue + start)))
            ++start;
        if (start < len)
        {
            while ((len > start) && isspace(*(pValue + len - 1)))
                --len;
            m_pCurNode->setValue(pValue + start, len - start);
            m_setValue = false;
            *m_curValue.buf() = 0;
            m_curValue.setLen(0);
        }
    }
    m_pCurNode = m_pCurNode->getParent();
}


void XmlTree::charHandler(const char *el, int len)
{
    if (!m_setValue)
    {
        int start = 0;
        while ((start < len) && isspace(*(el + start)))
            ++start;
        if (start == len)
            return;
    }
    m_setValue = true;
    if (len + m_curValue.len() >= MAX_XML_VALUE_LEN)
        len = MAX_XML_VALUE_LEN - m_curValue.len();
    if (len > 0)
    {
        memmove(m_curValue.buf() + m_curValue.len(), el, len);
        m_curValue.setLen(len + m_curValue.len());
        *(m_curValue.buf() + m_curValue.len()) = 0;
    }
}


static void startElement(void *data, const char *el, const char **attr)
{
    XmlTree *pTree = (XmlTree *)data;
    pTree->startElement(el, attr);
}


static void endElement(void *data, const char *el)
{
    XmlTree *pTree = (XmlTree *)data;
    pTree->endElement(el);
}


static void charHandler(void *data, const char *el, int len)
{
    XmlTree *pTree = (XmlTree *)data;
    pTree->charHandler(el, len);
}


XmlNode *XmlTreeBuilder::parse(const char *pFilePath, char *pError,
                               int errBufLen)
{
    int fd = open(pFilePath, O_RDONLY);
    if (fd == -1)
    {
        ls_snprintf(pError, errBufLen, "Cannot open xml file: %s\n", pFilePath);
        return NULL;
    }

    char buf[BUF_SIZE];
    XmlTree tree;
    XML_Parser parser = XML_ParserCreate(NULL);
    int done;
    XML_SetUserData(parser, &tree);
    XML_SetElementHandler(parser, startElement, endElement);
    XML_SetCharacterDataHandler(parser, charHandler);

    do
    {
        size_t len = read(fd, buf, sizeof(buf));
        done = len < sizeof(buf);

        if (XML_Parse(parser, buf, len, done) == XML_STATUS_ERROR)
        {
            ls_snprintf(pError, errBufLen, "[%s:%d] %s \n", pFilePath,
                        XML_GetCurrentLineNumber(parser),
                        XML_ErrorString(XML_GetErrorCode(parser))
                       );
            XML_ParserFree(parser);
            close(fd);
            if (tree.m_pRoot)
                delete tree.m_pRoot;
            return NULL;
        }
    }
    while (!done);

    XML_ParserFree(parser);

    close(fd);

    return tree.m_pRoot;
}

