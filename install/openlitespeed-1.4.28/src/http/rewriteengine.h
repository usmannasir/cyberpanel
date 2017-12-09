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
#ifndef REWRITEENGINE_H
#define REWRITEENGINE_H



#include <lsdef.h>
#include <http/httpdefs.h>
#include <util/tsingleton.h>

#include <sys/stat.h>

#define MAX_REWRITE_MATCH   10
#define REWRITE_BUF_SIZE    MAX_BUF_SIZE

class AutoStr2;
class RewriteCond;
class RewriteRule;
class RewriteRuleList;
class RewriteMapList;
class RewriteSubstItem;
class RewriteSubstFormat;
class HttpSession;
class HttpContext;

class RewriteEngine : public TSingleton<RewriteEngine>
{
    friend class TSingleton<RewriteEngine>;

    const char     *m_pSourceURL;
    int             m_sourceURLLen;
    const char     *m_pQS;
    int             m_qsLen;
    const char     *m_pOrgSourceURL;
    int             m_orgSourceURLLen;

    int             m_rewritten;
    int             m_ruleMatches;
    int             m_condMatches;
    int             m_pDestURLLen;
    short           m_iScriptLen;
    short           m_iPathInfoLen;
    int             m_iFilePathLen;
    short           m_flag;
    short           m_action;
    int             m_statusCode;
    int             m_logLevel;
    char           *m_pDestURL;
    char           *m_pCondBuf;
    char           *m_pFreeBuf;
    const HttpContext *m_pContext;
    const AutoStr2 *m_pBase;
    const AutoStr2 *m_pStrip;
    const RewriteSubstFormat *m_pLastCondStr;
    char           *m_pLastTestStr;
    int             m_lastTestStrLen;
    int             m_noStat;
    struct stat     m_st;

    int             m_stripLen;
    int             m_ruleVec[ MAX_REWRITE_MATCH * 3 ];
    int             m_condVec[ MAX_REWRITE_MATCH * 3 ];

    char            m_rewriteBuf[3][REWRITE_BUF_SIZE];
    char            m_qsBuf[REWRITE_BUF_SIZE];

    RewriteEngine();

    int processQueryString(HttpSession *pSession, int flag);
    int getSubstValue(const RewriteSubstItem *pItem, HttpSession *pSession,
                      char *&pValue, int bufLen);

    int appendSubst(const RewriteSubstItem *pItem, HttpSession *pSession,
                    char *&pBegin, char *pBufEnd, int &esc_uri, int noDupSlash = 0);
    char *buildString(const RewriteSubstFormat *pFormat, HttpSession *pSession,
                      char *pBuf, int &len, int esc_uri = 0, int noDupSlash = 0);
    int processCond(const RewriteCond *pCond, HttpSession *pSession);
    int processRule(const RewriteRule *pRule, HttpSession *pSession);
    int processRewrite(const RewriteRule *pRule, HttpSession *pSession);
    int expandEnv(const RewriteRule *pRule, HttpSession *pSession);
    int setCookie(char *pBuf, int len, HttpSession *pSession);
    const RewriteRule *getNextRule(const RewriteRule *pRule,
                                   const HttpContext *&pContext, const HttpContext *&pRootContext);
public:
    ~RewriteEngine();

    static int loadRewriteFile(char *path, RewriteRuleList *pRuleList,
                               const RewriteMapList *pMaps);
    static int parseRules(char *&pRules, RewriteRuleList *pRuleList,
                          const RewriteMapList *pMapList);
    int processRuleSet(const RewriteRuleList *pRuleList, HttpSession *pSession,
                       const HttpContext *pContext, const HttpContext *pRootContext);
    const char *getResultURI()     {   return m_pSourceURL;    }
    int          getResultURILen()  {   return m_sourceURLLen;  }

    void clearUnparsedRuleBuf()     {   m_qsLen = 0;            }
    int appendUnparsedRule(AutoStr2 &sDirective, char *pBegin,
                           char *pEnd);
    int parseUnparsedRules(RewriteRuleList *pRuleList,
                           const RewriteMapList *pMapList);

    LS_NO_COPY_ASSIGN(RewriteEngine);
};

#endif
