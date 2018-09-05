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
#ifndef ZCONFMANAGER_H
#define ZCONFMANAGER_H

#include <util/tsingleton.h>
#include <ls.h>

class AutoBuf;
class AutoStr2;
class HttpListener;
class HttpVHost;
class SslContext;
class ZConfClient;

#define ZCMF_SENDZCUP       (1<<0)
#define ZCMF_SENDZCSSL      (1<<1)

class ZConfManager : public TSingleton<ZConfManager>
{
    friend class TSingleton<ZConfManager>;
    ZConfManager();
public:
    ~ZConfManager();

    int init(const char *pAuth, const char *pAdcList, const char *pConfName);

    AutoStr2 *getConfName() const           {   return m_pConfName;     }

    void setFlag(uint32_t flag)             {   m_iFlags |= flag;       }
    void unsetFlag(uint32_t flag)           {   m_iFlags &= ~flag;      }
    uint32_t isFlagSet(uint32_t flag) const {   return m_iFlags & flag; }

    int appendListener(HttpListener *pListener);

    void resetDomainList();

    int appendToTmpDomainList(const char *pDomainList, int iListLen);

    int appendSslContext(const char *pDomainList, int iListLen, SslContext *pCtx);

    int appendSslListener(SslContext *pCtx);

    void prepareServerUp();

    void sendStartUp();

    void sendServerUp();

    void requestDone(ZConfClient *pClient, int iRequestDone);

private:

    static int hashConf(AutoBuf *pBuf, const char *path, unsigned long long *outHash);
    static int updateFile(const char *path, const char *pCurHash, int iCurHashLen);

    uint32_t            m_iFlags;
    unsigned long long  m_iConfHash;
    AutoBuf            *m_pSvrConf;
    AutoBuf            *m_pSslConf;
    AutoStr2           *m_pAuth;
    AutoStr2           *m_pConfName;
    AutoStr2           *m_pAdcList;
    AutoBuf            *m_pTmpDomainList;
    ZConfClient        *m_pClients;

    LS_NO_COPY_ASSIGN(ZConfManager);
};


#endif // ZCONFMANAGER_H
