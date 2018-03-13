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
#include "ssiengine.h"

#include "ssiscript.h"
#include "ssiruntime.h"
#include "ssiconfig.h"

#include <http/handlertype.h>
#include <http/httpcgitool.h>
#include <http/httpsession.h>
#include <http/httpstatuscode.h>
#include <http/requestvars.h>
#include <log4cxx/logger.h>
#include <lsr/ls_fileio.h>
#include <util/httputil.h>
#include <util/ienv.h>

#include <stdio.h>

SSIEngine::SSIEngine()
    : HttpHandler(HandlerType::HT_SSI)
{
}


SSIEngine::~SSIEngine()
{
}


const char *SSIEngine::getName() const
{
    return "ssi";
}


void SSIEngine::printError(HttpSession *pSession, char *pError)
{
    char achBuf[] = "[an error occurred while processing this directive]\n";
    if (!pError)
        pError = achBuf;

    pSession->appendDynBody(pError, strlen(pError));
}


int SSIEngine::startExecute(HttpSession *pSession,
                            SSIScript *pScript)
{
    if (!pScript)
        return SC_500;
    SSIRuntime *pRuntime = pSession->getReq()->getSSIRuntime();
    if (!pRuntime)
    {
        char ct[] = "text/html";
        HttpReq *pReq = pSession->getReq();
        pRuntime = new SSIRuntime();
        if (!pRuntime)
            return SC_500;
        pRuntime->init();
        pRuntime->initConfig(pReq->getSSIConfig());
        pReq->setSSIRuntime(pRuntime);
        pSession->getResp()->reset();
        //pSession->getResp()->prepareHeaders( pReq );
        //pSession->setupChunkOS( 0 );
        HttpCgiTool::processContentType(pReq, pSession->getResp(),
                                        ct , 9);
//        pSession->setupRespCache();
        if (pReq->isXbitHackFull())
            pSession->getResp()->appendLastMod(pReq->getLastMod());
        int status = pReq->getStatusCode();
        if ((status >= SC_300) && (status < SC_400))
        {
            if (pReq->getLocation() != NULL)
                pSession->addLocationHeader();
        }
        pSession->setupGzipFilter();
        pReq->andGzip(~GZIP_ENABLED);    //disable GZIP
    }
    if (pRuntime->push(pScript) == -1)
        return SC_500;
    pSession->getReq()->backupPathInfo();
    pScript->resetRuntime();
    return resumeExecute(pSession);
}


int SSIEngine::updateSSIConfig(HttpSession *pSession,
                               SSIComponent *pComponent,
                               SSIRuntime *pRuntime)
{
    SubstItem *pItem = (SubstItem *)pComponent->getFirstAttr();
    char achBuf[4096];
    char *p;
    int len;
    int attr;
    while (pItem)
    {
        attr = pItem->getSubType();
        p = achBuf;
        len = 4096;
        switch (attr)
        {
        case SSI_ECHOMSG:
        case SSI_ERRMSG:
        case SSI_TIMEFMT:
            RequestVars::appendSubst(pItem, pSession, p, len, 0, NULL);
            if (attr == SSI_ERRMSG)
                pRuntime->getConfig()->setErrMsg(achBuf, p - achBuf);
            else if (attr == SSI_ECHOMSG)
                pRuntime->getConfig()->setEchoMsg(achBuf, p - achBuf);
            else
                pRuntime->getConfig()->setTimeFmt(achBuf, p - achBuf);
            break;
        case SSI_SIZEFMT:
            if (pItem->getType() == REF_STRING)
            {
                const AutoStr2 *pStr = pItem->getStr();
                if ((pStr) && (pStr->c_str()))
                    pRuntime->getConfig()->setSizeFmt(pStr->c_str(), pStr->len());
            }
            break;

        }

        pItem = (SubstItem *) pItem->next();
    }
    return 0;
}


