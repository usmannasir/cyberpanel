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
#include "requestvars.h"

#include <http/httpheader.h>
#include <http/httplog.h>
#include <http/httpmethod.h>
#include <http/httpserverversion.h>
#include <http/httpsession.h>
#include <http/httpstatuscode.h>
#include <http/httpver.h>
#include <http/httpvhost.h>
#include <http/iptogeo.h>
#include <http/iptoloc.h>
#include <log4cxx/logger.h>
#include <lsr/ls_strtool.h>
#include <ssi/ssiruntime.h>
#include <ssi/ssiscript.h>
#include <sslpp/sslcert.h>
#include <util/autostr.h>
#include <util/datetime.h>
#include <util/httputil.h>
#include <util/stringtool.h>

#include <ctype.h>
#include <grp.h>
#include <pwd.h>
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>


SubstItem::SubstItem()
    : m_type(0)
    , m_subType(0)
{
    m_value.m_pStr = NULL;
}


SubstItem::~SubstItem()
{
    if (m_value.m_pStr)
    {
        if ((m_type == REF_STRING) || (m_type == REF_ENV))
            delete m_value.m_pStr;
        if (m_type == REF_FORMAT_STR)
            delete(SubstFormat *)m_value.m_pAny;
    }
}


SubstItem::SubstItem(const SubstItem &rhs)
    : LinkedObj(), m_type(rhs.m_type)
{
    if (rhs.m_value.m_pStr)
    {
        switch (rhs.m_type)
        {
        case REF_STRING:
        case REF_ENV:
            m_value.m_pStr = new AutoStr2(*rhs.m_value.m_pStr);
            break;
        case REF_FORMAT_STR:
            m_value.m_pAny = new SubstFormat(*rhs.getFormatStr());
        default:
            m_value.m_index = rhs.m_value.m_index;
            break;
        }
    }
    else
        m_value.m_index = 0;

}


AutoStr2 *SubstItem::setStr(const char *pStr, int len)
{
    m_value.m_pStr = new AutoStr2(pStr, len);
    if (!m_value.m_pStr)
        LS_ERR_NO_MEM("new AutoStr2()");

    return m_value.m_pStr;
}


void SubstItem::parseString(const char *&pBegin, const char *pEnd,
                            const char *stopChars)
{
    char *pCur;
    char *pBufEnd;
    char achBuf[40960];
    pCur = achBuf;
    pBufEnd = &achBuf[40959];
    setType(REF_STRING);
    while (pBegin < pEnd)
    {
        char ch = *pBegin;
        if (strchr(stopChars, ch))
            break;
        else if (ch == '\\')
        {
            if (++pBegin >= pEnd)
                break;
            ch = *pBegin;
        }
        if (pCur < pBufEnd)
            *pCur++ = ch;
        ++pBegin;
    }
    *pCur = 0;
    setStr(achBuf, pCur - achBuf);
}


static const char *findEndOfVarName(const char *pBegin, const char *pEnd)
{
    if (*pBegin == '{')
        return StringTool::findCloseBracket(pBegin + 1, pEnd, '{', '}');
    while (pBegin < pEnd)
    {
        char ch = *pBegin;
        if (!(isalpha(ch) || isdigit(ch) || (ch == '_') ||
              (ch == '-') || (ch == ':')))
            break;
        ++pBegin;
    }
    return pBegin;
}


int SubstItem::parseServerVar(const char *pCurLine,
                              const char *&pFormatStr,
                              const char *pEnd, int isSSI)
{
    const char *pName = pFormatStr;
    const char *pClose = findEndOfVarName(pName, pEnd);
    int len;
    if (*pName == '{')
    {
        if (pClose == pEnd)
        {
            HttpLog::parse_error(pCurLine,  "missing '}'");
            return LS_FAIL;
        }
        else
        {
            pFormatStr = pClose + 1;
            ++pName;
        }
    }
    else
        pFormatStr = pClose;

    if (pClose == pName)
        return -2;
    if ((strncasecmp(pName, "LA-U:", 5) == 0) ||
        (strncasecmp(pName, "LA-F:", 5) == 0))
        pName += 5;

    if (!isSSI && (pName + 3 > pClose))
    {
        HttpLog::parse_error(pCurLine,  "missing variable name");
        return LS_FAIL;
    }
    if ((strncasecmp(pName, "HTTP_", 5) == 0) ||
        (strncasecmp(pName, "HTTP:", 5) == 0))
    {
        pName += 5;
        len = pClose - pName;
        const char *pHeaderStr = NULL;
        int HeaderLen;
        int type = RequestVars::parseHttpHeader(pName, len, pHeaderStr, HeaderLen);
        if (type != -1)
        {
            setType(type);
            if (type == REF_HTTP_HEADER)
                setStr(pHeaderStr, HeaderLen);
        }
        else
        {
            HttpLog::parse_error(pCurLine,  "unknown HTTP request header");
            return LS_FAIL;
        }
    }
    else if (strncasecmp(pName, "ENV:", 4) == 0)
    {
        setType(REF_ENV);
        if (setStr(pName + 4, pClose - pName - 4) == NULL)
            return LS_FAIL;
    }
    else
    {
        int len = pClose - pName;
        int type = RequestVars::parseBuiltIn(pName, len, isSSI);
        if (type != -1)
            setType(type);
        else if (isSSI)
        {
            setType(REF_ENV);
            if (setStr(pName, pClose - pName) == NULL)
                return LS_FAIL;
        }
        else
        {
            HttpLog::parse_error(pCurLine,  "unknown server variable");
            return LS_FAIL;
        }
    }
    return 0;
}


