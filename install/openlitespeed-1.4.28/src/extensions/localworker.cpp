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
#include "localworker.h"

#include "localworkerconfig.h"
#include "pidlist.h"
#include "cgi/suexec.h"
#include "registry/extappregistry.h"

#include <http/httpvhost.h>
#include <http/serverprocessconfig.h>
#include <log4cxx/logger.h>
#include <lsr/ls_fileio.h>
#include <main/configctx.h>
#include <main/mainserverconfig.h>
#include <main/serverinfo.h>
#include <socket/gsockaddr.h>
#include <util/datetime.h>
#include <util/env.h>

#include <errno.h>
#include <signal.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define GRACE_TIMEOUT 20
#define KILL_TIMEOUT 25

LocalWorker::LocalWorker(int type)
    : ExtWorker(type)
    , m_fdApp(-1)
    , m_sigGraceStop(SIGTERM)
    , m_pidList(NULL)
    , m_pidListStop(NULL)
{
    m_pidList = new PidList();
    m_pidListStop = new PidList();

}


LocalWorkerConfig &LocalWorker::getConfig() const
{   return *(static_cast<LocalWorkerConfig *>(getConfigPointer()));  }


LocalWorker::~LocalWorker()
{
    if (m_pidList)
        delete m_pidList;
    if (m_pidListStop)
        delete m_pidListStop;
}


static void killProcess(pid_t pid)
{
    if (((kill(pid, SIGTERM) == -1) && (errno == EPERM)) ||
        ((kill(pid, SIGUSR1) == -1) && (errno == EPERM)))
        PidRegistry::markToStop(pid, KILL_TYPE_TERM);
}


void LocalWorker::moveToStopList()
{
    PidList::iterator iter;
    for (iter = m_pidList->begin(); iter != m_pidList->end();
         iter = m_pidList->next(iter))
        m_pidListStop->add((int)(long)iter->first(), DateTime::s_curTime);
    m_pidList->clear();
}


void LocalWorker::moveToStopList(int pid)
{
    PidList::iterator iter = m_pidList->find((void *)(long)pid);
    if (iter != m_pidList->end())
    {
        killProcess(pid);
        m_pidListStop->add(pid, DateTime::s_curTime - GRACE_TIMEOUT);
        m_pidList->erase(iter);
    }
}


void LocalWorker::cleanStopPids()
{
    if ((m_pidListStop) &&
        (m_pidListStop->size() > 0))
    {
        pid_t pid;
        PidList::iterator iter, iterDel;
        for (iter = m_pidListStop->begin(); iter != m_pidListStop->end();)
        {
            pid = (pid_t)(long)iter->first();
            long delta = DateTime::s_curTime - (long)iter->second();
            int sig = 0;
            iterDel = iter;
            iter = m_pidListStop->next(iter);
            if (delta > GRACE_TIMEOUT)
            {
                if ((kill(pid, 0) == -1) && (errno == ESRCH))
                {
                    m_pidListStop->erase(iterDel);
                    PidRegistry::remove(pid);
                    continue;
                }
                if (delta > KILL_TIMEOUT)
                {
                    sig = SIGKILL;
                    LS_NOTICE("[%s] Send SIGKILL to process [%d] that won't stop.",
                              getName(), pid);
                }
                else
                {
                    sig = m_sigGraceStop;
                    LS_NOTICE("[%s] Send SIGTERM to process [%d].",
                              getName(), pid);
                }
                if (kill(pid , sig) != -1)
                    LS_DBG_L("[%s] kill pid: %d", getName(), pid);
                else if (errno == EPERM)
                    PidRegistry::markToStop(pid, KILL_TYPE_TERM);
            }
        }
    }
}


void LocalWorker::detectDiedPid()
{
    PidList::iterator iter;
    for (iter = m_pidList->begin(); iter != m_pidList->end();)
    {
        pid_t pid = (pid_t)(long)iter->first();
        if ((kill(pid, 0) == -1) && (errno == ESRCH))
        {
            LS_INFO("Process with PID: %d is dead ", pid);
            PidList::iterator iterNext = m_pidList->next(iter);
            m_pidList->erase(iter);
            PidRegistry::remove(pid);

            iter = iterNext;

        }
        else
            iter = m_pidList->next(iter);
    }
}


