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
#include "httpcontext.h"

#include <extensions/extworker.h>
#include <http/contextlist.h>
#include <http/handlerfactory.h>
#include <http/handlertype.h>
#include <http/htauth.h>
#include <http/httplog.h>
#include <http/httpmime.h>
#include <http/phpconfig.h>
#include <http/rewriteengine.h>
#include <http/rewriterule.h>
#include <http/rewriterulelist.h>
#include <http/statusurlmap.h>
#include <http/urimatch.h>
#include <http/userdir.h>
#include <log4cxx/logger.h>
#include <lsiapi/lsiapihooks.h>
#include <lsiapi/modulemanager.h>
#include <lsr/ls_strtool.h>
#include <main/configctx.h>
#include <util/accesscontrol.h>
#include <util/pool.h>
#include <util/stringlist.h>
#include <util/stringtool.h>
#include <util/xmlnode.h>

#include <ctype.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

CtxInt HttpContext::s_defaultInternal =
{
    NULL, NULL, NULL, NULL, NULL, NULL,
    NULL, NULL, NULL, NULL, NULL, NULL,
    NULL, NULL, NULL, GSockAddr()
} ;


HttpContext::HttpContext()
    : m_iConfigBits(0)
    , m_pURIMatch(NULL)
    , m_pMatchList(NULL)
    , m_pFilesMatchStr(NULL)
    , m_pHandler(NULL)
    , m_pInternal(NULL)
    , m_redirectCode(-1)
    , m_iSetUidMode(ENABLE_SCRIPT)
    , m_iRewriteEtag(0)
    , m_iConfigBits2(BIT2_URI_CACHEABLE)
    , m_iFeatures(BIT_F_ALLOW_BROWSE | BIT_F_INCLUDES | BIT_F_INCLUDES_NOEXEC)
//    , m_iFilesMatchCtx( 0 )
    , m_lHTALastMod(0)
    , m_pRewriteBase(NULL)
    , m_pRewriteRules(NULL)
    , m_pParent(NULL)
{
    m_pInternal = &s_defaultInternal;
}


HttpContext::~HttpContext()
{
    if (m_pMatchList)
        delete m_pMatchList;

    if (m_pFilesMatchStr)
        delete m_pFilesMatchStr;
    if (m_pURIMatch)
        delete m_pURIMatch;
    if (m_pRewriteBase)
        delete m_pRewriteBase;
    releaseHTAConf();

    if ((m_iConfigBits & BIT_CTXINT))
        Pool::deallocate(m_pInternal, sizeof(CtxInt));
    if ((m_iConfigBits & BIT_MODULECONFIG))
        delete m_pInternal->m_pModuleConfig;
    if ((m_iConfigBits & BIT_SESSIONHOOKS))
        delete m_pInternal->m_pSessionHooks;
}


void HttpContext::releaseHTAConf()
{
    if ((m_pRewriteRules) && (m_iConfigBits & BIT_REWRITE_RULE))
        delete m_pRewriteRules;
    if ((m_iConfigBits & BIT_CTXINT))
    {
        if ((m_iConfigBits & BIT_DIRINDEX) && (m_pInternal->m_pIndexList))
            delete m_pInternal->m_pIndexList;
        if ((m_iConfigBits & BIT_PHPCONFIG) && (m_pInternal->m_pPHPConfig))
            delete m_pInternal->m_pPHPConfig;
        if ((m_iConfigBits & BIT_ERROR_DOC) && (m_pInternal->m_pCustomErrUrls))
            delete m_pInternal->m_pCustomErrUrls;
        if ((m_iConfigBits & BIT_AUTH_REQ) && (m_pInternal->m_pRequired))
            delete m_pInternal->m_pRequired;
        if ((m_iConfigBits & BIT_FILES_MATCH) && (m_pInternal->m_pFilesMatchList))
            delete m_pInternal->m_pFilesMatchList;
        if ((m_iConfigBits & BIT_EXTRA_HEADER) && (m_pInternal->m_pExtraHeader))
            delete m_pInternal->m_pExtraHeader;
        releaseHTAuth();
        releaseAccessControl();
        releaseMIME();
        releaseDefaultCharset();

        memset(m_pInternal, 0 , sizeof(CtxInt));
        m_iConfigBits = BIT_CTXINT;
    }
    else
        clearConfigBit();
}


int HttpContext::set(const char *pURI, const char *pLocation,
                     const HttpHandler *pHandler, bool browse, int regex)
{
    if (pURI == NULL)
        return EINVAL;
    if (strncasecmp(pURI, "exp:", 4) == 0)
    {
        regex = 1;
        pURI += 4;
        while (isspace(*pURI))
            ++pURI;
        if (!*pURI)
            return EINVAL;
    }
    if (regex)
    {
        int ret = setURIMatch(pURI, pLocation);
        if (ret)
            return ret;
    }
    int isDir = 0;
    if ((pLocation) && (*pLocation))
    {
        int len = strlen(pLocation);
        m_sLocation.prealloc(len + 15);
        strcpy(m_sLocation.buf(), pLocation);
        m_sLocation.setLen(len);
        if (*(pLocation + len - 1) == '/')
            isDir = 1;
//        if ( type < HandlerType::HT_FASTCGI )
//        {
//            // if context URI end with '/', then the m_sLocation must be end with '/'
//            if  (( '/' == *( getURI() + getURILen() - 1 ))&&
//                ( m_sLocation.at( m_sLocation.len() - 1 ) != '/' ))
//                m_sLocation += "/";
//        }
    }
    int len = strlen(pURI);
    m_sContextURI.prealloc(len + 8);
    strcpy(m_sContextURI.buf(), pURI);
    if ((isDir && !regex) && (*(pURI + len - 1) != '/'))
    {
        *(m_sContextURI.buf() + len++) = '/';
        *(m_sContextURI.buf() + len) = '\0';
    }
    m_sContextURI.setLen(len);
    m_pHandler = pHandler;
    allowBrowse(browse);
    return 0;
}


