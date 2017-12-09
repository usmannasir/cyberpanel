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
#include "lshttpdmain.h"

#include <adns/adns.h>
#include <http/httpaiosendfile.h>
#include <http/httplog.h>
#include <http/httpserverconfig.h>
#include <http/httpserverversion.h>
#include <http/httpsignals.h>
#include <http/serverprocessconfig.h>
#include <http/stderrlogger.h>
#include <log4cxx/logger.h>
#include <log4cxx/logrotate.h>
#include <lsiapi/lsiapihooks.h>
#include <lsr/ls_time.h>
#include <lsr/ls_fileio.h>
#include <lsr/ls_strtool.h>
#include <main/configctx.h>
#include <main/httpserver.h>
#include <main/httpconfigloader.h>
#include <main/mainserverconfig.h>
#include <main/plainconf.h>
#include <main/serverinfo.h>
#include <socket/coresocket.h>
#include <util/datetime.h>
#include <util/daemonize.h>
#include <util/emailsender.h>
#include <util/gpath.h>
#include <util/pcutil.h>
#include <util/stringlist.h>
#include <util/signalutil.h>
#include <util/vmembuf.h>
#include <sys/sysctl.h>

#include <extensions/cgi/cgidworker.h>
#include <extensions/registry/extappregistry.h>
#include <openssl/crypto.h>
#include <assert.h>
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include <config.h>

#define GlobalServerSessionHooks (LsiApiHooks::getServerSessionHooks())

static char s_iRunning = 0;
char *argv0 = NULL;
static int s_iCpuCount = 1;

LshttpdMain::LshttpdMain()
    : m_pServer(NULL)
    , m_pBuilder(NULL)
    , m_noDaemon(0)
    , m_noCrashGuard(0)
    , m_pProcState(NULL)
    , m_curChildren(0)
    , m_fdAdmin(-1)
{
    m_pServer = &HttpServer::getInstance();
    
#ifndef IS_LSCPD
    m_pBuilder = new HttpConfigLoader();
#endif
}


LshttpdMain::~LshttpdMain()
{
    if (HttpServerConfig::getInstance().getChildren() >= 32)
        free(m_pProcState);
    if (m_pBuilder)
        delete m_pBuilder;
}


int LshttpdMain::forkTooFreq()
{
    LS_WARN("[AutoRestarter] forking too frequently, suspend for a while!");
    return 0;
}


int LshttpdMain::preFork()
{
    LS_DBG_L("[AutoRestarter] prepare to fork new child process to handle request!");

    if (GlobalServerSessionHooks->isEnabled(LSI_HKPT_MAIN_PREFORK))
        GlobalServerSessionHooks->runCallbackNoParam(LSI_HKPT_MAIN_PREFORK, NULL);
    return 0;
}


int LshttpdMain::forkError(int err)
{
    return 0;
}


int LshttpdMain::postFork(pid_t pid)
{
    LS_NOTICE("[AutoRestarter] new child process with pid=%d is forked!",
              pid);
    return 0;
}


int LshttpdMain::childExit(pid_t ch_pid, int stat)
{
    LS_NOTICE("[AutoRestarter] child process with pid=%d exited with status=%d!",
              ch_pid, stat);
    if (stat != 100)
        return 0;
    return 0;
}


int LshttpdMain::childSignaled(pid_t pid, int signal, int coredump)
{
    static char pCoreFile[2][30] =
    {
        "no core file is created",
        "a core file is created"
    };
    LS_NOTICE("[AutoRestarter] child process with pid=%d received signal=%d, %s!",
              (int)pid, signal, pCoreFile[ coredump != 0 ]);
    //cleanUp();

    //We are in middle of graceful shutdown, do not restart another copy
    SendCrashNotification(pid, signal, coredump, pCoreFile[coredump != 0]);
    if (coredump)
    {

        if (access(DEFAULT_TMP_DIR "/bak_core", X_OK) == -1)
            ::system("mkdir " DEFAULT_TMP_DIR "/bak_core");

        else
        {
            int status = ::system("expr `ls " DEFAULT_TMP_DIR "/bak_core | wc -l` \\< 5");
            if (WEXITSTATUS(status))
                ::system("rm " DEFAULT_TMP_DIR "/bak_core/*");
        }
        ::system("mv " DEFAULT_TMP_DIR "/core* " DEFAULT_TMP_DIR "/bak_core");
    }
    return 0;
}


