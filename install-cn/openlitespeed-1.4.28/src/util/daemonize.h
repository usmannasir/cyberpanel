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
#ifndef DAEMONIZE_H
#define DAEMONIZE_H


#include <sys/types.h>
class ConfigCtx;
class Daemonize
{
    Daemonize() {};
    ~Daemonize() {};
public:
    static int daemonize(int nochdir, int noclose);
    static int close();
    //static int writePIDFile( const char * pFile );
    static int initGroups(const char *pUser, gid_t gid, gid_t pri_gid,
                          char *pErr, int errLen);
    static int changeUserChroot(const char *pUser, uid_t uid,
                                const char *pChroot, char *pErr, int errLen);
    static int changeUserGroupRoot(const char *pUser, uid_t uid, gid_t gid,
                                   gid_t pri_gid, const char *pChroot, char *pErr, int errLen);
    static struct passwd *configUserGroup(const char *pUser,
                                          const char *pGroup,
                                          gid_t &gid);
};

#endif
