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
#include "sslerror.h"
#include <openssl/err.h>
#include <string.h>

#define MSG_MAX_LEN sizeof( m_achMsg ) - 1

SslError::SslError() throw()
{
    char *p = m_achMsg;
    char *pEnd = &m_achMsg[MSG_MAX_LEN] - 1;
    const char *data;
    int flag;
    int iError;
    while ((iError = ERR_peek_error_line_data(NULL, NULL, &data, &flag)) != 0)
    {

        ERR_error_string_n(iError, p, pEnd - p);
        p += strlen(p);
        if (*data && (flag & ERR_TXT_STRING))
        {
            *p++ = ':';
            strncpy(p, data, pEnd - p);
        }
        p += strlen(p);
        ERR_get_error();
    }
}


SslError::SslError(int err) throw()
{
    m_achMsg[MSG_MAX_LEN] = 0;
    m_iError = err;
    ERR_error_string_n(m_iError, m_achMsg, MSG_MAX_LEN);
}


SslError::SslError(const char *pErr) throw()
{
    if (pErr)
    {
        m_achMsg[MSG_MAX_LEN] = 0;
        m_iError = -1;
        memccpy(m_achMsg, pErr, 0, MSG_MAX_LEN);
    }
    else
        m_achMsg[0] = 0;
}


SslError::~SslError() throw()
{
}
