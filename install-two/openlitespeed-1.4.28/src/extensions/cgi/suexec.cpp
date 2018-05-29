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
#ifndef _XPG4_2
# define _XPG4_2
#endif

#include "suexec.h"
#include "cgidworker.h"
#include "cgidconfig.h"

#include <http/serverprocessconfig.h>
#include <log4cxx/logger.h>
#include <lsr/ls_fileio.h>
#include <socket/coresocket.h>
#include <util/pcutil.h>
#include <util/rlimits.h>
#include <util/stringtool.h>

#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/uio.h>
#include <time.h>
#include <unistd.h>


#if defined(__FreeBSD__)
# include <sys/param.h>
#endif


SUExec *SUExec::s_pSUExec = NULL;


SUExec::SUExec()
{
}


SUExec::~SUExec()
{
}


int SUExec::buildArgv(char *pCmd, char **pDir,
                      char **pArgv, int argvLen)
{
    if (!pCmd || !pDir || !pArgv)
        return LS_FAIL;
    *pDir = NULL;
    char *p = (char *)StringTool::strNextArg(pCmd);
    if (p)
        *p++ = 0;
    char *pAppName = strrchr(pCmd, '/');
    if (pAppName)
    {
        *pAppName++ = 0;
        *pDir = pCmd;
        pCmd = pAppName;
    }
    int nargv = 0;
    pArgv[nargv++] =  pCmd;
    if (p)
    {
        while (*p == ' ' || *p == '\t')
            ++p;
        while (*p)
        {
            if (nargv < argvLen - 1)
                pArgv[nargv++] = p;
            if (('"' == *p) || ('\'' == *p))
                ++pArgv[nargv - 1];
            p = (char *)StringTool::strNextArg(p);
            if (p)
                *p++ = 0;
            else
                break;
            while (*p == ' ' || *p == '\t')
                ++p;
        }
    }
    pArgv[nargv++] = NULL;
    return 0;
}


int SUExec::spawnChild(const char *pAppCmd, int fdIn, int fdOut,
                       char *const *env, int priority, const RLimits *pLimits,
                       int umaskVal, uid_t uid, gid_t gid)
{

    int forkResult;
    if (!pAppCmd)
        return LS_FAIL;
    sigset_t sigset_old;
    sigset_t sigset_new;
    sigemptyset(&sigset_new);
    sigaddset(&sigset_new, SIGALRM);
    sigaddset(&sigset_new, SIGCHLD);
    pthread_sigmask(SIG_BLOCK, &sigset_new, &sigset_old);
    forkResult = fork();
    pthread_sigmask(SIG_SETMASK, &sigset_old, NULL);

    if (forkResult)
        return forkResult;

    //Child process
    //if ( listenFd != STDIN_FILENO )
    //    close(STDIN_FILENO);
    if (fdIn != STDIN_FILENO)
    {
        dup2(fdIn, STDIN_FILENO);
        close(fdIn);
    }
    if (fdOut != -1)
    {
        dup2(fdOut, STDOUT_FILENO);
        close(fdOut);
    }
    else
        close(STDOUT_FILENO);

    if (pLimits)
    {
        pLimits->applyMemoryLimit();
        pLimits->applyProcLimit();
    }
    char *pPath = strdup(pAppCmd);
    char *argv[256];
    char *pDir ;
    buildArgv(pPath, &pDir, argv, 256);
    if (pDir)
    {
        if (chdir(pDir))
        {
            LS_ERROR("chdir(\"%s\") failed with errno=%d, "
                     "when try to start Fast CGI application: %s!",
                     pDir, errno, pAppCmd);
            exit(-1);
        }
        *(argv[0] - 1) = '/';
    }
    else
        pDir = argv[0];
    umask(umaskVal);
    if (getuid() == 0)
    {
        if (uid)
            setuid(uid);
        if (gid)
            setgid(gid);
    }
    setpriority(PRIO_PROCESS, 0, priority);
    PCUtil::setCpuAffinityAll();
    execve(pDir, &argv[0], env);
    LS_ERROR("execve() failed with errno=%d, "
             "when try to start Fast CGI application: %s!",
             errno, pAppCmd);
    exit(-1);
    return 0;
}


void generateSecret(char *pBuf)
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    srand((tv.tv_sec % 0x1000 + tv.tv_usec) ^ rand());
    for (int i = 0; i < 16; ++i)
        pBuf[i] = 33 + (int)(94.0 * rand() / (RAND_MAX + 1.0));
    pBuf[16] = 0;
}


