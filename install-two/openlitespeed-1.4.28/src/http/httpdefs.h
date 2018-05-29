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
#ifndef HTTPDEFS_H_
#define HTTPDEFS_H_

#include <limits.h>


#define HEADER_BUF_PAD          4
#define DEFAULT_HTTP_PORT       80
#define MAX_BUF_SIZE            8192
#define MAX_URL_LEN             MAX_BUF_SIZE

#define THROTTLE_UNIT           4096
#define MAX_REQ_HEADER_BUF_LEN  (8192*2 - HEADER_BUF_PAD)
#define MAX_REQ_BODY_LEN        (LLONG_MAX - 1)
#define MAX_DYN_RESP_LEN        LLONG_MAX
#define MAX_DYN_RESP_HEADER_LEN 65536

#define DEFAULT_URL_LEN             2048
#define DEFAULT_REQ_HEADER_BUF_LEN  8192
#define DEFAULT_REQ_BODY_LEN        (2 * 1024 * 1024)
#define DEFAULT_DYN_RESP_HEADER_LEN 4096
#define DEFAULT_DYN_RESP_LEN        (2 * 1024 * 1024)

#define DEFAULT_CONN_LOW_MARK   5


#define DEFAULT_MAX_CONNS     INT_MAX
#define DEFAULT_MAX_SSL_CONNS INT_MAX
#define MAX_VHOSTS            INT_MAX
#define DEFAULT_INIT_POLL_SIZE  4096


#define HEC_RESP_GZIP           (1<<8)
#define HEC_RESP_CONN_CLOSE     (1<<9)
#define HEC_RESP_NPH            (1<<10)
#define HEC_RESP_NOBUFFER       (1<<11)
#define HEC_RESP_NPH2           (1<<12)
#define HEC_RESP_AUTHORIZER     (1<<13)
#define HEC_RESP_AUTHORIZED     (1<<14)
#define HEC_RESP_HTTP_10        (1<<15)
#define HEC_RESP_CONT_LEN       (1<<16)
//#define HEC_RESP_LOC_SET        (1<<17)
#define HEC_RESP_PROXY          (1<<18)


#define TIMER_PRECISION 10


#endif //HTTPDEFS_H_