int SSIEngine::processEcho(HttpSession *pSession, SSIComponent *pComponent)
{
    SubstItem *pItem = (SubstItem *)pComponent->getFirstAttr();
    char achBuf1[8192];
    char achBuf[40960];
    char *p;
    int len;
    int attr;
    int encode = SSI_ENC_ENTITY;
    while (pItem)
    {
        attr = pItem->getSubType();
        p = achBuf1;
        len = 8192;
        switch (attr)
        {
        case SSI_ECHO_VAR:
            if ((pItem->getType() == REF_DATE_LOCAL) ||
                (pItem->getType() == REF_LAST_MODIFIED) ||
                (pItem->getType() == REF_DATE_GMT))
                memccpy(p, pSession->getReq()->getSSIRuntime()
                        ->getConfig()->getTimeFmt()->c_str(), 0, 4096);
            RequestVars::appendSubst(pItem, pSession, p, len,
                                     0, pSession->getReq()->getSSIRuntime()->getRegexResult());
            if (encode == SSI_ENC_URL)
            {
                len = HttpUtil::escape(achBuf1, p - achBuf1,
                                       achBuf, 40960);
                p = achBuf;
            }
            else if (encode == SSI_ENC_ENTITY)
            {
                len = HttpUtil::escapeHtml(achBuf1, p, achBuf, 40960);
                p = achBuf;
            }
            else
            {
                len = p - achBuf1;
                p = achBuf1;
            }
            if (len > 0)
                pSession->appendDynBody(p, len);
            break;
        case SSI_ENC_NONE:
        case SSI_ENC_URL:
        case SSI_ENC_ENTITY:
            encode = attr;
            break;
        }

        pItem = (SubstItem *) pItem->next();
    }
    return 0;
}


int SSIEngine::processExec(HttpSession *pSession, SSIComponent *pComponent)
{
    if (pSession->getReq()->isIncludesNoExec())
    {
        //Notice: Exec from server side include is disabled.
        return 0;
    }
    SubstItem *pItem = (SubstItem *)pComponent->getFirstAttr();
    return processSubReq(pSession, pItem);

}


int SSIEngine::processFileAttr(HttpSession *pSession,
                               SSIComponent *pComponent)
{
    SubstItem *pItem = (SubstItem *)pComponent->getFirstAttr();
    if (!pItem)
        return 0;
    int len;
    int attr = pItem->getSubType();
    char achBuf[4096];
    char *p = achBuf;
    len = 4096;
    if ((attr != SSI_INC_FILE) && (attr != SSI_INC_VIRTUAL))
        return 0;
    SSIRuntime *pRuntime = pSession->getReq()->getSSIRuntime();
    RequestVars::appendSubst(pItem, pSession, p, len,
                             0, pRuntime->getRegexResult());
    {
        if (achBuf[0] == 0)
        {
            len = snprintf(achBuf, 4096,
                           "[an error occurred while processing this directive]\n");
            pSession->appendDynBody(achBuf, len);
            return 0;
        }
        HttpReq *pReq = pSession->getReq();
        const char *pURI ;
        const char *p1;
        if ((attr == SSI_INC_FILE) || (achBuf[0] != '/'))
        {
            pURI = pReq->getRealPath()->c_str();
            p1 =  pURI + pReq->getRealPath()->len();
            while ((p1 > pReq->getRealPath()->c_str()) && p1[-1] != '/')
                --p1;
        }
        else
        {
            pURI = pReq->getDocRoot()->c_str();
            p1 = pURI + pReq->getDocRoot()->len();
        }
        int prefix_len = p1 - pURI;
        memmove(&achBuf[prefix_len], achBuf, p - achBuf);
        memmove(achBuf, pURI, prefix_len);
        p += prefix_len;
    }
    *p = 0;
    p = achBuf;
    struct stat st;
    if (ls_fio_stat(achBuf, &st) == -1)
    {
        pSession->appendDynBody("[error: stat() failed!\n", 23);
        return 0;
    }
    if (pComponent->getType() == SSIComponent::SSI_FSize)
    {
        long long size = st.st_size;
        len = snprintf(achBuf, 1024, "%lld", size);
    }
    else    //SSIComponent::SSI_Flastmod
    {
        struct tm *tm;
        tm = localtime(&st.st_mtime);
        len = strftime(achBuf, 1024, pRuntime
                       ->getConfig()->getTimeFmt()->c_str(), tm);
    }
    pSession->appendDynBody(achBuf, len);
    return 0;
}


