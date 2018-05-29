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
#include <sys/time.h>

// #include <shm/lsshmapi.h>
#include <shm/lsi_shm.h>
#include "lsshmdebug.h"

// #define NO_LUA_TEST
#include <modules/lua/lsluashared.cpp>

//
//  LiteSpeed SHM API test module
//
//  Sample code to test LsLua Api related to LUA Share memory
//
static int    testLuaShmApi()
{
    ls_shmhash_t *pHash = ls_luashm_open("abc");
    assert(pHash);

    ls_luashm_t *pVal;
    const char *key = "Simon";

    pVal = ls_luashm_find(pHash, key);
    if (!pVal)
    {
        /* need to create a new value */
        uint32_t myValue = 8899;
        ls_luashm_setval(pHash, key, ls_luashm_long, &myValue, sizeof(myValue));

        pVal = ls_luashm_find(pHash, key);

        assert(pVal);
    }

    debugBase::dumpBuf("DECODE", (char *)pVal, sizeof(ls_luashm_t));

    fprintf(debugBase::fp(), "%s <%p> dProcess ID = %d ", key, pVal,
            pVal->m_ulong);
    pVal->m_ulong = getpid();
    fprintf(debugBase::fp(), " change to -> %d\n", pVal->m_ulong);

    ls_luashm_close(pHash);
    fflush(debugBase::fp());
    return 0;
}

/*
 * Sample testing code
 */
int    testShmApi()
{
    if (testLuaShmApi())
        return LS_FAIL;
    return 0;
}
