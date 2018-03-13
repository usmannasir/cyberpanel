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

#include <stdio.h>
#include <string.h>
#include <unistd.h>


static const char *g_pShmDirName = "/dev/shm/lslb";
static const char *g_pShmName = NULL;


char *argv0 = NULL;

#include <util/pool.h>
Pool g_pool;


void doStatShm(LsShm *pShm);
void doStatShmPool(LsShmPool *pPool);


LsShmSize_t blks2kbytes(LsShmSize_t blks)
{   return blks * LSSHM_SHM_UNITSIZE / 1024;  }


void usage()
{
    fprintf(stderr, "usage: ls_shmstat -f shmname [ -d dirname ]\n");
    return;
}


int getOptions(int ac, char *av[])
{
    int opt;
    while ((opt = getopt(ac, av, "f:d:")) != -1)
    {
        switch (opt)
        {
        case 'f':
            g_pShmName = optarg;
            break;
        case 'd':
            g_pShmDirName = optarg;
            break;
        default:
            usage();
            return -1;
        }
    }
    if (g_pShmName == NULL)
    {
        fprintf(stderr, "Missing mandatory shmname.\n");
        usage();
        return -1;
    }
    return 0;
}


int main(int ac, char *av[])
{
    LsShm *pShm;
    LsShmPool *pGPool;
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

    doStatShm(pShm);

    doStatShmPool(pGPool);

    return 0;
}


void doStatShm(LsShm *pShm)
{
    LsShmMapStat *pStat = (LsShmMapStat *)pShm->getMapStat();

    fprintf(stdout, "SHM [%s] (in kbytes unless otherwise specified)\n\
shm filesize:               %u\n\
currently used:             %u\n\
available before expanding: %u\n",
            pShm->mapName(),
            pStat->m_iFileSize / 1024,
            pStat->m_iUsedSize / 1024,
            (pStat->m_iFileSize - pStat->m_iUsedSize) / 1024
           );
    return;
}


void doStatShmPool(LsShmPool *pPool)
{
    LsShmPoolMapStat *pStat =
        (LsShmPoolMapStat *)pPool->offset2ptr(pPool->getPoolMapStatOffset());

    fprintf(stdout, "GLOBAL POOL (in kbytes unless otherwise specified)\n\
global allocated pages:          %u\n\
global released pages:           %u\n\
global freelist (count):         %u\n\
allocated pages (>1K):           %u\n\
released pages  (>1K):           %u\n\
allocated from freelist (bytes): %u\n\
released to freelist (bytes):    %u\n\
freelist elements (count):       %u\n\
buckets (<256):  allocated         released             free(count)\n",
            pStat->m_iGpAllocated,
            pStat->m_iGpReleased,
            pStat->m_iGpFreeListCnt,
            pStat->m_iPgAllocated,
            pStat->m_iPgReleased,
            pStat->m_iFlAllocated,
            pStat->m_iFlReleased,
            pStat->m_iFlCnt
           );
    LsShmSize_t poolFree = pStat->m_iFlReleased - pStat->m_iFlAllocated
                           + pStat->m_iFreeChunk;
    LsShmSize_t bcktsz = 0;
    struct LsShmPoolMapStat::bcktstat *p = &pStat->m_bckt[0];
    int i;
    for (i = 0; i < LSSHM_POOL_NUMBUCKET;
         ++i, ++p, bcktsz += LSSHM_POOL_BCKTINCR)
    {
        int num;
        if ((p->m_iBkAllocated == 0) && (p->m_iBkReleased == 0))
            continue;
        fprintf(stdout, "%5d %20u %16u",
                bcktsz, p->m_iBkAllocated, p->m_iBkReleased);
        if ((num = (p->m_iBkReleased - p->m_iBkAllocated)) > 0)
        {
            fprintf(stdout, " %16u\n", num);
            poolFree += (num * bcktsz);
        }
        else
            fputc('\n', stdout);
    }
    fprintf(stdout, "\
current allocated pages used (kbytes): %u\n\
current total pool used (bytes): %u\n\
current total pool free (bytes): %u\n",
            pStat->m_iPgAllocated - pStat->m_iPgReleased,
            pStat->m_iPoolInUse,
            poolFree
           );
    return;
}

