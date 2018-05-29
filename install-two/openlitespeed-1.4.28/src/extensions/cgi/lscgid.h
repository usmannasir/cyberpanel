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
#ifndef LSCGID_H_
#define LSCGID_H_

#include "lscgiddef.h"

#ifdef __cplusplus
extern "C"
{
#endif

extern int lscgid_main(int fd, char *argv0, const char *secret,
                       char *pServerSock);

typedef struct
{
    lscgid_req  m_data;
    char       *m_pBuf;
    char       *m_pChroot;
    char       *m_pCGIDir;
    char      **m_argv;
    char      **m_env;
    int         m_fdReceived;

} lscgid_t;



#ifdef __cplusplus
}
#endif

#endif