int SSIEngine::processSubReq(HttpSession *pSession, SubstItem *pItem)
{
    char achBuf[40960];
    char *p;
    int len;
    int attr;
    if (!pItem)
        return 0;
    SSIRuntime *pRuntime = pSession->getReq()->getSSIRuntime();
    attr = pItem->getSubType();
    p = achBuf;
    len = 40960;
    switch (attr)
    {
    case SSI_INC_FILE:
        {
            HttpReq *pReq = pSession->getReq();
            memmove(p, pReq->getURI(), pReq->getURILen());
            p = p + pReq->getURILen() - pReq->getPathInfoLen();
            while (p[-1] != '/')
                --p;
            *p = 0;
            len -= p - achBuf;
            break;
        }
    case SSI_EXEC_CGI:
        pRuntime->requireCGI();
        break;
    case SSI_EXEC_CMD:
        pRuntime->requireCmd();
        p += snprintf(achBuf, 40960, "%s",
                      pRuntime->getCurrentScript()->getPath());
        while (p[-1] != '/')
            --p;
        *p++ = '&';
        *p++ = ' ';
        *p++ = '-';
        *p++ = 'c';
        *p++ = ' ';
        len -= p - achBuf;
        // make the command looks like "/script/path/& command"
        // '&' tell cgid to execute it as shell command
        break;
    }
    RequestVars::appendSubst(pItem, pSession, p, len,
                             0, pRuntime->getRegexResult());
    if (attr == SSI_INC_FILE)
    {
        if (strstr(achBuf, "/../") != NULL)

            return 0;
    }
    else if (attr == SSI_EXEC_CMD)
    {

        if (pSession->execExtCmd(achBuf, p - achBuf) == 0)
            return -2;
        else
            return 0;
        //len = snprintf( achBuf, 40960, "'exec cmd' is not available, "
        //            "use 'include virutal' instead.\n" );
        //pSession->appendDynBody( achBuf, len );

        //return 0;
    }
    if ((achBuf[0] != '/') && (attr != SSI_EXEC_CMD))
    {
        if (achBuf[0] == 0)
        {
            len = snprintf(achBuf, 40960,
                           "[an error occurred while processing this directive]\n");
            pSession->appendDynBody(achBuf, len);
            return 0;
        }
        HttpReq *pReq = pSession->getReq();
        const char *pURI = pReq->getURI();
        const char *p1 = pURI + pReq->getURILen() - pReq->getPathInfoLen();
        while ((p1 > pURI) && p1[-1] != '/')
            --p1;
        int prefix_len = p1 - pURI;
        memmove(&achBuf[prefix_len], achBuf, p - achBuf);
        memmove(achBuf, pReq->getURI(), prefix_len);
        p += prefix_len;
    }
    if (achBuf[0] == '/')
    {
        pSession->getReq()->setLocation(achBuf, p - achBuf);
        pSession->changeHandler();
        pSession->continueWrite();
        return -2;
    }
    return 0;
}


int SSIEngine::processInclude(HttpSession *pSession,
                              SSIComponent *pComponent)
{
    SubstItem *pItem = (SubstItem *)pComponent->getFirstAttr();
    return processSubReq(pSession, pItem);
}


class SSIEnv : public IEnv
{
    HttpSession *m_pSession;


    SSIEnv(const SSIEnv &rhs);
    void operator=(const SSIEnv &rhs);
public:
    SSIEnv(HttpSession *pSession) : m_pSession(pSession)    {};
    ~SSIEnv()   {};
    int add(const char *name, const char *value)
    {   return IEnv::add(name, value);    }

