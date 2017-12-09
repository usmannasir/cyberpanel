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
#ifndef SSISCRIPT_H
#define SSISCRIPT_H


#include <lsdef.h>
#include <util/autobuf.h>

#include <util/autostr.h>
#include <util/tlinklist.h>


class HttpSession;
class SSITagConfig;
class LinkedObj;
class SSIBlock;
class SSI_If;
class SubstFormat;
class Pcregex;

enum
{
    SSI_NONE,
    SSI_ECHOMSG,
    SSI_ERRMSG,
    SSI_SIZEFMT,
    SSI_TIMEFMT,
    SSI_ECHO_VAR,
    SSI_ENCODING,
    SSI_EXEC_CGI,
    SSI_EXEC_CMD,
    SSI_INC_FILE,
    SSI_INC_VIRTUAL,
    SSI_SET_VALUE,
    SSI_EXPR,
    SSI_SET_VAR,
    SSI_ENC_NONE,
    SSI_ENC_URL,
    SSI_ENC_ENTITY
};

class ExprToken : public LinkedObj
{
public:
    enum
    {
        EXP_NONE,
        EXP_STRING,
        EXP_FMT,
        EXP_REGEX,
        EXP_OPENP,
        EXP_CLOSEP,
        EXP_EQ,
        EXP_NE,
        EXP_LESS,
        EXP_LE,
        EXP_GREAT,
        EXP_GE,
        EXP_NOT,
        EXP_AND,
        EXP_OR,
        EXP_END
    };
    ExprToken()
        : m_type(EXP_NONE)
        , m_obj(NULL)
    {}
    ~ExprToken();

    void setToken(int type, void *obj)
    {   m_type = type; m_obj = obj;     }
    int getType() const     {   return m_type;  }
    void *getObj() const   {   return m_obj;   }
    AutoStr2 *getStr() const   {   return (AutoStr2 *)m_obj;   }
    SubstFormat *getFormat() const {   return (SubstFormat *)m_obj;   }
    Pcregex *getRegex() const  {   return (Pcregex *)m_obj;    }

    static int s_priority[EXP_END];

    int getPriority() const {   return s_priority[m_type];  }

    ExprToken *next() const
    {   return (ExprToken *)LinkedObj::next();  }

private:

    int m_type;
    void *m_obj;


    LS_NO_COPY_ASSIGN(ExprToken);
};




class Expression : public LinkedObj, public TLinkList<ExprToken>
{
    int appendToken(int token);
    int appendString(const char *pBegin, int len);
    int appendRegex(const char *pBegin, int len, int flag);
    int buildPrefix();

public:
    Expression() {}
    ~Expression() { release_objects();  }
    int parse(const char *pBegin, const char *pEnd);
};


class SSIComponent : public LinkedObj
{
public:
    enum
    {
        SSI_String,
        SSI_Config,
        SSI_Echo,
        SSI_Exec,
        SSI_FSize,
        SSI_Flastmod,
        SSI_Include,
        SSI_Printenv,
        SSI_Set,
        SSI_If,
        SSI_Else,
        SSI_Elif,
        SSI_Endif,
        SSI_Block
    };

    SSIComponent()
        : m_content(0)
        , m_iType(0)
        , m_parsed(NULL)
    {}
    virtual ~SSIComponent();


    int getType() const     {   return m_iType; }
    void setType(int type) {   m_iType = type; }
    AutoBuf *getContentBuf()   {   return &m_content;  }

    void appendPrased(LinkedObj *p);

    LinkedObj *getFirstAttr() const
    {   return m_parsed;       }

private:
    AutoBuf m_content;
    int     m_iType;
    LinkedObj *m_parsed;
};

class SSI_If : public SSIComponent
{
public:
    SSI_If();
    ~SSI_If();
    void setIfBlock(SSIBlock *pBlock)    {   m_blockIf = pBlock;     }
    void setElseBlock(SSIBlock *pBlock)  {   m_blockElse = pBlock;   }

    SSIBlock *getIfBlock() const       {   return m_blockIf;   }
    SSIBlock *getElseBlock() const     {   return m_blockElse; }

private:
    SSIBlock *m_blockIf;
    SSIBlock *m_blockElse;


};


class SSIBlock : public TLinkList<SSIComponent>
{
public:
    SSIBlock()
        : m_pParentBlock(NULL)
        , m_pParentComp(NULL)
    {}
    SSIBlock(SSIBlock *pBlock, SSI_If *pComp)
        : m_pParentBlock(pBlock)
        , m_pParentComp(pComp)
    {}

    ~SSIBlock() {   release_objects();  }

    SSIBlock      *getParentBlock() const   {   return m_pParentBlock;  }
    SSI_If        *getParentComp() const    {   return m_pParentComp;   }
private:
    SSIBlock *m_pParentBlock;
    SSI_If    *m_pParentComp;

};

class SSIScript
{
public:
    SSIScript();

    ~SSIScript();

    int parse(SSITagConfig *pConfig, const char *pScriptPath);

    void resetRuntime()
    {
        m_pCurBlock = &m_main;
        m_pCurComponent = (SSIComponent *)m_main.head()->next();
    }
    void setCurrentBlock(SSIBlock *pBlock);

    SSIComponent *getCurrentComponent() const
    {   return m_pCurComponent;     }
    SSIComponent *nextComponent();

    const char *getPath() const
    {   return m_sPath.c_str();     }

    void setStatusCode(int code)   {   m_iParserState = code;      }
    int  getStatusCode() const      {   return m_iParserState;      }

    long getLastMod() const         {   return m_lModify;           }

    static int testParse();

private:
    int processSSIFile(SSITagConfig *pConfig, int fd);
    int parse(SSITagConfig *pConfig, char *pBegin, char *pEnd, int finish);
    int append_html_content(const char *pBegin, const char *pEnd);
    int parse_ssi_directive(const char *pBegin, const char *pEnd);

    int parseIf(int cmd, const char *pBegin, const char *pEnd);
    int addBlock(SSI_If *pSSI_If, int is_else);
    int parseAttrs(int cmd, const char *pBegin, const char *pEnd);

    int getAttr(const char *&pBegin, const char *pEnd,
                char *pAttrName, const char *&pValue,
                int &valLen);

    SSI_If *getComponentIf(SSIBlock *&pBlock);


    AutoStr2    m_sPath;
    int         m_iParserState;
    long        m_lModify;
    long        m_lSize;

    SSIBlock        m_main;
    SSIComponent   *m_pCurComponent;
    SSIBlock       *m_pCurBlock;
};

#endif
