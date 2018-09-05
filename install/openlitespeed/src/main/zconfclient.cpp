/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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

#include <main/zconfclient.h>

#include <main/configctx.h>
#include <main/httpserver.h>
#include <main/zconfmanager.h>

#include <http/connlimitctrl.h>
#include <http/httpvhost.h>
#include <lsr/ls_base64.h>
#include <lsr/ls_strtool.h>
#include <util/autobuf.h>
#include <util/stringlist.h>
#include <util/xmlnode.h>

static const char *ZCONFCLIENT_LOG_PREFIX = "ZConfClient";

// Uncomment as they are implemented.
static const char *s_achReqType[] =
    {
        "ZCUP",
        "ZCSSL",
        // "ZCDOWN",
        // "ZCQUERY",
        // "ZCRESUME",
        // "ZCSUSPEND",
    };

ZConfClient::ZConfClient()
    : LinkedObj()
    , m_iReqType(ZCUNKNOWN)
{
}


ZConfClient::~ZConfClient()
{
}


void ZConfClient::init(const char *pAdc, int iAdcLen)
{
    m_adc.setStr(pAdc, iAdcLen);
}


int ZConfClient::initFetch(const char *pAuth, int iAuthLen)
{
    m_iReqType = ZCUNKNOWN;
    m_fetch.reset();
    m_fetch.setResProcessor(processFetch, this);
    return m_fetch.setExtraHeaders(pAuth, iAuthLen);
}


int ZConfClient::sendReq(int reqType, const char *pConfName, AutoBuf *pReqBody)
{
    int ret;
    char achUrl[256];
    const char *pReqType;

    if (m_iReqType != ZCUNKNOWN)
    {
        LS_ERROR("[%s] Attempted to send a request in the middle of another request %d",
                ZCONFCLIENT_LOG_PREFIX, m_iReqType);
                return -1;
    }

    switch (reqType)
    {
    case ZCUP:
    case ZCSSL:
        pReqType = s_achReqType[reqType];
        break;
    case ZCDOWN:
    case ZCQUERY:
    case ZCRESUME:
    case ZCSUSPEND:
    default:
        LS_ERROR("[%s] Request type currently unsupported.",
                 ZCONFCLIENT_LOG_PREFIX);
        return -1;
    }

    m_iReqType = reqType;

    ls_snprintf(achUrl, 256, "https://%.*s/%s?name=%s",
                m_adc.len(), m_adc.c_str(), pReqType, pConfName);

    ret = m_fetch.startReq(achUrl, 1, 1, pReqBody->begin(),
                            pReqBody->size(), NULL, NULL, NULL);
    if (m_fetch.getHttpFd() != -1)
    {
        LS_DBG_L("[%s] Connected to Adc %s", ZCONFCLIENT_LOG_PREFIX,
                 m_adc.c_str());
    }
    else if (LS_FAIL == ret)
    {
        // -1 for fd and ret indicates httpfetch build failure, will never succeed.
        LS_DBG_L("[%s] Failed to connect to Adc %s", ZCONFCLIENT_LOG_PREFIX,
                 m_adc.c_str());
        return -1;
    }
    return 0;
}


int ZConfClient::processFetch(void* pArg, HttpFetch* pFetch)
{
    ZConfClient *pClient = (ZConfClient *)pArg;
    int iStatusCode = pFetch->getStatusCode();
    if (iStatusCode < 0)
    {
        LS_NOTICE("[%s] Fetch type %s failed to Adc %s, got HttpFetch error %d",
                  ZCONFCLIENT_LOG_PREFIX, s_achReqType[pClient->m_iReqType],
                  pClient->m_adc.c_str(), iStatusCode);
        return 0;
    }
    else if (iStatusCode != 200)
    {
        LS_NOTICE("[%s] Fetch type %s failed to Adc %s, returned status code %d",
                  ZCONFCLIENT_LOG_PREFIX, s_achReqType[pClient->m_iReqType],
                  pClient->m_adc.c_str(), iStatusCode);
        return 0;
    }
    LS_DBG_L("[%s] Message sent to %s successfully. Type %s",
            ZCONFCLIENT_LOG_PREFIX, pClient->m_adc.c_str(),
            s_achReqType[pClient->m_iReqType]);

    ZConfManager::getInstance().requestDone(pClient, pClient->m_iReqType);
    return 0;
}
