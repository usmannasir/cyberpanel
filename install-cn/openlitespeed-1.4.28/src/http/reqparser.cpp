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

#include "reqparser.h"

#include <http/httpreq.h>
#include <http/requestvars.h>

#include <log4cxx/logger.h>

#include <util/gpath.h>
#include <util/stringtool.h>
#include <util/vmembuf.h>
#include <util/autobuf.h>
#include <util/stringtool.h>

#include <ctype.h>
#include <stdlib.h>
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>

ReqParser::ReqParser()
    : m_decodeBuf(8192)
    , m_multipartBuf(8192)
    , m_ignore_part(1)
    , m_multipartState(0)
    , m_resume(0)
    , m_md5CachedNum(0)
    , m_iCurOff(0)
    , m_state_kv(0)
    , m_last_char(0)
    , m_iParseState(0)
    , m_beginIndex(0)
    , m_args(0)
    , m_maxArgs(0)
    , m_pArgs(NULL)
    , m_pReq(NULL)
    , m_sLastFileKey("")
    , m_pLastFileBuf(NULL)
    , m_iContentLength(0)
    , m_pFileUploadConfig(NULL)
{
    allocArgIndex(8);
}

ReqParser::~ReqParser()
{
    if (m_pLastFileBuf)
        closeLastMFile();
    m_sLastFileKey.setLen(0);

    if (m_pArgs)
    {
        for (int i = 0; i < m_args; ++i)
        {
            if (m_pArgs[i].filePath)
            {
                unlink(m_pArgs[i].filePath);
                free(m_pArgs[i].filePath);
            }
        }
        free(m_pArgs);
        m_pArgs = NULL;
    }

    if (m_pFileUploadConfig)
    {
        delete m_pFileUploadConfig;
        m_pFileUploadConfig = NULL;
    }
}


void ReqParser::reset()
{
    m_decodeBuf.clear();
    m_multipartBuf.clear();
    m_state_kv = 0;
    m_beginIndex = 0;
    m_args = 0;
    m_part_boundary = "";
    m_ignore_part = 1;
    m_multipartState = MPS_INIT_BOUNDARY;
    m_iCurOff = 0;
    m_last_char = 0;
    m_pErrStr = NULL;
    m_iParseState = 0;
    m_qsBegin   = 0;
    m_qsArgs    = 0;
    m_postBegin = 0;
    m_postArgs  = 0;
    m_pLastFileBuf = NULL;
    m_resume = 0;
    m_md5CachedNum = 0;
    m_pReq = NULL;
    m_sLastFileKey.setLen(0);
    m_iContentLength = 0;
    if (m_pFileUploadConfig)
    {
        delete m_pFileUploadConfig;
        m_pFileUploadConfig = NULL;
    }
}


int ReqParser::allocArgIndex(int newMax)
{
    if (newMax <= m_maxArgs)
        return 0;
    KeyValuePairFile *pNewBuf = (KeyValuePairFile *)realloc(m_pArgs,
                                sizeof(KeyValuePairFile) * newMax);
    if (pNewBuf)
    {
        m_pArgs = pNewBuf;
        m_maxArgs = newMax;
    }
    else
        return -1;
    return 0;
}


int ReqParser::appendArgKeyIndex(int begin, int len)
{
    ++m_args;
    if (m_args >= m_maxArgs)
    {
        int newMax = m_maxArgs << 1;
        if (allocArgIndex(newMax))
            return -1;
    }
    m_pArgs[m_args - 1].keyOffset = begin;
    m_pArgs[m_args - 1].keyLen    = len;
    m_pArgs[m_args - 1].valueOffset   = begin + len + 1;
    m_pArgs[m_args - 1].valueLen      = 0;
    m_pArgs[m_args - 1].filePath = NULL;
    if (m_pLastFileBuf)
        closeLastMFile();
    m_sLastFileKey.setLen(0);
    return 0;
}

int ReqParser::appendArg(int beginIndex, int endIndex, int isValue)
{
    int len = endIndex - beginIndex;

    //if( len > 0 )
    //    len = normalisePath( beginIndex, len );

    if (isValue)
    {
        //if ( m_args > 0)
        {
            m_pArgs[m_args - 1].valueOffset   = beginIndex;
            m_pArgs[m_args - 1].valueLen      = len;
        }
    }
    else
        return appendArgKeyIndex(beginIndex, len);
    return 0;
}

int ReqParser::normalisePath(int begin, int len)
{
    int n;
    m_decodeBuf.appendUnsafe('\0');
    n = GPath::clean(m_decodeBuf.getp(begin), len);
    if (n < len)
        m_decodeBuf.pop_end(len - n + 1);
    else
        m_decodeBuf.pop_end(1);
    return n;
}

int ReqParser::appendArgKey(const char *pStr, int len)
{
    if (m_decodeBuf.size())
        m_decodeBuf.append("&", 1);
    int begin = m_decodeBuf.size();
    m_decodeBuf.append(pStr, len);

    //len = normalisePath( begin, len );

    m_decodeBuf.append("=", 1);
    return appendArgKeyIndex(begin, len);

}


