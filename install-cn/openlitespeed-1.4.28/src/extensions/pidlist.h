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
#ifndef PIDLIST_H
#define PIDLIST_H


#include <lsdef.h>

#include <sys/types.h>
#include <util/ghash.h>
class ExtWorker;

class PidList : public GHash
{
public:
    explicit PidList(int size = 13)
        : GHash(size, NULL, NULL)
    {}
    void add(pid_t pid, long tm);
    long remove(pid_t pid);
    LS_NO_COPY_ASSIGN(PidList);
};

class PidInfo
{
public:
    pid_t   m_pid;
    pid_t   m_parent;
    ExtWorker *m_pWorker;
};

#define KILL_TYPE_TERM  -1

class PidSimpleList
{
public:
    PidInfo *m_pBegin;
    PidInfo *m_pCur;
    char     *m_pEnd;

    PidSimpleList(char *pBegin, char *pEnd);
    ~PidSimpleList();
    void add(pid_t pid, pid_t parent, ExtWorker *pWorker);
    ExtWorker *remove(pid_t pid);
    int markToStop(pid_t pid, int kill_type);

    LS_NO_COPY_ASSIGN(PidSimpleList);
};

#endif

