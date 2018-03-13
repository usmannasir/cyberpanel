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
#include <signal.h>

#ifndef _XPG4_2
# define _XPG4_2
#endif

#include "lscgid.h"

#include <lsdef.h>
#include <util/fdpass.h>
#include <util/stringtool.h>

#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <poll.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/time.h>
#include <sys/uio.h>
#include <sys/wait.h>
#include <pwd.h>
#include <time.h>
#include <unistd.h>


#define uint32_t unsigned long

static uid_t        s_uid;
#ifdef HAS_CLOUD_LINUX
#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
#include <lve/lve-ctl.h>
static int s_enable_lve = 0;
static struct liblve *s_lve = NULL;

static void *s_liblve;
static int (*fp_lve_is_available)(void) = NULL;
static int (*fp_lve_instance_init)(struct liblve *) = NULL;
static int (*fp_lve_destroy)(struct liblve *) = NULL;
static int (*fp_lve_enter)(struct liblve *, uint32_t, int32_t, int32_t,
                           uint32_t *) = NULL;
static int (*fp_lve_leave)(struct liblve *, uint32_t *) = NULL;
static int (*fp_lve_jail)(struct passwd *, char *) = NULL;
static int load_lve_lib()
{
    s_liblve = dlopen("liblve.so.0", RTLD_LAZY);
    if (s_liblve)
    {
        fp_lve_is_available = dlsym(s_liblve, "lve_is_available");
        if (dlerror() == NULL)
        {
            if (!(*fp_lve_is_available)())
            {
                int uid = getuid();
                if (uid)
                {
                    setreuid(s_uid, uid);
                    if (!(*fp_lve_is_available)())
                        s_enable_lve = 0;
                    setreuid(uid, s_uid);
                }
            }
        }
    }
    else
        s_enable_lve = 0;
    return (s_liblve) ? 0 : -1;
}


static int init_lve()
{
    int rc;
    if (!s_liblve)
        return LS_FAIL;
    fp_lve_instance_init = dlsym(s_liblve, "lve_instance_init");
    fp_lve_destroy = dlsym(s_liblve, "lve_destroy");
    fp_lve_enter = dlsym(s_liblve, "lve_enter");
    fp_lve_leave = dlsym(s_liblve, "lve_leave");
    if (s_enable_lve >= 2)
        fp_lve_jail = dlsym(s_liblve, "jail");

    if (s_lve == NULL)
    {
        rc = (*fp_lve_instance_init)(NULL);
        s_lve = malloc(rc);
    }
    rc = (*fp_lve_instance_init)(s_lve);
    if (rc != 0)
    {
        perror("lscgid: Unable to initialize LVE");
        free(s_lve);
        s_lve = NULL;
        return LS_FAIL;
    }
    //fprintf( stderr, "lscgid (%d) LVE initialized !\n", getpid() );

    //fprintf( stderr, "lscgid (%d) LVE initialized: %d, %p !\n", getpid(), s_enable_lve, fp_lve_jail );
    return 0;

}

#endif
#endif

static char         s_pSecret[24];
static pid_t        s_parent;
static int          s_run = 1;
static char         s_sDataBuf[16384];
static int          s_fdControl = -1;


static void log_cgi_error(const char *func, const char *arg,
                                                    const char *explanation)
{
    char err[128];
    int n = ls_snprintf(err, 127, "%s:%s%.*s %s\n", func, (arg) ? arg : "",
                    !!arg, ":", explanation ? explanation : strerror(errno));
    write(STDERR_FILENO, err, n);
}


static int timed_read(int fd, char *pBuf, int len, int timeout)
{
    struct pollfd   pfd;
    time_t          begin;
    time_t          cur;
    int             left = len;
    int             ret;

    begin = cur = time(NULL);
    pfd.fd      = fd;
    pfd.events  = POLLIN;

    while (left > 0)
    {
        ret = poll(&pfd, 1, 1000);
        if (ret == 1)
        {
            if (pfd.revents & POLLIN)
            {
                ret = read(fd, pBuf, left);
                if (ret > 0)
                {
                    left -= ret;
                    pBuf += ret;
                }
                else if (ret <= 0)
                {
                    if (ret)
                        log_cgi_error("scgid: read()", NULL, NULL);
                    else
                        log_cgi_error("scgid", NULL, "pre-mature request");
                    return LS_FAIL;
                }
            }
        }
        if (ret == -1)
        {
            if (errno != EINTR)
            {
                log_cgi_error("scgid: poll()", NULL, NULL);
                return LS_FAIL;
            }
        }

        cur = time(NULL);
        if (cur - begin >= timeout)
        {
            log_cgi_error("scgid", NULL, "request timed out!");
            return LS_FAIL;
        }
    }
    return len;
}