void ReqParser::resumeDecode(const char *&pStr, const char *pEnd)
{
    char ch;
    if (m_last_char == 1)
    {
        if (pEnd > pStr)
        {
            if (isxdigit(*pStr))
                m_last_char = *pStr++;
            else
                m_last_char = 0;
        }
    }
    if (isxdigit(m_last_char))
    {
        if (pEnd > pStr)
        {
            if (isxdigit(*pStr))
            {
                ch = (hexdigit(m_last_char) << 4) + hexdigit(*pStr++);
                if (!ch)
                    ch = ' ';
                m_decodeBuf.appendUnsafe(ch);
            }
            else
                m_decodeBuf.appendUnsafe(m_last_char);
            m_last_char = 0;
        }
    }
}

int ReqParser::parseArgs(const char *pStr, int len, int resume, int last)
{
    const char *pEnd = pStr + len;
    char   ch = 0;
    if (m_decodeBuf.available() < len)
        m_decodeBuf.grow(len);
    if (!resume)
        m_beginIndex = m_decodeBuf.size();
    else
    {
        if (m_last_char)
            resumeDecode(pStr, pEnd);
    }
    while (pStr < pEnd)
    {
        ch = *pStr++;
        switch (ch)
        {
        case '#':
            pStr = pEnd;
            break;
        case '=':
            if (m_state_kv)
                break;
        //fall through
        case '&':
            appendArg(m_beginIndex, m_decodeBuf.size(), m_state_kv);
            m_state_kv = (ch == '=');
            m_decodeBuf.appendUnsafe(ch);
            m_beginIndex = m_decodeBuf.size();
            continue;
        case '+':
            ch = ' ';
            break;
        case '%':
            m_last_char = 1;
            resumeDecode(pStr, pEnd);
            continue;
        }
        if (!ch)
            ch = ' ';
        m_decodeBuf.appendUnsafe(ch);
    }
    if (last)
    {
        if (isxdigit(m_last_char))
            m_decodeBuf.appendUnsafe(ch);
        if (m_beginIndex != m_decodeBuf.size())
        {
            if ((!m_state_kv) || (m_args))
                appendArg(m_beginIndex, m_decodeBuf.size(), m_state_kv);
        }
    }
    return 0;
}

int ReqParser::parseQueryString(const char *pQS, int len)
{
    if (len > 0)
    {
        int ret;
        m_last_char = 0;
        m_qsBegin = m_args;
        ret = parseArgs(pQS, len, 0, 1);
        m_qsArgs = m_args - m_qsBegin;
        return ret;
    }
    return 0;
}

int ReqParser::initMutlipart(const char *pContentType, int len)
{
    if (!pContentType)
    {
        m_pErrStr = "Missing ContentType";
        return -1;
    }
    m_last_char = 0;
    m_multipartBuf.clear();
    const char *p = strstr(pContentType, "boundary=");
    if (p && *(p + 9))
    {
        len = len - ((p + 9) - pContentType);
        if (len > MAX_BOUNDARY_LEN)
        {
            m_pErrStr = "Boundary string is too long";
            m_multipartState = MPS_ERROR;
            return -1;
        }
        m_part_boundary.setStr(p + 9, len);
    }
    else
    {
        m_pErrStr = "Boundary string is not available";
        m_multipartState = MPS_ERROR;
        return -1;
    }

    m_multipartState = MPS_INIT_BOUNDARY;
    return 0;
}

int ReqParser::parseKeyValue(char *&pBegin, char *pLineEnd,
                             char *&pKey, int &keyLen, char *&pValue, int &valLen)
{
    char *pValueEnd;
    pValue = (char *)memchr(pBegin, '=', pLineEnd - pBegin);
    if (!pValue)
    {
        m_pErrStr = "Invalid Content-Disposition value";
        m_multipartState = MPS_ERROR;
        return -1;
    }
    pKey = pBegin;
    keyLen = pValue - pKey;
    ++pValue;

    if (*pValue == '"')
    {
        ++pValue;
        pValueEnd = (char *)memchr(pValue, '"', pLineEnd - pBegin);
        if (!pValueEnd)
        {
            m_pErrStr = "missing ending '\"' in Content-Disposition value";
            m_multipartState = MPS_ERROR;
            return -1;
        }
    }
    else
    {
        pValueEnd = strpbrk(pValue, " \t;\r\n");
        if (!pValueEnd)
            pValueEnd = pLineEnd;
    }

    valLen = pValueEnd - pValue;
    pBegin = pValueEnd + 1;
    return 0;
}


