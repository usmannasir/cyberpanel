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

#include "iptoloc.h"

#ifdef USE_IP2LOCATION

#include <http/httplog.h>
#include <log4cxx/logger.h>
#include <main/configctx.h>
#include <util/ienv.h>
#include <util/xmlnode.h>

#include <fcntl.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>


IpToLoc *IpToLoc::s_pIpToLoc = NULL;


LocInfo::LocInfo()
    : m_pRecord(NULL)
{
}


LocInfo::~LocInfo()
{
    release();
}

void LocInfo::reset()
{
    release();
}

void LocInfo::release()
{
    if (m_pRecord)
    {
        IP2Location_free_record(m_pRecord);
        m_pRecord = NULL;
    }
}


const char *LocInfo::getLocEnv(const char *pEnvName)
{
    static char s_achBuf[16] = { 0 };
    if (strncasecmp(pEnvName, "IP2LOCATION_", 12) == 0)
        pEnvName += 12;
    else
        return NULL;

    if (strncasecmp(pEnvName, "COUNTRY_", 8) == 0)
    {
        pEnvName += 8;
        if (strcasecmp(pEnvName, "SHORT") == 0)
            return m_pRecord->country_short;
        else if (strcasecmp(pEnvName, "LONG") == 0)
            return m_pRecord->country_long;
        else
            return NULL;
    }
    else if (strcasecmp(pEnvName, "LATITUDE") == 0)
    {
        if (m_pRecord->latitude)
        {
            snprintf(s_achBuf, 15, "%f", m_pRecord->latitude);
            return s_achBuf;
        }
        else
            return NULL;
    }
    else if (strcasecmp(pEnvName, "LONGITUDE") == 0)
    {
        if (m_pRecord->longitude)
        {
            snprintf(s_achBuf, 15, "%f", m_pRecord->longitude);
            return s_achBuf;
        }
        else
            return NULL;
    }
    else if (strcasecmp(pEnvName, "ELEVATION") == 0)
    {
        if (m_pRecord->elevation)
        {
            snprintf(s_achBuf, 15, "%f", m_pRecord->elevation);
            return s_achBuf;
        }
        else
            return NULL;
    }
    else if (strcasecmp(pEnvName, "REGION") == 0)
        return m_pRecord->region;
    else if (strcasecmp(pEnvName, "CITY") == 0)
        return m_pRecord->city;
    else if (strcasecmp(pEnvName, "ISP") == 0)
        return m_pRecord->isp;
    else if (strcasecmp(pEnvName, "DOMAIN") == 0)
        return m_pRecord->domain;
    else if (strcasecmp(pEnvName, "ZIPCODE") == 0)
        return m_pRecord->zipcode;
    else if (strcasecmp(pEnvName, "TIMEZONE") == 0)
        return m_pRecord->timezone;
    else if (strcasecmp(pEnvName, "NETSPEED") == 0)
        return m_pRecord->netspeed;
    else if (strcasecmp(pEnvName, "IDDCODE") == 0)
        return m_pRecord->iddcode;
    else if (strcasecmp(pEnvName, "AREACODE") == 0)
        return m_pRecord->areacode;
    else if (strcasecmp(pEnvName, "WEATHERSTATIONCODE") == 0)
        return m_pRecord->weatherstationcode;
    else if (strcasecmp(pEnvName, "WEATHERSTATIONNAME") == 0)
        return m_pRecord->weatherstationname;
    else if (strcasecmp(pEnvName, "MCC") == 0)
        return m_pRecord->mcc;
    else if (strcasecmp(pEnvName, "MNC") == 0)
        return m_pRecord->mnc;
    else if (strcasecmp(pEnvName, "MOBILEBRAND") == 0)
        return m_pRecord->mobilebrand;
    else if (strcasecmp(pEnvName, "USAGETYPE") == 0)
        return m_pRecord->usagetype;

    return NULL;
}