int LshttpdMain::SendCrashNotification(pid_t pid, int signal, int coredump,
                                       char *pCoreFile)
{
    MainServerConfig  &MainServerConfigObj =  MainServerConfig::getInstance();
    char achSubject[512];
    char achContent[2048];
    char achTime[50];
    static struct utsname      s_uname;
    const char *pAdminEmails = MainServerConfigObj.getAdminEmails();
    if ((!pAdminEmails) || (!*pAdminEmails))
        return 0;
    memset(&s_uname, 0, sizeof(s_uname));
    if (uname(&s_uname) == -1)
        LS_WARN("uname() failed!");
    ls_snprintf(achSubject, sizeof(achSubject) - 1,
                "Web server %s on %s is automatically restarted",
                MainServerConfigObj.getServerName(), s_uname.nodename);
    DateTime::getLogTime(DateTime::s_curTime, achTime);
    achTime[28] = 0;
    int len = ls_snprintf(achContent, sizeof(achContent) - 1,
                          "At %s, web server with pid=%d received unexpected signal=%d, %s."
                          " A new instance of web server will be started automatically!\n\n"
                          , achTime, (int)pid, signal, pCoreFile);
    if (coredump)
    {

        len += ls_snprintf(achContent + len, sizeof(achContent) - len - 1,
                           "Please forward the following debug information to bug@litespeedtech.com.\n"
                           "Environment:\n\n"
                           "Server: %s\n"
                           "OS: %s\n"
                           "Release: %s\n"
                           "Version: %s\n"
                           "Machine: %s\n\n"
                           "If the call stack information does not show up here, "
                           "please compress and forward the core file located in %s.\n\n",
                           HttpServerVersion::getVersion(),
                           s_uname.sysname,
                           s_uname.release,
                           s_uname.version,
                           s_uname.machine,
                           DEFAULT_TMP_DIR);
    }
    char achFileName[50] = "/tmp/m-XXXXXX";
    int fd = mkstemp(achFileName);
    if (fd == -1)
        return LS_FAIL;
    write(fd, achContent, len);
    close(fd);
    if (coredump)
    {
        const char *pGDB = MainServerConfigObj.getGDBPath();
        if ((pGDB == NULL || !*pGDB))
            pGDB = "gdb";
        char achCmd[1024];
        ls_snprintf(achCmd, 1024,
                    "%s --batch --command=%s/admin/misc/gdb-bt %s/bin/lshttpd %s/core* >> %s",
                    pGDB, MainServerConfigObj.getServerRoot(),
                    MainServerConfigObj.getServerRoot(),
                    DEFAULT_TMP_DIR, achFileName);

        if (::system(achCmd) == 0)
        {

            //removeMatchFile( DEFAULT_TMP_DIR, "core" );
        }
    }
    EmailSender::sendFile(achSubject, pAdminEmails, achFileName);
    ::unlink(achFileName);
    return 0;
}


void LshttpdMain::onGuardTimer()
{
    MainServerConfig  &MainServerConfigObj =  MainServerConfig::getInstance();
    static int s_count = 0;
    DateTime::s_curTime = time(NULL);
//#if !defined( RUN_TEST )
    if (m_pidFile.testAndRelockPidFile(getPidFile(), m_pid))
    {
        LS_NOTICE("Failed to lock PID file, restart server gracefully ...");
        gracefulRestart();
        return;
    }
//#endif
    CgidWorker::checkRestartCgid(MainServerConfigObj.getServerRoot(),
                                 MainServerConfigObj.getChroot(),
                                 ServerProcessConfig::getInstance().getPriority());
    HttpLog::onTimer();
    m_pServer->onVHostTimer();
    s_count = (s_count + 1) % 5;
    clearToStopApp();

    //processAdminCtrlFile( m_sCtrlFile.c_str());

    checkRestartReq();
}


int LshttpdMain::processAdminCmd(char *pCmd, char *pEnd, int &apply)
{
    if (strncasecmp(pCmd, "reload:", 7) == 0)
    {
        apply = 1;
        pCmd += 7;
        if (strncasecmp(pCmd, "config", 6) == 0)
        {
            LS_NOTICE("Reload configuration request from admin interface!");
            reconfig();
        }
        /* COMMENT: Not support reconfigVHost NOW.
        else if ( strncasecmp( pCmd, "vhost:", 6 ) == 0 )
        {
            pCmd += 6;
            LS_NOTICE( "Reload configuration for virtual host %s!", pCmd ));
            if ( m_pBuilder->loadConfigFile( NULL ) == 0 )
                m_pServer->reconfigVHost( pCmd, m_pBuilder->getRoot() );
                //m_pBuilder->reconfigVHost( pCmd );
        }*/
    }
    else if (strncasecmp(pCmd, "enable:", 7) == 0)
    {
        apply = 1;
        pCmd += 7;
        if (strncasecmp(pCmd, "vhost:", 6) == 0)
        {
            pCmd += 6;
            if (!m_pServer->enableVHost(pCmd, 1))
                LS_NOTICE("Virtual host %s is enabled!", pCmd);
            else
                LS_ERROR("Virtual host %s can not be enabled, reload first!", pCmd);
        }
    }
    else if (strncasecmp(pCmd, "disable:", 8) == 0)
    {
        apply = 1;
        pCmd += 8;
        if (strncasecmp(pCmd, "vhost:", 6) == 0)
        {
            pCmd += 6;
            if (!m_pServer->enableVHost(pCmd, 0))
                LS_NOTICE("Virtual host %s is disabled!", pCmd);
            else
                LS_ERROR("Virtual host %s can not be disabled, reload first!", pCmd);
        }
    }
    else if (strncasecmp(pCmd, "restart", 7) == 0)
    {
        LS_NOTICE("Server restart request from admin interface!");
        gracefulRestart();
    }
    else if (strncasecmp(pCmd, "toggledbg", 7) == 0)
    {
        LS_NOTICE("Toggle debug logging request from admin interface!");
        broadcastSig(SIGUSR2, 0);
        HttpLog::toggleDebugLog();
        apply = 0;
    }
    return 0;
}


int LshttpdMain::getFullPath(const char *pRelativePath, char *pBuf,
                             int bufLen)
{
    AutoStr2 *pProcChroot = ServerProcessConfig::getInstance().getChroot();
    return ls_snprintf(pBuf, bufLen, "%s%s%s",
                       (pProcChroot != NULL) ? pProcChroot->c_str() : "",
                       MainServerConfig::getInstance().getServerRoot(),
                       pRelativePath);

}


int LshttpdMain::execute(const char *pExecCmd, const char *pParam)
{
    char achBuf[512];
    int n = getFullPath(pExecCmd, achBuf, 512);
    ls_snprintf(&achBuf[n], 511 - n, " %s", pParam);
    int ret = system(achBuf);
    return ret;
}