int SUExec::checkLScgid(const char *path)
{
    struct stat st;
    if ((ls_fio_stat(path, &st) == -1) || !(st.st_mode & S_IXOTH))
    {
        LS_ERROR("[%s] is not a valid executable."
                 , path);
        return LS_FAIL;
    }
    if (st.st_uid)
    {
        LS_ERROR("[%s] is not owned by root user.", path);
        return LS_FAIL;
    }
    if (!(st.st_mode & S_ISUID))
    {
        LS_ERROR("[%s] setuid bit is off.", path);
        return LS_FAIL;
    }
    if (st.st_mode & (S_IWOTH | S_IWGRP))
    {
        LS_ERROR("[%s] is writeable by group or other.", path);
        return LS_FAIL;
    }
    return 0;
}


static char sDefaultPath[] = "PATH=/bin:/usr/bin:/usr/local/bin";
//static char sLVE[] = "LVE_ENABLE=1";


int SUExec::suEXEC(const char *pServerRoot, int *pfd, int listenFd,
                   char *const *pArgv, char *const *env, const RLimits *pLimits)
{
    char *pEnv[3];
    char achExec[2048];
    char sockAddr[256];
    int len = snprintf(achExec, 2048, "%sbin/httpd", pServerRoot);
    if (checkLScgid(achExec))
        return LS_FAIL;
    while (1)
    {
        ++pArgv;        //skip the first argv
        m_req.appendArgv(*pArgv, *pArgv ? strlen(*pArgv) : 0);
        if (!*pArgv)
            break;
    }

    while (1)
    {
        m_req.appendEnv(*env, *env ? strlen(*env) : 0);
        if (!*env)
            break;
        ++env;
    }
    pEnv[0] = sDefaultPath;
#ifdef _HAS_LVE_
    if ((CgidWorker::getCgidWorker()->getLVE()) && (m_req.getCgidReq()->m_uid))
    {
        sLVE[11] = CgidWorker::getCgidWorker()->getLVE() + '0';
        pEnv[1] = sLVE;
        pEnv[2] = 0;
    }
    else
        pEnv[1] = 0;
#else
    pEnv[1] = 0;
#endif
    int fds[2];
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, fds) == -1)
    {
        LS_ERROR("[suEXEC] socketpair() failed!");
        return LS_FAIL;
    }
    snprintf(&achExec[len], 2048 - len, " -n %d", fds[1]);
    ::fcntl(fds[0], F_SETFD, FD_CLOEXEC);

    int fdsData[2];
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, fdsData) == -1)
    {
        LS_ERROR("[suEXEC] socketpair() failed!");
        return LS_FAIL;
    }
    len = snprintf(sockAddr, 250, "uds:/%s",
                   CgidWorker::getCgidWorker()->getConfig().getServerAddrUnixSock());
    write(fdsData[0], sockAddr, len + 1);
    close(fdsData[0]);

    int pid = SUExec::spawnChild(achExec, listenFd, fdsData[1], pEnv, 0,
                                 pLimits,
                                 ServerProcessConfig::getInstance().getUMask()
                                );
    close(fdsData[1]);
    close(fds[1]);
    if (pid != -1)
    {
        //send request to fd[0]

        m_req.finalize(0, CgidWorker::getCgidWorker()->getConfig().getSecret(),
                       LSCGID_TYPE_CGI);
        int size = m_req.size();
        len = write(fds[0], m_req.get(), size);
        if (len != size)
        {
            LS_ERROR("[suEXEC] Failed to write %d bytes to lscgid, written: %d",
                     size, len);
        }
    }
    if (pfd)
        *pfd = fds[0];
    else
        close(fds[0]);
    return pid;
}


/*
int
send_fd(int sock, int fd )
{
    struct msghdr msghdr;
    char nothing = '!';
    struct iovec nothing_ptr;
    struct cmsghdr *cmsg;
    char buffer[ sizeof( struct cmsghdr) + sizeof(int) ];

    nothing_ptr.iov_base = &nothing;
    nothing_ptr.iov_len = 1;
    msghdr.msg_name = NULL;
    msghdr.msg_namelen = 0;
    msghdr.msg_iov = &nothing_ptr;
    msghdr.msg_iovlen = 1;
    msghdr.msg_flags = 0;
    msghdr.msg_control = buffer;
    msghdr.msg_controllen = sizeof( buffer );
    cmsg = CMSG_FIRSTHDR(&msghdr);
    cmsg->cmsg_len = msghdr.msg_controllen;
    cmsg->cmsg_level = SOL_SOCKET;
    cmsg->cmsg_type = SCM_RIGHTS;
    *((int *)CMSG_DATA(cmsg)) = fd;
    return(sendmsg(sock, &msghdr, 0) >= 0 ? 0 : -1);
}
*/

