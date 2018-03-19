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
#include "ssiscript.h"
#include "ssiconfig.h"

#include <http/requestvars.h>
#include <log4cxx/logger.h>
#include <lsr/ls_fileio.h>
#include <util/gpointerlist.h>
#include <util/pcregex.h>
#include <util/stringtool.h>

#include <pcreposix.h>

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>


static SubstFormat *parseFormat(const char *pBegin, int len)
{
    SubstFormat *pFormat = new SubstFormat();
    pFormat->parse(pBegin, pBegin, pBegin + len, 1);
    return pFormat;
}


ExprToken::~ExprToken()
{
    switch (m_type)
    {
    case EXP_STRING:
        delete(AutoStr2 *)m_obj;
        break;
    case EXP_FMT:
        delete(SubstFormat *)m_obj;
        break;
    case EXP_REGEX:
        delete(Pcregex *)m_obj;
        break;
    }
    return;
}


int Expression::appendToken(int token)
{
    ExprToken *pTok = new ExprToken();
    if (!pTok)
        return LS_FAIL;
    pTok->setToken(token, NULL);
    push_front(pTok);
    return 0;
}


int Expression::appendString(const char *pBegin, int len)
{
    ExprToken *pTok = new ExprToken();
    int tok = ExprToken::EXP_STRING;
    if (!pTok)
        return LS_FAIL;
    void *pObj = NULL;
    if (memchr(pBegin, '$', len))
    {
        SubstFormat *pFormat = parseFormat(pBegin, len);
        if (pFormat)
        {
            tok = ExprToken::EXP_FMT;
            pObj = pFormat;
        }
    }
    else
    {
        AutoStr2 *pStr = new AutoStr2(pBegin, len);
        if (pStr)
            pObj = pStr;
    }
    if (!pObj)
    {
        delete pTok;
        return LS_FAIL;
    }
    pTok->setToken(tok, pObj);
    push_front(pTok);
    return 0;

}


int Expression::appendRegex(const char *pBegin, int len, int flag)
{
    ExprToken *pTok = new ExprToken();
    int tok = ExprToken::EXP_REGEX;
    if (!pTok)
        return LS_FAIL;
    Pcregex *regex = new Pcregex();
    regex->compile(pBegin, REG_EXTENDED | flag);
    pTok->setToken(tok, regex);
    push_front(pTok);
    return 0;
}


int Expression::parse(const char *pBegin, const char *pEnd)
{
    char achBuf[ 10240];
    char *p = achBuf;
    char quote = 0;
    char space = 1;
    char ch;
    char token = 0;
    while (pBegin < pEnd)
    {
        ch = *pBegin++;

        if (quote)
        {
            if (ch == quote)
            {
                //end of a quote string
                *p = 0;
                if (quote == '/')
                {
                    int case_ins = 0;
                    if (*pBegin == 'i')
                    {
                        case_ins = REG_ICASE;
                        ++pBegin;
                    }
                    appendRegex(achBuf, p - achBuf, case_ins);
                }
                else
                    appendString(achBuf, p - achBuf);
                p = achBuf;
                quote = 0;
            }
            else
            {
                if (ch == '\\')
                {
                    if (pBegin >= pEnd)
                        break;
                    ch = *pBegin++;
                }
                *p++ = ch;
            }
            continue;
        }

        switch (ch)
        {
        case '=':
            if (*pBegin == '=')
                ++pBegin;
            token = ExprToken::EXP_EQ;
            break;
        case '!':
            if (*pBegin == '=')
            {
                ++pBegin;
                token = ExprToken::EXP_NE;
            }
            else
                token = ExprToken::EXP_NOT;
            break;
        case '<':
            if (*pBegin == '=')
            {
                ++pBegin;
                token = ExprToken::EXP_LE;
            }
            else
                token = ExprToken::EXP_LESS;
            break;
        case '>':
            if (*pBegin == '=')
            {
                ++pBegin;
                token = ExprToken::EXP_GE;
            }
            else
                token = ExprToken::EXP_GREAT;
            break;
        case '(':
            token = ExprToken::EXP_OPENP;
            break;
        case ')':
            token = ExprToken::EXP_CLOSEP;
            break;
        case '&':
            if (*pBegin == '&')
                ++pBegin;
            token = ExprToken::EXP_AND;
            break;
        case '|':
            if (*pBegin == '|')
                ++pBegin;
            token = ExprToken::EXP_OR;
            break;
        case ' ':
        case '\t':
            if (!space)
                space = 1;
            continue;

        case '"':
        case '\'':
            quote = ch;
            break;
        case '\\':
            if (pBegin >= pEnd)
                break;
            ch = *pBegin++;
        //fall through
        default:
            if (space)
            {
                if (p != achBuf)
                    *p++ = ' ';
                space = 0;
            }
            *p++ = ch;
            continue;
        }
        space = 0;
        if (p != achBuf)
        {
            *p = 0;
            appendString(achBuf, p - achBuf);
            p = achBuf;
        }
        if (token)
        {
            if ((token == ExprToken::EXP_EQ) ||
                (token == ExprToken::EXP_NE))
            {
                while (isspace(*pBegin))
                    ++pBegin;
                if (*pBegin == '/')
                {
                    ++pBegin;
                    quote = '/';
                }
            }
            appendToken(token);
            token = 0;
        }
    }
    if (p != achBuf)
    {
        appendString(achBuf, p - achBuf);
        p = achBuf;
    }
    buildPrefix();
    return 0;
}


