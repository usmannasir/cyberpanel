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
#include "awstats.h"
#include <http/httplog.h>
#include <http/httpvhost.h>
#include <http/accesslog.h>
#include <http/handlertype.h>
#include <http/httpmime.h>
#include <http/serverprocessconfig.h>
#include <log4cxx/logger.h>
#include <log4cxx/logrotate.h>
#include <lsr/ls_fileio.h>
#include <lsr/ls_strtool.h>
#include <main/configctx.h>
#include <main/mainserverconfig.h>
#include <util/xmlnode.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>



Awstats::Awstats()
    : m_iUpdateInterval(0)
    , m_iUpdateTimeOffset(0)
    , m_iLastUpdate(0)
    , m_iMode(AWS_STATIC)
{
}


Awstats::~Awstats()
{
}


static int copyFile(const char *pSrc, const char *pDest)
{
    int fd = open(pSrc, O_RDONLY);
    if (fd == -1)
    {
        LS_ERROR("Can not open Awstats model configuration file[%s]: %s",
                 pSrc, strerror(errno));
        return LS_FAIL;
    }
    int fdDest = open(pDest, O_RDWR | O_CREAT | O_TRUNC, 0644);
    if (fdDest == -1)
    {
        LS_ERROR("Can not create file [%s], %s", pDest, strerror(errno));
        close(fd);
        return LS_FAIL;
    }
    int ret = 0;
    int len;
    char achBuf[8192];

    while ((len = read(fd, achBuf, 8192)) > 0)
    {
        if (write(fdDest, achBuf, len) != len)
        {
            LS_ERROR("Can not write to file [%s], disk full?", pDest);
            unlink(pDest);
            ret = -1;
            break;
        }
    }
    close(fd);
    close(fdDest);
    return ret;
}


static const char *s_pList[] =
{
    "LogFile=\"%s.awstats\"\n",
    "LogType=W\n",
    "SiteDomain=\"%s\"\n",
    "HostAliases=\"%s\"\n",
    "DirData=\"%s/data\"\n",
    "DirCgi=\"%s\"\n",
    "DirIcons=\"/awstats/icon\"\n"
};


static int s_pKeyLen[] =
{   7, 7, 10, 11, 7, 6, 8    };


static int s_pLineLen[] =
{   0, 10, 10, 11, 7, 6, 25    };


static int findKeyInList(const char *pCur)
{
    unsigned int i;
    for (i = 0; i < sizeof(s_pList) / sizeof(char *); ++i)
    {
        if (strncasecmp(pCur, s_pList[i], s_pKeyLen[i]) == 0)
        {
            pCur += s_pKeyLen[i];
            while ((*pCur == ' ') || (*pCur == '\t'))
                ++pCur;
            if (*pCur == '=')
                break;
        }
    }
    return i;
}


int renameLogFile(const char *pLogPath, const char *pSrcSuffix,
                  const char *pDestSuffix)
{
    struct stat st;
    char achDest[1024];
    char achSrc[1024];
    ls_snprintf(achDest, sizeof(achDest), "%s%s", pLogPath, pDestSuffix);
    if (ls_fio_stat(achDest, &st) == 0)
    {
        LS_ERROR("File already exists: [%s], Awstats updating"
                 " might be in progress.", achDest);
        return LS_FAIL;
    }
    ls_snprintf(achSrc, sizeof(achSrc), "%s%s", pLogPath, pSrcSuffix);
    if (ls_fio_stat(achSrc, &st) == -1)
    {
        LS_ERROR("Log file does not exist: [%s], cannot update"
                 " Awstats statistics", achSrc);
        return LS_FAIL;
    }
    if (st.st_size == 0)
        return LS_FAIL;
    if (rename(achSrc, achDest) == -1)
    {
        LS_ERROR("Cannot rename file from [%s] to [%s]: %s",
                 achSrc, achDest, strerror(errno));
        return LS_FAIL;
    }
    return 0;

}


