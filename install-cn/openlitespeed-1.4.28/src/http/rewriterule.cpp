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
#include "rewriterule.h"

#include <http/httplog.h>
#include <http/httpstatuscode.h>
#include <http/rewritemap.h>
#include <log4cxx/logger.h>
#include <util/stringtool.h>

#include <assert.h>
#include <ctype.h>
#include <pcreposix.h>
#include <string.h>

static const char *s_pCurLine          = NULL;
static const char *s_pLogId            = NULL;
static LOG4CXX_NS::Logger   *s_pLogger  = NULL;
// static void parse_error( const char * pError )
// {
//     LS_ERROR( s_pLogger, "[%s] rewrite: %s while parsing: %s",
//                     s_pLogId, pError, s_pCurLine ));
// }


void RewriteRule::setLogger(LOG4CXX_NS::Logger *pLogger, const char *pId)
{
    s_pLogger = pLogger;
    s_pLogId = pId;
}


void RewriteRule::error(const char *pError)
{
    LS_ERROR(s_pLogger, "[%s] rewrite: %s.",
             s_pLogId, pError);
}


RewriteSubstItem::RewriteSubstItem()
{
}


RewriteSubstItem::~RewriteSubstItem()
{
    if (getType() == REF_MAP)
        delete getMapRef();
}


int RewriteSubstItem::needUrlDecode() const
{
    switch (getType())
    {
    case REF_STRING:
    case REF_MAP:
    case REF_REQ_URI:
        return 1;
    }
    return 0;
}


RewriteSubstItem::RewriteSubstItem(const RewriteSubstItem &rhs)
    : SubstItem()
{
    if (getType() == REF_MAP)
        setMapRef(new MapRefItem(*rhs.getMapRef()));
}


RewriteSubstFormat::RewriteSubstFormat()
{
}


RewriteSubstFormat::~RewriteSubstFormat()
{
    release_objects();
}


RewriteSubstFormat::RewriteSubstFormat(const RewriteSubstFormat &rhs)
    : TLinkList<RewriteSubstItem>(rhs)
    , LinkedObj()
{

}


int RewriteSubstFormat::equal(const RewriteSubstFormat &rhs) const
{
    const RewriteSubstItem *pItem = begin();
    const RewriteSubstItem *pRhsItem = rhs.begin();
    while (pItem)
    {
        if (!pRhsItem || !pItem->equal(*pRhsItem))
            return 0;
        pItem = (const RewriteSubstItem *)pItem->next();
        pRhsItem = (const RewriteSubstItem *)pRhsItem->next();
    }
    if (pRhsItem)
        return 0;
    return 1;
}


int RewriteSubstFormat::parse(const char *pFormatStr, const char *pEnd,
                              const RewriteMapList *pMaps)
{
    while ((pFormatStr < pEnd) && (isspace(*pFormatStr)))
        ++pFormatStr;
    int err = 0;
    LinkedObj *pLast = head();
    RewriteSubstItem *pItem;
    while (pFormatStr < pEnd)
    {
        pItem = new RewriteSubstItem();
        if (!pItem)
        {
            ERR_NO_MEM("new SubstItem()");
            return LS_FAIL;
        }

        switch (*pFormatStr)
        {
        case '$':
            if (pFormatStr + 1 == pEnd)
            {
                HttpLog::parse_error(s_pCurLine,  "Line ended with '$'");
                err = 1;
                break;
            }
            if (*(pFormatStr + 1) == '{')
            {
                if (!pMaps)
                {
                    HttpLog::parse_error(s_pCurLine,  "No rewrite map defined");
                    err = 1;
                    break;
                }
                pItem->setType(REF_MAP);
                MapRefItem *pMapRef = new MapRefItem();
                if (!pMapRef)
                {
                    ERR_NO_MEM("new MapRefItem()");
                    err = 1;
                    break;
                }
                if (pMapRef->parse(pFormatStr, pEnd, pMaps))
                {
                    delete pMapRef;
                    err = 1;
                    break;
                }
                pItem->setMapRef(pMapRef);
            }
            else if (isdigit(*(pFormatStr + 1)))
            {
                pItem->setType(REF_RULE_SUBSTR);
                pItem->setIndex(*(pFormatStr + 1) - '0');
                pFormatStr += 2;
            }
            else
            {
                HttpLog::parse_error(s_pCurLine,
                                     "'$' should be followed by a digit for a RewriteRule backreference.");
                pItem->setType(REF_STRING);
                pItem->setStr(pFormatStr, 1);
                ++pFormatStr;
            }
            break;
        case '%':
            if (pFormatStr + 1 == pEnd)
            {
                HttpLog::parse_error(s_pCurLine,  "Line ended with '%'");
                err = 1;
                break;
            }
            if (*(pFormatStr + 1) == '{')
            {
                ++pFormatStr;
                if (pItem->parseServerVar(s_pCurLine, pFormatStr, pEnd))
                {
                    err = 1;
                    break;
                }
            }
            else if (isdigit(*(pFormatStr + 1)))
            {
                pItem->setType(REF_COND_SUBSTR);
                pItem->setIndex(*(pFormatStr + 1) - '0');
                pFormatStr += 2;
            }
            else
            {
                HttpLog::parse_error(s_pCurLine,
                                     "'%' should be followed by a digit for a RewriteCond backreference.");
                pItem->setType(REF_STRING);
                pItem->setStr(pFormatStr, 1);
                ++pFormatStr;
            }
            break;
        case '\\':
        default:
            pItem->parseString(pFormatStr, pEnd, "$%");
            break;
        }
        if (err)
        {
            delete pItem;
            return LS_FAIL;
        }
        else
        {
            pLast->addNext(pItem);
            pLast = pItem;
        }
    }
    return 0;
}


