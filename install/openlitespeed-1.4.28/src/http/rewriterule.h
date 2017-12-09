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
#ifndef REWRITERULE_H
#define REWRITERULE_H

#include <http/requestvars.h>
#include <log4cxx/nsdefs.h>
#include <util/pcregex.h>
#include <util/autostr.h>
#include <util/tlinklist.h>


BEGIN_LOG4CXX_NS
class Logger;
END_LOG4CXX_NS


#define COND_FLAG_NONE          0
#define COND_FLAG_NOCASE        1
#define COND_FLAG_OR            2
#define COND_FLAG_NOMATCH       4

#define COND_OP_REGEX           0
#define COND_OP_LESS            1
#define COND_OP_GREATER         2
#define COND_OP_EQ              3
#define COND_OP_DIR             4
#define COND_OP_FILE            5
#define COND_OP_SIZE            6
#define COND_OP_SYM             7
#define COND_OP_FILE_ACC        8
#define COND_OP_URL_ACC         9

#define RULE_FLAG_NONE          0
#define RULE_FLAG_LAST          (1<<0)
#define RULE_FLAG_NEXT          (1<<1)
#define RULE_FLAG_CHAIN         (1<<2)
#define RULE_FLAG_NOSUBREQ      (1<<3)
#define RULE_FLAG_PASSTHRU      (1<<4)
#define RULE_FLAG_QSAPPEND      (1<<5)
#define RULE_FLAG_NOESCAPE      (1<<6)
#define RULE_FLAG_NOCASE        (1<<7)
#define RULE_FLAG_NOMATCH       (1<<8)
#define RULE_FLAG_NOREWRITE     (1<<9)
#define RULE_FLAG_WITHQS        (1<<10)
#define RULE_FLAG_DPI           (1<<11)
#define RULE_FLAG_QSDISCARD     (1<<12)
#define RULE_FLAG_END           (1<<13)
#define RULE_FLAG_BR_ESCAPE     (1<<14)

#define RULE_ACTION_NONE        0
#define RULE_ACTION_REDIRECT    1
#define RULE_ACTION_FORBID      2
#define RULE_ACTION_GONE        3
#define RULE_ACTION_PROXY       4



//class RewriteMap
//{
//
//public:
//
//};


class RewriteMap;
class RewriteMapList;
class MapRefItem;





class RewriteSubstItem : public SubstItem
{
    void operator=(const RewriteSubstItem &rhs);
public:
    RewriteSubstItem();
    ~RewriteSubstItem();
    RewriteSubstItem(const RewriteSubstItem &rhs);

    void setMapRef(MapRefItem *p)    {   setAny(p);      }
    MapRefItem *getMapRef() const
    {   return (MapRefItem *) getAny();   }

    int needUrlDecode() const;
};

class RewriteSubstFormat : public TLinkList< RewriteSubstItem >,
    public LinkedObj
{
    int m_type;
    void operator=(const RewriteSubstFormat &rhs);
public:
    enum
    {
        ENV,
        COOKIE
    };
    RewriteSubstFormat();
    ~RewriteSubstFormat();
    RewriteSubstFormat(const RewriteSubstFormat &rhs);
    int parse(const char *pFormatStr, const char *pEnd,
              const RewriteMapList *pMaps);
    int equal(const RewriteSubstFormat &rhs) const;

    int isEnv() const       {   return m_type == ENV;       }
    int isCookie() const    {   return m_type == COOKIE;    }

    void setType(int t)    {   m_type = t;     }
};

class MapRefItem
{
    RewriteMap   *m_pMap;
    RewriteSubstFormat *m_pKeyFormat;
    RewriteSubstFormat *m_pDefaultFormat;
    void operator=(const MapRefItem &rhs);
public:
    MapRefItem();
    ~MapRefItem();
    MapRefItem(const MapRefItem &rhs);
    const RewriteSubstFormat *getKeyFormat() const        {   return m_pKeyFormat;        }
    const RewriteSubstFormat *getDefaultFormat() const    {   return m_pDefaultFormat;    }
    RewriteMap *getMap() const                     {   return m_pMap;              }

    int parse(const char *&pFormatStr, const char *pEnd,
              const RewriteMapList *pMaps);
};


class RewriteCond : public LinkedObj
{
    Pcregex     m_regex;
    AutoStr     m_pattern;

    RewriteSubstFormat m_testStringFormat;
    char        m_opcode;
    char        dummy;
    short       m_flag;

    int parseTestString(const char *&pRuleStr, const char *pEnd,
                        const RewriteMapList *pMaps);
    int parseCondPattern(const char *&pRuleStr, const char *pEnd);
    int praseFlag(const char *&pRuleStr, const char *pEnd);
    int compilePattern();
    void operator=(const RewriteCond &rhs);

public:
    RewriteCond();
    ~RewriteCond();
    RewriteCond(const RewriteCond &rhs);
    char getOpcode() const          {   return m_opcode;            }
    short getFlag() const           {   return m_flag;              }
    const char *getPattern() const {   return m_pattern.c_str();   }
    const Pcregex *getRegex() const {   return &m_regex;            }

    const RewriteSubstFormat *getTestStringFormat() const     {   return &m_testStringFormat; }


    int parse(const char *pCondStr, const char *pEnd,
              const RewriteMapList *pMaps);
};


class RewriteRule : public LinkedObj
{
    Pcregex                     m_regex;
    TLinkList<RewriteCond>      m_conds;
    RewriteSubstFormat          m_targetFormat;
    AutoStr                     m_sMimeType;
    short                       m_action;
    short                       m_flag;
    int                         m_statusCode;
    int                         m_skipRules;
    TLinkList<RewriteSubstFormat> m_env;
    AutoStr                     m_pattern;


    int parseRuleSubst(const char *&pRuleStr, const char *pEnd,
                       const RewriteMapList *pMaps);
    int parseRuleFlag(const char *&pRuleStr, const char *pEnd);
    int parseOneFlag(const char *&pRuleStr, const char *pEnd);
    int compilePattern();
    void operator=(const RewriteRule &rhs);

public:
    RewriteRule();
    ~RewriteRule();
    RewriteRule(const RewriteRule &rhs);
    int parseRule(char *pRuleStr, const char *pEnd,
                  const RewriteMapList *pMaps);
    int parse(char *&pRuleStr, const RewriteMapList *pMaps);

    const Pcregex *getRegex() const        {   return &m_regex;            }
    const RewriteCond *getFirstCond() const {   return m_conds.begin();     }
    const RewriteSubstFormat *getTargetFmt() const {   return &m_targetFormat;     }
    const char    *getMimeType() const  {   return m_sMimeType.c_str();     }
    short          getAction() const    {   return m_action;                }
    short          getFlag() const      {   return m_flag;                  }
    int     getStatusCode() const       {   return m_statusCode;            }
    int     getSkip() const             {   return m_skipRules;             }
    const TLinkList<RewriteSubstFormat> *getEnv() const
    {   return &m_env;      }
    const char *getPattern() const {   return m_pattern.c_str();   }
    int parseCookieAction(const char *pRuleStr, const char *pEnd);
    static void setLogger(LOG4CXX_NS::Logger *pLogger, const char *pId);
    static void error(const char *pError);
};



#endif
