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
#ifndef REQUESTVARS_H
#define REQUESTVARS_H


#include <util/tlinklist.h>


#define REF_STRING          100
#define REF_MAP             101
#define REF_RULE_SUBSTR     102
#define REF_COND_SUBSTR     103
#define REF_ENV             104
#define REF_HTTP_HEADER     105
#define REF_SSI_VAR         106
#define REF_FORMAT_STR      107
#define REF_EXPR            108
#define REF_RESP_HEADER     109


#define REF_REMOTE_ADDR     110
#define REF_REMOTE_PORT     111
#define REF_REMOTE_HOST     112
#define REF_REMOTE_USER     113
#define REF_REMOTE_IDENT    114
#define REF_REQ_METHOD      115
#define REF_QUERY_STRING    116
#define REF_AUTH_TYPE       117
#define REF_PATH_INFO       118
#define REF_SCRIPTFILENAME  119
#define REF_REQUST_FN       120
#define REF_REQ_URI         121
#define REF_DOC_ROOT        122
#define REF_SERVER_ADMIN    123
#define REF_SERVER_NAME     124
#define REF_SERVER_ADDR     125
#define REF_SERVER_PORT     126
#define REF_SERVER_PROTO    127
#define REF_SERVER_SOFT     128
#define REF_API_VERSION     129
#define REF_REQ_LINE        130
#define REF_IS_SUBREQ       131
#define REF_TIME            132
#define REF_TIME_YEAR       133
#define REF_TIME_MON        134
#define REF_TIME_DAY        135
#define REF_TIME_HOUR       136
#define REF_TIME_MIN        137
#define REF_TIME_SEC        138
#define REF_TIME_WDAY       139
#define REF_SCRIPT_NAME     140
#define REF_CUR_REWRITE_URI 141
#define REF_REQ_BASENAME    142
#define REF_SCRIPT_UID      143
#define REF_SCRIPT_GID      144
#define REF_SCRIPT_USERNAME 145
#define REF_SCRIPT_GRPNAME  146
#define REF_SCRIPT_MODE     147
#define REF_SCRIPT_BASENAME 148
#define REF_SCRIPT_URI      149
#define REF_ORG_REQ_URI     150
#define REF_ORG_QS          151
#define REF_HTTPS           152

#define REF_DUMMY           153
#define REF_PID             154
#define REF_STATUS_CODE     155
#define REF_STRFTIME        156
#define REF_REQ_TIME_SEC    157
#define REF_CUR_URI         158    //no query string part
#define REF_CONN_STATE      159
#define REF_BYTES_IN        160
#define REF_BYTES_OUT       161
#define REF_RESP_BYTES      162
#define REF_VH_CNAME        163
#define REF_COOKIE_VAL      164

#define REF_DATE_GMT        165
#define REF_DATE_LOCAL      166
#define REF_DOCUMENT_NAME   167
#define REF_DOCUMENT_URI    168
#define REF_LAST_MODIFIED   169
#define REF_QS_UNESCAPED    170
#define REF_REQ_TIME_MS     171

#define REF_EXT_END         172

#define REF_BEGIN           110
#define REF_END             153
#define REF_COUNT           (REF_END - REF_BEGIN)
#define REF_EXT_COUNT       (REF_EXT_END - REF_BEGIN)

#define REF_RESP_CONTENT_TYPE       172
#define REF_RESP_CONTENT_LENGTH     173
#define REF_RESP_BODY               174
#define REF_MATCHED_VAR             175

#define REF_RESP_HEADER_BEGIN       200


class AutoStr2;

class HttpSession;
class HttpReq;

class MapRefItem;
class RewriteMapList;
class RegexResult;

class SubstFormat;


class SubstItem : public LinkedObj
{
    short         m_type;
    short         m_subType;
    union
    {
        long          m_index;
        AutoStr2     *m_pStr;
        void         *m_pAny;

    }           m_value;


    void operator=(const SubstItem &rhs);
public:
    SubstItem();
    ~SubstItem();
    SubstItem(const SubstItem &rhs);
    void setType(int type)            {   m_type = type;              }
    int getType() const                 {   return m_type;              }

    void setSubType(int type)         {   m_subType = type;           }
    int getSubType() const              {   return m_subType;           }


    void setIndex(int index)          {   m_value.m_index = index;    }
    long getIndex() const               {   return m_value.m_index;     }

    AutoStr2 *setStr(const char *pStr, int len);
    void setStr(AutoStr2 *pStr)      {   m_value.m_pStr = pStr;      }
    AutoStr2 *getStr() const           {   return m_value.m_pStr;      }

    void setAny(void *p)             {   m_value.m_pAny = p;      }
    void *getAny() const               {   return m_value.m_pAny;   }

    SubstFormat *getFormatStr() const
    {   return (SubstFormat *)m_value.m_pAny;   }


    void parseString(const char *&pBegin, const char *pEnd,
                     const char *stopChars);
    int parseServerVar(const char *pCurLine, const char *&pFormatStr,
                       const char *pEnd, int isSSI = 0);

    int equal(const SubstItem &rhs) const
    {   return ((m_type == rhs.m_type) && (m_value.m_index == rhs.m_value.m_index));  }
};

class SubstFormat : public TLinkList< SubstItem >
{
    //int   m_type;

    void operator=(const SubstFormat &rhs);
public:
    SubstFormat();
    ~SubstFormat();
    SubstFormat(const SubstFormat &rhs);
    int parse(const char *pCurLine,
              const char *pFormatStr, const char *pEnd, int isSSI = 0,
              char varChar = '$');
    int equal(const SubstFormat &rhs) const;

    //void setType( int type ) {  m_type = type;  }
    //int getType() const      {  return m_type;  }

};



class RequestVars
{
public:
    RequestVars();

    ~RequestVars();
    static int parseBuiltIn(const char *pVar, int len, int ext = 0);
    static int parseHttpHeader(const char *pName, int len,
                               const char *&pHeaderName, int &headerLen);

    static int getReqVar(HttpSession *pSession, int type, char *&pValue,
                         int bufLen);
    static int getReqVar2(HttpSession *pSession, int type, char *&pValue,
                          int bufLen);

    static const char *getUnknownHeader(HttpReq *pReq, const char *pName,
                                        int nameLen, int &headerLen);
    static const char *getHeaderString(int iIndex);
    static const char *getCookieValue(HttpReq *pReq, const char *pCookieName,
                                      int nameLen, int &idLen);
    static int getCookieCount(HttpReq *pReq);
    static const char *getEnv(HttpSession *pSession, const char *pKey,
                              int keyLen, int &valLen);

    static int getSubstValue(const SubstItem *pItem, HttpSession *pSession,
                             char *&pValue, int bufLen);

    static int appendSubst(const SubstItem *pItem, HttpSession *pSession,
                           char *&pBegin, int len, int noDupSlash,
                           const RegexResult *pRegRes, const char *pTmFmt = NULL);

    static char *buildString(const SubstFormat *pFormat, HttpSession *pSession,
                             char *pBuf, int &len, int noDupSlash, const RegexResult *pRegRes,
                             const char *pTmFmt = NULL);

    static const char *getVarNameStr(int var_id, int &len);

    static int setEnv(HttpSession *pSession, const char *pName, int nameLen,
                      const char *pValue, int valLen);

};

#endif