MapRefItem::MapRefItem()
    : m_pMap(NULL)
    , m_pKeyFormat(NULL)
    , m_pDefaultFormat(NULL)
{
}


MapRefItem::~MapRefItem()
{
    if (m_pKeyFormat)
        delete m_pKeyFormat;
    if (m_pDefaultFormat)
        delete m_pDefaultFormat;
}


MapRefItem::MapRefItem(const MapRefItem &rhs)
    : m_pMap(rhs.m_pMap)
    , m_pKeyFormat(NULL)
    , m_pDefaultFormat(NULL)
{
    if (rhs.m_pKeyFormat)
        m_pKeyFormat = new RewriteSubstFormat(*rhs.m_pKeyFormat);
    if (rhs.m_pDefaultFormat)
        m_pDefaultFormat = new RewriteSubstFormat(*rhs.m_pDefaultFormat);
}


int MapRefItem::parse(const char *&pFormatStr, const char *pEnd,
                      const RewriteMapList *pMaps)
{
    const char *pMapName = pFormatStr + 2;
    const char *pClose = StringTool::findCloseBracket(pMapName, pEnd, '{',
                         '}');
    if (pClose == pEnd)
    {
        HttpLog::parse_error(s_pCurLine,  "missing '}'");
        return LS_FAIL;
    }
    const char *pColon = StringTool::findCharInBracket(pMapName, pClose, ':',
                         '{', '}');
    if (pColon == NULL)
    {
        HttpLog::parse_error(s_pCurLine,  "missing ':'");
        return LS_FAIL;
    }
    else
    {
        char achName[1024];
        memmove(achName, pMapName, pColon - pMapName);
        achName[pColon - pMapName] = 0;
        RewriteMapList::iterator iter = pMaps->find(achName);
        if (iter == pMaps->end())
        {
            HttpLog::parse_error(s_pCurLine,  "rewrite map is not defined");
            return LS_FAIL;
        }
        m_pMap = iter.second();
    }
    pFormatStr = pClose + 1;
    const char *pDefault = StringTool::findCharInBracket(pMapName, pClose, '|',
                           '{', '}');
    if (pDefault != NULL)
    {
        assert(!m_pDefaultFormat);
        m_pDefaultFormat = new RewriteSubstFormat();
        if (!m_pDefaultFormat)
        {
            ERR_NO_MEM("new SubstFormat()");
            return LS_FAIL;
        }
        if (m_pDefaultFormat->parse(pDefault + 1, pClose, pMaps))
            return LS_FAIL;
    }
    else
        pDefault = pClose;
    if (++pColon == pDefault)
    {
        HttpLog::parse_error(s_pCurLine,  "missing map key");
        return LS_FAIL;
    }
    assert(!m_pKeyFormat);
    m_pKeyFormat = new RewriteSubstFormat();
    if (!m_pKeyFormat)
    {
        ERR_NO_MEM("new SubstFormat()");
        return LS_FAIL;
    }
    return m_pKeyFormat->parse(pColon, pDefault, pMaps);
}


