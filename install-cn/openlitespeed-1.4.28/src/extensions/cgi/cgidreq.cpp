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
#include "cgidreq.h"

#include <util/rlimits.h>
#include <util/stringtool.h>

#include <openssl/rand.h>
#include <stdio.h>

CgidReq::CgidReq()
    : m_buf(2048)
{
    clear();
}


CgidReq::~CgidReq()
{
}


int CgidReq::add(const char *name, size_t nameLen,
                 const char *value, size_t valLen)
{
    //assert( value );
    //assert( nameLen == strlen( name ) );
    //assert( valLen == strlen( value ) );
    int bufLen = m_buf.available();
    int len = nameLen + valLen + 4;
    if (len > 65530)
        return LS_FAIL;
    if (value && strncmp(value, "() {", 4) == 0)
        return LS_FAIL;
    if (bufLen < len)
    {
        int grow = ((len - bufLen + 1023) >> 10) << 10;
        int ret = m_buf.grow(grow);
        if (ret == -1)
            return ret;
    }
    char *pBuf = m_buf.end();
    if (name)
    {
#if defined( sparc )
        unsigned short l = len - 2;
        *pBuf++ = *(char *)&l;
        *pBuf++ = *(((char *)&l) + 1);
#else
        *(unsigned short *)pBuf = len - 2;
        pBuf += 2;
#endif
        memcpy(pBuf, name, nameLen);
        pBuf += nameLen;
        *pBuf++ = '=';
        memcpy(pBuf, value, valLen);
        pBuf += valLen;
        *pBuf++ = 0;
        m_buf.used(len);
    }
    else
    {
        m_buf.appendUnsafe('\0');
        m_buf.appendUnsafe('\0');
    }
    ++getCgidReq()->m_nenv;
    return 0;
}


int CgidReq::appendString(const char *pStr, size_t strlen)
{
    int bufLen = m_buf.available();
    int len = strlen + 3;
    if (len > 65530)
        return LS_FAIL;
    if (bufLen < len)
    {
        int grow = ((len - bufLen + 1023) >> 10) << 10;
        int ret = m_buf.grow(grow);
        if (ret == -1)
            return ret;
    }
    char *pBuf = m_buf.end();
    if (pStr)
    {
#if defined( sparc )
        unsigned short l = strlen + 1;
        *pBuf++ = *(char *)&l;
        *pBuf++ = *(((char *)&l) + 1);
#else
        *(unsigned short *)pBuf = strlen + 1;
        pBuf += 2;
#endif
        memcpy(pBuf, pStr, strlen);
        pBuf += strlen;
        *pBuf++ = 0;
        m_buf.used(len);
    }
    else
    {
        m_buf.appendUnsafe('\0');
        m_buf.appendUnsafe('\0');
    }
    return 0;
}


int CgidReq::appendArgv(const char *pArgv, int len)
{
    if (appendString(pArgv, len))
        return LS_FAIL;
    ++getCgidReq()->m_nargv;
    return 0;
}


int CgidReq::appendEnv(const char *pEnv, int len)
{
    if (appendString(pEnv, len))
        return LS_FAIL;
    ++getCgidReq()->m_nenv;
    return 0;
}


void CgidReq::clear()
{
    m_buf.resize(sizeof(lscgid_req));
    memset(m_buf.begin(), 0, sizeof(lscgid_req));
}


int CgidReq::buildReqHeader(int uid, int gid, int priority, int umaskVal,
                            const char *pChroot, int chrootLen,
                            const char *pReal, int pathLen, const RLimits *pLimits)
{
    lscgid_req *pHeader = getCgidReq();
    const char *pEnd;
    clear();
    //pReal = pReq->getRealPath()->c_str();
    pHeader->m_uid = uid;
    pHeader->m_gid = gid;
    if (pChroot)
    {
        pHeader->m_chrootPathLen = chrootLen + 1;
        add(pChroot, pHeader->m_chrootPathLen);
    }
    else
        pHeader->m_chrootPathLen = 0;
    pHeader->m_priority = priority;
    pHeader->m_umask = umaskVal;
    add(pReal, pathLen + 1);
    pEnd = pReal + pathLen;
    const char *p = pEnd;
    while (*(p - 1) != '/')
        --p;
    pHeader->m_exePathLen = p - pReal;
    pHeader->m_exeNameLen = pEnd - p;

    pHeader->m_nargv = 1;
    if (pLimits)
    {
        memmove(
#if defined(RLIMIT_AS) || defined(RLIMIT_DATA) || defined(RLIMIT_VMEM)
            &pHeader->m_data,
#elif defined(RLIMIT_NPROC)
            &pHeader->m_nproc,
#elif defined(RLIMIT_CPU)
            &pHeader->m_cpu,
#endif
            pLimits, sizeof(RLimits));
    }

    return 0;
}


int CgidReq::finalize(int req_id, const char *pSecret, int type)
{
    lscgid_req *pHeader = getCgidReq();
    pHeader->m_version = LSCGID_VERSION_1;
    pHeader->m_type = type;
    pHeader->m_reqid = req_id;
    pHeader->m_szData = size() - sizeof(lscgid_req);

    RAND_pseudo_bytes(pHeader->m_nonce, 16);
    memmove(pHeader->m_md5, pSecret, 16);
    StringTool::getMd5((const char *)pHeader, sizeof(lscgid_req),
                       pHeader->m_md5);
    return 0;
}