int LshttpdMain::startAdminSocket()
{
    int i;
    char achBuf[1024];
    AutoStr2 *pProcChroot = ServerProcessConfig::getInstance().getChroot();
    if (m_fdAdmin != -1)
        return 0;
    srand(time(NULL));
    for (i = 0; i < 100; ++i)
    {
        snprintf(achBuf, 132, "uds:/%s%sadmin/tmp/admin.sock.%d",
                 (pProcChroot != NULL) ? pProcChroot->c_str() : "",
                 MainServerConfig::getInstance().getServerRoot(),
                 7000 + rand() % 1000);
        //snprintf(achBuf, 255, "127.0.0.1:%d", 7000 + rand() % 1000 );
        if (CoreSocket::listen(achBuf, 10, &m_fdAdmin, 0 , 0) == 0)
            break;
        if (!(i % 20))
        {
            snprintf(achBuf, 1024, "rm -rf '%s%sadmin/tmp/admin.sock.*'",
                     (pProcChroot != NULL) ? pProcChroot->c_str() : "",
                     MainServerConfig::getInstance().getServerRoot());
            system(achBuf);
        }
    }
    if (i == 100)
        return LS_FAIL;
    ::fcntl(m_fdAdmin, F_SETFD, FD_CLOEXEC);
    HttpServerConfig::getInstance().setAdminSock(strdup(achBuf));
    LS_NOTICE("[ADMIN] server socket: %s", achBuf);
    return 0;
}


int LshttpdMain::closeAdminSocket()
{
    const char *pAdminSock = HttpServerConfig::getInstance().getAdminSock();
    if (pAdminSock != NULL)
    {
        if (strncmp(pAdminSock, "uds://", 6) == 0)
            unlink(&pAdminSock[5]);
    }
    close(m_fdAdmin);
    return 0;
}


int LshttpdMain::acceptAdminSockConn()
{
    struct sockaddr_in peer;
    socklen_t addrlen;
    addrlen = sizeof(peer);
    int fd = accept(m_fdAdmin, (struct sockaddr *)&peer, &addrlen);
    if (fd == -1)
        return LS_FAIL;
    int ret = 0;
    ::fcntl(fd, F_SETFD, FD_CLOEXEC);
    //TODO: add access control here
    ret = processAdminSockConn(fd);
    if (ret != 2)
    {
        static const char *pCode[2] = {"OK", "Failed"};
        if (ret != 0)
            ret = 1;
        ls_fio_write(fd, pCode[ret], strlen(pCode[ret]));
    }
    close(fd);
    return 0;
}


int LshttpdMain::processAdminSockConn(int fd)
{
    char achBuf[4096];
    char *pEnd = &achBuf[4096];
    char *p = achBuf;
    int len;
    while ((len = ls_fio_read(fd, p, pEnd - p)) > 0)
        p += len;

    if ((len == -1) || (pEnd == p))
    {
        LS_ERROR("[ADMIN] failed to read command, command buf len=%d",
                 (int)(p - achBuf));
        return LS_FAIL;
    }
    char *pEndAuth = strchr(achBuf, '\n');
    if (!pEndAuth)
        return LS_FAIL;
    if (m_pServer->authAdminReq(achBuf) != 0)
        return LS_FAIL;
    ++pEndAuth;
    return processAdminBuffer(pEndAuth, p);

}


int LshttpdMain::processAdminBuffer(char *p, char *pEnd)
{
    while ((pEnd > p) && isspace(pEnd[-1]))
        --pEnd;
    if (pEnd - p < 14)
        return LS_FAIL;
    if (strncasecmp(pEnd - 14, "end of actions", 14) != 0)
    {
        LS_ERROR("[ADMIN] failed to read command, command buf len=%d",
                 (int)(pEnd - p));
        return LS_FAIL;
    }
    pEnd -= 14;
    int apply;
    char *pLineEnd;
    while (p < pEnd)
    {
        pLineEnd = (char *)memchr(p, '\n', pEnd - p);
        if (pLineEnd == NULL)
            pLineEnd = pEnd;
        char *pTemp = pLineEnd;
        while ((pLineEnd > p) && isspace(pLineEnd[-1]))
            --pLineEnd;
        *pLineEnd = 0;
        if (processAdminCmd(p, pLineEnd, apply))
            break;
        p = pTemp + 1;
    }
    m_pBuilder->releaseConfigXmlTree();
    if (s_iRunning > 0)
        m_pServer->generateStatusReport();
    if (apply)
        applyChanges();
    return 0;
}


#define DEFAULT_CONFIG_FILE         "conf/httpd_config.conf"

int LshttpdMain::testServerRoot(const char *pRoot)
{
    struct stat st;
    if (ls_fio_stat(pRoot, &st) == -1)
        return LS_FAIL;
    if (!S_ISDIR(st.st_mode))
        return LS_FAIL;
    char achBuf[MAX_PATH_LEN] = {0};

#ifndef IS_LSCPD
    if (GPath::getAbsoluteFile(achBuf, MAX_PATH_LEN, pRoot,
                               DEFAULT_CONFIG_FILE) == 0)
    {
        if (access(achBuf, R_OK) == 0)
            m_pBuilder->setConfigFilePath(achBuf);
        else
            return LS_FAIL;
    }
#else
    strcpy(achBuf, pRoot);
#endif

    int len = strlen(pRoot);
    if (pRoot[len - 1] == '/')
        achBuf[len] = 0;
    else
        achBuf[++len] = 0;
    if (GPath::checkSymLinks(achBuf, &achBuf[len],
                             &achBuf[MAX_PATH_LEN], achBuf, 1) == -1)
        return LS_FAIL;
    m_pServer->setServerRoot(achBuf);
    return 0;
}


int LshttpdMain::getServerRootFromExecutablePath(const char *command,
        char  *pBuf, int len)
{
    char achBuf[512];
    if (*command != '/')
    {
        getcwd(achBuf, 512);
        strcat(achBuf, "/");
        strcat(achBuf, command);
    }
    else
        strcpy(achBuf, command);
    char *p = strrchr(achBuf, '/');
    if (p)
        *(p + 1) = 0;
    strcat(p, "../");
    GPath::clean(achBuf);
    memccpy(pBuf, achBuf, 0, len);
    return 0;

}


