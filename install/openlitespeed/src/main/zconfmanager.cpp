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

#include <main/zconfmanager.h>

#include <main/configctx.h>
#include <main/zconfclient.h>

#include <http/connlimitctrl.h>
#include <http/httplistener.h>
#include <http/vhostmap.h>

#include <log4cxx/logger.h>

#include <lsr/ls_base64.h>
#include <lsr/ls_strtool.h>
#include <lsr/ls_fileio.h>
#include <lsr/xxhash.h>

#include <sslpp/sslcontext.h>
#include <sslpp/sslutil.h>

#include <util/autobuf.h>
#include <util/autostr.h>
#include <util/gpath.h>
#include <util/httputil.h>
#include <util/stringlist.h>

#include <fcntl.h>
#include <unistd.h>

static const char *ZCONFMGR_LOG_PREFIX = "ZConfManager";


ZConfManager::ZConfManager()
    : m_iFlags(0)
    , m_iConfHash(0)
    , m_pSvrConf(NULL)
    , m_pSslConf(NULL)
    , m_pAuth(NULL)
    , m_pConfName(NULL)
    , m_pAdcList(NULL)
    , m_pTmpDomainList(NULL)
    , m_pClients(NULL)
{
}


ZConfManager::~ZConfManager()
{
    ZConfClient *pClient;
    if (m_pSvrConf)
        delete m_pSvrConf;
    if (m_pSslConf)
        delete m_pSslConf;
    if (m_pAuth)
        delete m_pAuth;
    if (m_pAdcList)
        delete m_pAdcList;
    if (m_pConfName)
        delete m_pConfName;
    if (m_pTmpDomainList)
        delete m_pTmpDomainList;
    while (m_pClients)
    {
        pClient = m_pClients;
        m_pClients = (ZConfClient *)m_pClients->next();
        delete pClient;
    }
}


int ZConfManager::init(const char *pAuth, const char *pAdcList,
        const char *pConfName)
{
    int iAuthLen, iPrefixLen, iConfLen;
    char *pDest;
    m_pSvrConf = new AutoBuf(1024);
    m_pSvrConf->used(ls_snprintf(m_pSvrConf->begin(), 60,
            "conf=\n"
            "{\n" // open conf
            "\"max_conn\":%d,\n"
            "\"vhost_list\":\n"
            "[\n", // open vhost list
            ConnLimitCtrl::getInstance().getMaxConns()));

    iConfLen = strlen(pConfName);
    m_pConfName = new AutoStr2();
    pDest = m_pConfName->prealloc(iConfLen * 3);
    iConfLen = HttpUtil::escapeQs(pConfName, iConfLen, pDest, iConfLen * 3);
    m_pConfName->setLen(iConfLen);

    m_pAuth = new AutoStr2("Authorization: Basic ");
    iAuthLen = strlen(pAuth);
    iPrefixLen = m_pAuth->len();
    m_pAuth->prealloc(iPrefixLen + ls_base64_encodelen(iAuthLen));
    iAuthLen = ls_base64_encode(pAuth, iAuthLen, m_pAuth->buf() + iPrefixLen);
    m_pAuth->setLen(iPrefixLen + iAuthLen);

    m_pAdcList = new AutoStr2(pAdcList);
    StringList adcList;
    ZConfClient *pClient;
    adcList.split(m_pAdcList->c_str(),
                  m_pAdcList->c_str() + m_pAdcList->len(), ",");

    StringList::iterator iter;
    AutoStr2 *pAdc;

    for (iter = adcList.begin(); iter != adcList.end(); ++iter)
    {
        pAdc = *iter;
        pClient = new ZConfClient();
        pClient->init(pAdc->c_str(), pAdc->len());
        pClient->initFetch(m_pAuth->c_str(), m_pAuth->len());
        pClient->setNext(m_pClients);
        m_pClients = pClient;
    }
    return 0;
}


static const char *s_pSslConfBeginning = "conf=\n{\n\"ssl_list\" :\n[\n";
static const int s_iSslConfBeginningLen = 23;
/**
 * Take vhost mapping and appends it to the server up message.
 * Also looks for vhost specific SSL configuration.
 *   If the vhost ssl configuration exists:
 *     Appends the vhost cert and key to the SSL conf.
 *   else if the listener is a ssl listener:
 *     Append to the tmp domain list.
 */
