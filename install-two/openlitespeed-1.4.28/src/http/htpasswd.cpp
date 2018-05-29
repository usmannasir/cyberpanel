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
#include "htpasswd.h"

#include <http/authuser.h>
#include <util/stringtool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>


// Passwoard file format can be
// <user_name>:<password>
// <user_name>:<password>:<groups>
// <user_name>:<password>:<groups>:comments
//
// <groups> is comma seperated list of group name


KeyData *PasswdFile::newEmptyData(const char *pKey, int len)
{
    KeyData *pData = new AuthUser();
    if (pData)
        pData->setKey(pKey, len);
    return pData;
}


KeyData *PasswdFile::parseLine(const char *pKey, int keyLen, char *pPos,
                               char *pLineEnd)
{
    char *pEnd;
    char *pGroups;
    AuthUser *pData;
    pData = new AuthUser();
    if (pData)
    {
        pEnd = pGroups = strchr(pPos, ':');
        if (!pEnd)
            pEnd = pLineEnd;
        else
            *pEnd = 0;
        StringTool::strTrim((const char *&)pPos, (const char *&)pEnd);
        pData->setKey(pKey, keyLen);
        pData->setPasswd(pPos, pEnd - pPos);
        if (pGroups)
        {
            ++pGroups;
            pEnd = strchr(pGroups, ':');
            if (!pEnd)
                pEnd = pLineEnd;
            else
                *pEnd = 0;
            pData->setGroups(pGroups, pEnd);
        }
    }
    return pData;

}


static char *parseKey(char *&pPos, char *pLineEnd, int &keyLen)
{
    char ch;
    char *pKey = NULL;
    char *pKeyEnd;
    while (((ch = *pPos) == ' ') || (ch == '\t'))
        ++pPos;
    char *pValue = (char *)memchr(pPos, ':', pLineEnd - pPos);
    if (pValue)
    {
        pKey = pPos;
        pKeyEnd = pValue;
        pPos = pValue + 1;
        while (((ch = *(pKeyEnd - 1)) == ' ') || (ch == '\t'))
            --pKeyEnd;
        keyLen = pKeyEnd - pKey;
    }
    return pKey;
}


KeyData *PasswdFile::parseLine(char *pPos, char *pLineEnd)
{
    char *pKey;
    int keyLen;
    pKey = parseKey(pPos, pLineEnd, keyLen);
    if (pKey)
        return parseLine(pKey, keyLen, pPos, pLineEnd);
    return NULL;
}


// <group_name>:<member list>
// <group_name>:<member list>:comments
//
// <groups> is a comma seperated list of group name


KeyData *GroupFile::parseLine(char *pPos, char *pLineEnd)
{
    char *pKey;
    int keyLen;
    pKey = parseKey(pPos, pLineEnd, keyLen);
    if (pKey)
        return parseLine(pKey, keyLen, pPos, pLineEnd);
    return NULL;
}


KeyData *GroupFile::parseLine(const char *pKey, int keyLen, char *pPos,
                              char *pLineEnd)
{
    char *pEnd;
    AuthGroup *pData;
    pData = new AuthGroup();
    if (pData)
    {
        pData->setKey(pKey, keyLen);
        pEnd = strchr(pPos, ':');
        if (!pEnd)
            pEnd = pLineEnd;
        else
            *pEnd = 0;
        if (pData->split(pPos, pEnd, ", ") > 1)
            pData->sort();
    }
    return pData;
}


KeyData *GroupFile::newEmptyData(const char *pKey, int len)
{
    KeyData *pData = new AuthGroup();
    if (pData)
        pData->setKey(pKey, len);
    return pData;
}