int LocInfo::addLocEnv(IEnv *pEnv)
{
    int count = 0;
    char achBuf[256];
    int len;

    if (!m_pRecord)
        return count;

    if (m_pRecord->country_short)
    {
        pEnv->add("IP2LOCATION_COUNTRY_SHORT", 25, m_pRecord->country_short,
                    strlen(m_pRecord->country_short));
        ++count;
    }
    if (m_pRecord->country_long)
    {
        pEnv->add("IP2LOCATION_COUNTRY_LONG", 24, m_pRecord->country_long,
                    strlen(m_pRecord->country_long));
        ++count;
    }
    if (m_pRecord->latitude)
    {
        len = sprintf(achBuf, "%f", m_pRecord->latitude);
        pEnv->add("IP2LOCATION_LATITUDE", 20, achBuf, len);
    }
    if (m_pRecord->longitude)
    {
        len = sprintf(achBuf, "%f", m_pRecord->longitude);
        pEnv->add("IP2LOCATION_LONGITUDE", 21, achBuf, len);
    }
    if (m_pRecord->elevation)
    {
        len = sprintf(achBuf, "%f", m_pRecord->elevation);
        pEnv->add("IP2LOCATION_ELEVATION", 21, achBuf, len);
    }
    if (m_pRecord->region)
    {
        pEnv->add("IP2LOCATION_REGION", 18, m_pRecord->region,
                    strlen(m_pRecord->region));
        ++count;
    }
    if (m_pRecord->city)
    {
        pEnv->add("IP2LOCATION_CITY", 16, m_pRecord->city,
                    strlen(m_pRecord->city));
        ++count;
    }
    if (m_pRecord->isp)
    {
        pEnv->add("IP2LOCATION_ISP", 15, m_pRecord->isp,
                    strlen(m_pRecord->isp));
        ++count;
    }
    if (m_pRecord->domain)
    {
        pEnv->add("IP2LOCATION_DOMAIN", 18, m_pRecord->domain,
                    strlen(m_pRecord->domain));
        ++count;
    }
    if (m_pRecord->zipcode)
    {
        pEnv->add("IP2LOCATION_ZIPCODE", 19, m_pRecord->zipcode,
                    strlen(m_pRecord->zipcode));
        ++count;
    }
    if (m_pRecord->timezone)
    {
        pEnv->add("IP2LOCATION_TIMEZONE", 20, m_pRecord->timezone,
                    strlen(m_pRecord->timezone));
        ++count;
    }
    if (m_pRecord->netspeed)
    {
        pEnv->add("IP2LOCATION_NETSPEED", 20, m_pRecord->netspeed,
                    strlen(m_pRecord->netspeed));
        ++count;
    }
    if (m_pRecord->iddcode)
    {
        pEnv->add("IP2LOCATION_IDDCODE", 19, m_pRecord->iddcode,
                    strlen(m_pRecord->iddcode));
        ++count;
    }
    if (m_pRecord->areacode)
    {
        pEnv->add("IP2LOCATION_AREACODE", 20, m_pRecord->areacode,
                    strlen(m_pRecord->areacode));
        ++count;
    }
    if (m_pRecord->weatherstationcode)
    {
        pEnv->add("IP2LOCATION_WEATHERSTATIONCODE", 30,
                    m_pRecord->weatherstationcode,
                    strlen(m_pRecord->weatherstationcode));
        ++count;
    }
    if (m_pRecord->weatherstationname)
    {
        pEnv->add("IP2LOCATION_WEATHERSTATIONNAME", 30,
                    m_pRecord->weatherstationname,
                    strlen(m_pRecord->weatherstationname));
        ++count;
    }
    if (m_pRecord->mcc)
    {
        pEnv->add("IP2LOCATION_MCC", 15, m_pRecord->mcc,
                    strlen(m_pRecord->mcc));
        ++count;
    }
    if (m_pRecord->mnc)
    {
        pEnv->add("IP2LOCATION_MNC", 15, m_pRecord->mnc,
                    strlen(m_pRecord->mnc));
        ++count;
    }
    if (m_pRecord->mobilebrand)
    {
        pEnv->add("IP2LOCATION_MOBILEBRAND", 23, m_pRecord->mobilebrand,
                    strlen(m_pRecord->mobilebrand));
        ++count;
    }
    if (m_pRecord->usagetype)
    {
        pEnv->add("IP2LOCATION_USAGETYPE", 21, m_pRecord->usagetype,
                    strlen(m_pRecord->usagetype));
        ++count;
    }
    return count;
}


