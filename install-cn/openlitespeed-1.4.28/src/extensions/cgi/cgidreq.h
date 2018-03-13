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
#ifndef CGIDREQ_H
#define CGIDREQ_H

#include <lsdef.h>
#include <util/autobuf.h>
#include <util/ienv.h>
#include "lscgiddef.h"

class RLimits;
class CgidReq : public IEnv
{
    AutoBuf m_buf;
public:
    CgidReq();
    ~CgidReq();
    int add(const char *name, const char *value)
    {   return IEnv::add(name, value);    }

    int add(const char *name, size_t nameLen,
            const char *value, size_t valLen);
    int add(const char *buf, size_t len)
    {   return m_buf.append(buf, len);    }

    void clear();

    const char *get() const    {   return m_buf.begin();       }
    int size() const            {   return m_buf.size();        }
    int appendString(const char *pBuf, size_t len);

    lscgid_req *getCgidReq()   {   return (lscgid_req *)m_buf.begin();   }

    int appendArgv(const char *pArgv, int len);
    int appendEnv(const char *pEnv, int len);
    int buildReqHeader(int uid, int gid, int priority, int umaskVal,
                       const char *pChroot, int chrootLen,
                       const char *pReal, int pathLen, const RLimits *pLimits);
    int finalize(int req_id, const char *pSecret, int type);

    LS_NO_COPY_ASSIGN(CgidReq);
};

#endif