static int writeall(int fd, const char *pBuf, int len)
{
    int left = len;
    int ret;
    while (left > 0)
    {
        ret = write(fd, pBuf, left);
        if (ret == -1)
        {
            if (errno == EINTR)
                continue;
            return LS_FAIL;
        }
        if (ret > 0)
        {
            left -= ret;
            pBuf += ret;
        }
    }
    return len;
}


static int cgiError(int fd, int status)
{
    char achBuf[ 256 ];
    int ret = ls_snprintf(achBuf, sizeof(achBuf) - 1,
                          "Status:%d\n\nInternal error.\n", status);
    writeall(fd, achBuf, ret);
    close(fd);
    return 0;
}


static int setUIDs(uid_t uid, gid_t gid, char *pChroot)
{
    int rv;

    //if ( !uid || !gid )  //do not allow root
    //{
    //    return LS_FAIL;
    //}
    struct passwd *pw = getpwuid(uid);
    rv = setgid(gid);
    if (rv == -1)
    {
        log_cgi_error("lscgid: setgid()", NULL, NULL);
        return LS_FAIL;
    }
    if (pw && (pw->pw_gid == gid))
    {
        rv = initgroups(pw->pw_name, gid);
        if (rv == -1)
        {
            log_cgi_error("lscgid: initgroups()", NULL, NULL);
            return LS_FAIL;
        }
    }
    else
    {
        rv = setgroups(1, &gid);
        if (rv == -1)
            log_cgi_error("lscgid: setgroups()", NULL, NULL);
    }
    if (pChroot)
    {
        rv = chroot(pChroot);
        if (rv == -1)
        {
            log_cgi_error("lscgid: chroot()", NULL, NULL);
            return LS_FAIL;
        }
    }
    rv = setuid(uid);
    if (rv == -1)
    {
        log_cgi_error("lscgid: setuid()", NULL, NULL);
        return LS_FAIL;
    }
    return 0;
}


static int applyLimits(lscgid_req *pCGI)
{
    //fprintf( stderr, "Proc: %ld, data: %ld\n", pCGI->m_nproc.rlim_cur,
    //                        pCGI->m_data.rlim_cur );
#if defined(RLIMIT_AS) || defined(RLIMIT_DATA) || defined(RLIMIT_VMEM)
    if (pCGI->m_data.rlim_cur)
    {
#if defined(RLIMIT_AS)
        setrlimit(RLIMIT_AS, &pCGI->m_data);
#elif defined(RLIMIT_DATA)
        setrlimit(RLIMIT_DATA, &pCGI->m_data);
#elif defined(RLIMIT_VMEM)
        setrlimit(RLIMIT_VMEM, &pCGI->m_data);
#endif
    }
#endif

#if defined(RLIMIT_NPROC)
    if (pCGI->m_nproc.rlim_cur)
        setrlimit(RLIMIT_NPROC, &pCGI->m_nproc);
#endif

#if defined(RLIMIT_CPU)
    if (pCGI->m_cpu.rlim_cur)
        setrlimit(RLIMIT_CPU, &pCGI->m_cpu);
#endif

    return 0;
}


