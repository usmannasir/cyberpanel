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
#include <util/daemonize.h>

#include <lsr/ls_strtool.h>

#include <ctype.h>
#include <fcntl.h>
#include <grp.h>
#include <pwd.h>
#include <stdlib.h>
#include <sys/types.h>
#include <unistd.h>

int Daemonize::daemonize(int nochdir, int noclose)
{
#ifdef daemon
    return daemon(nochdir, noclose);
#else
    if (fork())
        _exit(0);
    if (setsid() == -1)
        return LS_FAIL;
    if (fork())
        _exit(0);
    if (!nochdir)
    {
        if (!getuid())
            chroot("/");
        chdir("/");
    }
    if (!noclose)
        close();
    return 0;
#endif
}


int Daemonize::close()
{
    int fd = open("/dev/null", O_RDWR);
    if (fd != -1)
    {
        dup2(fd, 0);
        dup2(fd, 1);
        dup2(fd, 2);
        ::close(fd);
        return 0;
    }
    return LS_FAIL;
}


//int Daemonize::writePIDFile( const char * pFileName )
//{
//    FILE* pidfp = fopen( pFileName, "w" );
//    if ( pidfp == NULL )
//        return LS_FAIL;
//    fprintf( pidfp, "%d\n", (int)getpid() );
//    fclose( pidfp );
//    return 0;
//}


int Daemonize::changeUserGroupRoot(const char *pUser, uid_t uid, gid_t gid,
                                   gid_t pri_gid, const char *pChroot, char *pErr, int errLen)
{
    if (initGroups(pUser, gid, pri_gid, pErr, errLen) == -1)
        return LS_FAIL;
    return changeUserChroot(pUser, uid, pChroot, pErr, errLen);
}


int Daemonize::initGroups(const char *pUser, gid_t gid, gid_t pri_gid,
                          char *pErr, int errLen)
{
    if (getuid() == 0)
    {
        if (setgid(gid)  < 0)
        {
            ls_snprintf(pErr, errLen, "setgid( %d ) failed!", (int)gid);
            return LS_FAIL;
        }
        if (initgroups(pUser, pri_gid) == -1)
        {
            ls_snprintf(pErr, errLen, "initgroups( %s, %d ) failed!",
                        pUser, (int)pri_gid);
            return LS_FAIL;
        }
    }
    return 0;
}


int Daemonize::changeUserChroot(const char *pUser, uid_t uid,
                                const char *pChroot, char *pErr, int errLen)
{
    if (getuid() == 0)
    {
        if ((pChroot) && (*(pChroot + 1) != 0))
        {
            if (chroot(pChroot) == -1)
            {
                ls_snprintf(pErr, errLen, "chroot( %s ) failed!", pChroot);
                return LS_FAIL;
            }
        }
        if (setuid(uid) < 0)
        {
            ls_snprintf(pErr, errLen, "setuid( %d ) failed!", (int)uid);
            return LS_FAIL;
        }
        if (setuid(0) != -1)
        {
            ls_snprintf(pErr, errLen,
                        "[Kernel bug] setuid(0) succeed after gave up root privilege!");
            return LS_FAIL;
        }
    }
    return 0;
}
struct passwd *Daemonize::configUserGroup(const char *pUser,
        const char *pGroup,
        gid_t &gid)
{
    if (!pUser || !pGroup)
        return NULL;

    struct passwd *pw;
    pw = getpwnam(pUser);

    if (!pw)
    {
        if (isdigit(*pUser))
        {
            uid_t uid = atoi(pUser);
            pw = getpwuid(uid);
        }

        if (!pw)
            return NULL;
    }

    struct group *gr;

    gr = getgrnam(pGroup);

    if (!gr)
    {
        if (isdigit(*pGroup))
            gid = atoi(pGroup);
        else
            return NULL;
    }
    else
        gid = gr->gr_gid;

    return pw;
}
