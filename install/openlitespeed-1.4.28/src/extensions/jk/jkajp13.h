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
#ifndef JKAJP13_H
#define JKAJP13_H


#include <lsdef.h>

#define AJP_REQ_PREFIX_B1       0x12
#define AJP_REQ_PREFIX_B2       0x34

#define AJP_RESP_PREFIX_B1      0x41 //'A'
#define AJP_RESP_PREFIX_B2      0x42 //'B'

#define AJP_HEADER_LEN          0x04

#define AJP_MAX_PACKET_SIZE     8192
#define AJP_MAX_PKT_BODY_SIZE   (AJP_MAX_PACKET_SIZE - AJP_HEADER_LEN )

#define AJP13_FORWARD_REQUEST   0x02
#define AJP13_RESP_BODY_CHUNK   0x03
#define AJP13_RESP_HEADERS      0x04
#define AJP13_END_RESP          0x05
#define AJP13_MORE_REQ_BODY     0x06
#define AJP13_SHUTDOWN          0x07
#define AJP13_PING              0x08


/* Second Login Phase (servlet engine -> web server), md5 seed is received */
#define AJP14_LOGON_SEED        0x11

/* Login Accepted (servlet engine -> web server) */
#define AJP14_LOGON_OK          0x13

/* Login Rejected (servlet engine -> web server) */
#define AJP14_LOGON_ERR         0x14

/* Dispatcher for jni channel ( jvm->C ) */
#define AJP14_JNI_DISPATCH      0x15

/* Dispatcher for shm object ( jvm->C) */
#define AJP14_SHM_DISPATCH      0x16

/* Dispatcher for channel components ( jvm->C )*/
#define AJP14_CH_DISPATCH       0x17

/* Dispatcher for mutex object  ( jvm->C ) */
#define AJP14_MUTEX_DISPATCH    0x18



/*
 * Frequent request headers, these headers are coded as numbers
 * instead of strings.
 */

#define AJP_ACCEPT              0xA001
#define AJP_ACCEPT_CHARSET      0xA002
#define AJP_ACCEPT_ENCODING     0xA003
#define AJP_ACCEPT_LANGUAGE     0xA004
#define AJP_AUTHORIZATION       0xA005
#define AJP_CONNECTION          0xA006
#define AJP_CONTENT_TYPE        0xA007
#define AJP_CONTENT_LENGTH      0xA008
#define AJP_COOKIE              0xA009
#define AJP_COOKIE2             0xA00A
#define AJP_HOST                0xA00B
#define AJP_PRAGMA              0xA00C
#define AJP_REFERER             0xA00D
#define AJP_USER_AGENT          0xA00E

/*
 * request attributes
 */
#define AJP_A_CONTEXT           1
#define AJP_A_SERVLET_PATH      2
#define AJP_A_REMOTE_USER       3
#define AJP_A_AUTH_TYPE         4
#define AJP_A_QUERY_STRING      5
#define AJP_A_JVM_ROUTE         6
#define AJP_A_SSL_CERT          7
#define AJP_A_SSL_CIPHER        8
#define AJP_A_SSL_SESSION       9
#define AJP_A_REQ_ATTRIBUTE     10
#define AJP_A_SSL_KEY_SIZE      11
#define AJP_A_SECRET            12
#define AJP_A_END               0xFF


/*
 * Frequent response headers, these headers are coded as numbers
 * instead of strings.
 *
 * Content-Type
 * Content-Language
 * Content-Length
 * Date
 * Last-Modified
 * Location
 * Set-Cookie
 * Servlet-Engine
 * Status
 * WWW-Authenticate
 *
 */
#define AJP_RESP_CONTENT_TYPE        0xA001
#define AJP_RESP_CONTENT_LANGUAGE    0xA002
#define AJP_RESP_CONTENT_LENGTH      0xA003
#define AJP_RESP_DATE                0xA004
#define AJP_RESP_LAST_MODIFIED       0xA005
#define AJP_RESP_LOCATION            0xA006
#define AJP_RESP_SET_COOKIE          0xA007
#define AJP_RESP_SET_COOKIE2         0xA008
#define AJP_RESP_SERVLET_ENGINE      0xA009
#define AJP_RESP_STATUS              0xA00A
#define AJP_RESP_WWW_AUTHENTICATE    0xA00B
#define AJP_RESP_HEADERS_NUM          11

class HttpSession;

class JWorker;

class JkAjp13
{
    static const char *s_pRespHeaders[AJP_RESP_HEADERS_NUM + 1];
    static int          s_iRespHeaderLen[AJP_RESP_HEADERS_NUM + 1];
public:
    JkAjp13();
    ~JkAjp13();
    static int buildReq(HttpSession *pSession, char *&p, char *pEnd);
    static int buildWorkerHeader(JWorker *pWorker, char *&p, char *pEnd);
    static void buildAjpHeader(char *pBuf, int size);
    static void buildAjpReqBodyHeader(char *pBuf, int size);
    static const char *getRespHeaderById(unsigned char id)
    {   return s_pRespHeaders[ id ];    }
    static int getRespHeaderLenById(unsigned char id)
    {   return s_iRespHeaderLen[id];    }
    LS_NO_COPY_ASSIGN(JkAjp13);
};

#endif