int HttpContext::setFilesMatch(const char *pURI, int regex)
{
    if (!pURI)
        return LS_FAIL;
    setConfigBit2(BIT2_IS_FILESMATCH_CTX, 1);
    if (regex)
    {
        //m_iFilesMatchCtx = 1;
        return setURIMatch(pURI, NULL);
    }
    else
    {
        if (m_pFilesMatchStr)
        {
            //assert( m_iFilesMatchCtx );
            delete m_pFilesMatchStr;
        }
        m_pFilesMatchStr = StringTool::parseMatchPattern(pURI);
        //m_iFilesMatchCtx = 1;
        return (m_pFilesMatchStr == NULL);
    }

}


int HttpContext::matchFiles(const char *pFile, int len) const
{
    //if ( !m_iFilesMatchCtx )
    //    return 0;
    if (m_pURIMatch)
        return (m_pURIMatch->match(pFile, len) > 0) ;
    else if (m_pFilesMatchStr)
    {
        return (StringTool::strMatch(pFile, pFile + len,
                                     m_pFilesMatchStr->begin(),
                                     m_pFilesMatchStr->end(), 1) == 0);
    }
    return 0;
}


const HttpContext *HttpContext::matchFilesContext(const char *pFile,
        int len) const
{
    //if ( !m_pInternal ||!m_pInternal->m_pFilesMatchList)
    if (!m_pInternal->m_pFilesMatchList)
        return NULL;
    ContextList::iterator iter;
    for (iter = m_pInternal->m_pFilesMatchList->begin();
         iter != m_pInternal->m_pFilesMatchList->end();
         ++iter)
    {
        if ((*iter)->matchFiles(pFile, len) == 1)
            return *iter;
    }
    return NULL;
}


int HttpContext::addFilesMatchContext(HttpContext *pContext)
{
    if (!(m_iConfigBits & BIT_FILES_MATCH))
    {
        if (allocateInternal())
            return LS_FAIL;
        ContextList *pList = new ContextList();
        if (!pList)
            return LS_FAIL;
        m_pInternal->m_pFilesMatchList = pList;
        m_iConfigBits |= BIT_FILES_MATCH;
    }
    if (m_pInternal->m_pFilesMatchList->add(pContext, 1) == -1)
        return LS_FAIL;
    pContext->setParent(this);
    return 0;
}


int HttpContext::setURIMatch(const char *pRegex, const char *pSubst)
{
    if (m_pURIMatch)
        delete m_pURIMatch;
    m_pURIMatch = new URIMatch();
    if (!m_pURIMatch)
        return ENOMEM;
    m_pURIMatch->set(pRegex, pSubst);
    if (pRegex)
        m_sContextURI.setStr(pRegex);
    if (pSubst)
        m_sLocation.setStr(pSubst);
    return 0;
}


void HttpContext::setRoot(const char *pRoot)
{
    m_sLocation.setStr(pRoot, strlen(pRoot));
}


int HttpContext::allocateInternal()
{
    if (!(m_iConfigBits & BIT_CTXINT))
    {
        m_pInternal = (CtxInt *)Pool::allocate(sizeof(CtxInt));
        if (!m_pInternal)
            return LS_FAIL;
        memset(m_pInternal, 0, sizeof(CtxInt));
        m_iConfigBits |= BIT_CTXINT;
    }
    return 0;
}


void HttpContext::releaseMIME()
{
    if ((m_iConfigBits & BIT_MIME) && m_pInternal->m_pMIME)
    {
        delete m_pInternal->m_pMIME;
        m_iConfigBits &= ~BIT_MIME;
        m_pInternal->m_pMIME = NULL;
    }
}


int HttpContext::initMIME()
{
    if (!(m_iConfigBits & BIT_MIME))
    {
        if (allocateInternal())
            return LS_FAIL;
        HttpMime *pMIME = new HttpMime();
        if (!pMIME)
            return LS_FAIL;
        m_pInternal->m_pMIME = pMIME;
        m_iConfigBits |= BIT_MIME;
    }
    return 0;
}


static AutoStr2 *s_pDefaultCharset = NULL;

void HttpContext::releaseDefaultCharset()
{
    if ((m_iConfigBits & BIT_DEF_CHARSET) && m_pInternal->m_pDefaultCharset
        && (m_pInternal->m_pDefaultCharset != s_pDefaultCharset))
    {
        delete m_pInternal->m_pDefaultCharset;
        m_iConfigBits &= ~BIT_DEF_CHARSET;
    }
    if (m_pInternal)
        m_pInternal->m_pDefaultCharset = NULL;
}


void HttpContext::setDefaultCharset(const char *pCharset)
{
    releaseDefaultCharset();
    if (pCharset)
    {
        if (allocateInternal())
            return ;
        char achBuf[256];
        ls_snprintf(achBuf, 255, "; charset=%s", pCharset);
        achBuf[255] = 0;
        m_pInternal->m_pDefaultCharset = new AutoStr2(achBuf);
    }
    m_iConfigBits |= BIT_DEF_CHARSET;
}