int ReqParser::multipartParseHeader(char *pBegin, char *pLineEnd)
{
    char   *pName       = NULL;
    int     nameLen     = 0;
    char   *fileStr     = NULL;
    int     fileStrLen  = 0;
    int     fileStrType = 0; //1: FILENAME, 2: CONTENTTYPE

    int     ret = 0;
    while (pBegin < pLineEnd)
    {
        if (strncasecmp("content-disposition:", pBegin, 20) == 0)
        {
            pBegin += 20;
            while (isspace(*pBegin))
                ++pBegin;
            if (strncasecmp("form-data;", pBegin, 10) != 0)
            {
                m_pErrStr = "missing 'form-data;' string in Content-Disposition value";
                m_multipartState = MPS_ERROR;
                return -1;
            }
            pBegin += 10;
            while (isspace(*pBegin))
                ++pBegin;
            while ((*pBegin) && (*pBegin != '\n') && (*pBegin != '\r'))
            {
                char *pKey, *pValue;
                int keyLen, valLen;
                if (parseKeyValue(pBegin, pLineEnd, pKey, keyLen, pValue, valLen) == -1)
                    break;
                if (keyLen == 4 && strncasecmp("name", pKey, 4) == 0)
                {
                    if (valLen == 0)
                        m_ignore_part = 1;
                    else
                    {
                        pName   = pValue;
                        nameLen = valLen;
                    }
                }
                else if (keyLen == 8 && strncasecmp("filename", pKey, 8) == 0)
                {
                    m_ignore_part   = 1;
                    fileStr       = pValue;
                    fileStrLen     = valLen;
                    fileStrType = 1;

                    ret = appendArgKey(pName, nameLen);
                    if (ret == 0)
                    {
                        m_decodeBuf.append(fileStr, fileStrLen);
                        fileStrLen = normalisePath(m_pArgs[m_args - 1].valueOffset, fileStrLen);

                        m_pArgs[m_args - 1].valueLen = fileStrLen;
                        m_sLastFileKey.setStr(pName, nameLen);

                        if (fileStrLen > 0 && m_pFileUploadConfig)
                        {
                            int templateLen = m_pFileUploadConfig->m_sUploadFilePathTemplate.len();
                            char *p = (char *)malloc(templateLen + 8);
                            if (!p)
                                return -1;

                            memcpy(p, m_pFileUploadConfig->m_sUploadFilePathTemplate.c_str(), templateLen);
                            memcpy(p + templateLen, "/XXXXXX", 7);
                            *(p + templateLen + 7) = 0x00;
                            int fd = mkstemp(p);
                            if (fd == -1)
                            {
                                m_multipartState = MPS_ERROR;
                                free(p);
                                return -1;
                            }

                            m_pLastFileBuf = new VMemBuf;
                            if (!m_pLastFileBuf)
                            {
                                free(p);
                                close(fd);
                                return -1;
                            }
                            m_pLastFileBuf->setFd(p, fd);
                            m_pArgs[m_args - 1].filePath = p;
                            fchmod(fd, m_pFileUploadConfig->m_iFileMod);

                            //m_iFormState = PARSE_FORM_NAME;
                            //Need to append to bodyBuf path, name, content_type
                            appendFileKeyValue("_name", 5, fileStr, fileStrLen, true);
                            appendFileKeyValue("_path", 5, p, strlen(p));
                            ls_md5_init(&m_md5Ctx);
                        }
                        else
                        {
                            m_pArgs[m_args - 1].filePath = NULL;
                            appendFileKeyValue("_name", 5, "", 0, true);
                            appendFileKeyValue("_path", 5, "", 0);
                        }
                    }
                }
                while ((*pBegin == ' ') || (*pBegin == '\t') || (*pBegin == ';'))
                    ++pBegin;

            }
        }
        else if (strncasecmp("content-type:", pBegin, 13) == 0)
        {
            pBegin += 13;
            while (isspace(*pBegin))
                ++pBegin;
            if (strncasecmp("multipart/mixed", pBegin, 15) == 0)
                m_ignore_part = 1;
            else
            {
                fileStrType = 2;
                fileStr = pBegin;
            }
        }

        pBegin = (char *)memchr(pBegin, '\n', pLineEnd - pBegin);
        if (!pBegin)
            pBegin = pLineEnd;
        else
            ++pBegin;

        if (fileStrType == 2)
        {
            fileStrLen = pBegin - fileStr;
            if (*(pBegin - 1) == '\r')
                --fileStrLen;
            appendFileKeyValue("_content-type", 13, fileStr, fileStrLen);
        }

    }
    if (!pName)
    {
        m_pErrStr = "missing 'name' value in Content-Disposition value";
        m_multipartState = MPS_ERROR;
        return -1;
    }


    if (!m_ignore_part)
        ret = appendArgKey(pName, nameLen);
    return ret;
}

int ReqParser::popProcessedData(char *pBegin, char *pEnd)
{
    if (m_multipartBuf.empty())
    {
        assert(m_iCurOff == 0);
        if (pBegin < pEnd)
        {
            m_iCurOff = pEnd - pBegin;
            m_multipartBuf.append(pBegin, m_iCurOff);
        }
    }
    else
    {
        int iBeginOff = pBegin - m_multipartBuf.begin();
        m_iCurOff = m_multipartBuf.size();
        if (iBeginOff > 0)
        {
            m_multipartBuf.pop_front(iBeginOff);
            m_iCurOff -= iBeginOff;
        }
    }
    return 0;
}

