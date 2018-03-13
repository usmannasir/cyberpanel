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

#include "iptogeo.h"

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


IpToGeo *IpToGeo::s_pIpToGeo = NULL;


GeoInfo::GeoInfo()
    : m_netspeed(-1)
{
    memset(&m_countryId, 0, (char *)(&m_pIsp + 1) - (char *)&m_countryId);
}


GeoInfo::~GeoInfo()
{
    release();
}

void GeoInfo::reset()
{
    release();
    m_netspeed = -1;
    memset(&m_countryId, 0, (char *)(&m_pIsp + 1) - (char *)&m_countryId);
}

void GeoInfo::release()
{
    if (m_pRegion)
        GeoIPRegion_delete(m_pRegion);
    if (m_pCity)
        GeoIPRecord_delete(m_pCity);
    if (m_pOrg)
        free(m_pOrg);
    if (m_pIsp)
        free(m_pIsp);
}


const char *GeoInfo::getGeoEnv(const char *pEnvName)
{
    static char s_achBuf[15];
    if (strncasecmp(pEnvName, "GEOIP_", 6) == 0)
        pEnvName += 6;
    else if (strncasecmp(pEnvName, "GEO:", 4) == 0)
        pEnvName += 4;
    else
        return NULL;

    if (strncasecmp(pEnvName, "COUNTRY_", 8) == 0)
    {
        pEnvName += 8;
        if (strncasecmp(pEnvName, "CODE", 4) == 0)
        {

            if ((m_countryId > 0)
                && (m_countryId < (int)(sizeof(GeoIP_country_name) / sizeof(
                                            const char *))))
            {
                if (*(pEnvName + 4) == '3')
                    return GeoIP_country_code3[m_countryId];
                else
                    return GeoIP_country_code[m_countryId];
            }
            else if (m_pRegion)
                return m_pRegion->country_code;
            else if (m_pCity)
                return m_pCity->country_code;
        }
        else if (strcasecmp(pEnvName, "NAME") == 0)
        {
            if ((m_countryId > 0)
                && (m_countryId < (int)(sizeof(GeoIP_country_name) / sizeof(
                                            const char *))))
                return GeoIP_country_name[m_countryId];
            else if (m_pCity)
                return m_pCity->country_name;
        }
        else if (strcasecmp(pEnvName, "CONTINENT") == 0)
        {
            if ((m_countryId > 0)
                && (m_countryId < (int)(sizeof(GeoIP_country_name) / sizeof(
                                            const char *))))
                return GeoIP_country_continent[ m_countryId ];
            else if (m_pCity)
                return m_pCity->continent_code;

        }
    }
    else if (strcasecmp(pEnvName, "REGION") == 0)
    {
        if (m_pRegion)
        {
            if (m_pRegion->region[0])
                return m_pRegion->region;
        }
        if (m_pCity)
            return m_pCity->region;
    }
    else if (strcasecmp(pEnvName, "CONTINENT_CODE") == 0)
    {
        if ((m_countryId > 0)
            && (m_countryId < (int)(sizeof(GeoIP_country_name) / sizeof(
                                        const char *))))
            return GeoIP_country_continent[m_countryId];
        else if (m_pCity)
            return m_pCity->continent_code;
    }
    else if (strcasecmp(pEnvName, "CITY") == 0)
    {
        if (m_pCity)
            return m_pCity->city;
    }
    else if (strcasecmp(pEnvName, "POSTAL_CODE") == 0)
    {
        if (m_pCity && m_pCity->postal_code)
            return m_pCity->postal_code;
    }
    else if (strcasecmp(pEnvName, "NETSPEED") == 0)
    {
        switch (m_netspeed)
        {
        case GEOIP_DIALUP_SPEED:
            return "dialup";
        case GEOIP_CABLEDSL_SPEED:
            return "cabledsl";
        case GEOIP_CORPORATE_SPEED:
            return "corporate";
        case GEOIP_UNKNOWN_SPEED:
        case -1:
            return NULL;
        default:
            return "unknown";
        }
    }
    else if (strcasecmp(pEnvName, "ORGANIZATION") == 0)
        return m_pOrg;
    else if (strcasecmp(pEnvName, "ISP") == 0)
        return m_pIsp;
    else if ((strcasecmp(pEnvName, "AREA_CODE") == 0) ||
             (strcasecmp(pEnvName, "DMA_CODE") == 0))
    {
        snprintf(s_achBuf, 15, "%d", m_pCity->area_code);
        return s_achBuf;
    }
    return NULL;
}