void LocalWorker::addPid(pid_t pid)
{
    m_pidList->insert((void *)(unsigned long)pid, this);
}


void LocalWorker::removePid(pid_t pid)
{
    m_pidList->remove(pid);
    m_pidListStop->remove(pid);
}


int LocalWorker::selfManaged() const
{   return getConfig().getSelfManaged();    }


int LocalWorker::runOnStartUp()
{
    if (getConfig().getRunOnStartUp())
        return startEx();
    return 0;
}


int LocalWorker::startOnDemond(int force)
{
    if (!m_pidList)
        return LS_FAIL;
    int nProc = m_pidList->size();
    if ((getConfig().getRunOnStartUp()) && (nProc > 0))
        return 0;
    if (force)
    {
        if (nProc >= getConfig().getInstances())
        {
//            if ( getConfig().getInstances() > 1 )
//                return restart();
//            else
            return LS_FAIL;
        }
    }
    else
    {
        if (nProc >= getConnPool().getTotalConns())
            return 0;
        if ((nProc == 0)
            && (getConnPool().getTotalConns() > 2))     //server socket is in use.
            return 0;
    }
    return startEx();
}


int LocalWorker::stop()
{
    pid_t pid;
    PidList::iterator iter;
    removeUnixSocket();
    LS_NOTICE("[%s] stop worker processes", getName());
    for (iter = getPidList()->begin(); iter != getPidList()->end();)
    {
        pid = (pid_t)(long)iter->first();
        iter = getPidList()->next(iter);
        killProcess(pid);
        LS_DBG_L("[%s] kill pid: %d", getName(), pid);
    }
    moveToStopList();
    setState(ST_NOTSTARTED);

    return 0;
}


void LocalWorker::removeUnixSocket()
{
    const GSockAddr &addr = ((LocalWorkerConfig *)
                             getConfigPointer())->getServerAddr();
    if ((m_fdApp >= 0) && (getPidList()->size() > 0) &&
        (addr.family() == PF_UNIX))
    {
        LS_DBG_L("[%s] remove unix socket: %s", getName(),
                 addr.getUnix());
        unlink(addr.getUnix());
        close(m_fdApp);
        m_fdApp = -2;
        getConfigPointer()->altServerAddr();
    }
}


int LocalWorker::addNewProcess()
{
    if ((getConfigPointer()->getURL()) &&
        (((LocalWorkerConfig *)getConfigPointer())->getCommand()))
        return startEx();
    return 1;
}


int LocalWorker::tryRestart()
{
    if (DateTime::s_curTime - getLastRestart() > 10)
    {
        LS_NOTICE("[%s] try to fix 503 error by restarting external application",
                  getName());
        return restart();
    }
    return 0;
}


int LocalWorker::restart()
{
    setLastRestart(DateTime::s_curTime);
    clearCurConnPool();
    if ((getConfigPointer()->getURL()) &&
        (((LocalWorkerConfig *)getConfigPointer())->getCommand()))
    {
        removeUnixSocket();
        moveToStopList();
        return start();
    }
    return 1;
}


int LocalWorker::getCurInstances() const
{   return getPidList()->size();  }


// void LocalWorker::setPidList( PidList * l)
// {
//     m_pidList = l;
//     if (( l )&& !m_pidListStop )
//         m_pidListStop = new PidList();
// }


