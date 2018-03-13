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
#include <util/emailsender.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <lsr/ls_strtool.h>
#include <lsdef.h>

EmailSender::EmailSender()
{
}
EmailSender::~EmailSender()
{
}


static int callShell(const char *command)
{
    int pid;

    if (command == NULL)
        return 1;
    pid = fork();
    if (pid == -1)
        return LS_FAIL;
    if (pid == 0)
    {
        char *argv[4];
        argv[0] = (char *)"sh";
        argv[1] = (char *)"-c";
        argv[2] = (char *)command;
        argv[3] = 0;
        execve("/bin/sh", argv, NULL);
        exit(0);
    }
    //return 0;

    int status;
    //cout << "waiting pid:" << pid << endl;
    do
    {
        if (waitpid(pid, &status, 0) == -1)
        {
            //cout << "waitpid() return -1, errno = " << errno << endl;
            if (errno != EINTR)
                return LS_FAIL;
        }
        else
        {
            //cout << "status = " << status << endl;
            return status;
        }
    }
    while (1);

}


int EmailSender::send(const char *pSubject, const char *to,
                      const char *content, const char *cc,
                      const char *bcc)
{
    char achFileName[50] = "/tmp/m-XXXXXX";
    int fd = mkstemp(achFileName);
    if (fd == -1)
        return LS_FAIL;
    write(fd, content, strlen(content));
    close(fd);
    int ret = sendFile(pSubject, to, achFileName, cc, bcc);
    ::unlink(achFileName);
    return ret;
}

int EmailSender::sendFile(const char *pSubject, const char *to,
                          const char *pFileName, const char *cc ,
                          const char *bcc)
{
    static const char *pMailCmds[5] =
    {
        "/usr/bin/mailx", "/bin/mailx", "/usr/bin/mail",
        "/bin/mail", "mailx"
    };
    char achCmd[2048];
    if ((!pSubject) || (!to) || (!pFileName))
    {
        errno = EINVAL;
        return LS_FAIL;
    }
    const char *pMailCmd;
    int i;
    for (i = 0; i < 4; ++i)
    {
        if (access(pMailCmds[i], X_OK) == 0)
            break;
    }
    pMailCmd = pMailCmds[i];
    if (cc == NULL)
        cc = "";
    if (bcc == NULL)
        bcc = "";
    ls_snprintf(achCmd, sizeof(achCmd),
                "%s -b '%s' -c '%s' -s '%s' %s < %s",
                pMailCmd, bcc, cc, pSubject, to, pFileName);
    return callShell(achCmd);
}