int GeoInfo::addGeoEnv(IEnv *pEnv)
{
    int count = 0;
    const char *pStr;
    int len;
    if ((m_countryId > 0)
        && (m_countryId < (int)(sizeof(GeoIP_country_name) / sizeof(
                                    const char *))))
    {
        pStr = GeoIP_country_name[m_countryId];
        pEnv->add("GEOIP_COUNTRY_CODE", 18, GeoIP_country_code[m_countryId], 2);
        pEnv->add("GEOIP_COUNTRY_NAME", 18, pStr, strlen(pStr));
        pStr = GeoIP_country_continent[ m_countryId ];
        pEnv->add("GEOIP_CONTINENT_CODE", 20, pStr, 2);

        count += 3;
    }

    if (m_netspeed != -1)
    {
        switch (m_netspeed)
        {
        case GEOIP_DIALUP_SPEED:
            pStr = "dialup";
            len = 6;
            break;

        case GEOIP_CABLEDSL_SPEED:
            pStr = "cabledsl";
            len = 8;
            break;

        case GEOIP_CORPORATE_SPEED:
            pStr = "corporate";
            len = 9;
            break;

        case GEOIP_UNKNOWN_SPEED:
        default:
            pStr = "unknown";
            len = 7;
            break;
        }
        pEnv->add("GEOIP_NETSPEED", 14, pStr, len);
        ++count;
    }

    if (m_pRegion)
    {
        pEnv->add("GEOIP_COUNTRY_CODE", 18, m_pRegion->country_code, 2);
        ++count;
        if (m_pRegion->region[0])
        {
            pEnv->add("GEOIP_REGION", 12, m_pRegion->region,
                      strlen(m_pRegion->region));
            ++count;
            pStr = GeoIP_region_name_by_code(m_pRegion->country_code,
                                             m_pRegion->region);
            if (pStr)
            {
                pEnv->add("GEOIP_REGION_NAME", 17, pStr, strlen(pStr));
                ++count;
            }
        }
    }

    if (m_pCity)
    {
        char achBuf[256];
        len = snprintf(achBuf, 256, "%d", m_pCity->dma_code);
        pEnv->add("GEOIP_DMA_CODE", 14, achBuf, len);
        pEnv->add("GEOIP_METRO_CODE", 16, achBuf, len);

        len = snprintf(achBuf, 256, "%d", m_pCity->area_code);
        pEnv->add("GEOIP_AREA_CODE", 15, achBuf, len);

        len = snprintf(achBuf, 256, "%f", m_pCity->latitude);
        pEnv->add("GEOIP_LATITUDE", 14, achBuf, len);

        len = snprintf(achBuf, 256, "%f", m_pCity->longitude);
        pEnv->add("GEOIP_LONGITUDE", 15, achBuf, len);

        pEnv->add("GEOIP_COUNTRY_CODE", 18, m_pCity->country_code, 2);

        if (m_pCity->country_name)
        {
            pEnv->add("GEOIP_COUNTRY_NAME", 18, m_pCity->country_name,
                      strlen(m_pCity->country_name));
            pEnv->add("GEOIP_CONTINENT_CODE", 20, m_pCity->continent_code, 2);
        }

        len = snprintf(achBuf, 256, "%d", m_pCity->area_code);
        pEnv->add("GEOIP_AREA_CODE", 15, achBuf, len);
        count += 9;

        if (m_pCity->postal_code)
        {
            pEnv->add("GEOIP_POSTAL_CODE", 17, m_pCity->postal_code,
                      strlen(m_pCity->postal_code));
            ++count;
        }

        if (m_pCity->region)
        {
            pEnv->add("GEOIP_REGION", 12, m_pCity->region,
                      strlen(m_pCity->region));
            ++count;
            pStr = GeoIP_region_name_by_code(m_pCity->country_code, m_pCity->region);
            if (pStr)
            {
                pEnv->add("GEOIP_REGION_NAME", 17, pStr, strlen(pStr));
                ++count;
            }
        }

        if (m_pCity->city)
        {
            pEnv->add("GEOIP_CITY", 10, m_pCity->city,
                      strlen(m_pCity->city));
            ++count;
        }
    }

    if (m_pOrg)
    {
        pEnv->add("GEOIP_ORGANIZATION", 18, m_pOrg, strlen(m_pOrg));
        ++count;
    }

    if (m_pIsp)
    {
        pEnv->add("GEOIP_ISP", 9, m_pIsp, strlen(m_pIsp));
        ++count;
    }
    return count;
}


