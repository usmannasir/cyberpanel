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
#ifndef LSHTTPDMAIN_H
#define LSHTTPDMAIN_H



#include <util/autostr.h>
#include <util/guardedapp.h>
#include <util/linkobjpool.h>
#include <util/pidfile.h>

#include <sys/types.h>


#define  CP_RUNNING     0
#define  CP_SHUTDOWN    1

class ChildProc : public LinkedObj
{


    ChildProc(const ChildProc &rhs);
    void operator=(const ChildProc &rhs);
public:
    int             m_pid;
    unsigned short  m_iProcNo;
    short           m_iState;
    char           *m_pBlackBoard;

    ChildProc()
        : m_pid(-1)
        , m_iProcNo(0)
        , m_iState(0)
        , m_pBlackBoard(NULL)
    {}

    ~ChildProc()
    {
        //Note: can not release blackboard
    }
};


class HttpConfigLoader;
class HttpServer;

class LshttpdMain
{
    HttpServer         *m_pServer;
    HttpConfigLoader *m_pBuilder;
    AutoStr             m_sCtrlFile;
    PidFile             m_pidFile;
    pid_t               m_pid;
    int                 m_noDaemon;
    int                 m_noCrashGuard;
    AutoStr             m_gdbPath;

    int                *m_pProcState;
    LinkQueue           m_childrenList;
    LinkObjPool<ChildProc>  m_pool;
    int                 m_curChildren;
    int                 m_fdAdmin;

    int     getFullPath(const char *pRelativePath, char *pBuf, int bufLen);
    int     execute(const char *pExecCmd, const char *pParam);

    int forkTooFreq();
    int preFork();
    int forkError(int err);
    int postFork(pid_t pid);
    int childExit(pid_t ch_pid, int stat);
    int childSignaled(pid_t pid, int signal, int coredump);
    int SendCrashNotification(pid_t pid, int signal, int coredump,
                              char *pCoreFile);
    int recoverShmCrash(ChildProc *pProc);

    void onGuardTimer();
    int processAdminCmd(char *pCmd, char *pEnd, int &apply);
    //void processAdminCtrlFile( const char * cmdFileName );
    void writeSysStats();
    void writeProcessData(int fd);
    int testServerRoot(const char *pRoot);
    int getServerRootFromExecutablePath(const char *command, char *pBuf,
                                        int len);
    int guessCommonServerRoot();
    int getServerRoot(int argc, char *argv[]);
    void changeOwner();
    void gracefulRestart();
    int  checkRestartReq();
    int  clearToStopApp();


    int config();
    int reconfig();
    int init(int argc, char *argv[]);
    void applyChanges();
    int testRunningServer();
    const char *getPidFile();
    
    void printVersion();
    void parseOpt(int argc, char *argv[]);
    char *allocateBlackBoard();
    int allocatePidTracker();
    void removeOldRtreport();

    void deallocateBlackBoard(char *pBuf);

    int             startChild(ChildProc *pProc);
    int             childDead(int pid);
    void            stopAllChildren();
    void            waitChildren();
    void            broadcastSig(int sig, int changeState);
    void            releaseExcept(ChildProc *pCurProc);
    int             getFirstAvailSlot();
    void            setChildSlot(int num, int val);
    int             guardCrash();
    int             cleanUp(int pid, char *pBB);

    int             startAdminSocket();
    int             closeAdminSocket();
    int             acceptAdminSockConn();

    int             processAdminSockConn(int fd);
    int             processAdminBuffer(char *p, char *pEnd);

    void            processSignal();

    int             getNumCores();
    void            setAffinity(pid_t pid, int cpuId);

    LshttpdMain(const LshttpdMain &rhs);
    void operator=(const LshttpdMain &rhs);
public:
    LshttpdMain();
    ~LshttpdMain();
    int main(int argc, char *argv[]);
};

#endif
