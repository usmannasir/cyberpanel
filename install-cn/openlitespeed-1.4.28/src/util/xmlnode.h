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
#ifndef XMLNODE_H
#define XMLNODE_H

#include <stdio.h>
#include <util/gpointerlist.h>

class XmlNodeImpl;
class XmlNode;
class Attr;

class XmlNodeList : public TPointerList<XmlNode>
{
public:
    explicit XmlNodeList(int n)
        : TPointerList<XmlNode>(n)
    {}
    XmlNodeList() {}
};


class XmlNode
{
private:
    XmlNode(const XmlNode &rhs) {}
    void operator=(const XmlNode &rhs) {}
    XmlNodeImpl *m_pImpl;

public:
    XmlNode();
    ~XmlNode();

    int init(const char *name, const char **attr);
    int addChild(const char *name, XmlNode *pChild);
    const XmlNode *getChild(const char *name, int bOptional  = 0) const;
    XmlNode *getChild(const char *name, int bOptional = 0);
    const XmlNodeList *getChildren(const char *name) const;
    int getAllChildren(XmlNodeList &list) const;
    int getAllChildren(XmlNodeList &list);
    int hasChild();
    const char *getChildValue(const char *name, int bKeyName = 0) const;
    int getChildValueLen(const char *name, int bKeyName = 0) const;
    const char *getAttr(const char *name) const;
    const char *getName() const;
    const char *getValue() const;
    int getValueLen() const;
    long long getLongValue(const char *pTag, long long min, long long max,
                           long long def, int base = 10) const;

    int setValue(const char *value, int len);
    XmlNode *getParent() const;
    int xmlOutput(FILE *fd, int depth) const;
};

class XmlTreeBuilder
{
public:
    XmlTreeBuilder() {};
    ~XmlTreeBuilder() {};

    XmlNode *parse(const char *fileName, char *pErrBuf, int errBufLen);
};

#endif