int ReqParser::checkBoundary(char *&pBegin, char *&pCur)
{
    char *p;
    int len;
    if (memcmp(pBegin + 2, m_part_boundary.c_str(),
               m_part_boundary.len()) == 0)
    {
        if (!m_ignore_part)
        {
            if (*(m_decodeBuf.end() - 2) == '\r')
                m_decodeBuf.pop_end(2);
            else
                m_decodeBuf.pop_end(1);
            *(m_decodeBuf.end()) = 0;
            if (m_args > 0)
            {
                len = m_decodeBuf.size() - m_pArgs[m_args - 1].valueOffset;
                len = normalisePath(m_pArgs[m_args - 1].valueOffset, len);
                m_pArgs[m_args - 1].valueLen = len;
            }
        }
        else if (m_pLastFileBuf)
        {
            off_t size = m_pLastFileBuf->getCurWOffset();
            int additionalBytes = m_trial_crlf - 1;
            if (additionalBytes > 0)
            {
                m_pLastFileBuf->rewindWOff(additionalBytes);
                m_pLastFileBuf->shrinkBuf(size - additionalBytes);
            }
            closeLastMFile();

            char s[30] = {0};
            int l = ls_snprintf(s, 30, "%lld", size - additionalBytes);
            appendFileKeyValue("_size", 5, s, l);

            //Now calc file size and MD5 and append to bodyBuf
            char sMd5[16], sMd5Hex[33];
            if (m_md5CachedNum - additionalBytes > 0)
                ls_md5_update(&m_md5Ctx, m_md5CachedBytes,
                              m_md5CachedNum - additionalBytes);
            ls_md5_final((unsigned char *)sMd5, &m_md5Ctx);
            m_md5CachedNum = 0;
            StringTool::hexEncode(sMd5, 16, sMd5Hex);
            appendFileKeyValue("_md5", 4, sMd5Hex, 32);
        }
        m_sLastFileKey.setLen(0);

        p = pBegin + 2 + m_part_boundary.len();
        if (*p == '-')
        {
            if (*(p + 1) == '-')
            {
                appendBodyBuf(pBegin, (p + 2 - pBegin));
                appendBodyBuf("\r\n", 2);
                m_multipartState = MPS_END;
                return 1;
            }
        }
        else
        {
            if (*p == '\r')
                ++p;
            if (*p == '\n')
            {
                m_multipartState = MPS_PART_HEADER;
                appendBodyBuf(pBegin, (p + 1 - pBegin));
                pCur = pBegin = ++p;
                m_ignore_part = 0;
                return 1;
            }
        }
        m_pErrStr = "Invalid boundary string encountered.";
        m_multipartState = MPS_ERROR;
        return -1;
    }
    if (m_multipartState == MPS_INIT_BOUNDARY)
    {
        m_pErrStr = "initial BOUNDARY string is missing";
        m_multipartState = MPS_ERROR;
        return -1;
    }
    m_multipartState = MPS_PART_DATA;
    pCur = pBegin;
    return 0;
}


int ReqParser::parseMultipart(const char *pBuf, size_t size,
                              int resume, int last)
{
    //TODO:  if m_multipartBuf is empty and do not copy,
    //use pBuf directly, if have left part, then write to it for next time using
    int    ret;
    int count = 0;
    char *pLineEnd = NULL, *p;
    char *pBegin, *pEnd, *pCur;
    char *pOldCur = NULL;

    if (m_multipartBuf.empty())
    {
        assert(m_iCurOff == 0);
        pBegin = (char *)pBuf;
        pEnd = (char *)pBuf + size;
        pCur = (char *)pBuf;
    }
    else
    {
        if (size > 0)
            m_multipartBuf.append(pBuf, size);

        pBegin = m_multipartBuf.begin();
        pEnd   = m_multipartBuf.end();
        pCur   = m_multipartBuf.begin() + m_iCurOff;
    }

    while (pCur < pEnd)
    {
        if (pOldCur != pCur)
        {
            count = 0;
            pOldCur = pCur;
        }
        else
        {
            ++count;
            if (count > 20)
            {
                if (pCur + 100 < pEnd)
                    *(pCur + 100) = 0;
                LS_ERROR("Parsing Error! resume: %d, last: %d, state: %d, pBegin: %p:%s, pCur: %p:%s, pEnd: %p",
                         resume, last, m_multipartState, pBegin, pBegin, pCur, pCur, pEnd);
                //*((char *)(0x0)) = 0;
            }
        }

        switch (m_multipartState)
        {
        case MPS_END:
            return 0;
        case MPS_INIT_BOUNDARY:
            if (pEnd - pBegin >= m_part_boundary.len() + 4)
            {
                ret = checkBoundary(pBegin, pCur);
                if (ret == -1)
                    return ret;
            }
            else
            {
                if (last)
                {
                    //unexpected end of initial boundary string
                    return -1;
                }
                else
                    return popProcessedData(pBegin, pEnd);
            }
            break;

        case MPS_PART_HEADER:
            pLineEnd = (char *)memchr(pCur, '\n', pEnd - pCur);
            if (!pLineEnd)
            {
                if (!last)
                    return popProcessedData(pBegin, pEnd);
                else
                {
                    //unexpected end of data, part header expected
                    return -1;
                }
            }
            p = pLineEnd - 1;
            if (*p == '\r')
                --p;
            if (*p == '\n')    //found end of part header
            {
                multipartParseHeader(pBegin, p);
                if (m_sLastFileKey.len() == 0)
                    appendBodyBuf(pBegin, pLineEnd + 1 - pBegin);
                pBegin = pCur = pLineEnd + 1;
                m_multipartState = MPS_PART_DATA_BOUNDARY;
            }
            else
                pCur = pLineEnd + 1;
            continue;
        case MPS_PART_DATA_BOUNDARY:
            if (*pBegin == '-')
            {
                if (pEnd - pBegin >= m_part_boundary.len() + 4)
                {
                    ret = checkBoundary(pBegin, pCur);
                    if (ret == -1)
                        return ret;
                    if (ret == 1)
                        continue;
                }
                else
                    return popProcessedData(pBegin, pEnd);
            }
            m_multipartState = MPS_PART_DATA;
        //fall through
        case MPS_PART_DATA:
            while (pCur < pEnd)
            {
                pCur = pLineEnd = (char *)memchr(pCur, '\n', pEnd - pCur);
                if (!pCur)
                {
                    pCur = pEnd;
                    break;
                }
                else
                    ++pCur;

                if (pEnd - pCur - 2 < m_part_boundary.len()
                    || memcmp(pCur + 2, m_part_boundary.c_str(),
                              m_part_boundary.len()) == 0)
                    break;
            }

            if (!m_ignore_part)
                m_decodeBuf.append(pBegin, pCur - pBegin);
            else if (m_pLastFileBuf && pCur > pBegin)
            {
                if (pCur - pBegin >= 2)
                {
                    m_trial_crlf = 0;
                }
                
                if (pCur[-1] == '\n') 
                {
                    if (pCur - pBegin >= 2 && pCur[-2] == '\r')
                        m_trial_crlf = 1;
                    else if (m_trial_crlf > 1)
                        m_trial_crlf = 0;
                    m_trial_crlf += 2;
                }
                else if (pCur[-1] == '\r')
                    m_trial_crlf = 1;
                                    
                writeToFile(pBegin, pCur - pBegin);
            }

            if (pLineEnd)
                m_multipartState = MPS_PART_DATA_BOUNDARY;

            if (m_sLastFileKey.len() == 0)
                appendBodyBuf(pBegin, pCur - pBegin);
            pBegin = pCur;
            continue;
        case MPS_ERROR:
            return -1;
        }

    }
    popProcessedData(pBegin, pEnd);
    return 0;
}