int LshttpdMain::guessCommonServerRoot()
{
    const char *pServerRoots[] =
    {
        NULL,
        "/usr/local/",
        "/opt/",
        "/usr/",
        "/var/",
        "/home/",
        "/usr/share/",
        "/usr/local/share/"
    };
    const char *pServerDirs[] =
    {
        "lsws/",
        "lshttpd/"
    };
    char *pHome = getenv("HOME");
    pServerRoots[0] = pHome;
    char achBuf[MAX_PATH_LEN];
    for (size_t i = 0; i < sizeof(pServerRoots) / sizeof(char *); ++i)
    {
        if (!pServerRoots[i])
            continue;
        strcpy(achBuf, pServerRoots[i]);
        for (size_t j = 0; j < sizeof(pServerDirs) / sizeof(char *); ++j)
        {
            strcat(achBuf, pServerDirs[j]);
            if (testServerRoot(achBuf) == 0)
                return 0;
        }
    }
    return LS_FAIL;
}


int LshttpdMain::getServerRoot(int argc, char *argv[])
{
    char achServerRoot[MAX_PATH_LEN];

    char pServerRootEnv[2][20] = {"LSWS_HOME", "LSHTTPD_HOME"};
    for (int i = 0; i < 2; ++i)
    {
        const char *pRoot = getenv(pServerRootEnv[i]);
        if (pRoot)
        {
            if (testServerRoot(pRoot) == 0)
                return 0;
        }
    }
    if (getServerRootFromExecutablePath(argv[0],
                                        achServerRoot, MAX_PATH_LEN) == 0)
    {
        if (testServerRoot(achServerRoot) == 0)
            return 0;
    }
    if (guessCommonServerRoot() == 0)
        return 0;
    return LS_FAIL;
}


int LshttpdMain::config()
{
    int iReleaseXmlTree;
    int ret = m_pServer->initServer(m_pBuilder->getRoot(), iReleaseXmlTree);
    if (iReleaseXmlTree)
        m_pBuilder->releaseConfigXmlTree();
    if (ret != 0)
        return 1;
    if (m_pServer->isServerOk())
        return 2;
//    if ( ServerProcessConfig::getInstance.getChroot != NULL )
//    {
//        mkdir( DEFAULT_TMP_DIR,  0755 );
//        PidFile PidFile;
//        PidFile.writePidFile( PID_FILE, m_pid );
//    }
    m_pServer->generateStatusReport();
    return 0;

}


int LshttpdMain::reconfig()
{
    int iReleaseXmlTree;
    int ret = m_pServer->initServer(m_pBuilder->getRoot(), iReleaseXmlTree, 1);
    if (iReleaseXmlTree)
        m_pBuilder->releaseConfigXmlTree();
    if (ret != 0)
    {
        LS_WARN("Reconfiguration failed, server is restored to "
                "the state before reconfiguration as much as possible, "
                "if any problem, please restart server!");
    }
    else
        LS_NOTICE("Reconfiguration succeed! ");
    m_pServer->generateStatusReport();
    return 0;
}


static void perr(const char *pErr)
{
    fprintf(stderr,  "[ERROR] %s\n", pErr);
}


const char *LshttpdMain::getPidFile()
{
    const char *pidFile = getenv("OLS_PID_FILE");
    if (!pidFile)
        pidFile = PID_FILE;
    
    return pidFile;
}

int LshttpdMain::testRunningServer()
{
    int count = 0;
    int ret;
    do
    {
        ret = m_pidFile.lockPidFile(getPidFile());
        if (ret)
        {
            if ((ret == -2) && (errno == EACCES || errno == EAGAIN))
            {
                ++count;
                if (count >= 10)
                {
                    perr("LiteSpeed Web Server is running!");
                    return 2;
                }
                ls_sleep(100);
            }
            else
            {
                fprintf(stderr, "[ERROR] Failed to write to pid file:%s!\n", 
                    getPidFile());
                return ret;
            }
        }
        else
            break;
    }
    while (true);
    return ret;
}


void LshttpdMain::printVersion()
{
    printf("%s\n\tmodule versions:\n%s\n",
           HttpServerVersion::getVersion(), LS_MODULE_VERSION_INFO);
}

void LshttpdMain::parseOpt(int argc, char *argv[])
{
    const char *opts = "cdnv";
    int c;
    char achCwd[512];
    getServerRootFromExecutablePath(argv[0], achCwd, 512);
    opterr = 0;
    while ((c = getopt(argc, argv, opts)) != EOF)
    {
        switch (c)
        {
        case 'c':
            m_noCrashGuard = 1;
            break;
        case 'd':
            m_noDaemon = 1;
            m_noCrashGuard = 1;
            break;
        case 'n':
            m_noDaemon = 1;
            break;
        case 'v':
            printVersion();
            exit(0);
            break;
        case '?':
            break;

        default:
            printf("?? getopt returned character code -%o ??\n", c);
        }
    }
}


static void enableCoreDump()
{
    struct  rlimit rl;
    if (getrlimit(RLIMIT_CORE, &rl) == -1)
        LS_WARN("getrlimit( RLIMIT_CORE, ...) failed!");
    else
    {
        //LS_DBG_L( "rl.rlim_cur=%d, rl.rlim_max=%d", rl.rlim_cur, rl.rlim_max );
        if ((getuid() == 0) && (rl.rlim_max < 10240000))
            rl.rlim_max = 10240000;
        rl.rlim_cur = rl.rlim_max;
        ::setrlimit(RLIMIT_CORE, &rl);
    }

    ::chdir(DEFAULT_TMP_DIR);
}


