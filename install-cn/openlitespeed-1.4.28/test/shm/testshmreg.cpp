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
#include <http/httplog.h>

#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <shm/lsshm.h>
#include <shm/lsshmpool.h>
#include <shm/lsshmhash.h>
#include "lsshmdebug.h"


static void testFindRegistry(LsShm *pShm, const char *name)
{
    LsShmReg *p_reg;
    if ((p_reg = pShm->findReg(name)))
        debugBase:: dumpRegistry(name , p_reg);
    else
        fprintf(debugBase::fp(), "ERROR: FAILED TO FIND REGISTRY [%s]\n",
                name ? name : "NULL");
}

static void testGetRegistry(LsShm *pShm, int regNum)
{
    char tag[0x100];
    LsShmReg *p_reg;
    snprintf(tag, 0x100, "GET-%d", regNum);
    if ((p_reg = pShm->getReg(regNum)))
        debugBase:: dumpRegistry(tag , p_reg);
    else
        fprintf(debugBase::fp(), "ERROR: FAILED TO GET REGISTRY %d", regNum);
}

void    testShmReg(LsShm *pShm)
{
    LsShmReg *p_reg;
    int    i;

    fprintf(debugBase::fp(), "\nTEST ShmReg BEGIN===============>\n");
    debugBase::dumpShmReg(pShm);
    fprintf(debugBase::fp(), "VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV\n");
    for (i = 1; i < 0x400;)
    {
        p_reg = pShm->getReg(i);
        if (p_reg)
        {
            if (!p_reg->x_iFlag)
            {
                //
                // Should never do this in real ...
                // do this in testing mode only
                // So I don't have to write too much code for testing.
                //
                snprintf((char *)p_reg->x_aName, 12, "NAME-%d", i);
                p_reg->x_iValue = i;
                p_reg->x_iFlag = 1; // set assigned...
            }
            else
                debugBase:: dumpRegistry("FIRST-TIME" , p_reg);
        }
        else
        {
            fprintf(debugBase::fp(), "EXPANDING REG AT %i MAX %d\n",
                    i, pShm->expandReg(i));
            i >>= 1;
        }
        fflush(debugBase::fp());
        i <<= 1;
    }
    fprintf(debugBase::fp(), "^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n");
    debugBase::dumpShmReg(pShm);
    fprintf(debugBase::fp(), "===================================\n");

    testFindRegistry(pShm, "NAME-16");
    testFindRegistry(pShm, "NAME-64");
    testFindRegistry(pShm, "NAME-1");

    /* Fault test... these two should fail. */
    testFindRegistry(pShm, "");
    testFindRegistry(pShm, NULL);

    testGetRegistry(pShm, 2);
    testGetRegistry(pShm, 8);
    testGetRegistry(pShm, 16);
    testGetRegistry(pShm, 13);
    testGetRegistry(pShm, 0);
    testGetRegistry(pShm, 100);

    fprintf(debugBase::fp(), "\nTESTING ShmReg<==================\n");
}