//-1 error. otherwise return handled srcBuf
int ReqParser::parsePostBody(const char *srcBuf, size_t srcSize,
                             int bodyType, int resume, int last)
{
    int ret;
    if (bodyType == REQ_BODY_FORM)
    {
        parseArgs(srcBuf, srcSize, resume, last);
        ret = appendBodyBuf(srcBuf, srcSize);
    }
    else
        ret = parseMultipart(srcBuf, srcSize, resume, last);
    return ret;
}


// int ReqParser::parsePostBody( HttpReq * pReq )
// {
//     if ( pReq->getContentLength() <= 0 )
//         return 0;
//     VMemBuf * pBodyBuf = pReq->getBodyBuf();
//     if ( !pBodyBuf )
//         return 0;
//     m_state_kv = 0;
//
//     char * pBuf;
//     size_t size;
//     int resume = 0;
//     short bodyType = pReq->getBodyType();
//     if (bodyType == REQ_BODY_MULTIPART)
//     {
//         if ( initMutlipart( pReq->getHeader( HttpHeader::H_CONTENT_TYPE ),
//                         pReq->getHeaderLen( HttpHeader::H_CONTENT_TYPE ) ) == -1)
//         {
//             return -1;
//         }
//     }
//     pBodyBuf->rewindReadBuf();
//     while(( pBuf = pBodyBuf->getReadBuffer( size ) )&&(size>0))
//     {
//         parsePostBody( pBuf, size, pReq->getBodyType(), resume, 0 );
//         pBodyBuf->readUsed( size );
//         resume = 1;
//     }
//     parsePostBody( pBuf, 0, pReq->getBodyType(), 1, 1 );
//     //pBodyBuf->rewindReadBuf();
//     m_postArgs = m_args - m_postBegin ;
//
//     return 0;
// }

void ReqParser::logParsingError(HttpReq *pReq)
{
    LS_INFO(pReq->getLogSession(), "Error while parsing request: %s!",
            getErrorStr());
}

int ReqParser::appendBodyBuf(const char *s, size_t len)
{
    if (!isParseUploadByFilePath())
        return len;

    if (len <= 0 || !m_pReq)
        return len;

    size_t size;
    char *p = NULL;
    const char *end = s + len;

    while (s < end)
    {
        p = m_pReq->getBodyBuf()->getWriteBuffer(size);
        if (!p)
            return -1;

        //len is a local varibale now
        len = ((size_t)(end - s) < size ? (end - s) : size);
        memcpy(p, s, len);
        m_pReq->getBodyBuf()->writeUsed(len);
        s += len;
        m_iContentLength += len;
    }

    return 0;
}

int ReqParser::appendFileKeyValue(const char *key, size_t keylen,
                                  const char *val, size_t vallen,
                                  bool bFirstPart)
{
    if (!bFirstPart)
    {
        appendBodyBuf("--", 2);
        appendBodyBuf(m_part_boundary.c_str(), m_part_boundary.len());
        appendBodyBuf("\r\n", 2);
    }
    appendBodyBuf("Content-Disposition: form-data; name=\"",
                  sizeof("Content-Disposition: form-data; name=\"") - 1);
    appendBodyBuf(m_sLastFileKey.c_str(), m_sLastFileKey.len());
    appendBodyBuf(key, keylen);
    appendBodyBuf("\"\r\n\r\n", 5);
    appendBodyBuf(val, vallen);
    appendBodyBuf("\r\n", 2);
    return 0;
}