void HttpContext::setDefaultCharsetOn()
{
    releaseDefaultCharset();
    if (!s_pDefaultCharset)
    {
        s_pDefaultCharset = new AutoStr2("; charset=ISO-8859-1");
        if (!s_pDefaultCharset)
            return;
    }
    if (allocateInternal())
        return ;
    m_pInternal->m_pDefaultCharset = s_pDefaultCharset;
    m_iConfigBits |= BIT_DEF_CHARSET;
}


void HttpContext::setHTAuth(HTAuth *pHTAuth)
{
    releaseHTAuth();
    if (allocateInternal())
        return ;
    m_pInternal->m_pHTAuth = pHTAuth;
    m_iConfigBits |= BIT_AUTH;
}


int HttpContext::setExtraHeaders(const char *pLogId, const char *pHeaders,
                                 int len)
{
    if (allocateInternal())
        return LS_FAIL;
    if (!(m_iConfigBits & BIT_EXTRA_HEADER))
    {
        m_pInternal->m_pExtraHeader = new AutoBuf(512);
        if (!m_pInternal->m_pExtraHeader)
        {
            LS_WARN("[%s] Failed to allocate buffer for extra headers", pLogId);
            return LS_FAIL;
        }
    }
    m_iConfigBits |= BIT_EXTRA_HEADER;
    if (strcasecmp(pHeaders, "none") == 0)
        return 0;

    const char *pEnd = pHeaders + len;
    const char *pLineBegin, *pLineEnd;
    pLineBegin = pHeaders;
    while ((pLineEnd = StringTool::getLine(pLineBegin, pEnd)))
    {
        const char *pCurEnd = pLineEnd;
        StringTool::strTrim(pLineBegin, pCurEnd);
        if (pLineBegin < pCurEnd)
        {
            const char *pHeaderNameEnd = strpbrk(pLineBegin, ": ");
            if ((pHeaderNameEnd) && (pHeaderNameEnd > pLineBegin) &&
                (pHeaderNameEnd + 1 < pCurEnd))
            {
                m_pInternal->m_pExtraHeader->append(
                    pLineBegin, pHeaderNameEnd - pLineBegin);
                m_pInternal->m_pExtraHeader->appendUnsafe(':');
                m_pInternal->m_pExtraHeader->append(pHeaderNameEnd + 1,
                                                    pCurEnd - pHeaderNameEnd - 1);
                m_pInternal->m_pExtraHeader->append("\r\n", 2);
            }
            else
            {
                char *p = (char *)pCurEnd;
                *p = '0';
                LS_WARN("[%s] Invalid Header: %s", pLogId, pLineBegin);
                *p = '\n';
            }
        }

        pLineBegin = pLineEnd;
        while (isspace(*pLineBegin))
            ++pLineBegin;
    }
    return 0;
}


void HttpContext::releaseHTAuth()
{
    if ((m_iConfigBits & BIT_AUTH) && (m_pInternal->m_pHTAuth))
    {
        delete m_pInternal->m_pHTAuth;
        m_pInternal->m_pHTAuth = NULL;
    }
}


int HttpContext::setAuthRequired(const char *pRequired)
{
    if (!(m_iConfigBits & BIT_AUTH_REQ) ||
        (!m_pInternal) || !m_pInternal->m_pRequired)
    {
        if (allocateInternal())
            return LS_FAIL;
        if (!m_pInternal->m_pRequired)
        {
            m_pInternal->m_pRequired = new AuthRequired();
            if (!m_pInternal->m_pRequired)
                return LS_FAIL;
        }
        m_iConfigBits |= BIT_AUTH_REQ;

    }
    return m_pInternal->m_pRequired->parse(pRequired);
}


int HttpContext::setAccessControl(AccessControl *pAccess)
{
    releaseAccessControl();
    if (allocateInternal())
        return LS_FAIL;
    m_pInternal->m_pAccessCtrl = pAccess;
    m_iConfigBits |= BIT_ACCESS;
    return 0;
}


void HttpContext::releaseAccessControl()
{
    if ((m_iConfigBits & BIT_ACCESS) && m_pInternal->m_pAccessCtrl)
    {
        delete m_pInternal->m_pAccessCtrl;
        m_pInternal->m_pAccessCtrl = NULL;
    }
}


int HttpContext::addAccessRule(const char *pRule, int allow)
{
    if (!(m_iConfigBits & BIT_ACCESS) || !m_pInternal->m_pAccessCtrl)
    {
        AccessControl *pCtrl = new AccessControl();
        if ((!pCtrl) || (setAccessControl(pCtrl)))
            return LS_FAIL;
    }
    m_pInternal->m_pAccessCtrl->addList(pRule, allow);
    return 0;
}


int HttpContext::setAuthorizer(const HttpHandler *pHandler)
{
    if (allocateInternal())
        return LS_FAIL;
    m_pInternal->m_pAuthorizer = pHandler;
    m_iConfigBits |= BIT_AUTHORIZER;
    return 0;
}


static RewriteRuleList *getValidRewriteRules(
    const HttpContext *pContext)
{
    while (pContext)
    {
        if (pContext->getRewriteRules())
            return pContext->getRewriteRules();
        if (!(pContext->rewriteEnabled() & REWRITE_INHERIT))
            break;
        pContext = pContext->getParent();
    }
    return NULL;
}