int ExprToken::s_priority[EXP_END] =
{
    0, 0, 0, 0,
    5, // EXP_OPENP,
    1, // EXP_CLOSEP,
    3, // EXP_EQ,
    3, // EXP_NE,
    3, // EXP_LESS,
    3, // EXP_LE,
    3, // EXP_GREAT,
    3, // EXP_GE,
    4, // EXP_NOT,
    2, // EXP_AND,
    2  // EXP_OR,

};

/*
Algorithm
1) Reverse the input string.
2) Examine the next element in the input.
3) If it is operand, add it to output string.
4) If it is Closing parenthesis, push it on stack.
5) If it is an operator, then
i) If stack is empty, push operator on stack.
ii) If the top of stack is closing parenthesis, push operator on stack.
iii) If it has same or higher priority than the top of stack, push operator on stack.
iv) Else pop the operator from the stack and add it to output string, repeat step 5.
6) If it is a opening parenthesis, pop operators from stack and add them to output string until a closing parenthesis is encountered. Pop and discard the closing parenthesis.
7) If there is more input go to step 2
8) If there is no more input, unstack the remaining operators and add them to output string.
9) Reverse the output string.
*/

int Expression::buildPrefix()
{
    TLinkList<ExprToken> list;
    TPointerList<ExprToken> stack;
    ExprToken *tok;
    ExprToken *next;
    ExprToken *op;
    list.swap(*this);
    tok = list.begin();
    while (tok)
    {
        next = (ExprToken *)tok->next();
        tok->setNext(NULL);
        if (tok->getType() < ExprToken::EXP_OPENP)
            push_front(tok);
        else if (tok->getType() == ExprToken::EXP_CLOSEP)
            stack.push_back(tok);
        else if (tok->getType() > ExprToken::EXP_CLOSEP)
        {
            while (1)
            {
                if ((stack.empty()) ||
                    (tok->getPriority() >= stack.back()->getPriority()))
                {
                    stack.push_back(tok);
                    break;
                }
                else
                {
                    op = stack.pop_back();
                    push_front(op);
                }
            }
        }
        else if (tok->getType() == ExprToken::EXP_OPENP)
        {
            while ((!stack.empty()) &&
                   (stack.back()->getType() != ExprToken::EXP_CLOSEP))
            {
                op = stack.pop_back();
                push_front(op);
            }
            if (stack.empty())
            {
                op = stack.pop_back();
                delete op;
            }
            delete tok;
        }
        tok = next;
    }
    while (!stack.empty())
    {
        op = stack.pop_back();
        if (op->getType() != ExprToken::EXP_CLOSEP)
            push_front(op);
        else
            delete op;
    }
    return 0;
}


SSIComponent::~SSIComponent()
{
    LinkedObj *pNext, *p1 = m_parsed;
    while (p1)
    {
        pNext = p1->next();
        //delete p1
        delete(SubstItem *)p1;
        p1 = pNext;
    }
}


void SSIComponent::appendPrased(LinkedObj *p)
{
    if (!p)
        return;
    if (!m_parsed)
        m_parsed = p;
    else
    {
        LinkedObj *p1 = m_parsed;
        while (p1->next())
            p1 = p1->next();
        p1->setNext(p);
    }
}


SSI_If::SSI_If()
    : m_blockIf(NULL)
    , m_blockElse(NULL)
{}


SSI_If::~SSI_If()
{
    if (m_blockIf)
        delete m_blockIf;
    if (m_blockElse)
        delete m_blockElse;
}


SSIScript::SSIScript()
//    : m_pConfig( NULL )
{
}


SSIScript::~SSIScript()
{
}