void ReqParser::writeToFile(const char *buf, int len)
{
    if (len <= 0)
        return;

    m_pLastFileBuf->write(buf, len);

    int iUseCache, iUseBuf;
    if (len == 1)
    {
        iUseBuf = 0;
        if (m_md5CachedNum == 0)
            iUseCache = 0;
        else
            iUseCache = 1;
    }
    else
    {
        iUseBuf = len - 2;
        iUseCache = m_md5CachedNum;
    }

    if (iUseCache)
    {
        ls_md5_update(&m_md5Ctx, m_md5CachedBytes, iUseCache);
        m_md5CachedNum -= iUseCache;
        if (m_md5CachedNum == 1)
            m_md5CachedBytes[0] = m_md5CachedBytes[1];
    }

    memcpy(m_md5CachedBytes + m_md5CachedNum, buf + iUseBuf, len - iUseBuf);
    m_md5CachedNum += (len - iUseBuf);
    if (iUseBuf)
        ls_md5_update(&m_md5Ctx, buf, iUseBuf);
}

void ReqParser::closeLastMFile()
{
    if (m_pLastFileBuf)
    {
        m_pLastFileBuf->close();
        delete m_pLastFileBuf;
        m_pLastFileBuf = NULL;
    }
}


int ReqParser::init(HttpReq *pReq, int uploadPassByPath,
                    const char *uploadTmpDir, int uploadTmpFilePermission)
{
    reset();
    if (uploadPassByPath && uploadTmpDir)
    {
        m_pFileUploadConfig = new ReqParserParam;
        m_pFileUploadConfig->m_iFileMod = uploadTmpFilePermission;
        m_pFileUploadConfig->m_sUploadFilePathTemplate.setStr(uploadTmpDir);
    }
    m_pReq = pReq;

    //QS parsing, now it is time to do it
    if ((pReq->getQueryStringLen() > 0) &&
        (parseQueryString(pReq->getQueryString(),
                          pReq->getQueryStringLen()) == -1))
    {
        logParsingError(pReq);
        return -1;
    }

    return 0;
}


int ReqParser::beginParsePost()
{
    if (!m_pReq)
        return LS_FAIL;
    if (m_pReq->getBodyType() == REQ_BODY_MULTIPART
        && initMutlipart(m_pReq->getHeader(HttpHeader::H_CONTENT_TYPE),
                         m_pReq->getHeaderLen(HttpHeader::H_CONTENT_TYPE)) == -1)
        return LS_FAIL;
    m_iParseState = PARSE_START;
    
    if (m_pReq->getContentFinished() > 0)
        parseReceivedBody();
    return LS_OK;
}


int ReqParser::parseReceivedBody()
{
    VMemBuf * pBodyBuf = m_pReq->getBodyBuf();
    if ( !pBodyBuf )
        return 0;
    m_state_kv = 0;

    char * pBuf;
    size_t size;
    pBodyBuf->rewindReadBuf();
    while(( pBuf = pBodyBuf->getReadBuffer( size ) )&&(size>0))
    {
        parsePostBody( pBuf, size, m_pReq->getBodyType(), m_resume, 0 );
        pBodyBuf->readUsed( size );
        m_resume = 1;
    }
    if (!m_pReq->isChunked() && m_pReq->getBodyRemain() <= 0)
        return parseDone();
    return LS_OK;
}


int ReqParser::parseUpdate(char *buf, size_t size)
{
    int ret = parsePostBody(buf, size, m_pReq->getBodyType(), m_resume, 0);
    m_resume = 1;
    return ret;

    /*
        char * pBuf;
        size_t size;
        short bodyType = pReq->getBodyType();

        while(( pBuf = pBodyBuf->getReadBuffer( size ) )&&(size>0))
        {
            parsePostBody( pBuf, size, bodyType, m_resume, 0 );
            pBodyBuf->readUsed( size );
            m_resume = 1;
        }

        return 0;*/
}

int ReqParser::parseDone()
{
    //parseUpdate(pReq);
    int ret = parsePostBody("", 0, m_pReq->getBodyType(), 1, 1);
    if (ret == 0)
        m_postArgs = m_args - m_postBegin;
    if (m_pFileUploadConfig)
        m_pReq->setContentLength(m_iContentLength);

#if 0
    FILE *f = fopen("/tmp/decbuf", "wb");
    if (f)
    {
        fwrite(m_decodeBuf.begin(), m_decodeBuf.size(), 1, f);
        fclose(f);
    }


    f = fopen("/tmp/reqbodybuf", "wb");
    if (f)
    {
        VMemBuf *pVMBuf = m_pReq->getBodyBuf();
        pVMBuf->rewindReadBuf();
        char *pBuf;
        size_t size;
        while (((pBuf = pVMBuf->getReadBuffer(size)) != NULL)
               && (size > 0))
        {
            fwrite(pBuf, size, 1, f);
            pVMBuf->readUsed(size);
        }
        fclose(f);
    }

#endif
    m_iParseState = PARSE_DONE;
    return ret;
}

int ReqParser::getArgByIndex(int index, ls_strpair_t *pArg, char **filePath)
{
    if (index < 0 || index >= m_args)
        return -1;
    if (pArg)
    {
        char *p = m_decodeBuf.begin() + m_pArgs[index].keyOffset;
        pArg->key.ptr = p;
        pArg->key.len = m_pArgs[index].keyLen;
        pArg->val.ptr = m_decodeBuf.begin() + m_pArgs[index].valueOffset;
        pArg->val.len = m_pArgs[index].valueLen;
    }
    if (filePath)
        *filePath = m_pArgs[index].filePath;
    return 0;
}

const char *ReqParser::getReqVar(HttpSession *pSession, int varId,
                                 int &len,
                                 char *pBegin, int bufLen)
{
    len = RequestVars::getReqVar(pSession, varId, pBegin, bufLen);
    return pBegin;

}