static int execute_cgi(lscgid_t *pCGI)
{
    char ch;
    if (setpriority(PRIO_PROCESS, 0, pCGI->m_data.m_priority))
        perror("lscgid: setpriority()");
    applyLimits(&pCGI->m_data);

#ifdef HAS_CLOUD_LINUX

#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
    if (s_lve && pCGI->m_data.m_uid)   //root user should not do that
    {
        uint32_t cookie;
        int ret = -1;
        int count;
        //for( count = 0; count < 10; ++count )
        {
            ret = (*fp_lve_enter)(s_lve, pCGI->m_data.m_uid, -1, -1, &cookie);
            //if ( !ret )
            //    break;
            //usleep( 10000 );
        }
        if (ret < 0)
        {
            fprintf(stderr, "lscgid (%d): enter LVE (%d) : result: %d !\n", getpid(),
                    pCGI->m_data.m_uid, ret);
            log_cgi_error("lscgid", NULL, "lve_enter() failure, reached resource limit");
            return 500;
        }
    }
#endif

#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
    if (!s_uid && pCGI->m_data.m_uid && fp_lve_jail)
    {
        char  error_msg[1024] = "";
        int ret;
        struct passwd *pw = getpwuid(pCGI->m_data.m_uid);
        if (pw)
        {
            ret = (*fp_lve_jail)(pw, error_msg);
            if (ret < 0)
            {
                fprintf(stderr, "lscgid (%d): LVE jail(%d) ressult: %d, error: %s !\n",
                        getpid(), pCGI->m_data.m_uid, ret, error_msg);
                log_cgi_error("lscgid", NULL, "jail() failure");
                return 500;
            }
        }
    }
#endif

#endif

    if ((!s_uid) && (pCGI->m_data.m_uid || pCGI->m_data.m_gid))
    {
        if (setUIDs(pCGI->m_data.m_uid, pCGI->m_data.m_gid,
                    pCGI->m_pChroot) == -1)
            return 403;
    }
    ch = *(pCGI->m_argv[0]);
    * pCGI->m_argv[0] = 0;
    if (chdir(pCGI->m_pCGIDir) == -1)
    {
        int error = errno;
        log_cgi_error("lscgid: chdir()", pCGI->m_pCGIDir, NULL);
        switch (error)
        {
        case ENOENT:
            return 404;
        case EACCES:
            return 403;
        default:
            return 500;
        }
    }
    *(pCGI->m_argv[0]) = ch;
    if (ch == '&')
    {
        static const char sHeader[] = "Status: 200\r\n\r\n";
        writeall(STDOUT_FILENO, sHeader, sizeof(sHeader) - 1);
        pCGI->m_pCGIDir = (char *)"/bin/sh";
        pCGI->m_argv[0] = (char *)"/bin/sh";
    }
    else
    {
        //pCGI->m_argv[0] = strdup( pCGI->m_pCGIDir );
        pCGI->m_argv[0] = pCGI->m_pCGIDir;
    }

    umask(pCGI->m_data.m_umask);
    //fprintf( stderr, "execute_cgi m_umask=%03o\n", pCGI->m_data.m_umask );
    if (execve(pCGI->m_pCGIDir, pCGI->m_argv, pCGI->m_env) == -1)
    {
        log_cgi_error("lscgid: execve()", pCGI->m_pCGIDir, NULL);
        return 500;
    }

    return 0;
}


static int process_req_data(lscgid_t *cgi_req)
{
    char *p = cgi_req->m_pBuf;
    char *pEnd = p + cgi_req->m_data.m_szData;
    int i;
    unsigned short len;
    if (cgi_req->m_data.m_chrootPathLen > 0)
    {
        cgi_req->m_pChroot = p;
        p += cgi_req->m_data.m_chrootPathLen;
    }
    else
        cgi_req->m_pChroot = NULL;
    cgi_req->m_pCGIDir = p;
    p += cgi_req->m_data.m_exePathLen;
    if (p > pEnd)
    {
        fprintf(stderr, "exePathLen=%d\n", cgi_req->m_data.m_exePathLen);
        return 500;
    }
    cgi_req->m_argv[0] = p;
    p += cgi_req->m_data.m_exeNameLen + 1;

//    fprintf( stderr, "exePath=%s\n", cgi_req->m_pCGIDir );
//    fprintf( stderr, "nargv=%d\n", cgi_req->m_data.m_nargv );
//    fprintf( stderr, "exeName=%s\n", cgi_req->m_argv[0] );
//    fprintf( stderr, "exePath ends with %s\n",
//            cgi_req->m_pCGIDir + cgi_req->m_data.m_exePathLen );

    for (i = 1; i < cgi_req->m_data.m_nargv - 1; ++i)
    {
#if defined( sparc )
        *(unsigned char *)&len = *p++;
        *(((unsigned char *)&len) + 1) = *p++;
#else
        len = *((unsigned short *)p);
        p += sizeof(short);
#endif
        cgi_req->m_argv[i] = p;
        p += len;
        if (p > pEnd)
            return 500;
//        fprintf( stderr, "arg %d, len=%d, str=%s\n", i, len, cgi_req->m_argv[i] );
    }
    if (*p != 0 || *(p + 1) != 0)
    {
        fprintf(stderr, "argv is not terminated with \\0\\0\n");
        return 500;
    }
    p += sizeof(short);
    if (p > pEnd)
        return 500;
    cgi_req->m_argv[i] = NULL;

//    fprintf( stderr, "nenv=%d\n", cgi_req->m_data.m_nenv );
    for (i = 0; i < cgi_req->m_data.m_nenv - 1; ++i)
    {
#if defined( sparc )
        *(unsigned char *)&len = *p++;
        *(((unsigned char *)&len) + 1) = *p++;
#else
        len = *((unsigned short *)p);
        p += sizeof(short);
#endif
        cgi_req->m_env[i] = p;
        p += len;
        if (p > pEnd)
            return 500;
//        fprintf( stderr, "env %d, len=%d, str=%s\n", i, len, cgi_req->m_env[i] );
    }
    if (*p != 0 || *(p + 1) != 0)
    {
        fprintf(stderr, "env is not terminated with \\0\\0\n");
        return 500;
    }
    p += sizeof(short);
    if (p != pEnd)
    {
        fprintf(stderr, "header is too big\n");
        return 500;
    }
    cgi_req->m_env[i] = NULL;
    return 0;

}


