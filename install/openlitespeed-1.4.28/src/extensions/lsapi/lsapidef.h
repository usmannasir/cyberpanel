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
#ifndef  _LSAPIDEF_H_
#define  _LSAPIDEF_H_

#include <inttypes.h>

#if defined (c_plusplus) || defined (__cplusplus)
extern "C" {
#endif

    enum
    {
        H_ACCEPT = 0,
        H_ACC_CHARSET,
        H_ACC_ENCODING,
        H_ACC_LANG,
        H_AUTHORIZATION,
        H_CONNECTION,
        H_CONTENT_TYPE,
        H_CONTENT_LENGTH,
        H_COOKIE,
        H_COOKIE2,
        H_HOST,
        H_PRAGMA,
        H_REFERER,
        H_USERAGENT,
        H_CACHE_CTRL,
        H_IF_MODIFIED_SINCE,
        H_IF_MATCH,
        H_IF_NO_MATCH,
        H_IF_RANGE,
        H_IF_UNMOD_SINCE,
        H_KEEP_ALIVE,
        H_RANGE,
        H_X_FORWARDED_FOR,
        H_VIA,
        H_TRANSFER_ENCODING

    };
#define LSAPI_SOCK_FILENO           0

#define LSAPI_VERSION_B0            'L'
#define LSAPI_VERSION_B1            'S'

//Values for m_flag in lsapi_packet_header
#define LSAPI_ENDIAN_LITTLE         0
#define LSAPI_ENDIAN_BIG            1
#define LSAPI_ENDIAN_BIT            1

#if defined(__i386__)||defined( __x86_64 )||defined( __x86_64__ )
#define LSAPI_ENDIAN                LSAPI_ENDIAN_LITTLE
#else
#define LSAPI_ENDIAN                LSAPI_ENDIAN_BIG
#endif

//Values for m_type in lsapi_packet_header
#define LSAPI_BEGIN_REQUEST         1
#define LSAPI_ABORT_REQUEST         2
#define LSAPI_RESP_HEADER           3
#define LSAPI_RESP_STREAM           4
#define LSAPI_RESP_END              5
#define LSAPI_STDERR_STREAM         6
#define LSAPI_REQ_RECEIVED          7


#define LSAPI_MAX_HEADER_LEN        65535
#define LSAPI_MAX_DATA_PACKET_LEN   16384

#define LSAPI_RESP_HTTP_HEADER_MAX  4096
#define LSAPI_PACKET_HEADER_LEN     8

    struct lsapi_packet_header
    {
        char    m_versionB0;      //LSAPI protocol version
        char    m_versionB1;
        char    m_type;
        char    m_flag;
        union
        {
            int32_t m_iLen;    //include this header
            char    m_bytes[4];
        } m_packetLen;
    };

// LSAPI request header packet
//
// 1. struct lsapi_req_header
// 2. struct lsapi_http_header_index
// 3. lsapi_header_offset * unknownHeaders
// 4. org http request header
// 5. request body if available

    struct lsapi_req_header
    {
        struct lsapi_packet_header m_pktHeader;

        int32_t m_httpHeaderLen;
        int32_t m_reqBodyLen;
        int32_t m_scriptFileOff;   //path to the script file.
        int32_t m_scriptNameOff;   //decrypted URI, without pathinfo,
        int32_t m_queryStringOff;  //Query string inside env
        int32_t m_requestMethodOff;
        int32_t m_cntUnknownHeaders;
        int32_t m_cntEnv;
        int32_t m_cntSpecialEnv;
    } ;


    struct lsapi_http_header_index
    {
        int16_t m_headerLen[H_TRANSFER_ENCODING + 1];
        int32_t m_headerOff[H_TRANSFER_ENCODING + 1];
    } ;

    struct lsapi_header_offset
    {
        int32_t nameOff;
        int32_t nameLen;
        int32_t valueOff;
        int32_t valueLen;
    } ;

    struct lsapi_resp_info
    {
        int32_t m_cntHeaders;
        int32_t m_status;
    };

    struct lsapi_resp_header
    {
        struct  lsapi_packet_header  m_pktHeader;
        struct  lsapi_resp_info      m_respInfo;
    };

#if defined (c_plusplus) || defined (__cplusplus)
}
#endif


#endif

