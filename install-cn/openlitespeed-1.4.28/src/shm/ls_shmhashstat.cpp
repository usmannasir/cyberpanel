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

#include <shm/lsshmpool.h>
#include <shm/lsshmhash.h>

#include <stdio.h>
#include <string.h>
#include <unistd.h>


static const char *g_pShmDirName = "/dev/shm/lslb";
static const char *g_pShmName = NULL;
static const char *g_pHashName = NULL;

typedef struct
{
    LsShmHash *pHash;
    LsShmSize_t totalSize;
} MyStat;


char *argv0 = NULL;

#include <util/pool.h>
Pool g_pool;


int chkHashTable(LsShm *pShm, LsShmReg *pReg, int *pMode, int *pFlags);
void doStatShmHash(LsShmHash *pHash);


void usage()
{
    fprintf(stderr,
            "usage: ls_shmhashstat -f shmfile -t hashtable [ -d dirname ]\n");
    return;
}


int getOptions(int ac, char *av[])
{
    int opt;
    int ret = 0;
    while ((opt = getopt(ac, av, "d:f:t:")) != -1)
    {
        switch (opt)
        {
        case 'd':
            g_pShmDirName = optarg;
            break;
        case 'f':
            g_pShmName = optarg;
            break;
        case 't':
            g_pHashName = optarg;
            break;
        default:
            usage();
            return -1;
        }
    }
    if (g_pShmName == NULL)
    {
        fprintf(stderr, "Missing mandatory shmfile.\n");
        ret = -1;
    }
    if (g_pHashName == NULL)
    {
        fprintf(stderr, "Missing mandatory hashtable.\n");
        ret = -1;
    }
    if (ret < 0)
        usage();
    return ret;
}


int main(int ac, char *av[])
{
    LsShm *pShm;
    LsShmPool *pGPool;
    LsShmHash *pHash;
    LsShmReg *pReg;
    int mode;
    int flags;
    char buf[2048];

    if (getOptions(ac, av) < 0)
        return 1;

    snprintf(buf, sizeof(buf), "%s/%s.%s",
             g_pShmDirName, g_pShmName, LSSHM_SYSSHM_FILE_EXT);
    if (access(buf, R_OK | W_OK) < 0)
    {
        fprintf(stderr, "Unable to access [%s], %s.\n", buf, strerror(errno));
        return 2;
    }
    if ((pShm = LsShm::open(g_pShmName, 0, g_pShmDirName)) == NULL)
    {
        fprintf(stderr, "LsShm::open(%s/%s) FAILED!\n",
                g_pShmDirName, g_pShmName);
        fprintf(stderr, "%s\nstat=%d, errno=%d.\n",
                (char *)LsShm::getErrMsg(), LsShm::getErrStat(), LsShm::getErrNo());
        LsShm::clrErrMsg();
        return 1;
    }
    if ((pGPool = pShm->getGlobalPool()) == NULL)
    {
        fprintf(stderr, "getGlobalPool() FAILED!\n");
        return 2;
    }
    if ((pReg = pShm->findReg(g_pHashName)) == NULL)
    {
        fprintf(stderr, "Unable to find [%s] in registry!\n", g_pHashName);
        return 3;
    }
    if (LsShmHash::chkHashTable(pShm, pReg, &mode, &flags) < 0)
    {
        fprintf(stderr, "Not a Hash Table [%s]!\n", g_pHashName);
        return 4;
    }
    if ((pHash = pGPool->getNamedHash(g_pHashName, 0,
                                      (LsShmHasher_fn)(long)mode,
                                      (LsShmValComp_fn)(long)mode,
                                      flags)) == NULL)
    {
        fprintf(stderr, "getNamedHash(%s,lru=%d) FAILED!\n",
                g_pHashName, flags);
        return 5;
    }

    doStatShmHash(pHash);

    return 0;
}


int iterFunc(LsShmHash::iteroffset iterOff, void *pData)
{
    MyStat *pMyStat = (MyStat *)((LsHashStat *)pData)->userData;
    LsShmHash *pHash = pMyStat->pHash;
    LsShmHash::iterator iter = pHash->offset2iterator(iterOff);
    pMyStat->totalSize += LsShmPool::size2roundSize(iter->x_iLen);
    return 0;
}


void doStatShmHash(LsShmHash *pHash)
{
    LsHashStat hStat;
    LsHashLruInfo *pLru;
    MyStat mystat;
    LsShmHTableStat *pStat =
        (LsShmHTableStat *)pHash->offset2ptr(pHash->getHTableStatOffset());

    fprintf(stdout, "SHMHASH [%s]\ncurrent total hash memory: %u\n",
            pHash->name(),
            pStat->m_iHashInUse
           );

    fprintf(stdout, "checking iterators... ");
    fflush(stdout);
    mystat.pHash = pHash;
    mystat.totalSize = 0;
    if (pHash->stat(&hStat, iterFunc, (void *)&mystat) < 0)
    {
        fprintf(stdout, "ERRORS!!!\n");
        return;
    }
    fprintf(stdout, "DONE.\n"
                    "total elements:            %u\n"
                    "total hash indexes:        %u\n"
                    "occupied hash indexes:     %u\n"
                    "longest index linked list: %u\n"
                    "hash keys duplicated:      %u\n"
                    "total iterator memory:     %u\n",
            hStat.num,
            hStat.numIdx,
            hStat.numIdxOccupied,
            hStat.maxLink,
            hStat.numDup,
            mystat.totalSize
           );

    if ((pLru = pHash->getLru()) != NULL)
    {
        fprintf(stdout, "LRU\n"
                        "total elements:            %u\n"
                        "total elements trimmed:    %u\n",
                pHash->getLruTotal(), //pLru->nvalset,
                pHash->getLruTrimmed() //pLru->nvalexp
               );
        fprintf(stdout, "LRU linked list... ");
        fflush(stdout);
        const char *str;
        switch (pHash->check())
        {
            case SHMLRU_BADINIT:
                str = "Not an LRU Hash.";
                break;
            case SHMLRU_CHECKOK:
                str = "VERIFIED.";
                break;
            default:
                str = "ERRORS!!!";
                break;
        }
        fprintf(stdout, "%s\n", str);
    }
    return;
}