void LshttpdMain::changeOwner()
{
    ServerProcessConfig &procConfig = ServerProcessConfig::getInstance();
    chown(DEFAULT_TMP_DIR, procConfig.getUid(), procConfig.getGid());
    //chown( PID_FILE, procConfig.getUid(), procConfig.getGid() );
    chown(DEFAULT_SWAP_DIR, procConfig.getUid(), procConfig.getGid());
}


void LshttpdMain::removeOldRtreport()
{
    char achBuf[8192];
    int i = 1;
    int ret, len;
    ConfigCtx::getCurConfigCtx()->getAbsolute(achBuf, sStatDir, 0);
    len = strlen(achBuf);
    while (1)
    {
        ret = ::unlink(achBuf);
        if (ret == -1)
            break;
        ++i;
        achBuf[len] = '.';
        snprintf(&achBuf[len + 1], sizeof(achBuf) - len - 1, "%d", i);
    };
}


int LshttpdMain::init(int argc, char *argv[])
{
    int ret;
    ServerProcessConfig &procConfig = ServerProcessConfig::getInstance();
    if (argc > 1)
        parseOpt(argc, argv);
    if (getServerRoot(argc, argv) != 0)
    {
        //LS_ERROR("Failed to determine the root directory of server!" ));
        fprintf(stderr,
                "Can't determine the Home of LiteSpeed Web Server, exit!\n");
        return 1;
    }

    mkdir(DEFAULT_TMP_DIR,  0755);

    if (testRunningServer() != 0)
        return 2;

#ifndef IS_LSCPD

    //load the config
    m_pBuilder->loadConfigFile();
//    m_pBuilder->loadPlainConfigFile();
    if (m_pServer->configServerBasics(0, m_pBuilder->getRoot()))
        return 1;
#else
    //init lscpd
    if (m_pServer->initLscpd())
        return 1;
#endif
    
    if (!MainServerConfig::getInstance().getDisableLogRotateAtStartup())
        LOG4CXX_NS::LogRotate::roll(HttpLog::getErrorLogger()->getAppender(),
                                    procConfig.getUid(),
                                    procConfig.getGid(), 1);

    if (procConfig.getUid() <= 10 || procConfig.getGid() < 10)
    {
        MainServerConfig  &MainServerConfigObj =  MainServerConfig::getInstance();
        LS_ERROR("It is not allowed to run LiteSpeed web server on behalf of a "
                 "privileged user/group, user id must not be "
                 "less than 50 and group id must not be less than 10."
                 "UID of user '%s' is %d, GID of group '%s' is %d. "
                 "Please fix above problem first!",
                 MainServerConfigObj.getUser(), procConfig.getUid(),
                 MainServerConfigObj.getGroup(), procConfig.getGid());
        return 1;
    }
    changeOwner();

#ifndef IS_LSCPD
    plainconf::flushErrorLog();
#endif

    LS_NOTICE("Loading %s ...", HttpServerVersion::getVersion());
    LS_NOTICE("Using [%s]", SSLeay_version(SSLEAY_VERSION));

    if (!m_noDaemon)
    {
        if (Daemonize::daemonize(1, 1))
            return 3;
        LS_DBG_L("Daemonized!");
#ifndef RUN_TEST
        Daemonize::close();
#endif
    }

    enableCoreDump();


    if (testRunningServer() != 0)
        return 2;
    m_pid = getpid();
    if (m_pidFile.writePid(m_pid))
        return 2;


    if (!MainServerConfig::getInstance().getDisableWebAdmin())
        startAdminSocket();
    
#ifndef IS_LSCPD
    ret = config();
    if (ret)
    {
        LS_ERROR("Fatal error in configuration, exit!");
        fprintf(stderr, "[ERROR] Fatal error in configuration, shutdown!\n");
        return ret;
    }
#endif

    removeOldRtreport();
    {
        char achBuf[8192];

        if (procConfig.getChroot() != NULL)
        {
            PidFile pidfile;
            ConfigCtx::getCurConfigCtx()->getAbsolute(achBuf, getPidFile(), 0);
            pidfile.writePidFile(achBuf, m_pid);
        }
    }

#if defined(__FreeBSD__)
    //setproctitle( "%s", "lshttpd" );
#else
    argv[1] = NULL;
#ifdef IS_LSCPD
    strcpy(argv[0], "lscpd (lscpd - main)");
#else
    strcpy(argv[0], "openlitespeed (lshttpd - main)");
#endif
#endif
    //if ( !m_noCrashGuard && ( m_pBuilder->getCrashGuard() ))
    s_iCpuCount = PCUtil::getNumProcessors();

    //Server init done
    if (GlobalServerSessionHooks->isEnabled(LSI_HKPT_MAIN_INITED))
        GlobalServerSessionHooks->runCallbackNoParam(LSI_HKPT_MAIN_INITED, NULL);

    if (!m_noCrashGuard && (MainServerConfig::getInstance().getCrashGuard()))
    {
        if (guardCrash())
            return 8;
        m_pidFile.closePidFile();
    }
    else
    {
        HttpServerConfig::getInstance().setProcNo(1);
        allocatePidTracker();
        m_pServer->initAdns();
        m_pServer->enableAioLogging();
        if ((HttpServerConfig::getInstance().getUseSendfile() == 2)
            && (m_pServer->initAioSendFile() != 0))
            return LS_FAIL;
    }
    //if ( fcntl( 5, F_GETFD, 0 ) > 0 )
    //    printf( "find it!\n" );
    if (getuid() == 0)
    {
        if (m_pServer->changeUserChroot() == -1)
            return LS_FAIL;
        if (procConfig.getChroot() != NULL)
            m_pServer->offsetChroot();
    }

    if (1 == HttpServerConfig::getInstance().getProcNo())
        ExtAppRegistry::runOnStartUp();

    if (GlobalServerSessionHooks->isEnabled(LSI_HKPT_WORKER_INIT))
        GlobalServerSessionHooks->runCallbackNoParam(LSI_HKPT_WORKER_INIT,
                NULL);


    return 0;
}