/*
int ReqParser::testArgs( int location, HttpSession* pSession, SecRule * pRule, AutoBuf * pMatched,
                        int countOnly )
{
    int i, n;
    const char * p;
    int len;
    int ret, ret1;
    int offset;
    switch( location )
    {
    case SEC_LOC_ARGS_ALL:
        i = 0;
        n = m_args;
        break;
    case SEC_LOC_ARGS_GET:
        if ( m_qsArgs == 0 )
            return 0;
        i = m_qsBegin;
        n = m_qsBegin + m_qsArgs;
        break;
    case SEC_LOC_ARGS_POST:
        if ( m_postArgs == 0 )
            return 0;
        i = m_postBegin;
        n = m_postArgs;
        break;
    default:
        return 0;
    }
    int result = 0;
    int total = 0;
    for( ; i < n; ++i )
    {
        offset = m_pArgs[i].keyOffset;
        len = m_pArgs[i].keyLen;
        p = m_decodeBuf.begin() + offset;
        ret = pRule->getLocation()->shouldTest( p, len, SEC_LOC_ARGS );
        if (( ret & 4 )||(ret && countOnly)) //count_only
        {
            ++total;
        }
        if ( ret & 2 ) //value
        {
            offset = m_pArgs[i].valueOffset;
            len = m_pArgs[i].valueLen;
            p = m_decodeBuf.begin() + offset;
            ret1 = pRule->matchString( pSession, p, len, pMatched );
            if ( ret1 )
            {
                if ( pRule->isMatchVars() )
                     ++result;
                else
                    return 1;
            }
        }
        if ( ret & 1 ) //name
        {
            offset = m_pArgs[i].keyOffset;
            len = m_pArgs[i].keyLen;
            p = m_decodeBuf.begin() + offset;
            ret1 = pRule->matchString( pSession, p, len, pMatched );
            if ( ret1 )
            {
                if ( pRule->isMatchVars() )
                     ++result;
                else
                    return 1;
            }
        }
    }
    if (( total )&&( !countOnly ))
    {
        return pRule->matchCount( total, pSession, pMatched );
    }
    if ( countOnly )
        return total;
    else
        return result;
}
*/

void ReqParser::testQueryString()
{
    ReqParser parser;
    char achBufTest[] =
        "action=upload&action1=%26+%2Ba%25&action2==%21%40%23%24%25%5E%26*%28%29/";
    char achDecoded[] = "action=upload&action1=& +a%&action2==!@#$%^&*()/";
    parser.reset();
    parser.parseQueryString(achBufTest, sizeof(achBufTest) - 1);
    int res = memcmp(parser.m_decodeBuf.begin(), achDecoded,
                     sizeof(achDecoded) - 1);
    assert(res == 0);
    assert(parser.m_args == 3);

    assert(parser.m_pArgs[0].keyOffset == 0);
    assert(parser.m_pArgs[0].keyLen == 6);
    assert(parser.m_pArgs[0].valueOffset == 7);
    assert(parser.m_pArgs[0].valueLen == 6);

    assert(parser.m_pArgs[1].keyOffset == 14);
    assert(parser.m_pArgs[1].keyLen == 7);
    assert(parser.m_pArgs[1].valueOffset == 22);
    assert(parser.m_pArgs[1].valueLen == 5);

    assert(parser.m_pArgs[2].keyOffset == 28);
    assert(parser.m_pArgs[2].keyLen == 7);
    assert(parser.m_pArgs[2].valueOffset == 36);
    assert(parser.m_pArgs[2].valueLen == 12);

    parser.reset();

    parser.parseArgs("", 0, 0, 0);
    char *p = achBufTest;
    while (*p)
    {
        parser.parseArgs(p, 1, 1, 0);
        ++p;
    }
    parser.parseArgs("", 0, 1, 1);
    res = memcmp(parser.m_decodeBuf.begin(), achDecoded,
                 sizeof(achDecoded) - 1);
    assert(res == 0);

    assert(parser.m_args == 3);

    assert(parser.m_pArgs[0].keyOffset == 0);
    assert(parser.m_pArgs[0].keyLen == 6);
    assert(parser.m_pArgs[0].valueOffset == 7);
    assert(parser.m_pArgs[0].valueLen == 6);

    assert(parser.m_pArgs[1].keyOffset == 14);
    assert(parser.m_pArgs[1].keyLen == 7);
    assert(parser.m_pArgs[1].valueOffset == 22);
    assert(parser.m_pArgs[1].valueLen == 5);

    assert(parser.m_pArgs[2].keyOffset == 28);
    assert(parser.m_pArgs[2].keyLen == 7);
    assert(parser.m_pArgs[2].valueOffset == 36);
    assert(parser.m_pArgs[2].valueLen == 12);
}

