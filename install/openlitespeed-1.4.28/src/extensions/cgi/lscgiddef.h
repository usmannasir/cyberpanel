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
#ifndef LSCGIDDEF_H_
#define LSCGIDDEF_H_

#include <sys/types.h>
#include <sys/time.h>
#include <sys/resource.h>

#ifdef __cplusplus
extern "C"
{
#endif

#define LSCGID_LISTENSOCK_FD    0

#define LSCGID_VERSION_1         1

#define LSCGID_NAME             "lscgid"
#define LSCGID_SECRET           "LSCGID_SECRET"
#define LSCGID_SOCK             "LSCGID_SOCK"

#define LSCGID_TYPE_CGI         0
#define LSCGID_TYPE_SUEXEC      1

typedef struct
{
    short   m_version;
    short   m_type;
    int     m_reqid;
    int     m_szData;
    int     m_nenv;

    unsigned short m_nargv;
    unsigned short m_chrootPathLen;     //if chroot to '/', m_chrootPathLen = 0
    unsigned short m_exePathLen;
    unsigned short m_exeNameLen;

    uid_t   m_uid;
    gid_t   m_gid;
    int     m_priority;
    int     m_umask;


#if defined(RLIMIT_AS) || defined(RLIMIT_DATA) || defined(RLIMIT_VMEM)
    struct rlimit   m_data;
#endif
#if defined(RLIMIT_NPROC)
    struct rlimit   m_nproc;
#endif
#if defined(RLIMIT_CPU)
    struct rlimit   m_cpu;
#endif
    unsigned char   m_nonce[16];
    unsigned char   m_md5[16];

} lscgid_req;


#ifdef __cplusplus
}
#endif

#endif