int ZConfManager::appendListener(HttpListener *pListener)
{
    SslContext *pSslCtx = pListener->getVHostMap()->getSslContext();
    char isSsl = 0;
    if (NULL == m_pConfName)
        return LS_OK;

    if (!pListener->isSendZConf())
        return LS_OK;

    if (pSslCtx)
    {
        if (NULL == m_pSslConf)
        {
            m_pSslConf = new AutoBuf(1024);
            m_pSslConf->append(s_pSslConfBeginning, s_iSslConfBeginningLen);
        }
        isSsl = 1;
    }

    if (pListener->zconfAppendVHostList(m_pSvrConf) > 0)
        setFlag(ZCMF_SENDZCUP);

    // TODO: do this for subIpMap sslcontext?
    if (isSsl)
        appendSslListener(pSslCtx);
    resetDomainList();
    return LS_OK;
}


/**
 * Reset the tmp domain list.
 *
 * The tmp domain list is used to compile a list of domains to associate with
 * a listener's default ssl cert and key. appendVHost() is repeated for each
 * vhost mapping for a single listener, so this should be called after that
 * listener's configuration is finished.
 */
void ZConfManager::resetDomainList()
{
    if (NULL != m_pTmpDomainList)
        m_pTmpDomainList->clear();
}


/**
 * Appends a domain list to the tmp domain list.
 *
 * The tmp domain list is used to compile a list of domains to associate with
 * a listener's default ssl cert and key. appendVHost() is repeated for each
 * vhost mapping for a single listener, so this should be called if the vhost
 * does not have its own ssl cert and key.
 *
 * Returns 1 on success, 0 on failure.
 */
int ZConfManager::appendToTmpDomainList(const char *pDomainList, int iListLen)
{
    int len;
    if ((NULL == pDomainList) || (0 == iListLen))
        return 0;
    if (NULL != m_pTmpDomainList)
    {
        len = m_pTmpDomainList->size() + iListLen + 2;
        if (len > m_pTmpDomainList->capacity())
            m_pTmpDomainList->reserve(len);
        if (!m_pTmpDomainList->empty())
            m_pTmpDomainList->appendUnsafe(',');
    }
    else
    {
        len = ((iListLen > 1024) ? iListLen + 2 : 1024);
        m_pTmpDomainList = new AutoBuf(len);
    }

    m_pTmpDomainList->appendUnsafe(pDomainList, iListLen);
    return 1;
}


/**
 * Extract the SSL_CTX object from pCtx and append the domain list and
 * PEM versions of the key, cert, cabundle from pCtx to the ssl configuration.
 *
 * If pCtx does not exist or the key/cert combination is invalid, this method
 * will append to the tmp domain list to be listed under the default listener's
 * cert/key.
 *
 * NOTE: the listener configuration will also call this method. Note that if
 * pCtx does not exist or the key/cert are invalid, the tmp domain list will
 * be appended to, and nothing more.
 *
 * Returns 1 on success, 0 on failure.
 */
int ZConfManager::appendSslContext(const char *pDomainList, int iListLen,
    SslContext *pCtx)
{
    const int iBundlePrefixLen = 18;
    const char *pBundlePrefix = "\",\n\"ca_bundle\" : \"";
    int iPreBundleSize;
    if ((NULL == pCtx) || (!pCtx->checkPrivateKey()))
        return appendToTmpDomainList(pDomainList, iListLen);
    // Beyond this point, we have a context and the priv key and cert are valid
    m_pSslConf->reserve(m_pSslConf->size() + iListLen + 31);
    m_pSslConf->used(
        snprintf(m_pSslConf->end(), iListLen + 31,
            "{\n\"domain_list\":\n[%.*s],\n\"key\" : \"",
            iListLen, pDomainList)
    );
    SslUtil::getPrivateKeyPem(pCtx->get(), m_pSslConf);
    m_pSslConf->append("\",\n\"cert\" : \"");
    SslUtil::getCertPem(pCtx->get(), m_pSslConf);
    iPreBundleSize = m_pSslConf->size();
    m_pSslConf->grow(iBundlePrefixLen);
    m_pSslConf->used(iBundlePrefixLen); // Reserve space for ca bundle prefix
    if (SslUtil::getCertChainPem(pCtx->get(), m_pSslConf)) // If bundle exists
        memmove(m_pSslConf->getp(iPreBundleSize), pBundlePrefix, iBundlePrefixLen);
    else
        m_pSslConf->used(-iBundlePrefixLen); // no ca bundles, unreserve this space.

    m_pSslConf->append("\"\n},\n");
    return 1;
}


