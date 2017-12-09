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
#include "statusurlmap.h"

#include <http/httplog.h>
#include <util/autostr.h>

#include <stdlib.h>
#include <string.h>



StatusUrlMap::StatusUrlMap()
{
    memset(m_pSC, 0, sizeof(m_pSC));
}


StatusUrlMap::StatusUrlMap(const StatusUrlMap &rhs)
{
    int i;
    memset(m_pSC, 0, sizeof(m_pSC));
    for (i = 0 ; i < SC_END ; ++i)
        if (rhs.m_pSC[i] != NULL)
            m_pSC[i] = new AutoStr2(*rhs.m_pSC[i]);
}


StatusUrlMap::~StatusUrlMap()
{
    int i;
    for (i = 0 ; i < SC_END ; ++i)
        if (m_pSC[i] != NULL)
            delete m_pSC[i];

}


int StatusUrlMap::setUrl(int statusCode, const char *url)
{

    int index = HttpStatusCode::getInstance().codeToIndex(statusCode);
    if ((index > 0) && (index < SC_END))
    {
        if (*(m_pSC + index) == NULL)
            *(m_pSC + index) = new AutoStr2(url);
        else
            (*(m_pSC + index))->setStr(url, strlen(url));
        return 0;
    }
    else
    {
        HttpLog::error("Invalid status code in set status code URL mapping! %d - %s\n",
                       statusCode, url);
        return -1 ;
    }

    return 0;
}


int StatusUrlMap::setStatusUrlMap(int statusCode, const char *url)
{
    if (url == NULL)
    {
        HttpLog::error("Invalid Url in set status code URL mapping! %d - %s\n",
                       statusCode, url);
        return -1 ;
    }

    return setUrl(statusCode, url);

}


int StatusUrlMap::inherit(const StatusUrlMap *pMap)
{
    if (!pMap)
        return 0;
    for (int i = 0 ; i < SC_END ; ++i)
        if ((pMap->m_pSC[i] != NULL) && (m_pSC[i] == NULL))
            m_pSC[i] = new AutoStr2(*pMap->m_pSC[i]);
    return 0;
}