void HttpContext::inherit(const HttpContext *pRootContext)
{
    if (!m_pParent)
        return;
    if (!m_pHandler)
        m_pHandler = m_pParent->m_pHandler;
    if (!(m_iConfigBits & BIT_CTXINT))
        m_pInternal = m_pParent->m_pInternal;
    else
    {
        if (!(m_iConfigBits & BIT_AUTH))
            m_pInternal->m_pHTAuth = m_pParent->getHTAuth();
        if (!(m_iConfigBits & BIT_AUTH_REQ))
            m_pInternal->m_pRequired = m_pParent->m_pInternal->m_pRequired;
        if (!(m_iConfigBits & BIT_ACCESS))
            m_pInternal->m_pAccessCtrl = m_pParent->getAccessControl();
        if (!(m_iConfigBits & BIT_DEF_CHARSET))
            m_pInternal->m_pDefaultCharset = m_pParent->m_pInternal->m_pDefaultCharset;
        if (!(m_iConfigBits & BIT_MIME))
        {
            if (!(m_iConfigBits2 & BIT2_IS_FILESMATCH_CTX))
                m_pInternal->m_pMIME = m_pParent->m_pInternal->m_pMIME;
        }
        else
        {
            if (m_pInternal->m_pMIME)
            {
                //DumpSuffixMimeAssoc( this, "Before inheit Glboal", m_pInternal->m_pMIME, "php" );
                m_pInternal->m_pMIME->inherit(HttpMime::getMime(), 1);
                //DumpSuffixMimeAssoc( this, "After inheit Glboal", m_pInternal->m_pMIME, "php" );
                if (!(m_iConfigBits2 & BIT2_IS_FILESMATCH_CTX)
                    && m_pParent->m_pInternal->m_pMIME)
                {
                    m_pInternal->m_pMIME->inherit(m_pParent->m_pInternal->m_pMIME, 0);
                    m_pInternal->m_pMIME->inheritSuffix(m_pParent->m_pInternal->m_pMIME, 1);
                }
                //DumpSuffixMimeAssoc( pParent, pParent->getURI(), pParent->m_pInternal->m_pMIME, "php" );
                //DumpSuffixMimeAssoc( pParent, pParent->getURI(), pParent->m_pInternal->m_pMIME, "php5" );
                //DumpSuffixMimeAssoc( this, "After inheit parent", m_pInternal->m_pMIME, "php" );
                m_pInternal->m_pMIME->inheritSuffix(HttpMime::getMime(), 0);
                //DumpSuffixMimeAssoc( this, "After inheitSuffix Global", m_pInternal->m_pMIME, "php" );
                m_pInternal->m_pMIME->updateSuffixMimeHandler();
                //DumpSuffixMimeAssoc( this, "After updateSuffixMimeHandler", m_pInternal->m_pMIME, "php" );
            }
        }
        if (!(m_iConfigBits & BIT_FORCE_TYPE))
        {
            if (!(m_iConfigBits2 & BIT2_IS_FILESMATCH_CTX))
                m_pInternal->m_pForceType = m_pParent->m_pInternal->m_pForceType;
        }
        if (!(m_iConfigBits & BIT_AUTHORIZER))
            m_pInternal->m_pAuthorizer = m_pParent->m_pInternal->m_pAuthorizer;
        if (!(m_iConfigBits & BIT_DIRINDEX))
            m_pInternal->m_pIndexList = m_pParent->m_pInternal->m_pIndexList;
        if (!(m_iConfigBits & BIT_PHPCONFIG))
            m_pInternal->m_pPHPConfig = m_pParent->m_pInternal->m_pPHPConfig;
        else
        {
            m_pInternal->m_pPHPConfig->merge(m_pParent->m_pInternal->m_pPHPConfig);
            m_pInternal->m_pPHPConfig->buildLsapiEnv();
        }
        if (!(m_iConfigBits & BIT_ERROR_DOC))
            m_pInternal->m_pCustomErrUrls = m_pParent->m_pInternal->m_pCustomErrUrls;
        else
        {
            m_pInternal->m_pCustomErrUrls->inherit(
                m_pParent->m_pInternal->m_pCustomErrUrls);
        }
        if (m_iConfigBits & BIT_FILES_MATCH)
        {
            ContextList::iterator iter;
            for (iter = m_pInternal->m_pFilesMatchList->begin();
                 iter != m_pInternal->m_pFilesMatchList->end(); ++iter)
                (*iter)->inherit(pRootContext);
            m_pInternal->m_pFilesMatchList->merge(
                m_pParent->m_pInternal->m_pFilesMatchList, 0);
        }
        else
            m_pInternal->m_pFilesMatchList = m_pParent->m_pInternal->m_pFilesMatchList;

        if (!(m_iConfigBits & BIT_EXTRA_HEADER))
            m_pInternal->m_pExtraHeader = m_pParent->m_pInternal->m_pExtraHeader;

        if (!(m_iConfigBits & BIT_MODULECONFIG))
            m_pInternal->m_pModuleConfig = m_pParent->m_pInternal->m_pModuleConfig;

        if (!(m_iConfigBits & BIT_SESSIONHOOKS))
            m_pInternal->m_pSessionHooks = m_pParent->m_pInternal->m_pSessionHooks;

    }

    if (!(m_iConfigBits & BIT_ENABLE_EXPIRES))
        m_expires.enable(m_pParent->getExpires().isEnabled());
    if (!(m_iConfigBits & BIT_EXPIRES_DEFAULT))
    {
        m_expires.setBase(m_pParent->getExpires().getBase());
        m_expires.setAge(m_pParent->getExpires().getAge());
    }

    if (!(m_iConfigBits & BIT_SETUID))
    {
        setConfigBit(BIT_ALLOW_SETUID,
                     m_pParent->m_iConfigBits & BIT_ALLOW_SETUID);
    }
    if (m_pParent->m_iSetUidMode & CHANG_UID_ONLY)
        m_iSetUidMode |= CHANG_UID_ONLY;

    if (!(m_iConfigBits & BIT_SUEXEC))
    {
        m_iSetUidMode = (m_iSetUidMode & ~UID_MASK) |
                        (m_pParent->m_iSetUidMode & UID_MASK);
    }
    if (!(m_iConfigBits & BIT_CHROOT))
    {
        m_iSetUidMode = (m_iSetUidMode & ~CHROOT_MASK) |
                        (m_pParent->m_iSetUidMode & CHROOT_MASK);
    }
    if (!(m_iConfigBits & BIT_GEO_IP))
    {
        m_iSetUidMode = (m_iSetUidMode & ~CTX_GEOIP_ON) |
                        (m_pParent->m_iSetUidMode & CTX_GEOIP_ON);
    }
    if (!(m_iConfigBits2 & BIT2_IPTOLOC))
    {
        m_iFeatures = (m_iFeatures & ~BIT_F_IPTOLOC_ON) |
                        (m_pParent->m_iFeatures & BIT_F_IPTOLOC_ON);
    }
    if (!(m_iConfigBits & BIT_ENABLE_SCRIPT))
    {
        m_iSetUidMode = (m_iSetUidMode & ~ENABLE_SCRIPT) |
                        (m_pParent->m_iSetUidMode & ENABLE_SCRIPT);
    }

    if (!(m_iConfigBits & BIT_REWRITE_ENGINE))
    {
        m_iRewriteEtag = (m_iRewriteEtag & ~REWRITE_MASK) |
                         ((m_pParent->m_iRewriteEtag | REWRITE_INHERIT) & REWRITE_MASK);
    }
    if (!(m_iConfigBits2 & BIT2_FILES_ETAG))
    {
        m_iRewriteEtag = (m_iRewriteEtag & ~ETAG_MASK) |
                         (m_pParent->m_iRewriteEtag  & ETAG_MASK);
    }
    else
    {
        if (m_iRewriteEtag & ETAG_MOD_ALL)
        {
            int tag = m_pParent->m_iRewriteEtag & ETAG_ALL;
            int mask = (m_iRewriteEtag & ETAG_MOD_ALL) >> 3;
            int val = (m_iRewriteEtag & ETAG_ALL) & mask;
            m_iRewriteEtag = (m_iRewriteEtag & ~ETAG_MASK)
                             | ((tag & ~mask) | val) | (m_iRewriteEtag & ETAG_MOD_ALL);
        }
    }



    if (m_iConfigBits & BIT_REWRITE_INHERIT)
    {
        RewriteRuleList *pList =
            getValidRewriteRules(m_pParent);
        if (!(m_iConfigBits & BIT_REWRITE_RULE))
            m_pRewriteRules = pList;
    }

    if (!(m_iConfigBits & BIT_SATISFY))
        setConfigBit(BIT_SATISFY_ANY, m_pParent->isSatisfyAny());

    if (!(m_iConfigBits & BIT_AUTOINDEX))
        setFeaturesBit(BIT_F_AUTOINDEX_ON, m_pParent->isAutoIndexOn());

    if (m_pMatchList)
    {
        ContextList::iterator iter;
        for (iter = m_pMatchList->begin(); iter != m_pMatchList->end(); ++iter)
            (*iter)->inherit(pRootContext);
    }
}