int SSIScript::append_html_content(const char *pBegin, const char *pEnd)
{
    if ((!m_pCurComponent) ||
        (m_pCurComponent->getType() != SSIComponent::SSI_String))
    {
        m_pCurComponent = new SSIComponent();
        if (!m_pCurComponent)
            return LS_FAIL;
        m_pCurComponent->setType(SSIComponent::SSI_String);
        m_pCurBlock->append(m_pCurComponent);
    }
    m_pCurComponent->getContentBuf()->append(pBegin, pEnd - pBegin);
    return 0;
}


static const char *s_SSI_Cmd[] =
{
    "N/A",
    "config", "echo", "exec",
    "fsize", "flastmod", "include", "printenv",
    "set", "if", "else", "elif", "endif"
};
static int s_SSI_Cmd_len[] =
{   0, 6, 4, 4, 5, 8, 7, 8, 3, 2, 4, 4, 5 };

static const char *s_SSI_Attrs[] =
{
    "N/A", "echomsg", "errmsg", "sizefmt", "timefmt",
    "var", "encoding", "cgi", "cmd", "file", "virtual",
    "value", "expr", "var", "none", "url", "entity"
};

static int s_SSI_Attrs_len[] =
{   0, 7, 6, 7, 7, 3, 8, 3, 3, 4, 7, 5, 4, 3, 4, 3, 6  };


int SSIScript::getAttr(const char *&pBegin, const char *pEnd,
                       char *pAttrName, const char *&pValue, int &valLen)
{
    while (isspace(*pBegin))
        ++pBegin;
    if (pBegin >= pEnd)
        return -2;
    if (*pBegin == '=')
        return LS_FAIL;
    const char *pAttrEnd = (const char *)memchr(pBegin, '=', pEnd - pBegin);
    if (!pAttrEnd)
        return LS_FAIL;
    pValue = pAttrEnd + 1;
    while (isspace(pAttrEnd[ -1 ]))
        --pAttrEnd;
    if (pAttrEnd - pBegin > 80)
        return LS_FAIL;
    memmove(pAttrName, pBegin, pAttrEnd - pBegin);
    pAttrName[pAttrEnd - pBegin] = 0;

    while (isspace(*pValue))
        ++pValue;
    pAttrEnd = StringTool::strNextArg(pValue, NULL);
    if (!pAttrEnd)
        pAttrEnd = pEnd;
    valLen = pAttrEnd - pValue;
    pBegin = pAttrEnd + 1;
    return 0;

}


int SSIScript::parseAttrs(int cmd, const char *pBegin, const char *pEnd)
{
    char achAttr[100];
    const char *pValue;
    int  valLen;
    int ret;
    while (1)
    {
        ret = getAttr(pBegin, pEnd, achAttr, pValue, valLen);
        if (ret == -1)
            return LS_FAIL;
        if (ret == -2)
            break;
        int attr = 1;
        for (; attr <= SSI_EXPR; attr++)
        {
            if (strcasecmp(s_SSI_Attrs[attr], achAttr) == 0)
                break;
        }
        if (attr > SSI_EXPR)
        {
            //error: unknown SSI attribute
            continue;
        }
        if (attr == SSI_ENCODING)
        {
            attr = SSI_ENC_NONE;
            for (; attr <= SSI_ENC_ENTITY; attr++)
            {
                if ((strncasecmp(s_SSI_Attrs[attr], pValue, valLen) == 0)
                    && (s_SSI_Attrs_len[attr] == valLen))
                    break;
            }
            if (attr > SSI_ENC_ENTITY)
                continue;
        }
        if (attr == SSI_EXPR)
        {
            if ((cmd != SSIComponent::SSI_If) &&
                (cmd != SSIComponent::SSI_Elif))
                continue;
        }


        SubstItem *pItem = new SubstItem();

        if (attr == SSI_EXPR)
        {
            Expression *pExpr = new Expression();
            pExpr->parse(pValue, pValue + valLen);
            pItem->setType(REF_EXPR);
            pItem->setAny(pExpr);

        }
        else if (attr == SSI_ECHO_VAR)
        {
            if (cmd == SSIComponent::SSI_Set)
            {
                attr = SSI_SET_VAR;
                pItem->setType(REF_STRING);
                pItem->setStr(pValue, valLen);
            }
            else
            {
                int id = RequestVars::parseBuiltIn(pValue, valLen, 1);
                if (id == -1)
                {
                    id = REF_ENV;
                    pItem->setStr(pValue, valLen);
                }
                pItem->setType(id);
            }
        }
        else if (attr < SSI_ENC_NONE)
        {
            if (memchr(pValue, '$', valLen))
            {
                SubstFormat *pFormat = parseFormat(pValue, valLen);
                if (pFormat)
                {
                    pItem->setType(REF_FORMAT_STR);
                    pItem->setAny(pFormat);
                }
            }
            else
            {
                pItem->setType(REF_STRING);
                pItem->setStr(pValue, valLen);
            }
        }
        pItem->setSubType(attr);

        m_pCurComponent->appendPrased(pItem);

    }
    return 0;
}