RewriteCond::RewriteCond()
    : m_opcode(COND_OP_REGEX)
    , dummy(0)
    , m_flag(0)
{}


RewriteCond::RewriteCond(const RewriteCond &rhs)
    : LinkedObj()
    , m_pattern(rhs.m_pattern)
    , m_testStringFormat(rhs.m_testStringFormat)
    , m_opcode(rhs.m_opcode)
    , dummy(rhs.dummy)
    , m_flag(rhs.m_flag)
{
    if (m_opcode == COND_OP_REGEX)
        compilePattern();
}


RewriteCond::~RewriteCond()
{
}


int RewriteCond::parseTestString(const char *&pRuleStr, const char *pEnd,
                                 const RewriteMapList *pMaps)
{
    const char *argBegin = NULL;
    const char *argEnd = NULL;
    const char *pError = NULL;
    int ret = StringTool::parseNextArg(pRuleStr, pEnd, argBegin, argEnd,
                                       pError);
    if (ret)
    {
        if (pError)
            HttpLog::parse_error(s_pCurLine,  pError);
        return LS_FAIL;
    }
    m_flag = 0;
//    if ( *argBegin == '-' )
//    {
//        m_flag |= RULE_FLAG_NOREWRITE;
//        return 0;
//    }
    return m_testStringFormat.parse(argBegin, argEnd, pMaps);
}


int RewriteCond::parseCondPattern(const char *&pRuleStr, const char *pEnd)
{
    const char *argBegin = NULL;
    const char *argEnd = NULL;
    const char *pError = NULL;
    int stripQuote = 0;
    int ret = StringTool::parseNextArg(pRuleStr, pEnd, argBegin, argEnd,
                                       pError);
    if (ret)
    {
        if (pError)
            HttpLog::parse_error(s_pCurLine,  pError);
        return LS_FAIL;
    }
    if (*argBegin == '!')
    {
        ++argBegin;
        m_flag |= COND_FLAG_NOMATCH;
        while ((argBegin < argEnd) && (isspace(*argBegin)))
            argBegin++;
        stripQuote = 1;
    }
    m_opcode = COND_OP_REGEX;
    switch (*argBegin)
    {
    case '>':
        m_opcode = COND_OP_GREATER;
        ++argBegin;
        stripQuote = 1;
        break;
    case '<':
        m_opcode = COND_OP_LESS;
        ++argBegin;
        stripQuote = 1;
        break;
    case '=':
        m_opcode = COND_OP_EQ;
        ++argBegin;
        stripQuote = 1;
        break;
    case '-':
        if (argBegin + 2 != argEnd)
            break;
        m_pattern.setStr(argBegin, 2);
        switch (*(argBegin + 1))
        {
        case 'd':
            m_opcode = COND_OP_DIR;
            return 0;
        case 'f':
            m_opcode = COND_OP_FILE;
            return 0;
        case 's':
            m_opcode = COND_OP_SIZE;
            return 0;
        case 'l':
            m_opcode = COND_OP_SYM;
            return 0;
        case 'F':
            m_opcode = COND_OP_FILE_ACC;
            return 0;
        case 'U':
            m_opcode = COND_OP_URL_ACC;
            return 0;
        default:
            break;
        }
        break;
    }
    if (argBegin >= argEnd)
        return LS_FAIL;
    while ((argBegin < argEnd) && isspace(*argBegin))
    {
        ++argBegin;
        stripQuote = 1;
    }
    if (stripQuote && (argEnd - argBegin >= 2))
    {
        char ch = *argBegin;
        if ((ch == '"') || (ch == '\''))
        {
            if (argEnd[-1] == ch)
            {
                argBegin++;
                argEnd--;
            }
        }
    }
    m_pattern.setStr(argBegin, argEnd - argBegin);
    return 0;
}