void HttpContext::matchListInherit(const HttpContext *pRootContext) const
{
    if (m_pMatchList)
    {
        ContextList::iterator iter;
        for (iter = m_pMatchList->begin(); iter != m_pMatchList->end(); ++iter)
            (*iter)->inherit(pRootContext);
    }
}


int HttpContext::addMatchContext(HttpContext *pContext)
{
    //assert( !m_iFilesMatchCtx );
    if (!m_pMatchList)
    {
        m_pMatchList = new ContextList();
        if (!m_pMatchList)
            return LS_FAIL;
    }
    if (m_pMatchList->add(pContext, 1) == -1)
        return LS_FAIL;
    pContext->setParent(this);
    return 0;
}


const HttpContext *HttpContext::match(const char *pURI, int iURILen,
                                      char *pBuf, int &bufLen) const
{
    //if ( !m_pMatchList || m_iFilesMatchCtx)
    if (!m_pMatchList)
        return NULL;
    ContextList::iterator iter;
    for (iter = m_pMatchList->begin(); iter != m_pMatchList->end(); ++iter)
    {
        if ((*iter)->getURIMatch()->match(pURI, iURILen, pBuf, bufLen) == 0)
            return *iter;
    }
    return NULL;
}


const HttpContext *HttpContext::findMatchContext(const char *pURI,
        int useLocation) const
{
    //if ( !m_pMatchList || m_iFilesMatchCtx)
    if (!m_pMatchList)
        return NULL;
    ContextList::iterator iter;
    for (iter = m_pMatchList->begin(); iter != m_pMatchList->end(); ++iter)
    {
        const char *p;
        if (!useLocation)
            p = (*iter)->getURI();
        else
            p = (*iter)->getLocation();
        if (p && (strcmp(p, pURI) == 0))
            return *iter;
    }
    return NULL;

}


const MimeSetting *HttpContext::addMIME(const char *pMime,
                                        const char *pSuffix)
{
    if (initMIME())
        return NULL;
    char achBuf[1024];
    snprintf(achBuf, 1024, "%s", pMime);

    MimeSetting *pSetting = (MimeSetting *)lookupMimeSetting(achBuf, 1);
    snprintf(achBuf, 1024, "%s", pSuffix);
    if (pSetting)
        m_pInternal->m_pMIME->addUpdateSuffixMimeMap(pSetting, achBuf, 1);
    return pSetting;

}


