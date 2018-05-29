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
#include "pidlist.h"
#include <string.h>

void PidList::add(pid_t pid, long tm)
{
    insert((void *)(unsigned long)pid, (void *)tm);
}


long PidList::remove(pid_t pid)
{
    long tm = 0;
    PidList::iterator iter;
    iter = find((void *)(unsigned long)pid);
    if (iter != end())
    {
        tm = (long)iter->second();
        erase(iter);
    }
    return tm;
}


PidSimpleList::PidSimpleList(char *pBegin, char *pEnd)
    : m_pBegin((PidInfo *)pBegin)
    , m_pCur((PidInfo *)pBegin)
    , m_pEnd(pEnd)
{
}


PidSimpleList::~PidSimpleList()
{}


static PidInfo *lower_bound(PidInfo *b, PidInfo *e, pid_t pid)
{
    int c = -1;
    while (b < e)
    {
        PidInfo *m = b + (e - b) / 2;
        c = pid - m->m_pid;
        if (c == 0)
            return m;
        else if (c < 0)
            e = m;
        else
            b = m + 1;
    }
    return b;
}


void PidSimpleList::add(pid_t pid, pid_t parent, ExtWorker *pWorker)
{
    if (((char *)(m_pCur + 1)) > m_pEnd)
        return;
    PidInfo *pInsert = lower_bound(m_pBegin, m_pCur,  pid);
    if (pInsert->m_pid == pid)
    {
        pInsert->m_parent = parent;
        return;
    }
    if (m_pCur > pInsert)
        memmove(pInsert + 1, pInsert, (char *)m_pCur - (char *)pInsert);
    ++m_pCur;
    pInsert->m_pid = pid;
    pInsert->m_parent = parent;
    pInsert->m_pWorker = pWorker;
}


ExtWorker *PidSimpleList::remove(pid_t pid)
{
    ExtWorker *pWorker = NULL;
    if (m_pCur <= m_pBegin)
        return NULL;
    PidInfo *pInsert = lower_bound(m_pBegin, m_pCur,  pid);
    if (pInsert->m_pid == pid)
    {
        pWorker = pInsert->m_pWorker;
        --m_pCur;
        if (m_pCur > pInsert)
            memmove(pInsert, pInsert + 1, (char *)m_pCur - (char *)pInsert);
    }
    return pWorker;
}


int PidSimpleList::markToStop(pid_t pid, int kill_type)
{
    if (m_pCur <= m_pBegin)
        return 0;
    PidInfo *pInsert = lower_bound(m_pBegin, m_pCur,  pid);
    if (pInsert->m_pid == pid)
        pInsert->m_parent = kill_type;
    return 0;
}