    int add(const char *name, size_t nameLen,
            const char *value, size_t valLen);
    int add(const char *buf, size_t len);
    void clear()    { }
    int addVar(int var_id);
};


int SSIEnv::add(const char *name, size_t nameLen,
                const char *value, size_t valLen)
{
    char achBuf[40960];
    char *p = achBuf;
    if (!name)
        return 0;
    int len = HttpUtil::escapeHtml(name, name + nameLen, p, 40960);
    p += len;
    *p++ = '=';
    len = HttpUtil::escapeHtml(value, value + valLen, p, &achBuf[40960] - p);
    p += len;
    *p++ = '\n';
    m_pSession->appendDynBody(achBuf, p - achBuf);
    return 0;
}


int SSIEnv::add(const char *buf, size_t len)
{
    char achBuf[40960];
    int ret = HttpUtil::escapeHtml(buf, buf + len, achBuf, 40960);
    achBuf[ret] = '\n';
    m_pSession->appendDynBody(achBuf, ret + 1);
    return 0;
}


int SSIEnv::addVar(int var_id)
{
    char achBuf[4096];
    const char *pName;
    int nameLen;
    pName = RequestVars::getVarNameStr(var_id, nameLen);
    if (!pName)
        return 0;
    char *pValue = achBuf;
    memccpy(pValue, m_pSession->getReq()->getSSIRuntime()
            ->getConfig()->getTimeFmt()->c_str(), 0, 4096);
    int valLen = RequestVars::getReqVar(m_pSession, var_id, pValue, 4096);
    return add(pName, nameLen, pValue, valLen);
}


int SSIEngine::processPrintEnv(HttpSession *pSession)
{
    SSIEnv env(pSession);

    HttpCgiTool::buildEnv(&env, pSession);
    env.addVar(REF_DATE_GMT);
    env.addVar(REF_DATE_LOCAL);
    env.addVar(REF_DOCUMENT_NAME);
    env.addVar(REF_DOCUMENT_URI);
    env.addVar(REF_LAST_MODIFIED);
    env.addVar(REF_QS_UNESCAPED);
    return 0;
}


int SSIEngine::processSet(HttpSession *pSession, SSIComponent *pComponent)
{
    SubstItem *pItem = (SubstItem *)pComponent->getFirstAttr();
    const AutoStr2 *pVarName;
    char achBuf1[8192];
    char *p;
    int len;
    int attr;
    while (pItem)
    {

        attr = pItem->getSubType();
        if (attr == SSI_SET_VAR)
        {
            pVarName = pItem->getStr();
            pItem = (SubstItem *) pItem->next();
            if (!pItem)
                break;
            if (pItem->getSubType() != SSI_SET_VALUE)
                continue;
            p = achBuf1;
            len = 8192;
            len = RequestVars::appendSubst(pItem, pSession, p, len, 0,
                                           pSession->getReq()->getSSIRuntime()->getRegexResult(),
                                           pSession->getReq()->getSSIRuntime()
                                           ->getConfig()->getTimeFmt()->c_str());
            RequestVars::setEnv(pSession, pVarName->c_str(), pVarName->len(), achBuf1,
                                p - achBuf1);
        }

        pItem = (SubstItem *) pItem->next();
    }
    return 0;
}


int SSIEngine::appendLocation(HttpSession *pSession, const char *pLocation,
                              int len)
{
    char achBuf[40960];
    char *p = &achBuf[9];
    memcpy(achBuf, "<A HREF=\"", 9);
    memmove(p, pLocation, len);
    p += len;
    *p++ = '"';
    *p++ = '>';
    memmove(p, pLocation, len);
    p += len;
    memmove(p, "</A>", 4);
    p += 4;
    pSession->appendDynBody(achBuf, p - achBuf);
    return 0;
}


