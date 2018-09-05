/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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
#include "fcgistarter.h"
#include "fcgidef.h"
#include "fcgiapp.h"
#include "fcgiappconfig.h"

#include <extensions/registry/extappregistry.h>
#include <http/httplog.h>
#include <lsr/ls_fileio.h>
#include <main/serverinfo.h>

#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>


FcgiStarter::FcgiStarter()
{
}


FcgiStarter::~FcgiStarter()
{
}


int FcgiStarter::start(FcgiApp &app)
{
    int fd = app.getfd();
    FcgiAppConfig &config = app.getConfig();
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
//        ( "Fast CGI [%s]: Setuid bit is not allowed : %s\n",
//                config.getName(), config.getCommand() );
//        return LS_FAIL;
//    }
    if (app.getfd() < 0)
    {
        fd = ExtWorker::startServerSock(&config, config.getBackLog());
        if (fd != -1)
        {
            app.setfd(fd);
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
    int cur_instances = app.getCurInstances();
    int new_instances = app.getConnPool().getTotalConns() + 2 - cur_instances;
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
        pid = LocalWorker::workerExec(config, fd);
        if (pid > 0)
        {
            LS_DBG_L("[%s] add child process pid: %d", app.getName(), pid);
            PidRegistry::add(pid, &app, 0);
        }
        else
        {
            LS_ERROR("Start FCGI [%s]: failed to start the %d of %d instances.",
                     config.getName(), i + 1, instances);
            break;
        }
    }
    return (i == 0) ? LS_FAIL : LS_OK;
}