int Awstats::processLine(const HttpVHost *pVHost, int fdConf,
                         char *pCur, char *pLineEnd, char *&pLastWrite)
{
    while ((*pCur == ' ') || (*pCur == '\t'))
        ++pCur;
    if (*pCur == '#')
        return 0;
    int ret = findKeyInList(pCur);
    if (ret >= (int)(sizeof(s_pList) / sizeof(char *)))
        return 0;
    if (pLastWrite < pCur)
    {
        int len = write(fdConf, pLastWrite, pCur - pLastWrite);
        if (len < pCur - pLastWrite)
            return LS_FAIL;
        pLastWrite = pLineEnd + 1;
    }
    int n = 0;
    int len;
    const char *pBuf;
    char achBuf[2048];
    pBuf = achBuf;
    if (ServerProcessConfig::getInstance().getChroot() != NULL)
        len = ServerProcessConfig::getInstance().getChroot()->len();
    else
        len = 0;
    switch (ret)
    {
    case 0:
        n = ls_snprintf(achBuf, sizeof(achBuf), s_pList[ret],
                        pVHost->getAccessLogPath() + len);
        break;
    case 2:
        n = ls_snprintf(achBuf, sizeof(achBuf), s_pList[ret],
                        m_sSiteDomain.c_str());
        break;
    case 3:
        n = ls_snprintf(achBuf, sizeof(achBuf), s_pList[ret],
                        m_sSiteAliases.c_str());
        break;
    case 4:
        n = ls_snprintf(achBuf, sizeof(achBuf), s_pList[ret],
                        m_sWorkingDir.c_str() + len);
        break;
    case 5:
        n = ls_snprintf(achBuf, sizeof(achBuf), s_pList[ret],
                        m_sAwstatsURI.c_str());
        break;
    case 1:
    case 6:
        pBuf = s_pList[ret];
        n = s_pLineLen[ret];
        break;
    }
    if (write(fdConf, pBuf, n) != n)
        return LS_FAIL;
    return 0;
}


int Awstats::createConfigFile(char *pModel, const HttpVHost *pVHost)
{
    // create awstats.conf based on awstats.model.conf
    // search and replace
    //      LogFile="..."
    //      LogType=W
    //      LogFormat=1
    //      SiteDomain="..."
    //      HostAliases="..."
    //      DirData="..."
    //      DirCgi="..."
    //      DirIcons="/awstats/icon"
    int fd = open(pModel, O_RDONLY);
    if (fd == -1)
    {
        LS_ERROR("Can not open Awstats model configuration file[%s]: %s",
                 pModel, strerror(errno));
        return LS_FAIL;
    }
    int len = strlen(pModel);
    ls_snprintf(pModel + len - 10, 1024 - len, "%s.conf", pVHost->getName());
    int fdConf = open(pModel, O_RDWR | O_CREAT | O_TRUNC, 0644);
    if (fdConf == -1)
    {
        LS_ERROR("Can not create configuration file [%s], %s", pModel,
                 strerror(errno));
        close(fd);
        return LS_FAIL;
    }
    char *pCur;
    char *pBufEnd;
    char *pEnd;
    char *pLastWrite;
    char *pLineEnd;
    int    ret = 0;
    char achBuf[8192];

    pCur = pEnd = pLastWrite = achBuf;
    pBufEnd = &achBuf[8192];

    while (1)
    {
        len = read(fd, pEnd, pBufEnd - pEnd);
        if (len == 0)
            break;
        pEnd += len;
        while (pCur < pEnd)
        {
            pLineEnd = (char *)memchr(pCur, '\n', pEnd - pCur);
            if (!pLineEnd)
                break;
            if ((ret = processLine(pVHost, fdConf, pCur, pLineEnd,
                                   pLastWrite)) == -1)
                break;

            pCur = pLineEnd + 1;
        }
        if (pLastWrite < pCur)
        {
            len = write(fdConf, pLastWrite, pCur - pLastWrite);
            if (len < pCur - pLastWrite)
            {
                ret = -1;
                break;
            }
        }
        memmove(achBuf, pCur, pEnd - pCur);
        pEnd = &achBuf[pEnd - pCur];
        pCur = pLastWrite = achBuf;
        if (ret)
            break;
    }
    close(fd);
    close(fdConf);
    return ret;
}


