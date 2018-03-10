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
#include <util/crashguard.h>

#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#include <util/signalutil.h>

static int s_iRunning = 0;
static int s_iSigChild = 0;
static int s_pid    = 0;
static void sigChild(int sig)
{
    //printf( "signchild()!\n" );
    s_iSigChild = 1;
}

static void sigBroadcast(int sig)
{
    //printf( "sig_broadcast(%d)!\n", sig );
    kill(s_pid, sig);
    if (sig == SIGTERM)
        s_iRunning = false;
}

static void init()
{
    SignalUtil::signal(SIGTERM, sigBroadcast);
    SignalUtil::signal(SIGHUP, sigBroadcast);
    SignalUtil::signal(SIGCHLD, sigChild);
}

int CrashGuard::guardCrash()
{
    long lLastForkTime  = 0;
    int  iForkCount     = 0;
    int  rpid           = 0;
    int  ret            = 0;
    int  stat;
    assert(m_pGuardedApp);
    init();
    s_iRunning = 1;
    while (s_iRunning)
    {
        if (s_pid == rpid)
        {
            long curTime = time(NULL);
            if (curTime - lLastForkTime > 10)
            {
                iForkCount = 0;
                lLastForkTime = curTime;
            }
            else
            {
                ++iForkCount;
                if (iForkCount > 20)
                {
                    ret = m_pGuardedApp->forkTooFreq();
                    if (ret > 0)
                        break;
                    sleep(60);
                }
            }
            m_pGuardedApp->preFork();
            s_pid = fork();
            if (s_pid == -1)
            {
                m_pGuardedApp->forkError(errno);
                return LS_FAIL;
            }
            else if (s_pid == 0)
                return 0;
            else
                m_pGuardedApp->postFork(s_pid);
            rpid = 0;

        }
        ::sleep(1);
        if (s_iSigChild)
        {
            s_iSigChild = 0;
            //printf( "waitpid()\n" );
            rpid = ::waitpid(-1, &stat, WNOHANG);
            if (rpid > 0)
            {
                if (WIFEXITED(stat))
                {
                    ret = WEXITSTATUS(stat);
                    m_pGuardedApp->childExit(rpid, ret);
                    break;
                }
                else if (WIFSIGNALED(stat))
                {
                    int sig_num = WTERMSIG(stat);
                    if (sig_num == SIGKILL)
                        break;
                    ret = m_pGuardedApp->childSignaled(rpid, sig_num,
#ifdef WCOREDUMP
                                                       WCOREDUMP(stat)
#else
                                                       - 1
#endif
                                                      );
                    if (ret != 0)
                        break;
                }
            }
        }
        else
            m_pGuardedApp->onGuardTimer();
    }
    if (s_pid > 0)
        if (::kill(s_pid, 0) == 0)
        {
            sleep(1);
            ::kill(s_pid, SIGKILL);
        }
    exit(ret);
}