// static int workerSUExec( LocalWorkerConfig& config, int fd )
// {
//     const HttpVHost * pVHost = config.getVHost();
//     if (( !HttpGlobals::s_pSUExec )||( !pVHost ))
//         return LS_FAIL;
//     int mode = pVHost->getRootContext().getSetUidMode();
//     if ( mode != UID_DOCROOT )
//         return LS_FAIL;
//     uid_t uid = pVHost->getUid();
//     gid_t gid = pVHost->getGid();
//     if (( uid == HttpGlobals::s_uid )&&
//         ( gid == HttpGlobals::s_gid ))
//         return LS_FAIL;
//
//     if (( uid < HttpGlobals::s_uidMin )||
//         ( gid < HttpGlobals::s_gidMin ))
//     {
//         LS_INFO( "[VHost:%s] Fast CGI [%s]: suExec access denied,"
//                     " UID or GID of VHost document root is smaller "
//                     "than minimum UID, GID configured. ", pVHost->getName(),
//                     config.getName() ));
//         return LS_FAIL;
//     }
//     const char * pChroot = NULL;
//     int chrootLen = 0;
// //    if ( HttpGlobals::s_psChroot )
// //    {
// //        pChroot = HttpGlobals::s_psChroot->c_str();
// //        chrootLen = HttpGlobals::s_psChroot->len();
// //    }
//     char achBuf[4096];
//     memccpy( achBuf, config.getCommand(), 0, 4096 );
//     char * argv[256];
//     char * pDir ;
//     SUExec::buildArgv( achBuf, &pDir, argv, 256 );
//     if ( pDir )
//         *(argv[0]-1) = '/';
//     else
//         pDir = argv[0];
//     HttpGlobals::s_pSUExec->prepare( uid, gid, config.getPriority(),
//           pChroot, chrootLen,
//           pDir, strlen( pDir ), config.getRLimits() );
//     int rfd = -1;
//     int pid = HttpGlobals::s_pSUExec->suEXEC( HttpGlobals::s_pServerRoot, &rfd, fd, argv,
//                 config.getEnv()->get(), NULL );
// //    if ( pid != -1)
// //    {
// //        char achBuf[2048];
// //        int ret;
// //        while( ( ret = read( rfd, achBuf, 2048 )) > 0 )
// //        {
// //            write( 2, achBuf, ret );
// //        }
// //    }
//     if ( rfd != -1 )
//         close( rfd );
//
//     return pid;
// }


int LocalWorker::workerExec(LocalWorkerConfig &config, int fd)
{
    ServerProcessConfig &procConfig = ServerProcessConfig::getInstance();
    if (SUExec::getSUExec() == NULL)
        return LS_FAIL;
    uid_t uid;
    gid_t gid;
    const HttpVHost *pVHost = config.getVHost();
    uid = config.getUid();
    gid = config.getGid();
    if ((int)uid == -1)
        uid = procConfig.getUid();
    if ((int)gid == -1)
        gid = procConfig.getGid();

    if (pVHost && pVHost->getRootContext().getSetUidMode() == UID_DOCROOT)
    {
        uid = pVHost->getUid();
        gid = pVHost->getGid();
        if (procConfig.getForceGid() != 0)
            gid = procConfig.getForceGid();

        if ((uid < procConfig.getUidMin()) ||
            (gid < procConfig.getGidMin()))
        {
            if (LS_LOG_ENABLED(LOG4CXX_NS::Level::DBG_LESS))
                LS_INFO("[VHost:%s] Fast CGI [%s]: suExec access denied,"
                        " UID or GID of VHost document root is smaller "
                        "than minimum UID, GID configured. ", pVHost->getName(),
                        config.getName());
            return LS_FAIL;
        }
    }
    //if (( uid == HttpGlobals::s_uid )&&
    //    ( gid == HttpGlobals::s_gid ))
    //    return LS_FAIL;
    const AutoStr2 *pChroot = NULL;
    const char *pChrootPath = NULL;
    int chrootLen = 0;
    int chMode = 0;
    if (pVHost)
    {
        chMode = pVHost->getRootContext().getChrootMode();
        switch (chMode)
        {
        case CHROOT_VHROOT:
            pChroot = pVHost->getVhRoot();
            break;
        case CHROOT_PATH:
            pChroot = pVHost->getChroot();
            if (!pChroot->c_str())
                pChroot = NULL;
        }
        //Since we already in the chroot jail, do not use the global jail path
        //If start external app with lscgid, apply global chroot path,
        //  as lscgid is not inside chroot
        if (config.getStartByServer() == 2)
        {
            if (!pChroot)
                pChroot = procConfig.getChroot();
        }
        if (pChroot)
        {
            pChrootPath = pChroot->c_str();
            chrootLen = pChroot->len();
        }
    }
    char achBuf[4096];
    memccpy(achBuf, config.getCommand(), 0, 4096);
    char *argv[256];
    char *pDir ;
    SUExec::buildArgv(achBuf, &pDir, argv, 256);
    if (pDir)
        *(argv[0] - 1) = '/';
    else
        pDir = argv[0];
    SUExec::getSUExec()->prepare(uid, gid, config.getPriority(),
                                 config.getUmask(),
                                 pChrootPath, chrootLen,
                                 pDir, strlen(pDir), config.getRLimits());
    int rfd = -1;
    int pid;
    //if ( config.getStartByServer() == 2 )
    //{
    pid = SUExec::getSUExec()->cgidSuEXEC(
              MainServerConfig::getInstance().getServerRoot(), &rfd, fd, argv,
              config.getEnv()->get(), NULL);
    //}
    //else
    //{
    //    pid = HttpGlobals::s_pSUExec->suEXEC(
    //        HttpGlobals::s_pServerRoot, &rfd, fd, argv,
    //        config.getEnv()->get(), NULL );
    //}

    if (pid == -1)
        pid = SUExec::spawnChild(config.getCommand(), fd, -1,
                                 config.getEnv()->get(),
                                 config.getPriority(), config.getRLimits(),
                                 config.getUmask());
    if (rfd != -1)
        close(rfd);

    return pid;
}