void ReqParser::testMultipart()
{
    char achBufTest[] =
        "-----------------------------17146369151957747793424238335\r\n"
        "Content-Disposition: form-data; name=\"action\"\n"
        "\n"
        "upload\n"
        "-----------------------------17146369151957747793424238335\n"
        "Content-Disposition: form-data; name=\"./action1\"\n"
        "\n"
        "& +a%\n"
        "-----------------------------17146369151957747793424238335\r\n"
        "Content-Disposition: form-data; name=\"action2\"\r\n"
        "\r\n"
        "--@#$%^&*()\r\n"
        "-----------------------------17146369151957747793424238335\r\n"
        "Content-Disposition: form-data; name=\"action3\"\r\n"
        "\r\n"
        "line1\nline2\r\n/./bin/\n"
        "-----------------------------17146369151957747793424238335\r\n"
        "Content-Disposition: form-data; name=\"userfile\"; filename=\"abcd\"\r\n"
        "Content-Type: application/octet-stream\r\n"
        "\r\n"
        "\r\n"
        "-----------------------------1714636915195774779342423833\r"
        "\r\n"
        "\r\n"
        "\r\n"
        "-----------------------------17146369151957747793424238335\r\n"
        "Content-Disposition: form-data; name=\"./userfile2\"; filename=\"/./file2\"\r\n"
        "Content-Type: application/octet-stream\r\n"
        "\r\n"
        "\r\n"
        "-----------------------------17146369151957747793424238335--\r\n";
    const char *pContentType =
        "multipart/form-data; boundary=---------------------------17146369151957747793424238335";
    char achDecoded[] = "action=upload&./action1=& +a%&action2=--@#$%^&*()&"
                        "action3=line1\nline2\r\n/bin/&userfile=abcd&./userfile2=/file2";
    int res;
    ReqParser parser;

    parser.reset();
    parser.initMutlipart(pContentType, 86);

    parser.parseMultipart(achBufTest, sizeof(achBufTest) - 1, 0, 1);
    res = memcmp(parser.m_decodeBuf.begin(), achDecoded,
                 sizeof(achDecoded) - 1);
    assert(res == 0);
    assert(parser.m_args == 6);

    assert(parser.m_pArgs[0].keyOffset == 0);
    assert(parser.m_pArgs[0].keyLen == 6);
    assert(parser.m_pArgs[0].valueOffset == 7);
    assert(parser.m_pArgs[0].valueLen == 6);

    assert(parser.m_pArgs[1].keyOffset == 14);
    assert(parser.m_pArgs[1].keyLen == 9);
    assert(parser.m_pArgs[1].valueOffset == 24);
    assert(parser.m_pArgs[1].valueLen == 5);

    assert(parser.m_pArgs[2].keyOffset == 30);
    assert(parser.m_pArgs[2].keyLen == 7);
    assert(parser.m_pArgs[2].valueOffset == 38);
    assert(parser.m_pArgs[2].valueLen == 11);

    assert(parser.m_pArgs[3].keyOffset == 50);
    assert(parser.m_pArgs[3].keyLen == 7);
    assert(parser.m_pArgs[3].valueOffset == 58);
    assert(parser.m_pArgs[3].valueLen == 18);

    assert(parser.m_pArgs[4].keyOffset == 77);
    assert(parser.m_pArgs[4].keyLen == 8);
    assert(parser.m_pArgs[4].valueOffset == 86);
    assert(parser.m_pArgs[4].valueLen == 4);

    assert(parser.m_pArgs[5].keyOffset == 91);
    assert(parser.m_pArgs[5].keyLen == 11);
    assert(parser.m_pArgs[5].valueOffset == 103);
    assert(parser.m_pArgs[5].valueLen == 6);

    parser.reset();
    parser.initMutlipart(pContentType, 86);

    parser.parseMultipart("", 0, 0, 0);
    char *p = achBufTest;
    char *pEnd = &achBufTest[0] + sizeof(achBufTest) - 1;
    while (*p)
    {
        res = pEnd - p;
        if (res > 4)
            res = 4;
        parser.parseMultipart(p, res, 1, 0);
        p += res;
    }
    parser.parseMultipart("", 0, 1, 1);
    res = memcmp(parser.m_decodeBuf.begin(), achDecoded,
                 sizeof(achDecoded) - 1);
    assert(res == 0);
    assert(parser.m_args == 6);

    assert(parser.m_pArgs[0].keyOffset == 0);
    assert(parser.m_pArgs[0].keyLen == 6);
    assert(parser.m_pArgs[0].valueOffset == 7);
    assert(parser.m_pArgs[0].valueLen == 6);

    assert(parser.m_pArgs[1].keyOffset == 14);
    assert(parser.m_pArgs[1].keyLen == 9);
    assert(parser.m_pArgs[1].valueOffset == 24);
    assert(parser.m_pArgs[1].valueLen == 5);

    assert(parser.m_pArgs[2].keyOffset == 30);
    assert(parser.m_pArgs[2].keyLen == 7);
    assert(parser.m_pArgs[2].valueOffset == 38);
    assert(parser.m_pArgs[2].valueLen == 11);

    assert(parser.m_pArgs[3].keyOffset == 50);
    assert(parser.m_pArgs[3].keyLen == 7);
    assert(parser.m_pArgs[3].valueOffset == 58);
    assert(parser.m_pArgs[3].valueLen == 18);

    assert(parser.m_pArgs[4].keyOffset == 77);
    assert(parser.m_pArgs[4].keyLen == 8);
    assert(parser.m_pArgs[4].valueOffset == 86);
    assert(parser.m_pArgs[4].valueLen == 4);

    assert(parser.m_pArgs[5].keyOffset == 91);
    assert(parser.m_pArgs[5].keyLen == 11);
    assert(parser.m_pArgs[5].valueOffset == 103);
    assert(parser.m_pArgs[5].valueLen == 6);

}

void ReqParser::testAll()
{
    testQueryString();
    testMultipart();
}