static int  shortCurcuit(ExprToken *&pTok)
{
    if (!pTok)
        return 0;
    pTok = pTok->next();
    int type = pTok->getType();
    switch (type)
    {
    case ExprToken::EXP_STRING:
    case ExprToken::EXP_FMT:
    case ExprToken::EXP_REGEX:
        break;
    case ExprToken::EXP_AND:
    case ExprToken::EXP_OR:
        shortCurcuit(pTok);
    //Fall through
    case ExprToken::EXP_NOT:
        shortCurcuit(pTok);
        break;
    case ExprToken::EXP_EQ:
    case ExprToken::EXP_NE:
    case ExprToken::EXP_LE:
    case ExprToken::EXP_LESS:
    case ExprToken::EXP_GE:
    case ExprToken::EXP_GREAT:
        pTok = pTok->next();
        if (pTok)
            pTok = pTok->next();
        break;
    }
    return 1;
}


static int compString(HttpSession *pSession, int type, ExprToken *&pTok)
{
    int     len;
    int     ret;
    char achBuf2[40960] = "";
    char achBuf1[40960] = "";
    char   *p1 = achBuf1;
    char   *p2 = achBuf2;
    if (pTok->getType() == ExprToken::EXP_STRING)
    {
        p1 = (char *)pTok->getStr()->c_str();
        len = pTok->getStr()->len();
    }
    else if (pTok->getType() == ExprToken::EXP_FMT)
    {
        p1 = achBuf1;
        len = 40960;
        RequestVars::buildString(pTok->getFormat(), pSession, p1, len, 0,
                                 pSession->getReq()->getSSIRuntime()->getRegexResult());
        p1 = achBuf1;
    }
    pTok = pTok->next();
    if (!pTok)
        return 0;
    if (pTok->getType() == ExprToken::EXP_REGEX)
    {
        ret = pSession->getReq()->getSSIRuntime()->execRegex(pTok->getRegex(), p1,
                len);
        if (ret == 0)
            ret = 10;
        if (ret == -1)
            ret = 0;
        if (type == ExprToken::EXP_NE)
            ret = !ret;
        pTok = pTok->next();
        return ret;
    }

    if (pTok->getType() == ExprToken::EXP_STRING)
        p2 = (char *)pTok->getStr()->c_str();
    else if (pTok->getType() == ExprToken::EXP_FMT)
    {
        p2 = achBuf2;
        len = 40960;
        RequestVars::buildString(pTok->getFormat(), pSession, p2, len, 0,
                                 pSession->getReq()->getSSIRuntime()->getRegexResult());
        p2 = achBuf2;
    }
    pTok = pTok->next();
    ret = strcmp(p1, p2);
    switch (type)
    {
    case ExprToken::EXP_EQ:
        return (ret == 0);
    case ExprToken::EXP_NE:
        return (ret != 0);
    case ExprToken::EXP_LE:
        return (ret <= 0);
    case ExprToken::EXP_LESS:
        return (ret < 0);
    case ExprToken::EXP_GE:
        return (ret >= 0);
    case ExprToken::EXP_GREAT:
        return (ret > 0);
    }
    return 0;
}


int SSIEngine::evalOperator(HttpSession *pSession, ExprToken *&pTok)
{
    char   *p1 = NULL;
    int     len;
    int     ret;
    if (!pTok)
        return 0;
    int type = pTok->getType();
    ExprToken *pCur = pTok;
    pTok = pTok->next();
    switch (type)
    {
    case ExprToken::EXP_STRING:
        return (pCur->getStr()->len() > 0);
    case ExprToken::EXP_FMT:
        {
            char achBuf1[40960];
            p1 = achBuf1;
            len = 40960;
            RequestVars::buildString(pCur->getFormat(), pSession, p1, len, 0,
                                     pSession->getReq()->getSSIRuntime()->getRegexResult());
            return len > 0;
        }
    case ExprToken::EXP_REGEX:
        return 0;
    case ExprToken::EXP_NOT:
        if (pTok)
            return !evalOperator(pSession, pTok);
        else
            return 1;
    default:
        break;
    }

    if ((type == ExprToken::EXP_AND) ||
        (type == ExprToken::EXP_OR))
    {
        ret = evalOperator(pSession, pTok);
        if (((ret) && (pTok->getType() == ExprToken::EXP_OR)) ||
            ((!ret) && (pTok->getType() == ExprToken::EXP_AND)))
        {
            if (pTok)
                shortCurcuit(pTok);
            return ret;
        }
        ret = evalOperator(pSession, pTok);
        return ret;
    }
    if (!pTok)
        return 0;
    return compString(pSession, type, pTok);
}