/**
 * Appends the SslContext associated with the listener. This should be called
 * once the vhost mapping configuration for this listener is completed. This will
 * add the domain mapping for vhosts that do not contain their own configurations
 * or have invalid configurations.
 *
 * Returns 1 on success, 0 on failure.
 */
int ZConfManager::appendSslListener(SslContext *pCtx)
{
    int ret;
    if ((NULL == m_pTmpDomainList) || (m_pTmpDomainList->empty()))
        return 1;
    ret = appendSslContext(m_pTmpDomainList->begin(),
            m_pTmpDomainList->size(), pCtx);
    return ret;
}


/**
 * This method will update the hash file if it already exists.
 * It will first try to open and read the file, then compare the hash
 * to the updated hash. If it needs to be overwritten, try to do so.
 *
 * Returns -1 if it failed to update the file, 0 if it successfully updated.
 *
 * NOTE: If the old hash and new hash match, this method will return -1
 * because the file was not updated.
 */
int ZConfManager::updateFile(const char *path, const char *pCurHash, int iCurHashLen)
{
    const char *pMsg;
    const int prevHashLen = 128;
    int len, fd, ret = -1;
    char prevHash[prevHashLen];

    if (-1 == (fd = ls_fio_open(path, O_RDWR, 0600)))
    {
        pMsg = "[%s] Failed to open config file. %s";
    }
    else if (-1 == (len = ls_fio_read(fd, prevHash, prevHashLen)))
    {
        pMsg = "[%s] Failed to read config file. %s";
    }
    else if ((len == iCurHashLen)
        && (0 == strncmp(pCurHash, prevHash, iCurHashLen)))
    {
        pMsg = "[%s] Hashes match, %s";
    }
    else if (-1 == ls_fio_truncate(fd, 0))
    {
        pMsg = "[%s] Failed to truncate file for overwrite. %s";
    }
    else if ((off_t)-1 == ls_fio_lseek(fd, 0, SEEK_SET))
    {
        pMsg = "[%s] Failed to seek file for overwrite. %s";
    }
    else if (-1 == ls_fio_write(fd, pCurHash, iCurHashLen))
    {
        pMsg = "[%s] Failed to write config to file. %s";
    }
    else
    {
        pMsg = "[%s] Successfully overwrote the config file. %s";
        ret = 0;
    }

    LS_NOTICE(pMsg, ZCONFMGR_LOG_PREFIX, path);

    ls_fio_close(fd);
    return ret;
}


/**
 * Build a hash and update/create a hash file to remember old configurations.
 *
 * The hashing uses XXH64 and will exclude the conf= portion of the conf.
 * The exclusion is to make it easier on the ADC side.
 */
int ZConfManager::hashConf(AutoBuf *pBuf, const char *path,
        unsigned long long *outHash)
{
    unsigned long long hash;
    int fd, hashLen;
    char achHash[128];

    // 5 offset is to exclude conf= from the hash
    hash = XXH64(pBuf->begin() + 5, pBuf->size() - 5, 0);
    if (outHash)
    {
        *outHash = hash;
    }

    hashLen = ls_snprintf(achHash, 128, "%llx", hash);

    if (GPath::isValid(path))
    {
        return updateFile(path, achHash, hashLen);
    }
    LS_NOTICE("[%s] No current config file, create a new one.",
            ZCONFMGR_LOG_PREFIX);

    //file does not exist
    if (-1 == (fd = ls_fio_creat(path, 0600)))
    {
        LS_ERROR("[%s] Failed to open file to write config.",
                ZCONFMGR_LOG_PREFIX);
        return 0;
    }

    if (-1 == ls_fio_write(fd, achHash, hashLen))
    {
        LS_ERROR("[%s] Failed to write config to file.",
                ZCONFMGR_LOG_PREFIX);
        ls_fio_close(fd);
        return 0;
    }

    ls_fio_close(fd);
    LS_NOTICE("[%s] Successfully created a new config file.",
            ZCONFMGR_LOG_PREFIX);
    return 0;
}