int SSIScript::addBlock(SSI_If *pSSI_If, int is_else)
{
    SSIBlock *pBlock = new SSIBlock(m_pCurBlock, pSSI_If);
    if (!is_else)
        pSSI_If->setIfBlock(pBlock);
    else
        pSSI_If->setElseBlock(pBlock);
    m_pCurComponent = NULL;
    m_pCurBlock = pBlock;
    return 0;
}


SSI_If *SSIScript::getComponentIf(SSIBlock *&pBlock)
{
    SSI_If *pComp = m_pCurBlock->getParentComp();
    pBlock = m_pCurBlock->getParentBlock();
    while (pComp &&
           (pComp->getType() != SSIComponent::SSI_If))
    {
        pComp = pBlock->getParentComp();
        pBlock = pBlock->getParentBlock();
    }
    return pComp;
}


int SSIScript::parseIf(int cmd, const char *pBegin, const char *pEnd)
{
    if ((cmd == SSIComponent::SSI_Elif) ||
        (cmd == SSIComponent::SSI_Else))
    {
        SSIBlock *pBlock = m_pCurBlock->getParentBlock();
        SSI_If *pSSI_If = m_pCurBlock->getParentComp();
        if (!pSSI_If)
        {
            if (cmd == SSIComponent::SSI_Elif)
            {
                //Error: Elif block without matching If, treated as If block
                cmd = SSIComponent::SSI_If;
            }
            else
            {
                //Error: Else block without matching If, ignore
                return 0;
            }
        }
        else
        {
            m_pCurComponent = pSSI_If;
            m_pCurBlock = pBlock;
            addBlock(pSSI_If, 1);
        }
    }

    if (cmd == SSIComponent::SSI_Endif)
    {
        SSIBlock *pBlock;
        SSI_If *pSSI_If = getComponentIf(pBlock);
        if (!pSSI_If)
        {
            //Error: Endif without matching If, ignore
            return 0;
        }
        m_pCurBlock = pBlock;
        m_pCurComponent = NULL;
        return 0;
    }

    if ((cmd == SSIComponent::SSI_Elif) ||
        (cmd == SSIComponent::SSI_If))
    {
        SSI_If *pSSI_If = new SSI_If();
        m_pCurComponent = pSSI_If;
        m_pCurComponent->setType(cmd);
        m_pCurBlock->append(m_pCurComponent);
        while (isspace(*pBegin))
            ++pBegin;
        parseAttrs(cmd, pBegin, pEnd);

        addBlock(pSSI_If, 0);
    }
    return 0;
}


int SSIScript::parse_ssi_directive(const char *pBegin, const char *pEnd)
{
    while (isspace(*pBegin))
        ++pBegin;
    if (pBegin >= pEnd)
        return 0;
    int cmd = 1;
    for (; cmd < (int)(sizeof(s_SSI_Cmd) / sizeof(const char *)); cmd++)
    {
        if (strncasecmp(s_SSI_Cmd[cmd], pBegin,
                        s_SSI_Cmd_len[cmd]) == 0)
        {
            if (isspace(*(pBegin + s_SSI_Cmd_len[cmd])))
                break;
        }
    }
    if (cmd > SSIComponent::SSI_Endif)
    {
        //error: unknown SSI command
        return LS_FAIL;
    }
    pBegin += s_SSI_Cmd_len[cmd] + 1;
    while (isspace(*pBegin))
        ++pBegin;
    if ((cmd == SSIComponent::SSI_If) ||
        (cmd == SSIComponent::SSI_Elif) ||
        (cmd == SSIComponent::SSI_Else) ||
        (cmd == SSIComponent::SSI_Endif))
        return parseIf(cmd, pBegin, pEnd);

    m_pCurComponent = new SSIComponent();
    if (!m_pCurComponent)
        return LS_FAIL;
    m_pCurComponent->setType(cmd);
    m_pCurBlock->append(m_pCurComponent);
    return parseAttrs(cmd, pBegin, pEnd);

    return 0;
}