int LshttpdMain::main(int argc, char *argv[])
{
    argv0 = argv[0];

    VMemBuf::initAnonPool();
    umask(022);
    HttpLog::init();
    LsiApiHooks::initGlobalHooks();
#ifdef RUN_TEST
    if ((argc == 2) && (strcmp(argv[1], "-x") == 0))
    {
        allocatePidTracker();
        m_pServer->initMultiplexer("best");
        m_pServer->initAdns();
        m_pServer->test_main(argv0);
    }
    else
#endif
    {
        int ret = init(argc, argv);

        if (ret != 0)
            return ret;

        m_pServer->start();

        //If HttpServerConfig::s_iProcNo is 0, is main process
        if (GlobalServerSessionHooks->isEnabled(LSI_HKPT_WORKER_ATEXIT))
            GlobalServerSessionHooks->runCallbackNoParam(LSI_HKPT_WORKER_ATEXIT, NULL);
        m_pServer->releaseAll();
    }
    return 0;
}


static void sigchild(int sig)
{
    //printf( "signchild()!\n" );
    HttpSignals::orEvent(HS_CHILD);
}


#define BB_SIZE 32768
int LshttpdMain::allocatePidTracker()
{
    char *pBuf = allocateBlackBoard();
    if (pBuf == MAP_FAILED)
    {
        LOG_ERR_CODE((errno));
        return LS_FAIL;

    }
    m_pServer->setBlackBoard(pBuf);
    return 0;
}


char *LshttpdMain::allocateBlackBoard()
{
    char *pBuf = (char *) mmap(NULL, BB_SIZE, PROT_READ | PROT_WRITE,
                               MAP_ANON | MAP_SHARED, -1, 0);
    return pBuf;
}


void LshttpdMain::deallocateBlackBoard(char *pBuf)
{
    munmap(pBuf, BB_SIZE);
}


void LshttpdMain::releaseExcept(ChildProc *pCurProc)
{
    ChildProc *pProc;
    pProc = (ChildProc *)m_childrenList.pop();
    while (pProc)
    {
        if ((pProc != pCurProc) && (pProc->m_pBlackBoard))
            deallocateBlackBoard(pProc->m_pBlackBoard);
        m_pool.recycle(pProc);
        pProc = (ChildProc *)m_childrenList.pop();
    }
}


int LshttpdMain::getFirstAvailSlot()
{
    int mask = 2;
    int *pState;
    int i;
    int iNumChildren = HttpServerConfig::getInstance().getChildren();
    if (iNumChildren >= 32)
        pState = m_pProcState;
    else
        pState = (int *)&m_pProcState;
    for (i = 1; i <= iNumChildren; ++i)
    {
        if (!(*pState & mask))
            break;
        mask <<= 1;
        if (mask == 0)
        {
            ++pState;
            mask = 1;
        }
    }
    return i;
}


void LshttpdMain::setChildSlot(int num, int val)
{
    int *pState;
    if (num > HttpServerConfig::getInstance().getChildren())
        return;
    if (HttpServerConfig::getInstance().getChildren() >= 32)
        pState = m_pProcState;
    else
        pState = (int *)&m_pProcState;
    pState += num >> 5;
    int mask = 1 << (num & 31);
    *pState = (val) ? *pState | mask : *pState & ~mask;

}


int LshttpdMain::startChild(ChildProc *pProc)
{
    if (!pProc->m_pBlackBoard)
    {
        pProc->m_pBlackBoard = allocateBlackBoard();
        if (!pProc->m_pBlackBoard)
            return LS_FAIL;
    }
    pProc->m_iProcNo = getFirstAvailSlot();
    if (pProc->m_iProcNo > HttpServerConfig::getInstance().getChildren())
        return LS_FAIL;
    preFork();
    pProc->m_pid = fork();
    if (pProc->m_pid == -1)
    {
        forkError(errno);
        return LS_FAIL;
    }
    if (pProc->m_pid == 0)
    {
        //child process
        cpu_set_t       cpu_affinity;

        PCUtil::getAffinityMask(s_iCpuCount, pProc->m_iProcNo - 1, 1,
                                &cpu_affinity);
        PCUtil::setCpuAffinity(&cpu_affinity);
        m_pServer->setBlackBoard(pProc->m_pBlackBoard);
        m_pServer->setProcNo(pProc->m_iProcNo);
        //setAffinity( 0, pProc->m_iProcNo);  //TEST: need uncomment and debug
        releaseExcept(pProc);
        m_pServer->reinitMultiplexer();
        m_pServer->enableAioLogging();
        if ((HttpServerConfig::getInstance().getUseSendfile() == 2)
            && (m_pServer->initAioSendFile() != 0))
            return LS_FAIL;
        close(m_fdAdmin);
        
#ifdef IS_LSCPD
        snprintf(argv0, 80, "lscpd (lscpd - #%02d)", pProc->m_iProcNo);
#else
        snprintf(argv0, 80, "openlitespeed (lshttpd - #%02d)", pProc->m_iProcNo);
#endif

        return 0;
    }

    if (GlobalServerSessionHooks->isEnabled(LSI_HKPT_MAIN_POSTFORK))
        GlobalServerSessionHooks->runCallbackNoParam(LSI_HKPT_MAIN_POSTFORK, NULL);
    postFork(pProc->m_pid);
    m_childrenList.push(pProc);
    pProc->m_iState = CP_RUNNING;
    setChildSlot(pProc->m_iProcNo, 1);

    ++m_curChildren;
    return pProc->m_pid;
}