int Awstats::prepareAwstatsEnv(const HttpVHost *pVHost)
{
    ServerProcessConfig &procConfig = ServerProcessConfig::getInstance();
    uid_t uid = procConfig.getUid();
    gid_t gid = procConfig.getGid();
    struct stat st;
    char achBuf[1024];

    if (pVHost->getRootContext().getSetUidMode() == UID_DOCROOT)
    {
        uid = pVHost->getUid();
        gid = pVHost->getGid();
    }

    // create working directory if need
    if (ls_fio_stat(m_sWorkingDir.c_str(), &st) == -1)
    {
        if (mkdir(m_sWorkingDir.c_str(), 0755) == -1)
        {
            LS_ERROR("Can not create awstats working directory[%s]: %s",
                     m_sWorkingDir.c_str(), strerror(errno));
            return LS_FAIL;

        }
    }
    chown(m_sWorkingDir.c_str(), uid, gid);
    if (m_iMode == AWS_STATIC)
    {
        ls_snprintf(achBuf, 1024, "%s/html", m_sWorkingDir.c_str());
        if (ls_fio_stat(achBuf, &st) == -1)
        {
            if (mkdir(achBuf, 0755) == -1)
            {
                LS_ERROR("Can not create awstats working directory[%s]: %s",
                         achBuf, strerror(errno));
                return LS_FAIL;
            }
        }
        chown(achBuf, uid, gid);
    }
    // create data directory if need
    ls_snprintf(achBuf, 1024, "%s/data", m_sWorkingDir.c_str());
    mkdir(achBuf, 0755);
    chown(achBuf, uid, gid);
    // create conf directory if need
    ls_snprintf(achBuf, 1024, "%s/conf", m_sWorkingDir.c_str());
    mkdir(achBuf, 0755);
    chown(achBuf, uid, gid);
    // copy awstats.model.conf to conf/ directory if does not exist
    ls_snprintf(achBuf, 1024, "%s/conf/awstats.model.conf",
                m_sWorkingDir.c_str());
    if (ls_fio_stat(achBuf, &st) == -1)
    {
        char achTmp[1024];
        const char *pChroot = "";
        if (procConfig.getChroot() != NULL)
            pChroot = procConfig.getChroot()->c_str();

        ls_snprintf(achTmp, 1024,
                    "%s%s/add-ons/awstats/wwwroot/cgi-bin/awstats.model.conf",
                    pChroot, MainServerConfig::getInstance().getServerRoot());
        if (copyFile(achTmp, achBuf))
            return LS_FAIL;
        chown(achBuf, uid, gid);
    }

    if (createConfigFile(achBuf, pVHost) == -1)
        return LS_FAIL;
    chown(achBuf, uid, gid);
    return 0;
}


int Awstats::executeUpdate(const char *pName)
{
    const char *pWorking = m_sWorkingDir.c_str();
    char achBuf[8192];
    ls_snprintf(achBuf, 8192, "%s/add-ons/awstats",
                MainServerConfig::getInstance().getServerRoot());
    if (ServerProcessConfig::getInstance().getChroot() != NULL)
        pWorking += ServerProcessConfig::getInstance().getChroot()->len();
    if (chdir(achBuf) == -1)
    {
        LS_ERROR("Cannot change to dir [%s]: %s", achBuf, strerror(errno));
        return LS_FAIL;
    }
    if (m_iMode == AWS_STATIC)
    {
        ls_snprintf(achBuf, 8192,
                    "tools/awstats_buildstaticpages.pl -awstatsprog=wwwroot/cgi-bin/awstats.pl"
                    " -dir='%s/html' -update "
                    "-configdir='%s/conf' "
                    "-config='%s' -lang=en", pWorking, pWorking,
                    pName);
    }
    else if (m_iMode == AWS_DYNAMIC)
    {
        ls_snprintf(achBuf, 8192,
                    "wwwroot/cgi-bin/awstats.pl -update -configdir='%s/conf' -config='%s'",
                    pWorking, pName);
    }
    else
    {
        LS_ERROR("Unknown update method %d", m_iMode);
        return LS_FAIL;
    }

    setpriority(PRIO_PROCESS, 0, getpriority(PRIO_PROCESS, 0) + 4);
    int ret = system(achBuf);
    return ret;
}