int RewriteCond::praseFlag(const char *&pRuleStr, const char *pEnd)
{
    while ((pRuleStr < pEnd) && (isspace(*pRuleStr)))
        ++pRuleStr;
    if ((pRuleStr == pEnd) || (*pRuleStr == '#'))
        return 0;
    if (*pRuleStr != '[')
    {
        HttpLog::parse_error(s_pCurLine,  "'[' is expected");
        return LS_FAIL;
    }
    ++pRuleStr;

    while (pRuleStr < pEnd)
    {
        while ((pRuleStr < pEnd) && isspace(*pRuleStr))
            ++pRuleStr;
        if (strncasecmp(pRuleStr, "nocase", 6) == 0)
        {
            m_flag |= COND_FLAG_NOCASE;
            pRuleStr += 6;
        }
        else if (strncasecmp(pRuleStr, "nc", 2) == 0)
        {
            m_flag |= COND_FLAG_NOCASE;
            pRuleStr += 2;
        }
        else if (strncasecmp(pRuleStr, "ornext", 6) == 0)
        {
            m_flag |= COND_FLAG_OR;
            pRuleStr += 6;
        }
        else if (strncasecmp(pRuleStr, "or", 2) == 0)
        {
            m_flag |= COND_FLAG_OR;
            pRuleStr += 2;
        }
        while ((pRuleStr < pEnd) && isspace(*pRuleStr))
            ++pRuleStr;
        if (*pRuleStr == ']')
        {
            ++pRuleStr;
            return 0;
        }
        else if (*pRuleStr == ',')
            ++pRuleStr;
        else
        {
            HttpLog::parse_error(s_pCurLine,  "unknown rewrite condition flag");
            return LS_FAIL;
        }
    }
    HttpLog::parse_error(s_pCurLine,  "missing ']'");
    return LS_FAIL;
}


int RewriteCond::compilePattern()
{
    int flag = REG_EXTENDED;
    if (m_flag & COND_FLAG_NOCASE)
        flag = REG_EXTENDED | REG_ICASE;
    return m_regex.compile(m_pattern.c_str(), flag);
}


int RewriteCond::parse(const char *pRuleStr, const char *pEnd,
                       const RewriteMapList *pMaps)
{
    if (parseTestString(pRuleStr, pEnd, pMaps))
        return LS_FAIL;
    if (parseCondPattern(pRuleStr, pEnd))
        return LS_FAIL;
    if (praseFlag(pRuleStr, pEnd))
        return LS_FAIL;
    while ((pRuleStr < pEnd) && (isspace(*pRuleStr)))
        ++pRuleStr;
    if ((pRuleStr != pEnd) && (*pRuleStr != '#'))
        return 0;
    if (m_opcode == COND_OP_REGEX)
        return compilePattern();
    return 0;
}


RewriteRule::RewriteRule()
    : m_action(0)
    , m_flag(0)
    , m_statusCode(0)
    , m_skipRules(0)
{
}


RewriteRule::RewriteRule(const RewriteRule &rhs)
    : LinkedObj()
    , m_conds(rhs.m_conds)
    , m_targetFormat(rhs.m_targetFormat)
    , m_sMimeType(rhs.m_sMimeType)
    , m_action(rhs.m_action)
    , m_flag(rhs.m_flag)
    , m_statusCode(rhs.m_statusCode)
    , m_skipRules(rhs.m_skipRules)
    , m_env(rhs.m_env)
    , m_pattern(rhs.m_pattern)
{
    compilePattern();
}


RewriteRule::~RewriteRule()
{
    m_conds.release_objects();
    m_env.release_objects();
}


int RewriteRule::parseRuleSubst(const char *&pRuleStr, const char *pEnd,
                                const RewriteMapList *pMaps)
{
    const char *argBegin = NULL;
    const char *argEnd = NULL;
    const char *pError = NULL;
    int ret = StringTool::parseNextArg(pRuleStr, pEnd, argBegin, argEnd,
                                       pError);
    if ((ret) || (argEnd == argBegin))
    {
        if (pError)
            HttpLog::parse_error(s_pCurLine,  pError);
        HttpLog::parse_error(s_pCurLine,
                             "Rewrite rule missing substitution string.");
        return LS_FAIL;
    }

    if (strncmp(argBegin, "-", argEnd - argBegin) == 0)
    {
        m_flag |= RULE_FLAG_NOREWRITE;
        return 0;
    }

    ret = m_targetFormat.parse(argBegin, argEnd, pMaps);
    if (!ret)
    {
        const SubstItem *pItem = m_targetFormat.begin();
        while (pItem)
        {
            if (pItem->getType() == REF_STRING)
            {
                if (strchr(pItem->getStr()->c_str(), '?'))
                {
                    m_flag |= RULE_FLAG_WITHQS;
                    break;
                }
            }
            pItem = (const SubstItem *)pItem->next();
        }
    }
    return ret;
}