void LshttpdMain::waitChildren()
{
    int rpid;
    int  stat;
    int ret;
    //printf( "waitpid()\n" );
    while ((rpid = ::waitpid(-1, &stat, WNOHANG)) > 0)
    {
        if (WIFEXITED(stat))
        {
            ret = WEXITSTATUS(stat);
            if (childDead(rpid))
                childExit(rpid, ret);
        }
        else if (WIFSIGNALED(stat))
        {
            int sig_num = WTERMSIG(stat);
            ret = childSignaled(rpid, sig_num,
#ifdef WCOREDUMP
                                WCOREDUMP(stat)
#else
                                - 1
#endif
                               );
            childDead(rpid);
        }
    }
}


int LshttpdMain::cleanUp(int pid, char *pBB)
{
    if (pBB)
    {
        LS_NOTICE("[AutoRestarter] cleanup children processes and "
                  "unix sockets belong to process %d !", pid);
        ((ServerInfo *)pBB)->cleanUp();
    }
    return 0;
}


int LshttpdMain::checkRestartReq()
{
    MainServerConfig  &MainServerConfigObj =  MainServerConfig::getInstance();
    ChildProc *pProc;
//    LinkedObj * pPrev = m_childrenList.head();
    pProc = (ChildProc *)m_childrenList.begin();
    while (pProc)
    {
        if (((ServerInfo *)pProc->m_pBlackBoard)->getRestart())
        {
            LS_NOTICE("Child Process:%d request a graceful server restart ...",
                      pProc->m_pid);
            const char *pAdminEmails = MainServerConfigObj.getAdminEmails();
            if ((pAdminEmails) && (*pAdminEmails))
            {
                char achSubject[512];
                static struct utsname      s_uname;
                memset(&s_uname, 0, sizeof(s_uname));
                if (uname(&s_uname) == -1)
                    LS_WARN("uname() failed!");
                ls_snprintf(achSubject, sizeof(achSubject) - 1,
                            "LiteSpeed Web server %s on %s restarts "
                            "automatically to fix 503 Errors",
                            MainServerConfigObj.getServerName(), s_uname.nodename);
                EmailSender::send(
                    achSubject, pAdminEmails, "");
            }
            gracefulRestart();
            return 0;
        }
//        pPrev = pProc;
        pProc = (ChildProc *)pProc->next();
    }
    return 0;
}


int LshttpdMain::recoverShmCrash(ChildProc *pProc)
{
    if (((ServerInfo *)pProc->m_pBlackBoard)->isAdnsOp())
    {
        Adns::deleteCache();
    }
    return 0;
}


int LshttpdMain::childDead(int pid)
{
    ChildProc *pProc;
    LinkedObj *pPrev = m_childrenList.head();
    pProc = (ChildProc *)m_childrenList.begin();
    while (pProc)
    {
        if (pProc->m_pid == pid)
        {
            recoverShmCrash(pProc);
            cleanUp(pid, pProc->m_pBlackBoard);
            if (pProc->m_iState == CP_RUNNING)
            {
                setChildSlot(pProc->m_iProcNo, 0);
                --m_curChildren;
            }
            m_childrenList.removeNext(pPrev);
            m_pool.recycle(pProc);
            return 1;
        }
        else
        {
            pPrev = pProc;
            pProc = (ChildProc *)pProc->next();
        }
    }
    return 0;
}


int LshttpdMain::clearToStopApp()
{
    ChildProc *pProc;
    pProc = (ChildProc *)m_childrenList.begin();
    while (pProc)
    {
        ((ServerInfo *)pProc->m_pBlackBoard)->cleanPidList(1);
        pProc = (ChildProc *)pProc->next();
    }
    return 0;
}


void LshttpdMain::broadcastSig(int sig, int changeState)
{
    ChildProc *pProc;
    pProc = (ChildProc *)m_childrenList.begin();
    while (pProc)
    {
        if (pProc->m_pid > 0)
            kill(pProc->m_pid, sig);
        if ((changeState) && (pProc->m_iState == CP_RUNNING))
        {
            pProc->m_iState = CP_SHUTDOWN;
            setChildSlot(pProc->m_iProcNo, 0);
            --m_curChildren;
        }
        pProc = (ChildProc *)pProc->next();
    }
}


void LshttpdMain::stopAllChildren()
{
    ChildProc *pProc;
    broadcastSig(SIGTERM, 0);

    long tmBeginWait = time(NULL);
    long tmEndWait = tmBeginWait + 300 +
                     HttpServerConfig::getInstance().getRestartTimeout();

    while ((s_iRunning != -1) && (m_childrenList.size() > 0) &&
           (time(NULL) < tmEndWait))
    {
        sleep(1);
        waitChildren();
    }

    if (m_childrenList.size() > 0)
    {
        pProc = (ChildProc *)m_childrenList.begin();
        while (pProc)
        {
            kill(pProc->m_pid, SIGKILL);
            cleanUp(pProc->m_pid, pProc->m_pBlackBoard);
            pProc = (ChildProc *)pProc->next();
        }
    }
}


void LshttpdMain::applyChanges()
{
    LS_DBG_L("Applying new configuration. ");
    broadcastSig(SIGTERM, 1);
}