int Awstats::update(const HttpVHost *pVHost)
{
    // rotate current access log file to access.log.awstats
    const char *pLogPath;
    int ret;
    ServerProcessConfig &procConfig = ServerProcessConfig::getInstance();
    pLogPath = pVHost->getAccessLogPath();
    if (!pLogPath)
    {
        LS_ERROR("Virtual host [%s] must use its own access log, "
                 "in order to use awstats", pVHost->getName());
        return LS_FAIL;
    }

    if (prepareAwstatsEnv(pVHost))
        return LS_FAIL;

    ret = renameLogFile(pLogPath, "", ".awstats");
    LOG4CXX_NS::LogRotate::postRotate(pVHost->getAccessLog()->getAppender(),
                                      procConfig.getUid(),
                                      procConfig.getGid());
    if (ret == -1)
        return LS_FAIL;

    int pid = fork();
    if (pid)
    {
        //parent process or error
        return (pid == -1) ? pid : 0;
    }

    // child process
    // fork again
    pid = fork();
    if (pid < 0)
        LS_ERROR("fork() failed");
    else if (pid == 0)
    {
        if (procConfig.getChroot() != NULL)
            chroot(procConfig.getChroot()->c_str());
        if (pVHost->getRootContext().getSetUidMode() == UID_DOCROOT)
            setuid(pVHost->getUid());
        else
            setuid(procConfig.getUid());
        executeUpdate(pVHost->getName());
        exit(0);
    }
    else
        waitpid(pid, NULL, 0);

    // rotate again and compress if required
    if (archiveFile(pLogPath, ".awstats",
                    pVHost->getAccessLog()->getCompress(),
                    procConfig.getUid(), procConfig.getGid()) == -1)
    {
        char achBuf[1024];
        ls_snprintf(achBuf, 1024, "%s%s", pLogPath, ".awstats");
        unlink(achBuf);
        LS_ERROR("Unable to rename [%s], remove it.", achBuf);
    }
    exit(0);
}


int Awstats::shouldBuildStatic(const char *pName)
{
    struct stat st;
    char achBuf[1024];
    if (m_iMode == AWS_STATIC)
    {
        ls_snprintf(achBuf, 1024, "%s/html/awstats.%s.html",
                    m_sWorkingDir.c_str(), pName);
    }
    else
    {
        ls_snprintf(achBuf, 1024, "%s/conf/awstats.%s.conf",
                    m_sWorkingDir.c_str(), pName);
    }
    if (ls_fio_stat(achBuf, &st) == -1)
        return 1;
    return 0;
}


int Awstats::updateIfNeed(long curTime, const HttpVHost *pVHost)
{
    if (m_iUpdateInterval <= 0)
        return 0;
    int ret = 0;
    if (!m_iLastUpdate)
    {
        char achConfFile[1024];
        struct stat st;
        ls_snprintf(achConfFile, 1024, "%s/conf/awstats.%s.conf",
                    m_sWorkingDir.c_str(),
                    pVHost->getName());
        if (stat(achConfFile, &st) != -1)
            m_iLastUpdate = (st.st_mtime - m_iUpdateTimeOffset) / m_iUpdateInterval;

    }
    int count = (curTime - m_iUpdateTimeOffset) / m_iUpdateInterval;
    if ((count > m_iLastUpdate) || (shouldBuildStatic(pVHost->getName())))
    {
        m_iLastUpdate = count;
        if (m_iLastUpdate)
            ret = update(pVHost);
    }
    return ret;
}