int RewriteRule::parseCookieAction(const char *pCookie, const char *pEnd)
{
    if (memchr(pCookie, ':', pEnd - pCookie) == NULL)
    {
        HttpLog::parse_error(s_pCurLine,  "missing ':' in cookie string");
        return LS_FAIL;
    }
    RewriteSubstFormat *pFormat = new RewriteSubstFormat();
    if (!pFormat)
    {
        ERR_NO_MEM("new SubstFormat()");
        return LS_FAIL;
    }
    if (pFormat->parse(pCookie, pEnd, NULL))
    {
        HttpLog::parse_error(s_pCurLine,  "failed to parse cookie string");
        delete pFormat;
        return LS_FAIL;
    }
    pFormat->setType(RewriteSubstFormat::COOKIE);
    m_env.append(pFormat);

    return 0;
}


int RewriteRule::parseOneFlag(const char *&pRuleStr, const char *pEnd)
{
    switch (*pRuleStr)
    {
    case 'B':
    case 'b':
        m_flag |= RULE_FLAG_BR_ESCAPE;
        ++pRuleStr;
        break;
    case 'C':
    case 'c':
        if ((*(pRuleStr + 1) | 0x20) == 'o')
        {
            pRuleStr += 2;
            if (strncasecmp(pRuleStr, "okie", 4) == 0)
                pRuleStr += 4;
            if (*pRuleStr == '=')
            {
                ++pRuleStr;
                size_t n = strcspn(pRuleStr, ",] \t\r\n");
                if (n > 0)
                {
                    const char *pCookie = pRuleStr;
                    pRuleStr += n;
                    return parseCookieAction(pCookie, pRuleStr);
                }
                else
                {
                    HttpLog::parse_error(s_pCurLine,  "invalid cookie action string");
                    return LS_FAIL;
                }
            }
            break;
        }
        m_flag |= RULE_FLAG_CHAIN;
        if (strncasecmp(pRuleStr, "chain", 5) == 0)
            pRuleStr += 5;
        else
            ++pRuleStr;
        break;
    case 'D':
    case 'd':
        if (strncasecmp(pRuleStr, "DPI", 3) == 0)
        {
            pRuleStr += 3;
            m_flag |= RULE_FLAG_DPI;
        }
        else if (strncasecmp(pRuleStr, "discardpathinfo", 15) == 0)
        {
            pRuleStr += 15;
            m_flag |= RULE_FLAG_DPI;
        }
        else
            ++pRuleStr;
        break;
    case 'E':
    case 'e':
        if (strncasecmp(pRuleStr, "end", 3) == 0)
        {
            pRuleStr += 3;
            m_flag |= RULE_FLAG_END;
            m_flag |= RULE_FLAG_LAST;
            break;
        }
        if (strncasecmp(pRuleStr, "env", 3) == 0)
            pRuleStr += 3;
        else
            ++pRuleStr;
        if (*pRuleStr == '=')
        {
            int n = -1;
            int isQuoted = 0;
            ++pRuleStr;
            if (*pRuleStr == '"' || *pRuleStr == '\'')
            {
                const char *p = strchr(pRuleStr+1, *pRuleStr);
                if (p)
                    n = p - pRuleStr - 1;
                if (n >= 0)
                {
                    ++pRuleStr;
                    isQuoted = 1;
                }
            }
            if (n == -1)
                n = strcspn(pRuleStr, ",] \t\r\n");
            if (n > 0)
            {
                const char *pEnv = pRuleStr;
                pRuleStr += n;
                if (memchr(pEnv, ':', n) == NULL)
                {
                    HttpLog::parse_error(s_pCurLine,  "missing ':' in env string");
                    return LS_FAIL;
                }
                RewriteSubstFormat *pFormat = new RewriteSubstFormat();
                if (!pFormat)
                {
                    ERR_NO_MEM("new SubstFormat()");
                    return LS_FAIL;
                }
                if (pFormat->parse(pEnv, pRuleStr, NULL))
                {
                    pRuleStr += isQuoted;
                    HttpLog::parse_error(s_pCurLine,  "failed to parse env string");
                    delete pFormat;
                    return LS_FAIL;
                }
                pFormat->setType(RewriteSubstFormat::ENV);
                m_env.append(pFormat);
                pRuleStr += isQuoted;
            }
            else
            {
                HttpLog::parse_error(s_pCurLine,  "invalid env string, empty string");
                return LS_FAIL;
            }
        }
        break;
    case 'F':
    case 'f':
        m_action = RULE_ACTION_FORBID;
        m_flag |= RULE_FLAG_LAST;
        m_statusCode = SC_403;
        if (strncasecmp(pRuleStr, "forbidden", 9) == 0)
            pRuleStr += 9;
        else
            ++pRuleStr;
        break;
    case 'G':
    case 'g':
        m_action = RULE_ACTION_GONE;
        m_flag |= RULE_FLAG_LAST;
        m_statusCode = SC_410;
        if (strncasecmp(pRuleStr, "gone", 4) == 0)
            pRuleStr += 4;
        else
            ++pRuleStr;
        break;
    case 'L':
    case 'l':
        m_flag |= RULE_FLAG_LAST;
        if (strncasecmp(pRuleStr, "last", 4) == 0)
            pRuleStr += 4;
        else    // 'L'
            ++pRuleStr;
        break;
    case 'n':
    case 'N':
        if (strncasecmp(pRuleStr, "nocase", 6) == 0)
        {
            m_flag |= RULE_FLAG_NOCASE;
            pRuleStr += 6;
        }
        else if (strncasecmp(pRuleStr, "nc", 2) == 0)
        {
            m_flag |= RULE_FLAG_NOCASE;
            pRuleStr += 2;
        }
        else if (strncasecmp(pRuleStr, "nosubreq", 8) == 0)
        {
            m_flag |= RULE_FLAG_NOSUBREQ;
            pRuleStr += 8;
        }
        else if (strncasecmp(pRuleStr, "ns", 2) == 0)
        {
            m_flag |= RULE_FLAG_NOSUBREQ;
            pRuleStr += 2;
        }
        else if (strncasecmp(pRuleStr, "noescape", 8) == 0)
        {
            m_flag |= RULE_FLAG_NOESCAPE;
            pRuleStr += 8;
        }
        else if (strncasecmp(pRuleStr, "ne", 2) == 0)
        {
            m_flag |= RULE_FLAG_NOESCAPE;
            pRuleStr += 2;
        }
        else if (strncasecmp(pRuleStr, "next", 4) == 0)
        {
            m_flag |= RULE_FLAG_NEXT;
            pRuleStr += 4;
        }
        else    // 'N'
        {
            m_flag |= RULE_FLAG_NEXT;
            ++pRuleStr;
        }
        break;
    case 'P':
    case 'p':
        if (strncasecmp(pRuleStr, "passthrough", 11) == 0)
        {
            m_flag |= (RULE_FLAG_PASSTHRU | RULE_FLAG_LAST);
            pRuleStr += 11;
        }
        else if (strncasecmp(pRuleStr, "pt", 2) == 0)
        {
            m_flag |= (RULE_FLAG_PASSTHRU | RULE_FLAG_LAST);
            pRuleStr += 2;
        }
        else
        {
            m_action = RULE_ACTION_PROXY;
            m_flag |= RULE_FLAG_LAST;
            m_statusCode = -2; //proxy
            if (strncasecmp(pRuleStr, "proxy", 5) == 0)
                pRuleStr += 5;
            else    // 'P'
                ++pRuleStr;
        }
        break;

    case 'Q':
    case 'q':
        if (strncasecmp(pRuleStr, "qsappend", 8) == 0)
        {
            m_flag |= RULE_FLAG_QSAPPEND;
            pRuleStr += 8;
        }
        else if (strncasecmp(pRuleStr, "qsa", 3) == 0)
        {
            m_flag |= RULE_FLAG_QSAPPEND;
            pRuleStr += 3;
        }
        else if (strncasecmp(pRuleStr, "qsdiscard", 8) == 0)
        {
            m_flag |= RULE_FLAG_QSDISCARD;
            pRuleStr += 8;
        }
        else if (strncasecmp(pRuleStr, "qsd", 3) == 0)
        {
            m_flag |= RULE_FLAG_QSDISCARD;
            pRuleStr += 3;
        }
        else
        {
            HttpLog::parse_error(s_pCurLine,  "Unknown rewrite rule flag");
            return LS_FAIL;
        }
        break;
    case 'R':
    case 'r':
        m_action = RULE_ACTION_REDIRECT;
        if (strncasecmp(pRuleStr, "redirect", 8) == 0)
            pRuleStr += 8;
        else
            ++pRuleStr;
        if (*pRuleStr == '=')
        {
            ++pRuleStr;
            size_t n = strcspn(pRuleStr, ",] \t\r\n");
            if (n == 0)
                m_statusCode = SC_302;
            else if ((strncasecmp(pRuleStr, "temp", 4) == 0) && (n == 4))
            {
                pRuleStr += 4;
                m_statusCode = SC_302;
            }
            else if ((strncasecmp(pRuleStr, "permanent", 9) == 0) && (n == 9))
            {
                pRuleStr += 9;
                m_statusCode = SC_301;
            }
            else if ((strncasecmp(pRuleStr, "seeother", 8) == 0) && (n == 8))
            {
                pRuleStr += 8;
                m_statusCode = SC_303;
            }
            else
            {
                m_statusCode = HttpStatusCode::getInstance().codeToIndex(pRuleStr);
                if (m_statusCode == -1)
                    m_statusCode = SC_302;
                else
                    pRuleStr += n;
            }
        }
        else
            m_statusCode = SC_302;
        break;
    case 'S':
    case 's':
        if (strncasecmp(pRuleStr, "skip", 4) == 0)
            pRuleStr += 4;
        else
            ++pRuleStr;
        if (*pRuleStr == '=')
        {
            ++pRuleStr;
            char *p;
            m_skipRules = strtol(pRuleStr, &p, 10);
            if (p == pRuleStr)
            {
                HttpLog::parse_error(s_pCurLine,  "invalid number in 'skip' flag");
                return LS_FAIL;
            }
            pRuleStr = p;
        }
        else
        {
            HttpLog::parse_error(s_pCurLine,  "invalid 'skip' flag, '=' expected");
            return LS_FAIL;
        }
        break;
    case 'T':
    case 't':
    case 'H':
    case 'h':
        if (strncasecmp(pRuleStr, "type", 4) == 0)
            pRuleStr += 4;
        else if (strncasecmp(pRuleStr, "handler", 7) == 0)
            pRuleStr += 7;
        else
            ++pRuleStr;
        if (*pRuleStr == '=')
        {
            ++pRuleStr;
            size_t n = strcspn(pRuleStr, ",] \t\r\n");
            if (n == 0)
            {
                HttpLog::parse_error(s_pCurLine,
                                     "invalid 'type' flag, missing mime type.");
                return LS_FAIL;
            }
            m_sMimeType.setStr(pRuleStr, n);
            pRuleStr += n;
        }
        else
        {
            HttpLog::parse_error(s_pCurLine,  "invalid 'type' flag, '=' expected");
            return LS_FAIL;
        }
        break;
    default:
        HttpLog::parse_error(s_pCurLine,  "Unknown rewrite rule flag");
        return LS_FAIL;
        break;
    }
    return 0;
}


