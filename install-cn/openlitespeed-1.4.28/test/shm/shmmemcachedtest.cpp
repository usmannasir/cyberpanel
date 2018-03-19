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

#include <shm/lsshmmemcached.h>

#include <stdio.h>
#include <string.h>
#include <errno.h>

static const char *g_pShmDirName = LsShm::getDefaultShmDir();
static const char *g_pShmName = "SHMMCTEST";
static const char *g_pHashName = "SHMMCHASH";

char *argv0 = NULL;

union binbuf
{
    McBinCmdHdr binhdr;
    uint8_t data[1024];
} binbuf;


int main(int ac, char *av[])
{
    char achShmFileName[255];
    char achLockFileName[255];
    snprintf(achShmFileName, sizeof(achShmFileName), "%s/%s.shm",
             g_pShmDirName, g_pShmName);
    snprintf(achLockFileName, sizeof(achLockFileName), "%s/%s.lock",
             g_pShmDirName, g_pShmName);
#ifdef notdef
    unlink(achShmFileName);
    unlink(achLockFileName);
#endif

    fprintf(stdout, "shmmemcachedtest: [%s/%s]\n",
            g_pShmName, g_pHashName);

    LsShm *pShm;
    LsShmPool *pGPool;
    LsShmHash *pHash;
    LsShmMemCached *pMC;
    char cmdbuf[80];
    char databuf[80];

    pShm = LsShm::open(g_pShmName, 0, g_pShmDirName);
#ifdef notdef
    if (unlink(achShmFileName) != 0)
        perror(achShmFileName);
    if (unlink(achLockFileName) != 0)
        perror(achLockFileName);
#endif
    if (pShm == NULL)
    {
        fprintf(stderr, "LsShm::open [%s] failed!\n", achShmFileName);
        return 1;
    }

    if ((pGPool = pShm->getGlobalPool()) == NULL)
    {
        fprintf(stderr, "getGlobalPool failed!\n");
        return 2;
    }

    if ((pHash = pGPool->getNamedHash(g_pHashName, 0,
                                      LsShmHash::hashXXH32, memcmp, LSSHM_LRU_MODE1)) == NULL)
    {
        fprintf(stderr, "getNamedHash failed!\n");
        return 3;
    }

    pMC = new LsShmMemCached(pHash, true);
    while (fgets(cmdbuf, sizeof(cmdbuf), stdin) != NULL)
    {
        int ret;
        char *p;
        if ((p = strchr(cmdbuf, '\n')) != NULL)
            * p = '\0';
        if (memcmp(cmdbuf, "bin", 3) == 0)
        {
            if ((pMC->convertCmd(&cmdbuf[3], (uint8_t *)&binbuf.binhdr) < 0)
                || (pMC->processBinCmd((uint8_t *)&binbuf.binhdr) < 0))
                fprintf(stdout, "FAILED!\n");
        }
        else if ((ret = pMC->processCmd(cmdbuf)) < 0)
            fprintf(stdout, "FAILED!\n");
        else if (ret > 0)   // need more data
        {
            if (fgets(databuf, sizeof(databuf), stdin) == NULL)
                break;
            if ((p = strchr(databuf, '\n')) != NULL)
                * p = '\0';
            fprintf(stdout, "data:[%s]\n", databuf);
            if (pMC->doDataUpdate((uint8_t *)databuf) < 0)
                fprintf(stdout, "FAILED!\n");
        }
    }
    return 0;
}