void Awstats::config(HttpVHost *pVHost, int val, char *achBuf,
                     const XmlNode *pAwNode,
                     char *iconURI, const char *vhDomain, int vhAliasesLen)
{
    const char *pURI;
    const char *pValue;
    char *p;
    int handlerType;
    int len = strlen(achBuf);
    int iChrootLen = 0;
    if (ServerProcessConfig::getInstance().getChroot() != NULL)
        iChrootLen = ServerProcessConfig::getInstance().getChroot()->len();
    setMode(val);


    if (achBuf[len - 1] == '/')
        achBuf[len - 1] = 0;

    setWorkingDir(achBuf);

    pURI = pAwNode->getChildValue("awstatsURI");

    if ((!pURI) || (*pURI != '/') || (* (pURI + strlen(pURI) - 1) != '/')
        || (strlen(pURI) > 100))
    {
        LS_WARN(ConfigCtx::getCurConfigCtx(), "AWStats URI is invalid"
                ", use default [/awstats/].");
        iconURI[9] = 0;
        pURI = iconURI;
    }

    setURI(pURI);

    if (val == AWS_STATIC)
    {
        handlerType = HandlerType::HT_NULL;
        strcat(achBuf, "/html/");
    }
    else
    {
        ConfigCtx::getCurConfigCtx()->getValidPath(achBuf,
                "$SERVER_ROOT/add-ons/awstats/wwwroot/cgi-bin/",
                "AWStats CGI-BIN directory");

        if (pVHost->getRootContext().determineMime("pl",
                NULL)->getHandler()->getType())
            handlerType = HandlerType::HT_NULL;
        else
            handlerType = HandlerType::HT_CGI;
    }

    HttpContext *pContext =
        pVHost->addContext(pURI, handlerType, &achBuf[iChrootLen], NULL, 1);

    p = achBuf;
    if (ConfigCtx::getCurConfigCtx()->getLongValue(pAwNode, "securedConn", 0,
            1, 0) == 1)
    {
        p += ls_snprintf(achBuf, 8192,
                         "rewriteCond %%{HTTPS} !on\n"
                         "rewriteCond %%{HTTP:X-Forwarded-Proto} !https\n"
                         "rewriteRule ^(.*)$ https://%%{SERVER_NAME}%%{REQUEST_URI} [R,L]\n");

    }
    if (val == AWS_STATIC)
    {
        ls_snprintf(p, &achBuf[8192] - p,
                    "RewriteRule ^$ awstats.%s.html\n",
                    pVHost->getName());
    }
    else
    {
        ls_snprintf(p, &achBuf[8192] - p,
                    "RewriteRule ^$ awstats.pl\n"
                    "RewriteCond %%{QUERY_STRING} !configdir=\n"
                    "RewriteRule ^awstats.pl "
                    "$0?config=%s&configdir=%s/conf [QSA]\n",
                    pVHost->getName(),
                    getWorkingDir() + iChrootLen);
        pContext->setUidMode(UID_DOCROOT);
    }

    pContext->enableRewrite(1);
    pContext->configRewriteRule(pVHost->getRewriteMaps(), achBuf);

    pValue = pAwNode->getChildValue("realm");

    if (pValue)
        pVHost->configAuthRealm(pContext, pValue);

    pValue = pAwNode->getChildValue("siteDomain");

    if (!pValue)
    {
        LS_WARN(ConfigCtx::getCurConfigCtx(), "SiteDomain configuration is invalid"
                ", use default [%s].",  vhDomain);
        pValue = vhDomain;
    }
    else
    {
        ConfigCtx::getCurConfigCtx()->expandDomainNames(pValue, achBuf, 4096);
        pValue = achBuf;
    }

    setSiteDomain(pValue);

    pValue = pAwNode->getChildValue("siteAliases");
    int needConvert = 1;

    if (!pValue)
    {
        if (vhAliasesLen == 0)
        {
            ls_snprintf(achBuf, 8192, "127.0.0.1 localhost REGEX[%s]",
                        getSiteDomain());
            LS_WARN(ConfigCtx::getCurConfigCtx(),
                    "SiteAliases configuration is invalid"
                    ", use default [%s].", achBuf);
            pValue = achBuf;
            needConvert = 0;
        }
        else
            pValue = "$vh_aliases";
    }

    if (needConvert)
    {
        ConfigCtx::getCurConfigCtx()->expandDomainNames(pValue, &achBuf[4096],
                4096, ' ');
        ConfigCtx::getCurConfigCtx()->convertToRegex(&achBuf[4096], achBuf, 4096);
        pValue = achBuf;
        LS_INFO(ConfigCtx::getCurConfigCtx(), "SiteAliases is set to '%s'",
                achBuf);
    }

    setAliases(pValue);

    val = ConfigCtx::getCurConfigCtx()->getLongValue(pAwNode, "updateInterval",
            3600, 3600 * 24, 3600 * 24);

    if (val % 3600 != 0)
        val = ((val + 3599) / 3600) * 3600;

    setInterval(val);

    val = ConfigCtx::getCurConfigCtx()->getLongValue(pAwNode, "updateOffset",
            0, LONG_MAX, 0);

    if (val > getInterval())
        val %= getInterval();

    setOffset(val);

    pVHost->setAwstats(this);
}
