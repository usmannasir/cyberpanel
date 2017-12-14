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
#include <util/semaphore.h>
#include <assert.h>
#include <stdio.h>

Semaphore::Semaphore(const char *pszPath, int projId)
{
    int iSemId;
    FILE *fp;
    assert(pszPath != NULL);
    if ((fp = fopen(pszPath, "r")) == NULL)
        fp = fopen(pszPath, "w+");
    if (fp)
    {
        fclose(fp);
        m_iSemId = ftok(pszPath, projId);
        iSemId = semget(m_iSemId, 1, IPC_CREAT);     // | IPC_EXCL
        if (iSemId != -1)
        {
            m_iSemId = iSemId;
            //union semun semval1;
            //semval1.val = 1;
            semctl(m_iSemId, 0, SETVAL, 1);
            return;
        }
    }
    throw;
}

Semaphore::~Semaphore()
{
//    if ( m_iSemId != -1 )
//    {
//        //semctl( m_iSemId, 0, IPC_RMID, 1 );
//        m_iSemId = -1;
//    }
}
int  Semaphore::op(int sem_num, int sem_op, int sem_flag)
{
    struct sembuf semBuf;
    semBuf.sem_num = sem_num;
    semBuf.sem_op = sem_op;
    semBuf.sem_flg = sem_flag;
    return op(&semBuf, 1);
}