int RewriteRule::parseRuleFlag(const char *&pRuleStr, const char *pEnd)
{
    while ((pRuleStr < pEnd) && (isspace(*pRuleStr)))
        ++pRuleStr;
    if ((pRuleStr == pEnd) || (*pRuleStr == '#'))
        return 0;
    if (*pRuleStr != '[')
    {
        HttpLog::parse_error(s_pCurLine,
                             "invalid third parameter, '[' is expected");
        return LS_FAIL;
    }
    ++pRuleStr;
    while (pRuleStr < pEnd)
    {
        while ((pRuleStr < pEnd) && isspace(*pRuleStr))
            ++pRuleStr;
        if (parseOneFlag(pRuleStr, pEnd))
            return LS_FAIL;
        while ((pRuleStr < pEnd) && isspace(*pRuleStr))
            ++pRuleStr;
        if (*pRuleStr == ']')
        {
            ++pRuleStr;
            return 0;
        }
        else if (*pRuleStr == ',')
            ++pRuleStr;
        else
        {
            HttpLog::parse_error(s_pCurLine,  "Unknown rewrite rule flag");
            return LS_FAIL;
        }
    }
    HttpLog::parse_error(s_pCurLine,  "missing ']'");
    return LS_FAIL;

}


int RewriteRule::compilePattern()
{
    int flag = REG_EXTENDED;
    if (m_flag & RULE_FLAG_NOCASE)
        flag = REG_EXTENDED | REG_ICASE;
    return m_regex.compile(m_pattern.c_str(), flag);
}


