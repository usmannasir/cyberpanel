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
#include "httpserverconfig.h"

#include <http/connlimitctrl.h>
#include <http/denieddir.h>
#include <http/httpdefs.h>
#include <http/httplog.h>
#include <stdio.h>
#include <sys/stat.h>

HttpServerConfig::HttpServerConfig()
    : m_iMaxURLLen(DEFAULT_URL_LEN + 20)
    , m_iMaxHeaderBufLen(DEFAULT_REQ_HEADER_BUF_LEN)
    , m_iMaxReqBodyLen(DEFAULT_REQ_BODY_LEN)
    , m_iMaxDynRespLen(DEFAULT_DYN_RESP_LEN)
    , m_iMaxDynRespHeaderLen(DEFAULT_DYN_RESP_HEADER_LEN)
    , m_iMaxKeepAliveRequests(100)
    , m_iSmartKeepAlive(0)
    , m_iUseSendfile(0)
    , m_iFollowSymLink(1)
    , m_iGzipCompress(0)
    , m_iDynGzipCompress(0)
    , m_iCompressLevel(4)
    , m_iBrCompress(0)
    , m_iMaxFcgiInstances(2000)
    , m_iMaxTempFileSize(10240)
    , m_iConnTimeout(300)
    , m_iKeepAliveTimeout(15)
    , m_iForbiddenBits(S_IFDIR | S_IXOTH | S_IXUSR | S_IXGRP | S_ISVTX)
    , m_iRequiredBits(S_IROTH)
    , m_iScriptForbiddenBits(000)   //S_IWOTH | S_IWGRP )
    , m_iDirForbiddenBits(000)   //S_IWOTH | S_IWGRP )
    , m_iRestartTimeout(300)
    , m_iDnsLookup(1)
    , m_iUseProxyHeader(0)
    , m_iEnableH2c(0)
    , m_iProcNo(0)
    , m_iChildren(1)
    , m_pAdminSock(NULL)
    , m_pGlobalVHost(NULL)
{
    m_pDeniedDir = new DeniedDir();
}


HttpServerConfig::~HttpServerConfig()
{
    delete m_pDeniedDir;
}


void HttpServerConfig::setDebugLevel(int level)
{
    HttpLog::setDebugLevel(level);
}


void HttpServerConfig::setMaxURLLen(int len)
{
    if ((len >= 200) && (len <= MAX_URL_LEN))
        m_iMaxURLLen = len + 20;
}


void HttpServerConfig::setMaxHeaderBufLen(int len)
{
    if ((len >= 1024) && (len <= MAX_REQ_HEADER_BUF_LEN))
        m_iMaxHeaderBufLen = len ;
}


void HttpServerConfig::setMaxReqBodyLen(int64_t len)
{
    if ((len >= 4096) && (len <= MAX_REQ_BODY_LEN))
        m_iMaxReqBodyLen = len ;
}


void HttpServerConfig::setMaxDynRespLen(int64_t len)
{
    if ((len >= 4096) && (len <= MAX_DYN_RESP_LEN))
        m_iMaxDynRespLen = len ;
}


void HttpServerConfig::setMaxDynRespHeaderLen(int len)
{
    if ((len >= 200) && (len <= MAX_DYN_RESP_HEADER_LEN))
        m_iMaxDynRespHeaderLen = len;
}


int HttpServerConfig::getSpdyKeepaliveTimeout()
{
    int timeout = m_iKeepAliveTimeout;
    timeout *= ConnLimitCtrl::getInstance().getSslAvailRatio() / 10 + 5;
    if (timeout > 60)
        timeout = 60;
    return timeout;
}




