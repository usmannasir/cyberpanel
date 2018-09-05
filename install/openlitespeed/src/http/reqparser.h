/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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

#ifndef REQPARSER_H
#define REQPARSER_H

#include <sys/types.h>
#include <util/autobuf.h>
#include <util/autostr.h>
#include <lsr/ls_md5.h>
#include <http/reqparserparam.h>

#define MAX_BOUNDARY_LEN  1024


class HttpSession;
class HttpReq;
class VMemBuf;

struct KeyValuePairFile
{
    int keyOffset;
    int keyLen;
    int valueOffset;
    int valueLen;
    char *filePath;
};

enum
{
    MPS_INIT_BOUNDARY,
    MPS_PART_HEADER,
    MPS_PART_DATA_BOUNDARY,
    MPS_PART_DATA,
    MPS_END,
    MPS_ERROR
};

enum
{
    MPS_NODATA,
    MPS_FORM_DATA,
    MPS_FILE_DATA
};

enum
{
    PARSE_UNKNOW = 0,
    PARSE_START,
    PARSE_DONE,
};

class ReqParser
{
public:
    ReqParser();
    ~ReqParser();

    void reset();
    const char *getErrorStr() const    {   return m_pErrStr;   }

    int init(HttpReq *pReq, int uploadPassByPath, const char *uploadTmpDir,
             int uploadTmpFilePermission);
    int parseReceivedBody();
    int parseUpdate(char *buf, size_t size);
    int parseDone();
    bool getEnableUploadFile()  {   return m_pFileUploadConfig != NULL; }
    int  isParsePost() const    {   return m_iParseState == PARSE_START;   }
    bool isParseDone() const    {   return m_iParseState == PARSE_DONE; }
    bool isParseUploadByFilePath() const 
    {   return m_pFileUploadConfig != NULL; }

    int  beginParsePost();

    const char *getReqVar(HttpSession *pSession, int varId, int &len,
                          char *pBegin, int bufLen);
    
    int getArgCount() const         {   return m_args;      }
    int getQsArgCount() const       {   return m_qsArgs;    }
    int getPostArgCount() const     {   return m_postArgs;  }
    int getArgByIndex(int index, ls_strpair_t *pArg, char **filePath);
    int getQsArgByIndex(int index, ls_strpair_t *pArg)
    {
        if (index < 0 || index >= m_qsArgs)
            return -1;
        return getArgByIndex(index + m_qsBegin, pArg, NULL);
    }
    int getPostArgByIndex(int index, ls_strpair_t *pArg, char **filePath)
    {   
        if (index < 0 || index >= m_postArgs)
            return -1;
        return getArgByIndex(index + m_postArgs, pArg, filePath);
    }
    
    bool isFile(int index) 
    { 
        if (index < 0 || index > m_args)
            return false;
        return (m_pArgs[index].filePath != NULL);  
    }


    static void testQueryString();
    static void testMultipart();
    static void testAll();

private:

    int allocArgIndex(int newMax);


    int parseArgs(const char *pStr, int len, int resume, int last);
    void resumeDecode(const char *&pStr, const char *pEnd);

    int parseQueryString(const char *pQS, int len);
    int parsePostBody(const char *srcBuf, size_t srcSize,
                      int bodyType, int resume, int last);
    //int parsePostBody( HttpReq * pReq );
    int popProcessedData(char *pBegin, char *pEnd);
    int checkBoundary(char *&pBegin, char *&pCur);
    int parseKeyValue(char *&pBegin, char *pLineEnd,
                      char *&pKey, int &keyLen, char *&pValue, int &valLen);

    int initMutlipart(const char *pContentType, int len);
    void logParsingError(HttpReq *pReq);

    int normalisePath(int begin, int len);

    int appendArg(int beginIndex, int endIndex, int isValue);
    int appendArgKeyIndex(int begin, int len);
    int appendArgKey(const char *pStr, int len);
    int multipartParseHeader(char *pBegin, char *pLineEnd);
    int parseMultipart(const char *srcBuf, size_t srcSize,
                       int resume, int last);

    int appendBodyBuf(const char *s, size_t len);
    int appendFileKeyValue(const char *key, size_t keylen, const char *val,
                           size_t vallen, bool bFirstPart = false);
    void closeLastMFile();
    void writeToFile(const char *buf, int len);

private:
    AutoBuf         m_decodeBuf;
    AutoBuf         m_multipartBuf;
    AutoStr2        m_part_boundary;
    int8_t          m_ignore_part;
    int8_t          m_multipartState;
    uint8_t         m_resume;
    int8_t          m_md5CachedNum;
    int             m_iCurOff;

    char            m_state_kv;
    char            m_last_char;
    char            m_trial_crlf;
    uint8_t         m_iParseState;

    int             m_beginIndex;
    int             m_args;
    int             m_maxArgs;
    KeyValuePairFile *m_pArgs;
    int             m_qsBegin;
    int             m_qsArgs;
    int             m_postBegin;
    int             m_postArgs;

    const char     *m_pErrStr;
    HttpReq        *m_pReq;

    /**Comment about the below varibles
     * Such as name="file1", filename="123.jpg"
     * the "file1" is the m_sLastFileKey
     * 123.jpg should be save as "$m_sLastFileKey_Name"'s value
     */
    AutoStr2        m_sLastFileKey;
    ls_md5_ctx_t    m_md5Ctx;
    char            m_md5CachedBytes[2];
    VMemBuf        *m_pLastFileBuf;
    off_t           m_iContentLength;
    ReqParserParam *m_pFileUploadConfig;
};

#endif