int HttpContext::setExpiresByType(const char *pValue)
{
    if (initMIME())
        return LS_FAIL;
    return m_pInternal->m_pMIME->setExpiresByType(pValue,
            HttpMime::getMime(),
            m_sLocation.c_str());
}


int HttpContext::setCompressByType(const char *pValue)
{
    if (initMIME())
        return LS_FAIL;
    return m_pInternal->m_pMIME->setCompressibleByType(pValue,
            HttpMime::getMime(),
            m_sLocation.c_str());
}


const MimeSetting *HttpContext::lookupMimeBySuffix(const char *pSuffix)
const
{
    const MimeSetting *pSetting = NULL;
    HttpMime *pMIME = m_pInternal->m_pMIME;
    const HttpContext *pCtx = this;
    while (pCtx && !pSetting)
    {
        pMIME = pCtx->m_pInternal->m_pMIME;
        if (pMIME && (pCtx->m_iConfigBits & BIT_MIME))
        {
            pSetting = pMIME->getFileMimeBySuffix(pSuffix);
            if (pSetting)
                break;
        }
        pCtx = pCtx->m_pParent;
    }
    if (!pSetting)
        pSetting = HttpMime::getMime()->getFileMimeBySuffix(pSuffix);
    return pSetting;
}


const MimeSetting *HttpContext::lookupMimeSetting(char *pValue) const
{
    const MimeSetting *pSetting = NULL;
    HttpMime *pMIME = m_pInternal->m_pMIME;
    const HttpContext *pCtx = this;
    StringTool::strLower(pValue, pValue);
    while (pCtx && !pSetting)
    {
        pMIME = pCtx->m_pInternal->m_pMIME;
        if (pMIME)
        {
            pSetting = pMIME->getMIMESettingLowerCase(pValue);
            if (pSetting)
                break;
        }
        pCtx = pCtx->m_pParent;
    }
    if (!pSetting)
        pSetting = HttpMime::getMime()->getMIMESettingLowerCase(pValue);
    return pSetting;
}


const MimeSetting *HttpContext::lookupMimeSetting(char *pValue,
        int forceAddMIME)
{
    const MimeSetting *pSetting = lookupMimeSetting(pValue);
    if (!pSetting && forceAddMIME)
    {
        char achTmp[] = "";
        const char *pReason;
//             HttpMime::getMime()->addUpdateMIME( achTmp, pValue, pReason, 1 );
//             pSetting = HttpMime::getMime()->getMIMESettingLowerCase( pValue );
        if (!m_pInternal->m_pMIME)
            initMIME();
        pSetting = m_pInternal->m_pMIME->addUpdateMIME(achTmp, pValue, pReason, 1);
    }
    return pSetting;
}


int HttpContext::forceAddMime(char *pMime)
{
    if (initMIME())
        return -1;
    const MimeSetting *pSetting = m_pInternal->m_pMIME
                                  ->getMIMESettingLowerCase(pMime);
    if (!pSetting)
    {
        const MimeSetting *pProto = lookupMimeSetting(pMime, 1);
        char achTmp[] = "";
        const char *pReason;
        pSetting = m_pInternal->m_pMIME->addUpdateMIME(achTmp, pMime, pReason, 1);
        if (pSetting && pProto)
            ((MimeSetting *)pSetting)->inherit(pProto, 0);
    }
    return 0;
}



int HttpContext::setForceType(char *pValue, const char *pLogId)
{
    const MimeSetting *pSetting = NULL;
    if (allocateInternal())
        return LS_FAIL;
    if (strcasecmp(pValue, "none") != 0)
    {
        if (m_pInternal->m_pMIME)
            pSetting = m_pInternal->m_pMIME->getMimeSetting(pValue);
        if (!pSetting)
            pSetting = HttpMime::getMime()->getMimeSetting(pValue);
        if (!pSetting)
        {
            LS_WARN("[%s] can't set 'Forced Type', undefined MIME Type %s",
                    pLogId, pValue);
            return LS_FAIL;
        }
    }
    m_pInternal->m_pForceType = pSetting;
    setConfigBit(BIT_FORCE_TYPE, 1);
    return 0;
}


const MimeSetting *HttpContext::determineMime(const char *pSuffix,
        char *pForcedType) const
{
    const MimeSetting *pMimeType = NULL;
    if (pForcedType)
    {
        if (m_pInternal->m_pMIME)
            pMimeType = m_pInternal->m_pMIME->getMimeSetting(pForcedType);
        if (!pMimeType)
            pMimeType = HttpMime::getMime()->getMimeSetting(pForcedType);
        if (pMimeType)
            return pMimeType;
    }
    if (m_pInternal->m_pForceType)
        return m_pInternal->m_pForceType;
    if (pSuffix)
    {
        char achSuffix[256];
        int len = 256;
        StringTool::strLower(pSuffix, achSuffix, len);
        if (m_pInternal->m_pMIME)
        {
            pMimeType = m_pInternal->m_pMIME->getFileMimeBySuffix(achSuffix);
            if (pMimeType)
                return pMimeType;
        }
        pMimeType = HttpMime::getMime()->getFileMimeBySuffix(achSuffix);
        if (pMimeType)
            return pMimeType;
    }
    if (m_pInternal->m_pMIME)
    {
        pMimeType = m_pInternal->m_pMIME->getDefault();
        if (pMimeType)
            return pMimeType;
    }
    pMimeType = HttpMime::getMime()->getDefault();
    return pMimeType;
}