SubstFormat::SubstFormat()
//    : m_type( 0 )
{
}


SubstFormat::~SubstFormat()
{
    release_objects();
}


SubstFormat::SubstFormat(const SubstFormat &rhs)
    : TLinkList<SubstItem>(rhs)
{

}


int SubstFormat::equal(const SubstFormat &rhs) const
{
    const SubstItem *pItem = begin();
    const SubstItem *pRhsItem = rhs.begin();
    while (pItem)
    {
        if (!pItem->equal(*pRhsItem))
            return 0;
        pItem = (const SubstItem *)pItem->next();
        pRhsItem = (const SubstItem *)pRhsItem->next();
    }
    return 1;
}


int SubstFormat::parse(const char *pCurLine, const char *pFormatStr,
                       const char *pEnd, int isSSI, char varChar)
{
    while ((pFormatStr < pEnd) && (isspace(*pFormatStr)))
        ++pFormatStr;
    int err = 0;
    char achVarChar[2];
    LinkedObj *pLast = head();
    SubstItem *pItem;
    achVarChar[0] = varChar;
    achVarChar[1] = 0;
    while (pFormatStr < pEnd)
    {
        pItem = new SubstItem();
        if (!pItem)
        {
            LS_ERR_NO_MEM("new SubstItem()");
            return LS_FAIL;
        }

        if (*pFormatStr == varChar)
        {
            if (pFormatStr + 1 == pEnd)
            {
                HttpLog::parse_error(pCurLine ,  "Line ended with '$'");
                err = 1;
            }
            if (isdigit(*(pFormatStr + 1)))
            {
                pItem->setType(REF_RULE_SUBSTR);
                pItem->setIndex(*(pFormatStr + 1) - '0');
                pFormatStr += 2;
            }
            else
            {
                ++pFormatStr;
                if (pItem->parseServerVar(pCurLine, pFormatStr, pEnd, isSSI))
                    err = 1;

            }
        }
        else
            pItem->parseString(pFormatStr, pEnd, achVarChar);
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


RequestVars::RequestVars()
{
}


RequestVars::~RequestVars()
{
}


static const char *ServerVarNames[REF_EXT_COUNT] =
{
    "REMOTE_ADDR",
    "REMOTE_PORT",
    "REMOTE_HOST",
    "REMOTE_USER",
    "REMOTE_IDENT",
    "REQUEST_METHOD",
    "QUERY_STRING",
    "AUTH_TYPE",
    "PATH_INFO",
    "SCRIPT_FILENAME",
    "REQUEST_FILENAME",
    "REQUEST_URI",
    "DOCUMENT_ROOT",
    "SERVER_ADMIN",
    "SERVER_NAME",
    "SERVER_ADDR",
    "SERVER_PORT",
    "SERVER_PROTOCOL",
    "SERVER_SOFTWARE",
    "API_VERSION",
    "THE_REQUEST",
    "IS_SUBREQ",
    "TIME",
    "TIME_YEAR",
    "TIME_MON",
    "TIME_DAY",
    "TIME_HOUR",
    "TIME_MIN",
    "TIME_SEC",
    "TIME_WDAY",
    "SCRIPT_NAME",
    "CURRENT_URI",
    "REQUEST_BASENAME",
    "SCRIPT_UID",
    "SCRIPT_GID",
    "SCRIPT_USERNAME",
    "SCRIPT_GROUPNAME",
    "SCRIPT_MODE",
    "SCRIPT_BASENAME",
    "SCRIPT_URI",
    "ORG_REQ_URI",
    "ORG_QUERY_STRING",
    "HTTPS",

    "DUMMY",
    "PID",
    "STATUS_CODE",
    "STRFTIME",
    "REQ_TIME_SEC",
    "URL_PATH",
    "CONN_STATE",
    "BYTES_IN",
    "BYTES_OUT",
    "RESP_BYTES",
    "VH_NAME",
    "COOKIE_VAL",

    "DATE_GMT",
    "DATE_LOCAL",
    "DOCUMENT_NAME",
    "DOCUMENT_URI",
    "LAST_MODIFIED",
    "QUERY_STRING_UNESCAPED",
    "REQ_TIME_MS",

};


static int ServerVarNameLen[REF_EXT_COUNT] =
{
    11, 11, 11, 11, 12, 14, 12, 9, 9, 15, 16, 11, 13, 12,
    11, 11, 11, 15, 15, 11, 11, 9, 4, 9, 8, 8, 9, 8, 8, 9, 11, 11,
    16, 10, 10, 15, 16, 11, 15, 10, 11, 16, 5,
    5, 3, 11, 8, 12, 8, 10, 8, 9, 10,
    7, 10, 8, 10, 13, 12, 13, 22, 11
};


const char *RequestVars::getVarNameStr(int var_id, int &len)
{
    var_id -= REF_BEGIN;
    if ((var_id < 0) || (var_id >= REF_EXT_COUNT))
        return NULL;
    len = ServerVarNameLen[ var_id ];
    return ServerVarNames[ var_id ];
}


int RequestVars::parseBuiltIn(const char *pVar, int len, int ext)
{
    int end = (ext) ? REF_EXT_COUNT : REF_COUNT;
    for (int i = 0; i < end; ++i)
    {
        if ((len == ServerVarNameLen[i]) &&
            (strncasecmp(pVar, ServerVarNames[i], ServerVarNameLen[i]) == 0))
            return REF_REMOTE_ADDR + i;
    }
    return LS_FAIL;
}


static char s_sForward[] = "forwarded";
static char s_sProxyConn[] = "proxy-connection";


int RequestVars::parseHttpHeader(const char *pName, int len,
                                 const char *&pHeaderName, int &headerLen)
{
    int ret = -1;
    if (len <= 0)
        return ret;
    if (len == 10 && strncasecmp(pName, "USER_AGENT", 10) == 0)
        ret = HttpHeader::H_USERAGENT;
    else if (len == 4 && strncasecmp(pName, "HOST", 4) == 0)
        ret = HttpHeader::H_HOST;
    else if (len == 6 && strncasecmp(pName, "ACCEPT", 6) == 0)
        ret = HttpHeader::H_ACCEPT;
    else if (len == 7 && strncasecmp(pName, "REFERER", 7) == 0)
        ret = HttpHeader::H_REFERER;
    else if (len == 6 && strncasecmp(pName, "COOKIE", 6) == 0)
        ret = HttpHeader::H_COOKIE;
    else if (len == 9 && strncasecmp(pName, "FORWARDED", 9) == 0)
    {
        ret = REF_HTTP_HEADER;
        pHeaderName = s_sForward;
        headerLen = 9;
    }
    else if (len == 16 && strncasecmp(pName, "PROXY_CONNECTION", 16) == 0)
    {
        ret = REF_HTTP_HEADER;
        pHeaderName = s_sProxyConn;
        headerLen   = 16;
    }
    else
    {
        int idx = HttpHeader::getIndex(pName);
        if ((idx < HttpHeader::H_HEADER_END) &&
            (len == HttpHeader::getHeaderStringLen(idx)))
            ret = idx;
        else
        {
            ret = REF_HTTP_HEADER;
            pHeaderName = pName;
            headerLen = len;
        }
    }
    return ret;
}


int RequestVars::getReqVar(HttpSession *pSession, int type, char *&pValue,
                           int bufLen)
{
    HttpReq *pReq = pSession->getReq();
    int i;
    char *p;
    if (type < REF_STRING)
    {
        pValue = (char *)pReq->getHeader(type);
        if (*pValue)
            return pReq->getHeaderLen(type);
        else
            return 0;
    }
    switch (type)
    {
    case REF_REMOTE_HOST:
    //TODO: use remote addr for now
    case REF_REMOTE_ADDR:
        pValue = (char *)pSession->getPeerAddrString();
        return pSession->getPeerAddrStrLen();
    case REF_REMOTE_PORT:
        return snprintf(pValue, bufLen, "%hu", pSession->getRemotePort());
    case REF_REMOTE_USER:
        pValue = (char *)pReq->getAuthUser();
        if (pValue)
            return strlen(pValue);
        return 0;
    case REF_REMOTE_IDENT:
        //do not support;
        return 0;
    case REF_REQ_METHOD:
        i = pReq->getMethod();
        strcpy(pValue, HttpMethod::get(i));
        return HttpMethod::getLen(i);
    case REF_QUERY_STRING:
        pValue = (char *)pReq->getQueryString();
        return pReq->getQueryStringLen();
    case REF_AUTH_TYPE:
        //TODO: hard code for now
        strncpy(pValue, "Basic", 6);
        return 5;
    case REF_REQUST_FN:
    case REF_SCRIPTFILENAME:
    case REF_SCRIPT_BASENAME:
    case REF_REQ_BASENAME:
        {
            const AutoStr2 *psTemp = pReq->getRealPath();
            if (psTemp)
            {
                if ((type == REF_SCRIPT_BASENAME) ||
                    (type == REF_REQ_BASENAME))
                {
                    const char *pEnd = psTemp->c_str() + psTemp->len();
                    pValue = (char *)pEnd;
                    while (pValue[-1] != '/')
                        --pValue;
                    return pEnd - pValue;
                }
                pValue = (char *)psTemp->c_str();
                return psTemp->len();
            }
            else
                return 0;
        }
    case REF_SCRIPT_UID:
    case REF_SCRIPT_GID:
    case REF_SCRIPT_USERNAME:
    case REF_SCRIPT_GRPNAME:
    case REF_SCRIPT_MODE:
        {
            const AutoStr2 *psTemp = pReq->getRealPath();
            if (psTemp)
            {
                struct stat &st = pReq->getFileStat();
                if (type == REF_SCRIPT_UID)
                    return snprintf(pValue, bufLen, "%d", st.st_uid);
                else if (type == REF_SCRIPT_GID)
                    return snprintf(pValue, bufLen, "%d", st.st_gid);
                else if (type == REF_SCRIPT_MODE)
                    return snprintf(pValue, bufLen, "%o", st.st_mode);
                else if (type == REF_SCRIPT_USERNAME)
                {
                    struct passwd *pw = getpwuid(st.st_uid);
                    if (pw)
                        return snprintf(pValue, bufLen, "%s", pw->pw_name);
                }
                else
                {
                    struct group *gr = getgrgid(st.st_gid);
                    if (gr)
                        return snprintf(pValue, bufLen, "%s", gr->gr_name);
                }
            }
            return 0;
        }
    case REF_PATH_INFO:
        pValue = (char *)pReq->getPathInfo();
        return pReq->getPathInfoLen();

    case REF_SCRIPT_NAME:
        pValue = (char *)pReq->getURI();
        return pReq->getScriptNameLen();
    case REF_SCRIPT_URI:
        p = pValue;
        if (pSession->isSSL())
        {
            strcpy(p, "https://");
            p += 8;
        }
        else
        {
            strcpy(p, "http://");
            p += 7;
        }
        i = pReq->getHeaderLen(HttpHeader::H_HOST);
        memmove(p, pReq->getHeader(HttpHeader::H_HOST),
                i);
        p += i;

        i = pReq->getOrgURILen();
        memmove(p, pReq->getOrgURI(), i);
        p += i;
        return p - pValue;

    case REF_ORG_REQ_URI:
        pValue = (char *)pReq->getOrgReqURL();
        return pReq->getOrgReqURILen();
    case REF_DOCUMENT_URI:
        return pReq->getDecodedOrgReqURI(pValue);
    case REF_REQ_URI:
        pValue = (char *)pReq->getOrgReqURL();
        return pReq->getOrgReqURLLen();

    case REF_DOC_ROOT:
        pValue = (char *)pReq->getDocRoot()->c_str();
        return pReq->getDocRoot()->len() - 1;

    case REF_SERVER_ADMIN:
        if (pReq->getVHost())
        {
            const AutoStr2 *pEmail = pReq->getVHost()->getAdminEmails();
            pValue = (char *)pEmail->c_str();
            return pEmail->len();
        }
        return 0;
    case REF_VH_CNAME:
        if (pReq->getVHost())
        {
            pValue = (char *)pReq->getVHost()->getVhName(i);
            return i;
        }
        return 0;

    case REF_SERVER_NAME:
        pValue = (char *)pReq->getHostStr();
        return pReq->getHostStrLen();
    case REF_SERVER_ADDR:
        pValue = (char *)pReq->getLocalAddrStr()->c_str();
        return pReq->getLocalAddrStr()->len();
    case REF_SERVER_PORT:
        pValue = (char *)pReq->getPortStr().c_str();
        return pReq->getPortStr().len();
    case REF_SERVER_PROTO:
        i = pReq->getVersion();
        pValue = (char *)HttpVer::getVersionString(i);
        return HttpVer::getVersionStringLen(i);
    case REF_SERVER_SOFT:
        pValue = (char *)HttpServerVersion::getVersion();
        return HttpServerVersion::getVersionLen();
    case REF_REQ_LINE:
        pValue = (char *)pReq->getOrgReqLine();
        return pReq->getOrgReqLineLen();
    case REF_IS_SUBREQ:
        strcpy(pValue, "false");
        return 5;

    case REF_RESP_BYTES:
        i = StringTool::offsetToStr(pValue, bufLen,
                                    pSession->getResp()->getBodySent());
        return i;
    //case REF_COOKIE_VAL
    //case REF_STRFTIME        155
    //case REF_CONN_STATE:
    case REF_REQ_TIME_MS:
        {
            struct timeval tv;
            gettimeofday(&tv, NULL);
            DateTime::s_curTime = tv.tv_sec;
            DateTime::s_curTimeUs = tv.tv_usec;

            long lReqTime = (DateTime::s_curTime - pSession->getReqTime()) * 1000000 +
                            (DateTime::s_curTimeUs - pSession->getReqTimeUs());
            i = snprintf(pValue, bufLen, "%ld", lReqTime);
            return i;
        }
    case REF_REQ_TIME_SEC:
        i = snprintf(pValue, bufLen, "%ld",
                     (DateTime::s_curTime - pSession->getReqTime()));
        return i;
    case REF_DUMMY:
        return 0;
    case REF_PID:
        i = snprintf(pValue, bufLen, "%d", getpid());
        return i;
    case REF_STATUS_CODE:
        memmove(pValue, HttpStatusCode::getInstance().getCodeString(
                    pReq->getStatusCode()) + 1,
                3);
        pValue[3] = 0;
        return 3;

    case REF_CUR_URI:
        pValue = (char *)pReq->getURI();
        i = pReq->getURILen();
        return i;
    case REF_BYTES_IN:
        i = StringTool::offsetToStr(pValue, bufLen, pSession->getBytesRecv());
        return i;
    case REF_BYTES_OUT:
        i = StringTool::offsetToStr(pValue, bufLen, pSession->getBytesSent());
        return i;

    case REF_HTTPS:
        i = snprintf(pValue, bufLen, "%s", pSession->isSSL() ? "on" : "off");
        return i;

    case REF_DATE_GMT:
    case REF_DATE_LOCAL:
    case REF_LAST_MODIFIED:
        {
            time_t mtime = DateTime::s_curTime;
            struct tm *tm;
            if (type == REF_LAST_MODIFIED)
            {
                if (pReq->getSSIRuntime() && pReq->getSSIRuntime()->getCurrentScript())
                    mtime = pReq->getSSIRuntime()->getCurrentScript()->getLastMod();
                else
                    mtime = pReq->getFileStat().st_mtime;
            }
            if (type == REF_DATE_GMT)
                tm = gmtime(&mtime);
            else
                tm = localtime(&mtime);
            char fmt[101];
            memccpy(fmt, pValue, 0, 100);
            fmt[100] = 0;
            i = strftime(pValue, bufLen, fmt, tm);
            return i;
        }
    case REF_DOCUMENT_NAME:
        {
            const AutoStr2 *psTemp = pReq->getRealPath();
            if (psTemp)
            {
                pValue = (char *)psTemp->c_str() + psTemp->len();
                while (*(pValue - 1) != '/')
                    --pValue;
                return psTemp->c_str() + psTemp->len() - pValue;
            }
            else
                return 0;
        }

    case REF_QS_UNESCAPED:
        {
            int qsLen = pReq->getQueryStringLen();
            const char *pQS = pReq->getQueryString();
            if (qsLen > 0)
                qsLen = HttpUtil::unescape(pQS, qsLen, pValue, bufLen);
            return qsLen;
        }
    case REF_RESP_CONTENT_TYPE:
        i = 0;
        pValue = (char *)pSession->getResp()->getContentTypeHeader(i);
        return i;
    case REF_RESP_CONTENT_LENGTH:
        {
            off_t l = pSession->getResp()->getContentLen();
            if (l <= 0)
                l = 0;
            i = StringTool::offsetToStr(pValue, bufLen, l);
            return i;
        }
    case REF_RESP_BODY:
        return 0;
    default:
        if (type >= REF_RESP_HEADER_BEGIN)
        {
            i = 0;
            pValue = (char *)pSession->getResp()->getRespHeaders().getHeader(
                         (HttpRespHeaders::INDEX)(type - REF_RESP_HEADER_BEGIN), &i);
            return i;
        }
        if (type >= REF_TIME)
        {
            time_t t = time(NULL);
            struct tm *tm = localtime(&t);
            switch (type)
            {
            case REF_TIME:
                i = snprintf(pValue, bufLen,
                             "%04d%02d%02d%02d%02d%02d", tm->tm_year + 1900,
                             tm->tm_mon + 1, tm->tm_mday,
                             tm->tm_hour, tm->tm_min, tm->tm_sec);
                break;
            case REF_TIME_YEAR:
                i = snprintf(pValue, bufLen, "%04d", tm->tm_year + 1900);
                break;
            case REF_TIME_MON:
                i = snprintf(pValue, bufLen, "%02d", tm->tm_mon + 1);
                break;
            case REF_TIME_DAY:
                i = snprintf(pValue, bufLen, "%02d", tm->tm_mday);
                break;
            case REF_TIME_HOUR:
                i = snprintf(pValue, bufLen, "%02d", tm->tm_hour);
                break;
            case REF_TIME_MIN:
                i = snprintf(pValue, bufLen, "%02d", tm->tm_min);
                break;
            case REF_TIME_SEC:
                i = snprintf(pValue, bufLen, "%02d", tm->tm_sec);
                break;
            case REF_TIME_WDAY:
                i = snprintf(pValue, bufLen, "%d", tm->tm_wday);
                break;
            default:
                return 0;
            }
            return i;
        }
        return 0;
    }
    return 0;

}


//Only for types from LSI_VAR_SSL_VERSION to LSI_VAR_PATH_TRANSLATED which are defined in ls.h
int RequestVars::getReqVar2(HttpSession *pSession, int type, char *&pValue,
                            int bufLen)
{
    HttpReq *pReq = pSession->getReq();
    int ret = 0;

    if (type >= LSI_VAR_SSL_VERSION && type <= LSI_VAR_SSL_CLIENT_CERT)
    {
        if (!pSession->isSSL())
            return 0;

        SslConnection *pSSL = pSession->getSSL();
        if (type == LSI_VAR_SSL_VERSION)
        {
            pValue = (char *)pSSL->getVersion();
            ret = strlen(pValue);
            return ret;
        }
        else if (type == LSI_VAR_SSL_SESSION_ID)
        {
            SSL_SESSION *pSession = pSSL->getSession();
            if (pSession)
            {
                int idLen = SslConnection::getSessionIdLen(pSession);
                ret = idLen * 2;
                if (ret > bufLen)
                    ret = bufLen;
                StringTool::hexEncode((char *)SslConnection::getSessionId(pSession),
                                      ret / 2, pValue);
            }
            return ret;
        }
        else if (type == LSI_VAR_SSL_CLIENT_CERT)
        {
            X509 *pClientCert = pSSL->getPeerCertificate();
            if (pClientCert)
                ret = SslCert::PEMWriteCert(pClientCert, pValue, bufLen);

            return ret;
        }
        else
        {
            const SSL_CIPHER *pCipher = pSSL->getCurrentCipher();
            if (pCipher)
            {
                if (type == LSI_VAR_SSL_CIPHER)
                {
                    pValue = (char *)pSSL->getCipherName();
                    ret = strlen(pValue);
                }
                else
                {
                    int algkeysize;
                    int keysize = SslConnection::getCipherBits(pCipher, &algkeysize);
                    if (type == LSI_VAR_SSL_CIPHER_USEKEYSIZE)
                        ret = ls_snprintf(pValue, 20, "%d", keysize);
                    else //LSI_VAR_SSL_CIPHER_ALGKEYSIZE
                        ret = ls_snprintf(pValue, 20, "%d", algkeysize);
                }
            }
            return ret;
        }
    }
    else if (type == LSI_VAR_GEOIP_ADDR)
    {
        ret = pSession->getPeerAddrStrLen();
        pValue = (char *)pSession->getPeerAddrString();
        return ret;
    }
    else if (type == LSI_VAR_PATH_TRANSLATED)
    {
        int n = pReq->getPathInfoLen();
        if (n > 0)
            ret =  pReq->translatePath(pReq->getPathInfo(), n, pValue, bufLen);
        return ret;
    }
    else
        return 0;
}


const char *RequestVars::getUnknownHeader(HttpReq *pReq, const char *pName,
        int nameLen, int &headerLen)
{
    int i;
    int n = pReq->getUnknownHeaderCount();
    for (i = 0; i < n; ++i)
    {
        const char *pKey;
        const char *pVal;
        int keyLen;
        int valLen;
        pKey = pReq->getUnknownHeaderByIndex(i, keyLen, pVal, valLen);
        if (pKey)
        {
            if ((keyLen == nameLen) && (strncasecmp(pKey, pName, keyLen) == 0))
            {
                headerLen = valLen;
                return pVal;
            }
        }
    }
    return NULL;
}


const char *RequestVars::getEnv(HttpSession *pSession, const char *pKey,
                                int keyLen, int &valLen)
{

    if ((strncmp(pKey, "GEOI", 4) == 0)
        || (strncmp(pKey, "GEO:", 4) == 0))
    {
        const char *pValue;
        GeoInfo *pInfo = pSession->getClientInfo()->getGeoInfo();
        valLen = 0;
        if (pInfo)
        {
            pValue = pInfo->getGeoEnv(pKey);
            if (pValue)
            {
                valLen = strlen(pValue);
                return pValue;
            }
        }
    }
#ifdef USE_IP2LOCATION
    else if (strncmp(pKey, "IP2L", 4) == 0)
    {
        const char *pValue;
        LocInfo *pInfo = pSession->getClientInfo()->getLocInfo();
        valLen = 0;
        if (pInfo)
        {
            pValue = pInfo->getLocEnv(pKey);
            if (pValue)
            {
                valLen = strlen(pValue);
                return pValue;
            }
        }
    }
#endif
    return pSession->getReq()->getEnv(pKey, keyLen, valLen);
}


int RequestVars::getCookieCount(HttpReq *pReq)
{
    const char *pCookie = pReq->getHeader(HttpHeader::H_COOKIE);
    if (!*pCookie)
        return 0;
    const char *p = pCookie;
    const char *pEnd = pCookie + pReq->getHeaderLen(HttpHeader::H_COOKIE);
    const char *p1;
    int count = 0;
    while (p != pEnd)
    {
        p1 = (const char *)memchr(p, '=', pEnd - p);
        if (p1 == NULL)
            break;
        ++count;
        p1 = (const char *)memchr(p1, ';', pEnd - p1);
        if (p1)
            p = p1 + 1;
        else
            p = pEnd;
    }
    return count;

}


const char *RequestVars::getCookieValue(HttpReq *pReq,
                                        const char *pCookieName,
                                        int nameLen, int &idLen)
{
#define TEST_NEW_FUN
#ifdef TEST_NEW_FUN
    //TODO: do some test right now, use these code to return the specified cookie
    cookieval_t *cookie = pReq->getCookie(pCookieName, nameLen);
    int cookieLen = cookie->valLen;
    char *pcookieval = pReq->getHeaderBuf().getp(cookie->valOff);

#endif

    const char *pCookie = pReq->getHeader(HttpHeader::H_COOKIE);
    if (!*pCookie)
        return NULL;
    const char *p = pCookie;
    const char *pEnd = pCookie + pReq->getHeaderLen(HttpHeader::H_COOKIE);
    const char *p1;
    while (p != pEnd)
    {
        p1 = (const char *)memchr(p, '=', pEnd - p);
        if (p1 == NULL)
            break;
        int l = p1 - p;
        if ((l >= nameLen) &&
            (strncasecmp(p1 - nameLen, pCookieName, nameLen) == 0))
        {
            const char *p2 = p1 - nameLen;
            const char *pIdEnd;
            if ((p2 <= pCookie) || isspace(p2[-1]) || (p2[-1] == ';'))
            {
                ++p1;

                pIdEnd = (const char *)memchr(p1, ';', pEnd - p1);
                if (pIdEnd == NULL)
                    pIdEnd = pEnd ;
                while ((pIdEnd > p1) && isspace(*(pIdEnd - 1)))
                    --pIdEnd;
                idLen = pIdEnd - p1;

#ifdef TEST_NEW_FUN
                assert(cookieLen == idLen);
                assert(memcmp(pcookieval, p1, idLen) == 0);
#endif
                return p1;
            }
        }
        p = p1 + 1;

    }
    return NULL;

}


static const char *const s_pHeaders[] =
{
    //Most common headers
    "accept",
    "accept-charset",
    "accept-encoding",
    "accept-language",
    "authorization",
    "connection",
    "content-type",
    "content-length",
    "cookie",
    "cookie2",
    "host",
    "pragma",
    "referer",
    "user-agent",
    "cache-control",
    "if-modified-since",
    "if-match",
    "if-none-match",
    "if-unmodified-since",
    "if-range",
    "keep-alive",
    "range",
    "x-forwarded-for",
    "via",
    "transfer-encoding"
};


const char *RequestVars::getHeaderString(int iIndex)
{
    if ((iIndex >= 0)
        && (iIndex <= (int)(sizeof(s_pHeaders) / sizeof(char *))))
        return s_pHeaders[iIndex];
    return NULL;
}


int RequestVars::getSubstValue(const SubstItem *pItem,
                               HttpSession *pSession,
                               char *&pValue, int bufLen)
{
    HttpReq *pReq = pSession->getReq();
    int type = pItem->getType();
    int i;
    if (type < REF_STRING)
    {
        pValue = (char *)pReq->getHeader(type);
        if (*pValue)
            return pReq->getHeaderLen(type);
        else
            return 0;
    }

    switch (type)
    {
    case REF_STRING:
        pValue = (char *)pItem->getStr()->c_str();
        return pItem->getStr()->len();

    case REF_ENV:
        pValue = (char *)RequestVars::getEnv(pSession, pItem->getStr()->c_str(),
                                             pItem->getStr()->len(), i);
        if (!pValue)
            i = 0;
        return i;
    case REF_HTTP_HEADER:
        pValue = (char *)pReq->getHeader(pItem->getStr()->c_str(),
                                         pItem->getStr()->len(), i);
        if (!pValue)
            i = 0;
        return i;
    default:
        return RequestVars::getReqVar(pSession, type, pValue, bufLen);
    }
    return 0;
}


int RequestVars::appendSubst(const SubstItem *pItem, HttpSession *pSession,
                             char *&pBegin, int len, int noDupSlash,
                             const RegexResult *pRegRes, const char *pTmFmt)
{
    char *pValue = pBegin;
    int valLen;
    if (pItem->getType() == REF_FORMAT_STR)
    {
        valLen = len;
        buildString((const SubstFormat *)pItem->getAny(), pSession,
                    pValue, valLen, noDupSlash, pRegRes, pTmFmt);

    }
    else
    {
        if (pItem->getType() == REF_RULE_SUBSTR)
        {
            if (pRegRes)
                valLen = pRegRes->getSubstr(pItem->getIndex(), pValue);
            else
                return 0;

        }
        else
        {
            if (pTmFmt && ((pItem->getType() == REF_DATE_LOCAL) ||
                           (pItem->getType() == REF_LAST_MODIFIED) ||
                           (pItem->getType() == REF_DATE_GMT)))
                memccpy(pValue, pTmFmt, 0, len);
            valLen = getSubstValue(pItem, pSession, pValue, len);
        }
        if (valLen <= 0)
            return valLen;
        if (len <= valLen)
            return 0;
        if (pValue != pBegin)
        {
            if ((*pValue == '/') && (noDupSlash) && (pBegin[-1] == '/'))
                --pBegin;
            memmove(pBegin, pValue, valLen);
        }
        else
        {
            if ((*pValue == '/') && (noDupSlash) && (pBegin[-1] == '/'))
            {
                --valLen;
                memmove(pBegin, pBegin + 1, valLen);
            }
        }
    }
    pBegin += valLen;
    return 0;
}


char *RequestVars::buildString(const SubstFormat *pFormat,
                               HttpSession *pSession,
                               char *pBuf, int &len, int noDupSlash,
                               const RegexResult *pRegRes, const char *pTmFmt)
{
    char *pBegin = pBuf;
    char *pBufEnd = pBuf + len - 1;
    const SubstItem *pItem = pFormat->begin();

//    if ( !pItem->next() )
//    {
//        int valLen = getSubstValue( pItem, pSession, pBegin, pBufEnd );
//        return valLen;
//        //only one variable, no need to copy to buffer
//    }

    while (pItem)
    {
        if (appendSubst(pItem, pSession, pBegin, pBufEnd - pBegin,
                        (pBegin > pBuf) ? noDupSlash : 0, pRegRes, pTmFmt) == -1)
            return NULL;
        pItem = (const SubstItem *)pItem->next();
    }
    *pBegin = 0;
    len = pBegin - pBuf;
    return pBuf;
}


int RequestVars::setEnv(HttpSession *pSession, const char *pName,
                        int nameLen,
                        const char *pValue, int valLen)
{
    if (*pName == '!')
    {
        ++pName;
        --nameLen;
        if (strcasecmp(pName, "no-gzip") == 0)
        {
            LS_DBG_M(pSession->getLogSession(), "no-gzip flag removed.");
            pSession->getReq()->andGzip(~GZIP_OFF);
            return 0;
        }
        pSession->getReq()->unsetEnv(pName, nameLen);
        LS_DBG_M(pSession->getLogSession(), "Remove ENV: '%s' ", pName);
        return 0;
    }
    if (!pValue)
    {
        pValue = "1";
        valLen = 1;
    }
    if (strcasecmp(pName, "dontlog") == 0)
    {
        LS_DBG_M(pSession->getLogSession(),
                 "Disable access log for this request.");
        pSession->setAccessLogOff();
        return 0;
    }
    else if ((*pName | 0x20) == 'n')
    {
        if (strcasecmp(pName, "nokeepalive") == 0)
        {
            LS_DBG_M(pSession->getLogSession(),
                     "Turn off connection keepalive.");
            pSession->getReq()->keepAlive(false);
            return 0;
        }
        //else if ( strcasecmp( pName, "noconntimeout" ) == 0 )
        //{
        //    LS_DBG_M(pSession->getLogSession(),
        //            "turn off connection timeout.");
        //    pSession->setFlag( HSF_NO_CONN_TIMEOUT );
        //}
        else if (strcasecmp(pName, "no-gzip") == 0)
        {
            if (strncmp(pValue, "0", 1) != 0)
            {
                LS_DBG_M(pSession->getLogSession(),
                         "turn off gzip compression for this requst.");
                pSession->getReq()->orGzip(GZIP_OFF);
            }
            else
                pSession->getReq()->andGzip(~GZIP_OFF);
            return 0;
        }
    }

    pSession->addEnv(pName, nameLen, pValue, valLen);

    LS_DBG_M(pSession->getLogSession(), "Add ENV: '%s:%s' ", pName, pValue);
    return 0;
}