IpToLoc::IpToLoc()
    : m_pDb(NULL)
{
}


IpToLoc::~IpToLoc()
{
    if (m_pDb)
        IP2Location_close(m_pDb);
}


int IpToLoc::loadIpToLocDbFile(char *pFile, int flag)
{
    IP2Location *pIpToLoc;
    pIpToLoc = IP2Location_open(pFile);

    if (!pIpToLoc)
    {
        LS_ERROR("Failed to open IP2Location DB file: %s", pFile);
        return LS_FAIL;
    }

    if (IP2Location_open_mem(pIpToLoc, (IP2Location_mem_type)flag) == -1)
    {
        LS_ERROR("loadIpToLocDbFile %s open mem failed.", pFile);
    }

    int fd = fileno(pIpToLoc->filehandle);
    if (fd != -1)
        ::fcntl(fd, F_SETFD, FD_CLOEXEC);

    if (m_pDb)
        IP2Location_close(m_pDb);
    m_pDb = pIpToLoc;

    return 0;
}


int IpToLoc::testIpToLocDbFile(char *pFile, int flag)
{
    pid_t pid = fork();
    if (pid < 0)
        return -1;
    if (pid == 0)
    {
        int ret = loadIpToLocDbFile(pFile, flag);
        if (ret == 0)
        {
            const char *addr = "88.252.206.167";
            LocInfo info;
            lookUp(addr, strlen(addr), &info);
        }
        exit(ret != 0);
    }
    else
    {
        int status;
        int wpid = waitpid(pid, &status, 0);
        if (wpid == pid && WIFEXITED(status) && WEXITSTATUS(status) == 0)
            return 0;
        LS_ERROR("IpToLoc DB file test failed: '%s'.", pFile);
    }
    return -1;
}


int IpToLoc::setIpToLocDbFile(char *pFile, const char *cacheMode)
{
    int flag = IP2LOCATION_CACHE_MEMORY;
    if (!pFile)
        return -1;
    if (cacheMode)
    {
        if (strcasecmp(cacheMode, "FileIo") == 0)
            flag = IP2LOCATION_FILE_IO;
        else if (strcasecmp(cacheMode, "MemoryCache") == 0)
            flag = IP2LOCATION_CACHE_MEMORY;
        else if (strcasecmp(cacheMode, "SharedMemoryCache") == 0)
            flag = IP2LOCATION_SHARED_MEMORY;
        else
        {
            //set a wrong mode, have to quit
            return -1;
        }
    }
    if (testIpToLocDbFile(pFile, flag) != 0)
        return -1;
    return loadIpToLocDbFile(pFile, flag);
}


int IpToLoc::lookUp(const char *pIpStr, int ipStrLen, LocInfo *pInfo)
{
    char sIp[256];
    if (!m_pDb || !pIpStr || !pInfo || ipStrLen < 7 || ipStrLen > 255)
        return LS_FAIL;

    if (*pIpStr == '[' && pIpStr[ipStrLen - 1] == ']')
    {
        ipStrLen -= 2;
        ++pIpStr;
    }
    memcpy(sIp, pIpStr, ipStrLen);
    sIp[ipStrLen] = '\0';

    pInfo->m_pRecord = IP2Location_get_all(m_pDb, sIp);
    return 0;
}


int IpToLoc::config(const XmlNodeList *pList)
{
    XmlNodeList::const_iterator iter;
    int succ = 0;

    for (iter = pList->begin(); iter != pList->end(); ++iter)
    {
        XmlNode *p = *iter;
        const char *pFile = p->getValue();
        char achBufFile[MAX_PATH_LEN];

        if ((!pFile) ||
            (ConfigCtx::getCurConfigCtx()->getValidFile(achBufFile, pFile,
                    "IpToLoc DB") != 0))
            continue;

        if (setIpToLocDbFile(achBufFile, p->getChildValue("iptolocDBCache")) == 0)
            succ = 1;
    }

    if (succ)
    {
        IpToLoc::setIpToLoc(this);
    }
    else
    {
        LS_WARN(ConfigCtx::getCurConfigCtx(),
                "Failed to setup a valid IP2Location DB file, Geolocation is disabled!");
        return LS_FAIL;
    }
    return 0;
}

#endif // USE_IP2LOCATION