int RewriteRule::parseRule(char *pRule, const char *pEnd,
                           const RewriteMapList *pMaps)
{
    const char *argBegin = NULL;
    const char *argEnd = NULL;
    const char *pRuleStr = pRule;
    const char *pError = NULL;
    m_flag = 0;
    int ret = StringTool::parseNextArg(pRuleStr, pEnd, argBegin, argEnd,
                                       pError);
    if (ret)
    {
        if (pError)
            HttpLog::parse_error(s_pCurLine,  pError);
        return LS_FAIL;
    }
    if (*argBegin == '!')
    {
        ++argBegin;
        m_flag |= RULE_FLAG_NOMATCH;
        while ((argBegin < argEnd) && (isspace(*argBegin)))
            argBegin++;
    }
    if (argBegin == argEnd)
    {
        HttpLog::parse_error(s_pCurLine,  "pre-mature rewrite rule");
        return LS_FAIL;
    }
    m_pattern.setStr(argBegin, argEnd - argBegin);

    if (parseRuleSubst(pRuleStr, pEnd, pMaps))
        return LS_FAIL;
    if (parseRuleFlag(pRuleStr, pEnd))
        return LS_FAIL;
    *((char *)argEnd) = '\0';
    int flag = REG_EXTENDED;
    if (m_flag & RULE_FLAG_NOCASE)
        flag = REG_EXTENDED | REG_ICASE;
    ret = m_regex.compile(m_pattern.c_str(), flag);
    if (ret)
    {
        HttpLog::parse_error(s_pCurLine,  "failed to parse rewrite pattern");
        return LS_FAIL;
    }
    return 0;

}


