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
#ifndef SEMAPHORE_H
#define SEMAPHORE_H


#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/sem.h>

class Semaphore
{
private:
    int m_iSemId;
    Semaphore(const Semaphore &);
    void operator=(const Semaphore &);
public:
    explicit Semaphore(int id)
        : m_iSemId(id)
    {}
    Semaphore(const char *pszPath, int projId);
    ~Semaphore();
    int  getSemId() const   {   return m_iSemId; }
    int  op(struct sembuf *sops, unsigned nsops)
    {   return  semop(m_iSemId, sops, nsops);  }
    int  op(int sem_num, int sem_op, int sem_flag);
};


#endif