#ifndef __CMSG_ALIGN
#define __CMSG_ALIGN(p) (((u_int)(p) + sizeof(int) - 1) &~(sizeof(int) - 1))
#endif

/* Length of the contents of a control message of length len */
#ifndef CMSG_LEN
#define CMSG_LEN(len)   (__CMSG_ALIGN(sizeof(struct cmsghdr)) + (len))
#endif

/* Length of the space taken up by a padded control message of
length len */
#ifndef CMSG_SPACE
#define CMSG_SPACE(len) (__CMSG_ALIGN(sizeof(struct cmsghdr)) + __CMSG_ALIGN(len))
#endif


int send_fd(int fd, int sendfd)
{
    struct msghdr    msg;
    struct iovec    iov[1];
    char nothing = '!';

#if (!defined(sun) && !defined(__sun)) || defined(_XPG4_2) || defined(_KERNEL)
    int             control_space = CMSG_SPACE(sizeof(int));
    union
    {
        struct cmsghdr    cm;
        char                control[sizeof(struct cmsghdr) + sizeof(int) + 8];
    } control_un;
    struct cmsghdr    *cmptr;
    int *pSendFd;

    msg.msg_control = control_un.control;
    msg.msg_controllen = control_space;

    cmptr = CMSG_FIRSTHDR(&msg);
    cmptr->cmsg_len = CMSG_LEN(sizeof(int));
    cmptr->cmsg_level = SOL_SOCKET;
    cmptr->cmsg_type = SCM_RIGHTS;
    pSendFd = (int *)CMSG_DATA(cmptr);
    *pSendFd = sendfd;
#else
    msg.msg_accrights = (caddr_t) &sendfd;
    msg.msg_accrightslen = sizeof(int);
#endif

    msg.msg_name = NULL;
    msg.msg_namelen = 0;
    msg.msg_flags = 0;

    iov[0].iov_base = &nothing;
    iov[0].iov_len = 1;
    msg.msg_iov = iov;
    msg.msg_iovlen = 1;

    return (sendmsg(fd, &msg, 0));
}


int SUExec::cgidSuEXEC(const char *pServerRoot, int *pfd, int listenFd,
                       char *const *pArgv, char *const *env, const RLimits *pLimits)
{
    //NOTE: should this happen?
    if (CgidWorker::getCgidWorker() == NULL)
        return LS_FAIL;


    int pid = -1;
    while (1)
    {
        ++pArgv;        //skip the first argv
        m_req.appendArgv(*pArgv, *pArgv ? strlen(*pArgv) : 0);
        if (!*pArgv)
            break;
    }

    while (1)
    {
        m_req.appendEnv(*env, *env ? strlen(*env) : 0);
        if (!*env)
            break;
        ++env;
    }
#ifdef _HAS_LVE_
    if ((CgidWorker::getCgidWorker()->getLVE())
        && (m_req.getCgidReq()->m_uid))
        sLVE[11] = CgidWorker::getCgidWorker()->getLVE() + '0';
#endif

    int fdReq = -1;



    CoreSocket::connect(
        CgidWorker::getCgidWorker()->getConfig().getServerAddr(), 0,
        &fdReq, 1);

    if (fdReq != -1)
    {
        m_req.finalize(0, CgidWorker::getCgidWorker()->getConfig().getSecret(),
                       LSCGID_TYPE_SUEXEC);
        int size = m_req.size();
        int len = write(fdReq, m_req.get(), size);
        if (len != size)
        {
            LS_ERROR("[suEXEC] Failed to write %d bytes to lscgid, written: %d",
                     size, len);
        }
        send_fd(fdReq, listenFd);
        pid = 0;
        if (read(fdReq, &pid, 4) != 4)
            return LS_FAIL;
    }
    if (pfd)
        *pfd = fdReq;
    else
        close(fdReq);
    return pid;

}
