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
#ifndef SUEXEC_H
#define SUEXEC_H

#include "cgidreq.h"

#include <lsdef.h>

class RLimits;
class SUExec
{
    CgidReq         m_req;
    static SUExec  *s_pSUExec;

public:
    SUExec();
    ~SUExec();
    static int buildArgv(char *pCmd, char **pDir, char **pArgv, int argvLen);
    static int spawnChild(const char *pAppCmd, int fdIn, int fdOut,
                          char *const *env, int priority, const RLimits *pLimits,
                          int umaskVal, uid_t uid = 0, gid_t gid = 0);

    int prepare(int uid, int gid, int priority, int umaskVal,
                const char *pChroot, int chrootLen,
                const char *pReal, int pathLen, const RLimits *pLimits)
    {
        return m_req.buildReqHeader(uid, gid, priority, umaskVal,
                                    pChroot, chrootLen, pReal, pathLen, pLimits);
    }

    int appendArgv(const char *pArgv, int len)
    {   return m_req.appendArgv(pArgv, len);  }

    int appendEnv(const char *pKey, int len, const char *pVal, int valLen)
    {   return m_req.add(pKey, len, pVal, valLen);    }

    int checkLScgid(const char *path);
    int suEXEC(const char *pServerRoot, int *pfd, int fdListen,
               char *const *pArgv, char *const *pEnv, const RLimits *pLimits);
    int cgidSuEXEC(const char *pServerRoot, int *pfd, int listenFd,
                   char *const *pArgv, char *const *env, const RLimits *pLimits);

    static void initSUExec()
    {   s_pSUExec = new SUExec();    }
    static SUExec *getSUExec()
    {   return s_pSUExec;       }

    LS_NO_COPY_ASSIGN(SUExec);
};

#endif