void HttpContext::setRewriteBase(const char *p)
{
    m_pRewriteBase = new AutoStr2(p);
}


void HttpContext::clearDirIndexes()
{
    if ((m_iConfigBits & BIT_DIRINDEX) && (m_pInternal->m_pIndexList))
        delete m_pInternal->m_pIndexList;
    if (m_pInternal)
        m_pInternal->m_pIndexList = NULL;
    m_iConfigBits &= ~BIT_DIRINDEX;
}


void HttpContext::addDirIndexes(const char *pList)
{
    if (!(m_iConfigBits & BIT_DIRINDEX))
    {
        m_iConfigBits |= BIT_DIRINDEX;
        if (allocateInternal())
            return ;
    }
    if (strcmp(pList, "-") == 0)
        return;
    if (!m_pInternal->m_pIndexList)
    {
        m_pInternal->m_pIndexList = new StringList();
        if (!m_pInternal->m_pIndexList)
            return;
    }
    char *p1 = strdup(pList);
    m_pInternal->m_pIndexList->split(p1, strlen(p1) + p1, ", ");
    free(p1);
}


int  HttpContext::setCustomErrUrls(const char *pStatusCode,
                                   const char *url)
{
    int statusCode = atoi(pStatusCode);
    if (!(m_iConfigBits & BIT_ERROR_DOC))
    {
        if (allocateInternal())
            return LS_FAIL;
        m_pInternal->m_pCustomErrUrls = new StatusUrlMap();
        if (!m_pInternal->m_pCustomErrUrls)
            return LS_FAIL;
        m_iConfigBits |= BIT_ERROR_DOC;
    }
    return m_pInternal->m_pCustomErrUrls->setStatusUrlMap(statusCode, url);
}


const AutoStr2 *HttpContext::getErrDocUrl(int statusCode) const
{
    return m_pInternal->m_pCustomErrUrls ?
           m_pInternal->m_pCustomErrUrls->getUrl(statusCode) : NULL;
}


void HttpContext::setPHPConfig(PHPConfig *pConfig)
{
    if (!allocateInternal())
    {
        m_pInternal->m_pPHPConfig = pConfig;
        m_iConfigBits |= BIT_PHPCONFIG;
    }
}


int HttpContext::initExternalSessionHooks()
{
    if (!(m_iConfigBits & BIT_SESSIONHOOKS))
    {
        if (allocateInternal())
            return LS_FAIL;
        HttpSessionHooks *pSessionHooks = new HttpSessionHooks();
        if (!pSessionHooks)
            return LS_FAIL;
        pSessionHooks->inherit(NULL, 1);  //inherit from global level

        m_pInternal->m_pSessionHooks = pSessionHooks;
        m_iConfigBits |= BIT_SESSIONHOOKS;
    }
    return 0;
}


int HttpContext::setModuleConfig(ModuleConfig  *pModuleConfig,
                                 int isOwnData)
{
    if (isOwnData && !(m_iConfigBits & BIT_MODULECONFIG))
    {
        if (allocateInternal())
            return LS_FAIL;

        m_iConfigBits |= BIT_MODULECONFIG;
    }

    m_pInternal->m_pModuleConfig = pModuleConfig;
    return 0;
}


int HttpContext::setOneModuleConfig(int moduel_id,
                                    lsi_module_config_t  *module_config)
{
    if (!(m_iConfigBits & BIT_MODULECONFIG))
    {
        ModuleConfig *pOldConfig = m_pInternal->m_pModuleConfig;
        if (allocateInternal())
            return LS_FAIL;

        ModuleConfig *pConfig = new ModuleConfig;
        if (!pConfig)
            return LS_FAIL;

        pConfig->init(ModuleManager::getInstance().getModuleCount());
        pConfig->inherit(pOldConfig);
        m_pInternal->m_pModuleConfig = pConfig;
        m_iConfigBits |= BIT_MODULECONFIG;
    }

    m_pInternal->m_pModuleConfig->copy(moduel_id, module_config);
    return 0;
}


void HttpContext::getAAAData(struct AAAData &data) const
{
    memmove(&data, &m_pInternal->m_pHTAuth, sizeof(AAAData));
}


void HttpContext::setWebSockAddr(GSockAddr &gsockAddr)
{
    if (!allocateInternal())
    {
        m_pInternal->m_GSockAddr = gsockAddr;
        m_iConfigBits2 |= BIT2_WEBSOCKADDR;
    }
}


int HttpContext::configAccess(const XmlNode *pContextNode)
{
    AccessControl *pAccess = NULL;

    if (AccessControl::isAvailable(pContextNode))
    {
        pAccess = new AccessControl();
        ConfigCtx::getCurConfigCtx()->configSecurity(pAccess, pContextNode);
        setAccessControl(pAccess);
    }

    return 0;
}


void HttpContext::configAutoIndex(const XmlNode *pContextNode)
{
    if (pContextNode->getChildValue("autoIndex"))
        setAutoIndex(ConfigCtx::getCurConfigCtx()->getLongValue(pContextNode,
                     "autoIndex", 0, 1, 0));
}


int HttpContext::configDirIndex(const XmlNode *pContextNode)
{
    clearDirIndexes();
    const char *pValue = pContextNode->getChildValue("indexFiles");

    if (pValue)
        addDirIndexes(pValue);

    return 0;
}


