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
#ifndef __PLAINCONF_H__
#define __PLAINCONF_H__

/*Usage of this module
 * parseFile() to parse a whole file includes "include" and return the root node
 * of the config tree
 * release() to release all the resources of the config tree
 * getConfDeepValue() to get the value of a multi level branch, such as "security|fileAccessControl|checkSymbolLink"
 * use XmlNode::getChild to get the XmlNode pointer of a node
 * use the XmlNodeList * XmlNode::getAllChildren to get a list of a certen node, and
 *      use the iterator to check all the value in this list
*/

#include <util/autostr.h>
#include <util/stringlist.h>

#include <stdio.h>

class XmlNode;

enum
{
    LOG_LEVEL_ERR = 'E',
    LOG_LEVEL_INFO = 'I',
};

enum ConfFileType
{
    eConfUnknown = 0,
    eConfFile,
    eConfDir,
    eConfWildcard,  //directory with wildchar
};


struct plainconfKeywords
{
    const char *name;
    const char *alias;
};

class plainconf
{
public:
    static void initKeywords();
    static void setRootPath(const char *root) ;
    static const char *getRealName(char *name);
    static void outputConfigFile(const XmlNode *pNode, FILE *fp, int level);
    static void testOutputConfigFile(const XmlNode *pNode, const char *file);
    static void loadDirectory(const char *pPath, const char *pPattern);
    static void checkInFile(const char *path);
    static void loadConfFile(const char *path);
    static XmlNode *parseFile(const char *configFilePath, const char *rootTag);
    static void release(XmlNode *pNode);


    static void logToMem(char errorLevel, const char *format, ...);
    static void flushErrorLog();

    static void tolowerstr(char *sLine);
    static void trimWhiteSpace(const char **p);
    static const char *getStrNoSpace(const char *sLine, size_t &length);
    static void removeSpace(char *sLine, int pos);
    static bool strcatchr(char *s, char c, int maxStrLen);

    static bool isChunkedLine(const char *sLine);
    static bool isValidline(const char *sLine);
    static int checkMultiLineMode(const char *sLine, char *sMultiLineModeSign,
                                  int maxSize);
    static bool isInclude(const char *sLine, AutoStr2 &path);

    static void saveUnknownItems(const char *fileName, int lineNumber,
                                 XmlNode *pCurNode, const char *name, const char *value);
    static void appendModuleParam(XmlNode *pModuleNode, const char *param);
    static void addModuleWithParam(XmlNode *pCurNode, const char *moduleName,
                                   const char *param);

    static void handleSpecialCase(XmlNode *pNode);
    static void handleSpecialCaseLoop(XmlNode *pNode);

    static void clearNameAndValue(char *name, char *value);

    static void parseLine(const char *fileName, int lineNumber,
                          const char *sLine);

    static ConfFileType checkFiletype(const char *path);
    static void getIncludeFile(const char *curDir, const char *orgFile,
                               char *targetFile);

    static const char *getConfDeepValue(const XmlNode *pNode,
                                        const char *name);

    static void outputSpaces(int level, FILE *fp);
    static void outputValue(FILE *fp, const char *value, int length);
    static void outputSigleNode(FILE *fp, const XmlNode *pNode, int level);

public:
    static plainconfKeywords sKeywords[];
    static GPointerList gModuleList;
    static bool bKeywordsInited;
    static AutoStr2 rootPath;
    static StringList errorLogList;
    static bool bErrorLogSetup;

};

#endif  //__PLAINCONF_H__