/*
void GeoInfo::addGeoEnv( HttpReq * pReq )
{
    const char * pStr;
    int len;
    if ( m_countryId )
    {
        pStr = GeoIP_country_name[m_countryId];
        pReq->addEnv( "GEOIP_COUNTRY_CODE", 18, GeoIP_country_code[m_countryId], 2 );
        pReq->addEnv( "GEOIP_COUNTRY_NAME", 18, pStr, strlen( pStr ) );
    }

    if ( m_netspeed != -1)
    {
        switch( m_netspeed )
        {
        case GEOIP_DIALUP_SPEED:
            pStr = "dialup";
            len = 6;
            break;

        case GEOIP_CABLEDSL_SPEED:
            pStr = "cabledsl";
            len = 8;
            break;

        case GEOIP_CORPORATE_SPEED:
            pStr = "corporate";
            len = 9;
            break;

        case GEOIP_UNKNOWN_SPEED:
        default:
            pStr = "unknown";
            len = 7;
            break;
        }
        pReq->addEnv( "GEOIP_NETSPEED", 14, pStr, len );
    }

    if ( m_pRegion )
    {
        pReq->addEnv( "GEOIP_COUNTRY_CODE", 18, m_pRegion->country_code, 2 );
        if (m_pRegion->region[0])
        {
            pReq->addEnv( "GEOIP_REGION", 12, m_pRegion->region, strlen( m_pRegion->region ));
        }
    }

    if ( m_pCity )
    {
        char achBuf[256];
        len = snprintf( achBuf, 256, "%d", m_pCity->dma_code );
        pReq->addEnv( "GEOIP_DMA_CODE", 14, achBuf, len );

        len = snprintf( achBuf, 256, "%d", m_pCity->area_code );
        pReq->addEnv( "GEOIP_AREA_CODE", 15, achBuf, len );

        len = snprintf( achBuf, 256, "%f", m_pCity->latitude );
        pReq->addEnv( "GEOIP_LATITUDE", 14, achBuf, len );

        len = snprintf( achBuf, 256, "%f", m_pCity->longitude );
        pReq->addEnv( "GEOIP_LONGITUDE", 15, achBuf, len );

        pReq->addEnv( "GEOIP_POSTAL_CODE", 17, m_pCity->postal_code,
                    strlen( m_pCity->postal_code ) );

        pReq->addEnv( "GEOIP_COUNTRY_CODE", 17, m_pCity->country_code, 2 );

        pReq->addEnv( "GEOIP_COUNTRY_NAME", 17, m_pCity->country_name,
                    strlen( m_pCity->country_name ) );

        pReq->addEnv( "GEOIP_REGION", 12, m_pCity->region,
                    strlen( m_pCity->region ) );

        pReq->addEnv( "GEOIP_CITY", 17, m_pCity->city,
                    strlen( m_pCity->city ) );
    }

    if ( m_pOrg )
    {
        pReq->addEnv( "GEOIP_ORGANIZATION", 18, m_pOrg, strlen( m_pOrg ) );
    }

    if ( m_pIsp )
    {
        pReq->addEnv( "GEOIP_ISP", 18, m_pIsp, strlen( m_pIsp ) );
    }

}
*/


IpToGeo::IpToGeo()
    : m_pLocation(NULL)
    , m_pOrg(NULL)
    , m_pIsp(NULL)
    , m_pNetspeed(NULL)
{
}

IpToGeo::~IpToGeo()
{
    if (m_pLocation)
        GeoIP_delete(m_pLocation);
    if (m_pOrg)
        GeoIP_delete(m_pOrg);
    if (m_pIsp)
        GeoIP_delete(m_pIsp);
    if (m_pNetspeed)
        GeoIP_delete(m_pNetspeed);
}


int IpToGeo::loadGeoIpDbFile(const char *pFile, int flag)
{
    GeoIP *pGip;
    pGip = GeoIP_open(pFile, flag);
    if (!pGip)
    {
        LS_ERROR("Failed to open GeoIP DB file: %s", pFile);
        return LS_FAIL;
    }
    int fd = fileno(pGip->GeoIPDatabase);
    if (fd != -1)
        ::fcntl(fd, F_SETFD, FD_CLOEXEC);

    flag = GeoIP_database_edition(pGip);
    switch (flag)
    {
    case GEOIP_COUNTRY_EDITION:
    case GEOIP_REGION_EDITION_REV0:
    case GEOIP_REGION_EDITION_REV1:
    case GEOIP_CITY_EDITION_REV0:
    case GEOIP_CITY_EDITION_REV1:
        if (m_pLocation)
            GeoIP_delete(m_pLocation);
        m_pLocation = pGip;
        m_locDbType = flag;
        break;

    case GEOIP_ORG_EDITION:
        if (m_pOrg)
            GeoIP_delete(m_pOrg);
        m_pOrg = pGip;
        break;

    case GEOIP_ISP_EDITION:
        if (m_pIsp)
            GeoIP_delete(m_pIsp);
        m_pIsp = pGip;
        break;

    case GEOIP_NETSPEED_EDITION:
        if (m_pNetspeed)
            GeoIP_delete(m_pNetspeed);
        m_pNetspeed = pGip;
        break;

    default:
        GeoIP_delete(pGip);
        return LS_FAIL;
    }
    return 0;
}


