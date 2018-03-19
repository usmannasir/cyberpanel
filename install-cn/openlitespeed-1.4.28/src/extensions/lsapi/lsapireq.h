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
#ifndef LSAPIREQ_H
#define LSAPIREQ_H

#include "lsapidef.h"

#include <lsdef.h>
#include <util/autobuf.h>

class HttpSession;
class HttpReq;
class IOVec;
class LsapiEnv;
struct lsapi_packet_header;

class LsapiReq
{
    AutoBuf     m_bufReq;
    IOVec      *m_pIovec;

    int appendEnv(LsapiEnv *pEnv, HttpSession *pSession);
    int appendSpecialEnv(LsapiEnv *pEnv, HttpSession *pSession,
                         struct lsapi_req_header *pHeader);
    int appendHttpHeaderIndex(HttpReq *pReq, int cntUnknown);
    int dumpReq(char *pFile);

public:
    LsapiReq(IOVec *pIovec);

    ~LsapiReq();

    static int addEnv(AutoBuf *pAutoBuf, const char *name,
                      size_t nameLen, const char *value, size_t valLen);
    int buildReq(HttpSession *pSession, int *totalLen);
    static void buildPacketHeader(struct lsapi_packet_header *pHeader,
                                  char type, int len)
    {
        pHeader->m_versionB0 = LSAPI_VERSION_B0;      //LSAPI protocol version
        pHeader->m_versionB1 = LSAPI_VERSION_B1;
        pHeader->m_type      = type;
        pHeader->m_flag      = LSAPI_ENDIAN;
        pHeader->m_packetLen.m_iLen = len;
    }
    LS_NO_COPY_ASSIGN(LsapiReq);
};

#endif
