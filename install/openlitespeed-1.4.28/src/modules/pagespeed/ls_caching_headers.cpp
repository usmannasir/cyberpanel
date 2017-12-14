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

#include "pagespeed.h"
#include <sys/uio.h>
#include "ls_caching_headers.h"

#define MAX_SAME_HEADER_NUM     5
bool LsiCachingHeaders::Lookup(const StringPiece &key,
                               StringPieceVector *values)
{
    iovec iov[MAX_SAME_HEADER_NUM];
    int n = g_api->get_resp_header(m_session, -1, key.as_string().c_str(),
                                   key.as_string().size(), iov,
                                   MAX_SAME_HEADER_NUM);

    if (n == 0)   // No header found with this name.
        return false;

    for (int i = 0; i < n; ++i)
    {
        StringPiece x;
        x.set(iov[i].iov_base, iov[i].iov_len);
        values->push_back(x);
    }

    for (int i = 0, n = values->size(); i < n; ++i)
        TrimWhitespace(& ((*values) [i]));

    return true;
}