int IpToGeo::testGeoIpDbFile(const char *pFile, int flag)
{
    pid_t pid = fork();
    if (pid < 0)
        return -1;
    if (pid == 0)
    {
        int ret = loadGeoIpDbFile(pFile, flag);
        if (ret == 0)
        {
            unsigned char addr[4] = { 88, 252, 206, 167 };
            GeoInfo info;
            lookUp(*((int *)&addr), &info);
        }
        exit(ret != 0);
    }
    else
    {
        int status;
        int wpid = waitpid(pid, &status, 0);
        if (wpid == pid && WIFEXITED(status) && WEXITSTATUS(status) == 0)
            return 0;
        LS_ERROR("GeoIP DB file test failed: '%s'.", pFile);
    }
    return -1;
}


int IpToGeo::setGeoIpDbFile(const char *pFile, const char *cacheMode)
{
    int flag = GEOIP_MEMORY_CACHE;
    if (!pFile)
        return -1;
    if (cacheMode)
    {
        if (strcasecmp(cacheMode, "Standard") == 0)
            flag = GEOIP_STANDARD;
        else if (strcasecmp(cacheMode, "MemoryCache") == 0)
            flag = GEOIP_MEMORY_CACHE;
        else if (strcasecmp(cacheMode, "CheckCache") == 0)
            flag = GEOIP_CHECK_CACHE;
        else if (strcasecmp(cacheMode, "IndexCache") == 0)
            flag = GEOIP_INDEX_CACHE;
    }
    if (testGeoIpDbFile(pFile, flag) != 0)
        return -1;
    return loadGeoIpDbFile(pFile, flag);
}


int IpToGeo::lookUp(uint32_t addr, GeoInfo *pInfo)
{
    addr = htonl(addr);
    if (m_pLocation)
    {
        switch (m_locDbType)
        {
        case GEOIP_COUNTRY_EDITION:
            pInfo->m_countryId = GeoIP_id_by_ipnum(m_pLocation, addr);
            break;

        case GEOIP_REGION_EDITION_REV0:
        case GEOIP_REGION_EDITION_REV1:
            pInfo->m_pRegion = GeoIP_region_by_ipnum(m_pLocation, addr);
            break;

        case GEOIP_CITY_EDITION_REV0:
        case GEOIP_CITY_EDITION_REV1:
            pInfo->m_pCity = GeoIP_record_by_ipnum(m_pLocation, addr);
            break;
        }

    }
    if (m_pOrg)
        pInfo->m_pOrg = GeoIP_name_by_ipnum(m_pOrg, addr);
    if (m_pIsp)
        pInfo->m_pIsp = GeoIP_name_by_ipnum(m_pIsp, addr);
    if (m_pNetspeed)
        pInfo->m_netspeed = GeoIP_id_by_ipnum(m_pNetspeed, addr);
    return 0;
}

int IpToGeo::lookUpV6(in6_addr addr, GeoInfo *pInfo)
{
    if (m_pLocation)
    {
        switch (m_locDbType)
        {
        case GEOIP_REGION_EDITION_REV0:
        case GEOIP_REGION_EDITION_REV1:
            pInfo->m_pRegion = GeoIP_region_by_ipnum_v6(m_pLocation, addr);
            break;
        case GEOIP_COUNTRY_EDITION_V6:
            pInfo->m_countryId = GeoIP_id_by_ipnum_v6(m_pLocation, addr);
            break;
        }

    }
    if (m_pOrg)
        pInfo->m_pOrg = GeoIP_name_by_ipnum_v6(m_pOrg, addr);
    if (m_pIsp)
        pInfo->m_pIsp = GeoIP_name_by_ipnum_v6(m_pIsp, addr);
    if (m_pNetspeed)
        pInfo->m_netspeed = GeoIP_id_by_ipnum_v6(m_pNetspeed, addr);
    return 0;
}

int IpToGeo::lookUp(const char *pIP, GeoInfo *pInfo)
{
    in_addr_t addr = inet_addr(pIP);
    if (addr == INADDR_BROADCAST)
        return LS_FAIL;
    return lookUp(addr, pInfo);
}


int IpToGeo::config(const XmlNodeList *pList)
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
                    "GeoIP DB") != 0))
            continue;

        if (setGeoIpDbFile(achBufFile, p->getChildValue("geoipDBCache")) == 0)
            succ = 1;
    }

    if (succ)
        IpToGeo::setIpToGeo(this);
    else
    {
        LS_WARN(ConfigCtx::getCurConfigCtx(),
                "Failed to setup a valid GeoIP DB file, Geolocation is disable!");
        return LS_FAIL;
    }
    return 0;
}
