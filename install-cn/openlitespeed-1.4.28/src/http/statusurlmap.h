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
#ifndef STATUSURLMAP_H
#define STATUSURLMAP_H


#include <http/httpstatuscode.h>

#define SC_300_LEN (SC_400 - SC_300)
#define SC_400_LEN (SC_500 - SC_400)
#define SC_500_LEN (SC_END - SC_500)

class AutoStr2;

class StatusUrlMap
{
private:
    AutoStr2   *m_pSC[SC_END];

    int setUrl(int statusCode, const char *url);

    void operator=(const StatusUrlMap &rhs);
public:
    StatusUrlMap();
    StatusUrlMap(const StatusUrlMap &rhs);
    ~StatusUrlMap();

    const AutoStr2 *getUrl(int statusCode) const
    {
        assert((statusCode >= SC_100) && (statusCode < SC_END));
        return *(m_pSC + statusCode);
        //return NULL;
    }
    int setStatusUrlMap(int statusCode, const char *url);
    int inherit(const StatusUrlMap *pMap);
};

#endif