#define MAX_CGI_DATA_LEN 65536

static int process_req_header(lscgid_t *cgi_req)
{
    char achMD5[16];
    int totalBufLen;
    memmove(achMD5, cgi_req->m_data.m_md5, 16);
    memmove(cgi_req->m_data.m_md5, s_pSecret, 16);
    StringTool::getMd5((const char *)&cgi_req->m_data,
                       sizeof(lscgid_req), cgi_req->m_data.m_md5);
    if (memcmp(cgi_req->m_data.m_md5, achMD5, 16) != 0)
    {
        log_cgi_error("lscgid", NULL, "request validation failed!");
        return 500;
    }
    totalBufLen = cgi_req->m_data.m_szData + sizeof(char *) *
                  (cgi_req->m_data.m_nargv + cgi_req->m_data.m_nenv);
    if ((unsigned int)totalBufLen < sizeof(s_sDataBuf))
        cgi_req->m_pBuf = s_sDataBuf;
    else
    {
        if (totalBufLen > MAX_CGI_DATA_LEN)
        {
            log_cgi_error("lscgid", NULL, "cgi header data is too big");
            return 500;

        }
        cgi_req->m_pBuf = (char *)malloc(totalBufLen);
        if (!cgi_req->m_pBuf)
        {
            log_cgi_error("lscgid: malloc()", NULL, NULL);
            return 500;
        }
    }
    cgi_req->m_argv = (char **)(cgi_req->m_pBuf + ((cgi_req->m_data.m_szData +
                                7) & ~7L));
    cgi_req->m_env = (char **)(cgi_req->m_argv + sizeof(char *) *
                               cgi_req->m_data.m_nargv);
    return 0;
}



static int recv_req(int fd, lscgid_t *cgi_req, int timeout)
{

    time_t          begin;
    time_t          cur;
    int             ret;

    begin = time(NULL);
    cgi_req->m_fdReceived = -1;
    ret = timed_read(fd, (char *)&cgi_req->m_data,
                     sizeof(lscgid_req), timeout - 1);
    if (ret == -1)
        return 500;
    ret = process_req_header(cgi_req);
    if (ret)
        return ret;
    //fprintf( stderr, "1 Proc: %ld, data: %ld\n", cgi_req->m_data.m_nproc.rlim_cur,
    //                        cgi_req->m_data.m_data.rlim_cur );

    if (cgi_req->m_data.m_type == LSCGID_TYPE_SUEXEC)
    {
        uint32_t pid = (uint32_t)getpid();
        write(STDOUT_FILENO, &pid, 4);
    }

    cur = time(NULL);
    timeout -= cur - begin;
    ret = timed_read(fd, cgi_req->m_pBuf,
                     cgi_req->m_data.m_szData, timeout);
    if (ret == -1)
        return 500;

    ret = process_req_data(cgi_req);
    if (ret)
    {
        log_cgi_error("lscgid", NULL, "data error!");
        return ret;
    }
    if (cgi_req->m_data.m_type == LSCGID_TYPE_SUEXEC)
    {
        //cgi_req->m_fdReceived = recv_fd( fd );
        char nothing;
        if ((FDPass::readFd(fd, &nothing, 1, &cgi_req->m_fdReceived) == -1) ||
            (cgi_req->m_fdReceived == -1))
        {
            fprintf(stderr, "lscgid: read_fd() failed: %s\n",
                    strerror(errno));
            return 500;
        }
        if (cgi_req->m_fdReceived != STDIN_FILENO)
        {
            dup2(cgi_req->m_fdReceived, STDIN_FILENO);
            close(cgi_req->m_fdReceived);
            cgi_req->m_fdReceived = -1;
        }
    }
    //fprintf( stderr, "2 Proc: %ld, data: %ld\n", cgi_req->m_data.m_nproc.rlim_cur,
    //                        cgi_req->m_data.m_data.rlim_cur );
    return 0;

}


static int processreq(int fd)
{
    lscgid_t cgi_req;
    int ret;

    ret = recv_req(fd, &cgi_req, 10);
    if (ret)
        cgiError(fd, ret);
    else
    {
        ret = execute_cgi(&cgi_req);
        if (ret)
            cgiError(fd, ret);
    }
    return ret;
}