int SSIEngine::evalExpr(HttpSession *pSession, SubstItem *pItem)
{
    int ret = 0;
    if ((!pItem) || (pItem->getType() != REF_EXPR))
        return 0;
    Expression *pExpr = (Expression *)pItem->getAny();
    ExprToken *pTok = pExpr->begin();
    ret = evalOperator(pSession, pTok);
    return ret;
}


int SSIEngine::processIf(HttpSession *pSession, SSI_If *pComponent)
{
    SubstItem *pItem = (SubstItem *)pComponent->getFirstAttr();
    int ret = evalExpr(pSession, pItem);
    SSIBlock *pBlock;
    if (ret)
        pBlock = pComponent->getIfBlock();
    else
        pBlock = pComponent->getElseBlock();
    if (pBlock != NULL)
    {
        SSIScript *pScript = pSession->getReq()->getSSIRuntime()
                             ->getCurrentScript();
        pScript->setCurrentBlock(pBlock);
    }
    return 0;
}


int SSIEngine::executeComponent(HttpSession *pSession,
                                SSIComponent *pComponent)
{
    AutoBuf *pBuf;
    int ret;

    LS_DBG_H(pSession->getLogSession(), "SSI Process component: %d",
             pComponent->getType());

    switch (pComponent->getType())
    {
    case SSIComponent::SSI_String:
        pBuf = pComponent->getContentBuf();
        pSession->appendDynBody(pBuf->begin(), pBuf->size());
        break;
    case SSIComponent::SSI_Config:
        updateSSIConfig(pSession, pComponent, pSession->getReq()->getSSIRuntime());
        break;
    case SSIComponent::SSI_Echo:
        processEcho(pSession, pComponent);
        break;
    case SSIComponent::SSI_Exec:
        ret = processExec(pSession, pComponent);
        return ret;
        break;
    case SSIComponent::SSI_FSize:
    case SSIComponent::SSI_Flastmod:
        processFileAttr(pSession, pComponent);
        break;
    case SSIComponent::SSI_Include:
        ret = processInclude(pSession, pComponent);
        return ret;
        break;
    case SSIComponent::SSI_Printenv:
        processPrintEnv(pSession);
        break;
    case SSIComponent::SSI_Set:
        processSet(pSession, pComponent);
        break;
    case SSIComponent::SSI_If:
    case SSIComponent::SSI_Elif:
        processIf(pSession, (SSI_If *)pComponent);
        break;
        //SSI_Else,
        //SSI_Elif,
        //SSI_Endif,

    }
    return 0;
}


int SSIEngine::endExecute(HttpSession *pSession)
{
    SSIRuntime *pRuntime = pSession->getReq()->getSSIRuntime();
    if (pRuntime)
        delete pRuntime;
    pSession->getReq()->setSSIRuntime(NULL);
    return 0;
}


int SSIEngine::resumeExecute(HttpSession *pSession)
{
    SSIRuntime *pRuntime = pSession->getReq()->getSSIRuntime();
    int ret = 0;
    if (!pRuntime)
        return LS_FAIL;
    SSIComponent *pComponent;
    while (!pRuntime->done())
    {
        SSIScript *pScript = pRuntime->getCurrentScript();
        pRuntime->clearFlag();
        pComponent = pScript->nextComponent();
        if (!pComponent)
        {
            pRuntime->pop();
            if (!pRuntime->done())
                pSession->getReq()->restorePathInfo();
            continue;
        }
        ret = executeComponent(pSession, pComponent);
        if (ret == -2)
            return 0;
    }
    endExecute(pSession);
    return pSession->endResponse(1);

}