int SSIScript::parse(SSITagConfig *pConfig, char *pBegin, char *pEnd,
                     int finish)
{
    static AutoStr2 sStart("<!--#");
    static AutoStr2 sEnd("-->");
    const AutoStr2 *pattern[2] = { NULL, NULL };
    char *p = pBegin;
    char *pTag;
    char *pContentBegin = pBegin;
    if (pConfig)
    {
        pattern[0] = &pConfig->getStartTag();
        pattern[1] = &pConfig->getEndTag();
    }
    if (!pattern[0] || !pattern[0]->c_str())
        pattern[0] = &sStart;
    if (!pattern[1] || !pattern[1]->c_str())
        pattern[1] = &sEnd;

    while (p < pEnd + 1 - pattern[m_iParserState]->len())
    {
        pTag = (char *)memchr(p, *(pattern[m_iParserState]->c_str()),
                              pEnd + 1 - pattern[m_iParserState]->len() - p);
        if (pTag)
        {
            if (memcmp(pTag, pattern[m_iParserState]->c_str(),
                       pattern[m_iParserState]->len()) == 0)
            {
                if (m_iParserState)
                {
                    *pTag = 0;
                    parse_ssi_directive(pContentBegin, pTag);
                }
                else
                {
                    if (pContentBegin != pTag)
                        append_html_content(pContentBegin, pTag);
                }
                p = pTag + pattern[m_iParserState]->len();
                pContentBegin = p;
                m_iParserState = !m_iParserState;
            }
            else
                p = pTag + 1;
            continue;
        }
        else
            break;
    }

    if (m_iParserState)
    {
        //looking for the end tag
    }
    else
    {
        //looking for the start tag
        if (finish)
            p = pEnd;
        else
        {
            if (pEnd - p > pattern[m_iParserState]->len() - 1)
                p = pEnd + 1 - pattern[m_iParserState]->len();
        }
        if (p > pContentBegin)
            append_html_content(pContentBegin, p);
        pContentBegin = p;
    }
    return pContentBegin - pBegin;
}


int SSIScript::processSSIFile(SSITagConfig *pConfig, int fd)
{
    int ret;
    int left;
    int finish = 0;
    char *pBegin;
    char *pEnd;
    char *pBufEnd;

    char achBuf[8192];

    m_iParserState = 0;
    pEnd = pBegin = achBuf;
    m_pCurComponent = NULL;
    m_pCurBlock = &m_main;

    pBufEnd = pBegin + sizeof(achBuf);
    while (!finish)
    {
        ret = ls_fio_read(fd, pEnd, pBufEnd - pEnd);
        if (ret < pBufEnd - pEnd)
            finish = 1;
        if (ret > 0)
            pEnd += ret;
        ret = parse(pConfig, pBegin, pEnd, finish);
        pBegin += ret;
        left = pEnd - pBegin;
        if (left > 0)
        {
            if (pBegin != achBuf)
            {
                memmove(achBuf, pBegin, left);
                pBegin = achBuf;
                pEnd = &achBuf[left];
            }
        }
        else
            pEnd = pBegin = achBuf;
    }
    return ret;

}


int SSIScript::parse(SSITagConfig *pConfig, const char *pScriptPath)
{
    struct stat st;
    int fd;
    int ret;
    fd = ls_fio_open(pScriptPath, O_RDONLY, 0644);
    if (fd != -1)
    {
        m_sPath.setStr(pScriptPath);
        if (fstat(fd, &st) == 0)
        {
            m_lModify = st.st_mtime;
            m_lSize = st.st_size;
        }
        ret = processSSIFile(pConfig, fd);
        close(fd);
        return ret;
    }
    else
    {
        LS_ERROR("[%s] Failed to open SSI script: %s",
                 pScriptPath, strerror(errno));
    }
    return LS_FAIL;

}


int SSIScript::testParse()
{
    SSIScript script;
    script.parse(NULL, "/home/gwang/proj/httpd/test_data/local_time.shtml");
    return 0;
}


SSIComponent *SSIScript::nextComponent()
{
    if (!m_pCurComponent)
        return NULL;
    SSIComponent *pComponent = m_pCurComponent;
    m_pCurComponent = (SSIComponent *)m_pCurComponent->next();
    while (!m_pCurComponent)
    {
        if (m_pCurBlock)
        {
            m_pCurComponent = m_pCurBlock->getParentComp();
            if (m_pCurComponent)
                m_pCurComponent = (SSIComponent *)m_pCurComponent->next();
            m_pCurBlock = m_pCurBlock->getParentBlock();
        }
        else
            break;
    }
    return pComponent;
}


void SSIScript::setCurrentBlock(SSIBlock *pBlock)
{
    SSIComponent *pComponent = (SSIComponent *)pBlock->head()->next();
    if (!pComponent)
        return;
    m_pCurBlock = pBlock;
    m_pCurComponent = pComponent;
}