int LocalWorker::startWorker()
{
    int fd = getfd();
    LocalWorkerConfig &config = getConfig();
    struct stat st;
//    if (( stat( config.getCommand(), &st ) == -1 )||
//        ( access(config.getCommand(), X_OK) == -1 ))
//    {
//        LS_ERROR("Start FCGI [%s]: invalid path to executable - %s,"
//                 " not exist or not executable ",
//                config.getName(),config.getCommand() ));
//        return LS_FAIL;
//    }
//    if ( st.st_mode & S_ISUID )
//    {
//        LS_DBG_L( "Fast CGI [%s]: Setuid bit is not allowed : %s\n",
//                config.getName(), config.getCommand());
//        return LS_FAIL;
//    }
    if (fd < 0)
    {
        fd = ExtWorker::startServerSock(&config, config.getBackLog());
        if (fd != -1)
        {
            setfd(fd);
            if (config.getServerAddr().family() == PF_UNIX)
            {
                ls_fio_stat(config.getServerAddr().getUnix(), &st);
                ServerInfo::getServerInfo()->addUnixSocket(
                    config.getServerAddr().getUnix(), &st);
            }
        }
        else
            return LS_FAIL;
    }
    int instances = config.getInstances();
    int cur_instances = getCurInstances();
    int new_instances = getConnPool().getTotalConns() + 2 - cur_instances;
    if (new_instances <= 0)
        new_instances = 1;
    if (instances < new_instances + cur_instances)
        new_instances = instances - cur_instances;
    if (new_instances <= 0)
        return 0;
    int i;
    for (i = 0; i < new_instances; ++i)
    {
        int pid;
        pid = workerExec(config, fd);
        if (pid > 0)
        {
            LS_DBG_L("[%s] add child process pid: %d", getName(), pid);
            PidRegistry::add(pid, this, 0);
        }
        else
        {
            LS_ERROR("Start [%s]: failed to start the # %d of %d instances.",
                     config.getName(), i + 1, instances);
            break;
        }
    }
    return (i == 0) ? LS_FAIL : LS_OK;
}


void LocalWorker::configRlimit(RLimits *pRLimits, const XmlNode *pNode)
{
    if (!pNode)
        return;

    pRLimits->setProcLimit(
        ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "procSoftLimit", 0,
                INT_MAX, 0),
        ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "procHardLimit", 0,
                INT_MAX, 0));

    pRLimits->setCPULimit(
        ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "CPUSoftLimit", 0,
                INT_MAX, 0),
        ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "CPUHardLimit", 0,
                INT_MAX, 0));
    long memSoft = ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                   "memSoftLimit", 0, INT_MAX, 0);
    long memHard = ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                   "memHardLimit", 0, INT_MAX, 0);

    if ((memSoft & (memSoft < 1024 * 1024)) ||
        (memHard & (memHard < 1024 * 1024)))
    {
        LS_ERROR(ConfigCtx::getCurConfigCtx(),
                 "Memory limit is too low with %ld/%ld",
                 memSoft, memHard);
    }
    else
        pRLimits->setDataLimit(memSoft, memHard);
}