int HttpContext::configErrorPages(const XmlNode *pNode)
{
    int add = 0;
    const XmlNodeList *pList = pNode->getChildren("errorPage");

    if (pList)
    {
        XmlNodeList::const_iterator iter;

        for (iter = pList->begin(); iter != pList->end(); ++iter)
        {
            const XmlNode *pNode = *iter;
            const char *pCode = pNode->getChildValue("errCode", 1);
            const char *pUrl = pNode->getChildValue("url");

            if (setCustomErrUrls(pCode, pUrl) != 0)
            {
                LS_ERROR(ConfigCtx::getCurConfigCtx(),
                         "failed to set up custom error page %s - %s!",
                         pCode, pUrl);
            }
            else
                ++add ;
        }
    }

    return (add == 0);
}


int HttpContext::configRewriteRule(const RewriteMapList *pMapList,
                                   char *pRule)
{
    RewriteRuleList *pRuleList;

    if (!pRule)
        return 0;
    AutoStr rule(pRule);
    pRule = rule.buf();

    pRuleList = new RewriteRuleList();

    if (pRuleList)
    {
        RewriteRule::setLogger(NULL, TmpLogId::getLogId());
        if (RewriteEngine::parseRules(pRule, pRuleList,
                                      pMapList) == 0)
            setRewriteRules(pRuleList);
        else
            delete pRuleList;
    }

    return 0;
}


int HttpContext::configMime(const XmlNode *pContextNode)
{
    const char *pValue = pContextNode->getChildValue("addMIMEType");

    if (pValue)
    {
        StringList list;
        list.split(pValue, strlen(pValue) + pValue, ",");
        StringList::iterator iter;
        for (iter = list.begin(); iter != list.end(); ++iter)
        {
            char *pSuffixes = (char *)
                              strpbrk((*iter)->c_str(), " \t");
            if (pSuffixes)
                *pSuffixes++ = 0;
            addMIME((*iter)->c_str(), pSuffixes);
        }
    }

    pValue = pContextNode->getChildValue("forceType");

    if (pValue)
        setForceType((char *) pValue, TmpLogId::getLogId());

    pValue = pContextNode->getChildValue("defaultType");

    if (pValue)
    {
        initMIME();
        getMIME()->initDefault((char *) pValue);
    }

    return 0;
}


int HttpContext::configExtAuthorizer(const XmlNode *pContextNode)
{
    const HttpHandler *pAuth;
    const char *pHandler = pContextNode->getChildValue("authorizer");

    if (pHandler)
        pAuth = HandlerFactory::getHandler("fcgiauth", pHandler);
    else
    {
        const XmlNode *pNode = pContextNode->getChild("extAuthorizer");

        if (!pNode)
            return 0;

        //pAuth = getHandler( pVHost, pNode );
        pAuth = HandlerFactory::getHandler(pNode);
    }

    if (!pAuth)
        return 1;

    if (((ExtWorker *) pAuth)->getRole() != EXTAPP_AUTHORIZER)
    {
        LS_ERROR(ConfigCtx::getCurConfigCtx(),
                 "External Application [%s] is not a Authorizer role.",
                 pAuth->getName());
        return 1;
    }

    setAuthorizer(pAuth);
    return 0;
}


int HttpContext::config(const RewriteMapList *pMapList,
                        const XmlNode *pContextNode,
                        int type)
{
    const char *pValue;
    configAutoIndex(pContextNode);
    configDirIndex(pContextNode);

    if (type == HandlerType::HT_CGI)
    {
        int val = ConfigCtx::getCurConfigCtx()->getLongValue(pContextNode,
                  "allowSetUID", 0, 1, -1);

        if (val != -1)
        {
            setConfigBit(BIT_SETUID, 1);
            setConfigBit(BIT_ALLOW_SETUID, val);
        }
    }
    configAccess(pContextNode);
    configExtAuthorizer(pContextNode);

    getExpires().config(pContextNode, NULL, this);
    pValue = pContextNode->getChildValue("expiresByType");

    if (pValue && (*pValue))
        setExpiresByType(pValue);

    pValue = pContextNode->getChildValue("extraHeaders");

    if (pValue && (*pValue))
        setExtraHeaders(TmpLogId::getLogId(), pValue, (int) strlen(pValue));

    pValue = pContextNode->getChildValue("addDefaultCharset");

    if (pValue)
    {
        if (strcasecmp(pValue, "on") == 0)
        {
            pValue = pContextNode->getChildValue("defaultCharsetCustomized");

            if (!pValue)
                setDefaultCharsetOn();
            else
                setDefaultCharset(pValue);
        }
        else
            setDefaultCharset(NULL);
    }

    configMime(pContextNode);
    const XmlNode *pNode = pContextNode->getChild("rewrite");

    if (pNode)
    {
        enableRewrite(ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "enable",
                      0, 1, 0));
        pValue = pNode->getChildValue("inherit");

        if ((pValue) && (strcasestr(pValue, "1")))
            setRewriteInherit(1);

        pValue = pNode->getChildValue("base");

        if (pValue)
        {
            if (*pValue != '/')
            {
                LS_ERROR(ConfigCtx::getCurConfigCtx(), "Invalid rewrite base: '%s'",
                         pValue);
            }
            else
                setRewriteBase(pValue);
        }

        pValue = pNode->getChildValue("rules");
        if (pValue)
            configRewriteRule(pMapList, (char *) pValue);

    }

    pNode = pContextNode->getChild("customErrorPages", 1);

    if (pNode)
    {
        ConfigCtx currentCtx("errorpages");
        configErrorPages(pNode);
    }

    return 0;
}