// NOTICE: I decided to send the update even if it fails to write to file.
// The thought behind this is that the server is still up and running, so
// the inability to write to the file should not impact the server up.
void ZConfManager::prepareServerUp()
{
    char path[256];

    if (!isFlagSet(ZCMF_SENDZCUP))
    {
        LS_NOTICE("[%s] No VHosts added, do not send!", ZCONFMGR_LOG_PREFIX);
        return;
    }

    LS_DBG_L("[%s] Prepare to send vhosts.", ZCONFMGR_LOG_PREFIX);

    m_pSvrConf->pop_end(2); // clear trailing comma
    m_pSvrConf->append("]\n}\n"); // close vhost list, close conf

    ConfigCtx::getCurConfigCtx()->getAbsoluteFile(path, "$SERVER_ROOT/conf/zconfsvrup.hash");
    if (-1 == hashConf(m_pSvrConf, path, &m_iConfHash))
    {
        unsetFlag(ZCMF_SENDZCUP);
    }

    if (NULL == m_pSslConf)
        return;
    // Generate a hash for ssl.
    if (s_iSslConfBeginningLen == m_pSslConf->size())
    {
        // No ssl confs added.
        delete m_pSslConf;
        m_pSslConf = NULL;
    }
    else
    {
        m_pSslConf->pop_end(2); // Clear trailing comma
        m_pSslConf->append("\n]\n}");
    }
    ConfigCtx::getCurConfigCtx()->getAbsoluteFile(path, "$SERVER_ROOT/conf/zconfssl.hash");
    if (0 == hashConf(m_pSslConf, path, NULL))
        setFlag(ZCMF_SENDZCSSL);
}


void ZConfManager::sendStartUp()
{
    ZConfClient *pClient = m_pClients, *pPrev = m_pClients;
    int iReq;
    AutoBuf *pReqBody;

    if (isFlagSet(ZCMF_SENDZCUP))
    {
        iReq = ZConfClient::ZCUP;
        pReqBody = m_pSvrConf;
    }
    else if (isFlagSet(ZCMF_SENDZCSSL))
    {
        iReq = ZConfClient::ZCSSL;
        pReqBody = m_pSslConf;
    }
    else
        return;

    while (pClient != NULL)
    {
        if (pClient->sendReq(iReq, m_pConfName->c_str(), pReqBody) != -1)
        {
            pPrev = pClient;
            pClient = (ZConfClient *)pClient->next();
            continue;
        }

        LS_NOTICE("[%s] Did not send request to %s", ZCONFMGR_LOG_PREFIX,
            pClient->getAdcAddr());

        if (pClient == m_pClients)
        {
            pPrev = (ZConfClient *)pClient->next();
            delete pClient;
            pClient = pPrev;
            m_pClients = pClient;
        }
        else
        {
            pPrev->setNext(pClient->next());
            delete pClient;
            pClient = (ZConfClient *)pPrev->next();
        }
    }
}


void ZConfManager::requestDone(ZConfClient *pClient, int iFinishedReq)
{
    switch (iFinishedReq)
    {
    case ZConfClient::ZCUP:
        if (!isFlagSet(ZCMF_SENDZCSSL))
            return;

        pClient->initFetch(m_pAuth->c_str(), m_pAuth->len());

        if (pClient->sendReq(ZConfClient::ZCSSL, m_pConfName->c_str(),
                    m_pSslConf) != -1)
        {
            LS_NOTICE("[%s] Sent SSL request to %s", ZCONFMGR_LOG_PREFIX,
                pClient->getAdcAddr());
            return;
        }
        LS_NOTICE("[%s] Did not send SSL request to %s", ZCONFMGR_LOG_PREFIX,
            pClient->getAdcAddr());
        break;
    case ZConfClient::ZCSSL:
    case ZConfClient::ZCDOWN:
    case ZConfClient::ZCQUERY:
    case ZConfClient::ZCRESUME:
    case ZConfClient::ZCSUSPEND:
        break;
    }
}