void LshttpdMain::gracefulRestart()
{
    LS_DBG_L("Graceful Restart... ");
    close(m_fdAdmin);
    broadcastSig(SIGTERM, 1);
    s_iRunning = 0;
    m_pidFile.closePidFile();
    m_pServer->passListeners();
    int pid = fork();
    if (!pid)
    {
        char achCmd[1024];
        int fd = StdErrLogger::getInstance().getStdErr();
        if (fd != 2)
            close(fd);
        int len = getFullPath("bin/litespeed", achCmd, 1024);
        achCmd[len - 10] = 0;
        chdir(achCmd);
        achCmd[len - 10] = '/';
        if (execl(achCmd, "litespeed", NULL))
            LS_ERROR("Failed to start new instance of LiteSpeed Web server!");
        exit(0);
    }
    if (pid == -1)
        LS_ERROR("Failed to restart the server!");
}


static void startTimer()
{
    struct itimerval tmv;
    memset(&tmv, 0, sizeof(struct itimerval));
    tmv.it_interval.tv_sec = 1;
    gettimeofday(&tmv.it_value, NULL);
    tmv.it_value.tv_sec = 0;
    tmv.it_value.tv_usec = 1000000 - tmv.it_value.tv_usec;
    setitimer(ITIMER_REAL, &tmv, NULL);
}


int LshttpdMain::guardCrash()
{
    long lLastForkTime  = DateTime::s_curTime = time(NULL);
    int  iForkCount     = 0;
    int  ret            = 0;
    int  iNumChildren = HttpServerConfig::getInstance().getChildren();
    struct pollfd   pfds[2];
    HttpSignals::init(sigchild);
    if (iNumChildren >= 32)
    {
        m_pProcState = (int *)malloc(((iNumChildren >> 5) + 1) * sizeof(
                                         int));
        memset(m_pProcState, 0, ((iNumChildren >> 5) + 1) * sizeof(int));
    }
    if (!MainServerConfig::getInstance().getDisableWebAdmin())
    {
        startAdminSocket();
    }
    else
        m_fdAdmin = -1;
    
    pfds[0].fd = m_fdAdmin;
    pfds[0].events = POLLIN;
    pfds[1].fd = -1;
    pfds[1].events = 0;
    s_iRunning = 1;
    startTimer();
    while (s_iRunning > 0)
    {
        if (DateTime::s_curTime - lLastForkTime > 60)
        {
            iForkCount = 0;
            lLastForkTime = DateTime::s_curTime;
        }
        else
        {

            if (iForkCount > (iNumChildren << 3))
            {
                ret = forkTooFreq();
                if (ret > 0)
                    break;
                iForkCount = -1;
            }
            else if (iForkCount >= 0)
            {
                while (m_curChildren < iNumChildren)
                {
                    ++iForkCount;
                    ChildProc *pProc = m_pool.get();
                    if (pProc)
                    {
                        ret = startChild(pProc);
                        if (ret == 0)    //children process
                            return 0;
                        else if (ret == -1)
                            m_pool.recycle(pProc);
                    }
                }
            }
        }
        if (m_fdAdmin != -1)
        {
            ret = ::poll(pfds, 1, 1000);
            if (ret > 0)
            {
                if (pfds[0].revents)
                    acceptAdminSockConn();
                continue;
            }

        }
        else
            ::sleep(1);
        if (HttpSignals::gotEvent())
            processSignal();
    }
    if (m_childrenList.size() > 0)
        stopAllChildren();

    //Server Exit hookpoint called here
    if (GlobalServerSessionHooks->isEnabled(LSI_HKPT_MAIN_ATEXIT))
        GlobalServerSessionHooks->runCallbackNoParam(LSI_HKPT_MAIN_ATEXIT, NULL);

    LS_NOTICE("[PID:%d] Server Stopped!\n", getpid());
    exit(ret);
}


void LshttpdMain::processSignal()
{
    if (HttpSignals::gotSigAlarm())
        onGuardTimer();
    if (HttpSignals::gotSigStop())
    {
        LS_NOTICE("SIGTERM received, stop server...");
        s_iRunning = -1;
    }
    if (HttpSignals::gotSigUsr1() || HttpSignals::gotSigHup())
    {
        LS_NOTICE("Server Restart Request via Signal...");
        gracefulRestart();
    }
//     if ( HttpSignals::gotSigHup() )
//     {
//         LS_NOTICE( "SIGHUP received, Reloading configuration file..."));
//         if ( reconfig() == -1)
//         {
//             s_iRunning = 0;
//             return;
//         }
//         applyChanges();
//     }
    if (HttpSignals::gotSigChild())
        waitChildren();
    HttpSignals::resetEvents();
}


int LshttpdMain::getNumCores()
{
#ifdef LSWS_NO_SET_AFFINITY
    return 2;
#else
#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
    return sysconf(_SC_NPROCESSORS_ONLN);
#else
    int nm[2];
    size_t len = 4;
    uint32_t count = 0;

#ifdef HW_AVAILCPU
    nm[0] = CTL_HW;
    nm[1] = HW_AVAILCPU;
    sysctl(nm, 2, &count, &len, NULL, 0);
#endif

    if (count < 1)
    {
        nm[1] = HW_NCPU;
        sysctl(nm, 2, &count, &len, NULL, 0);
        if (count < 1)  count = 1;
    }
    return count;
#endif
#endif
}
/*
void LshttpdMain::setAffinity( pid_t pid, int cpuId )
{
    if (numCPU <= 1)
        return ;

#ifndef LSWS_NO_SET_AFFINITY
    cpu_set_t mask;
    CPU_ZERO(&mask);
    CPU_SET((cpuId - 1)% numCPU, &mask);
    if (SET_AFFINITY(pid, sizeof(cpu_set_t), &mask) < 0)
        LS_ERROR( "[main] setAffinity error, pid %d cpuId %d [numCPU=%d]", pid, cpuId, numCPU ));
    else
        LS_DBG_L( "[main] setAffinity, pid %d cpuId %d [numCPU=%d]", pid, cpuId, numCPU );
#endif
}
*/