int RewriteRule::parse(char *&pRule, const RewriteMapList *pMaps)
{
    char *pCur;
    char *pLineEnd;
    LinkedObj *pLast = m_conds.head();
    assert(pLast->next() == NULL);
    while (*pRule)
    {
        while (isspace(*pRule))
            ++pRule;
        if (!*pRule)
            break;
        pCur = pRule;
        pLineEnd = strchr(pCur, '\n');
        if (!pLineEnd)
        {
            pLineEnd = pCur + strlen(pCur);
            pRule = pLineEnd;
        }
        else
        {
            pRule = pLineEnd + 1;
            *pLineEnd = 0;
        }
        s_pCurLine = pCur;
        if (*pCur != '#')
        {
            if ((strncasecmp(pCur, "RewriteCond", 11) == 0) &&
                (isspace(*(pCur + 11))))
            {
                RewriteCond *pCond = new RewriteCond();
                if (!pCond)
                {
                    ERR_NO_MEM("new RewriteCond()");
                    return LS_FAIL;
                }

                if (pCond->parse(pCur + 12, pLineEnd, pMaps))
                {
                    delete pCond;
                    HttpLog::parse_error(s_pCurLine,  "invalid rewrite condition");
                    return LS_FAIL;
                }
                pLast->addNext(pCond);
                pLast = pCond;
            }
            else if ((strncasecmp(pCur, "RewriteRule", 11) == 0) &&
                     (isspace(*(pCur + 11))))
            {
                int ret = parseRule(pCur + 12, pLineEnd, pMaps);
                pCur = pLineEnd + 1;
                return ret;
            }
            else
            {
                HttpLog::parse_error(s_pCurLine,  "invalid rewrite directive ");
                return LS_FAIL;
            }
        }
    }

    return LS_FAIL;
}