static void child_main(int fd)
{
    int closeit = 1;
    //close( LSCGID_LISTENSOCK_FD );
    if (s_fdControl != -1)
        close(s_fdControl);
    if (fd != STDIN_FILENO)
        dup2(fd, STDIN_FILENO);
    else
        closeit = 0;
    if (fd != STDOUT_FILENO)
        dup2(fd, STDOUT_FILENO);
    else
        closeit = 0;
    if (closeit)
        close(fd);
    processreq(STDOUT_FILENO);
    exit(0);
}


static int new_conn(int fd)
{
    pid_t pid;
    pid = fork();
    if (!pid)
        child_main(fd);
    close(fd);
    if (pid > 0)
        pid = 0;
    else
        perror("lscgid: fork() failed");
    return pid;
}


static int run(int fdServerSock)
{
    int ret;
    struct pollfd pfd;
    pfd.fd = fdServerSock;
    pfd.events = POLLIN;
    while (s_run)
    {
        ret = poll(&pfd, 1, 1000);
        if (ret == 1)
        {
            int fd = accept(fdServerSock, NULL, NULL);
            if (fd != -1)
                new_conn(fd);
            else
                perror("lscgid: accept() failed");
        }
        else
        {
            if (getppid() != s_parent)
                return 1;
        }
    }
    return 0;
}


static void sigterm(int sig)
{
    s_run = 0;
}


static void sigusr1(int sig)
{
    pid_t pid = getppid();
    if (pid != -1)
        kill(pid, SIGHUP);
}


static void sigchild(int sig)
{
    int status[2];
    while (1)
    {
        status[0] = waitpid(-1, &status[1], WNOHANG);
        if (status[0] <= 0)
        {
            //if ((pid < 1)&&( errno == EINTR ))
            //    continue;
            break;
        }
        if (s_fdControl != -1)
            write(s_fdControl, status, sizeof(status));
        if (WIFSIGNALED(status[1]))
        {
            int sig_num = WTERMSIG(status[1]);
            if (sig_num != 15)
            {
                fprintf(stderr,
                        "Cgid: Child process with pid: %d was killed by signal: %d, core dump: %d\n",
                        status[0], sig_num,
#ifdef WCOREDUMP
                        WCOREDUMP(status[1])
#else
                        - 1
#endif

                       );
            }
        }
        //fprintf( stderr, "reape child %d: status: %d\n", pid, status );
    }

}


//#define LOCAL_TEST

#ifndef sighandler_t
typedef void (*sighandler_t)(int);
#endif
sighandler_t my_signal(int sig, sighandler_t f)
{
    struct sigaction act, oact;

    act.sa_handler = f;
    sigemptyset(&act.sa_mask);
    act.sa_flags = 0;
    if (sig == SIGALRM)
    {
#ifdef SA_INTERRUPT
        act.sa_flags |= SA_INTERRUPT; /* SunOS */
#endif
    }
    else
    {
#ifdef SA_RESTART
        act.sa_flags |= SA_RESTART;
#endif
    }
    if (sigaction(sig, &act, &oact) < 0)
        return (SIG_ERR);
    return (oact.sa_handler);
}


int lscgid_main(int fd, char *argv0, const char *secret, char *pSock)
{
    int ret;

    s_parent = getppid();
    my_signal(SIGCHLD, sigchild);
    my_signal(SIGINT, sigterm);
    my_signal(SIGTERM, sigterm);
    my_signal(SIGHUP, sigusr1);
    my_signal(SIGUSR1, sigusr1);
    signal(SIGPIPE, SIG_IGN);
    s_uid = geteuid();

    memcpy(s_pSecret, secret, 16);

#ifdef HAS_CLOUD_LINUX

#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
    if ((pSock = getenv("LVE_ENABLE")) != NULL)
    {
        s_enable_lve = atol(pSock);
        unsetenv("LVE_ENABLE");
        pSock = NULL;
    }
    if (s_enable_lve && !s_uid)
    {
        load_lve_lib();
        if (s_enable_lve)
            init_lve();

    }
#endif

#endif

#if defined(__FreeBSD__)
    //setproctitle( "%s", "httpd" );
#else
    memset(argv0, 0, strlen(argv0));
    strcpy(argv0, "openlitespeed (lscgid)");
#endif

    ret = run(fd);
    if ((ret) && (pSock) && (strncasecmp(pSock, "uds:/", 5) == 0))
    {
        pSock += 5;
        close(STDIN_FILENO);
        unlink(pSock);
    }
    return ret;
}


