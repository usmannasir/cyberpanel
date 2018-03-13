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


FILE *debugBase::m_fp = NULL;
char *debugBase::m_outfile = NULL;

void debugBase::setup(const char *filename)
{
    if (m_fp)
        return;
    m_outfile = strdup(filename);
    m_fp = fopen(m_outfile, "w");
}

void debugBase::done()
{
    if (m_fp)
    {
        fclose(m_fp);
        m_fp = NULL;
    }
    if (m_outfile)
    {
        free(m_outfile);
        m_outfile = NULL;
    }
}

void debugBase::dumpFreeBlock(LsShm *pShm, LsShmOffset_t offset)
{
    LShmFreeTop *ap;
    LShmFreeBot *bp;

    ap = (LShmFreeTop *)pShm->offset2ptr(offset);
    bp = (LShmFreeBot *)pShm->offset2ptr(offset + ap->x_iFreeSize - sizeof(
            LShmFreeBot));

    fprintf(m_fp, "FLINK %s%8X %8X ->%8X %8X<- %s%s\n",
            (ap->x_iAMarker != LSSHM_FREE_AMARKER) ? "E" : "+",
            offset, ap->x_iFreeSize,
            ap->x_iFreeNext, ap->x_iFreePrev,
            (bp->x_iBMarker != LSSHM_FREE_BMARKER) ? "E" : "+",
            bp->x_iFreeOffset != offset ? "O" : " "
           );
}

void debugBase::dumpMapFreeList(LsShm *pShm)
{
    LsShmOffset_t offset;
    LShmFreeTop *ap;
    LsShmMap *hp;
    hp = pShm->x_pShmMap;

    for (offset = hp->x_iFreeOffset; offset;)
    {
        ap = (LShmFreeTop *)pShm->offset2ptr(offset);
        dumpFreeBlock(pShm, offset);
        offset = ap->x_iFreeNext;
    }
}

void debugBase::dumpMapCheckFree(LsShm *pShm)
{
    LShmFreeTop *ap;
    LShmFreeBot *bp;
    LsShmOffset_t offset;

    fprintf(m_fp, "FREE LINK\n");
    dumpMapFreeList(pShm);
    fprintf(m_fp, "FREE MAP\n");

    for (offset = pShm->getShmMap()->x_iXdataOffset +
                  pShm->getShmMap()->x_iXdataSize;
         offset < pShm->getShmMap()->x_iSize;
        )
    {
        ap = (LShmFreeTop *)pShm->offset2ptr(offset);
        if (ap->x_iAMarker == LSSHM_FREE_AMARKER)
        {
            bp = (LShmFreeBot *)pShm->offset2ptr(offset + ap->x_iFreeSize - sizeof(
                    LShmFreeBot));
            if (bp->x_iBMarker == LSSHM_FREE_BMARKER)
            {
                dumpFreeBlock(pShm, offset);
                offset += ap->x_iFreeSize;
                continue;
            }
        }
        offset += pShm->getShmMap()->x_iUnitSize;
    }
}

void debugBase::dumpMapHeader(LsShm *pShm)
{
    LsShmMap *hp;
    hp = pShm->x_pShmMap;
    fprintf(m_fp,
            "%.12s %X %d.%d.%d CUR %8X %8X DATA %8X AVAIL %X UNIT %X FREE %X\n",
            hp->x_aName,
            hp->x_iMagic,
            (int)hp->x_version.x.m_iMajor,
            (int)hp->x_version.x.m_iMinor,
            (int)hp->x_version.x.m_iRel,
            hp->x_iSize,
            hp->x_iMaxSize,
            hp->x_iXdataOffset,
            hp->x_iXdataSize,
            hp->x_iUnitSize,
            hp->x_iFreeOffset
           );
    fprintf(m_fp,
            "REG NUMPERPAGE %X SIZE %d E%d H%d R%d  OFFSET %X %X MAX %d\n",
            hp->x_iRegPerBlk,

            (int)sizeof(LsShmRegBlkHdr),
            (int)sizeof(LsShmReg),
            (int)sizeof(LsShmRegElem),
            (int)sizeof(LsShmRegBlk),

            hp->x_iRegBlkOffset,
            hp->x_iRegLastBlkOffset,
            hp->x_iMaxRegNum
           );
}

void debugBase::dumpHeader(LsShm *pShm)
{
    fprintf(m_fp, "%d %s %p %p MAXSIZE[%X] %p hdrsize %X\n",
            pShm->m_status,
            pShm->m_pFileName,
            pShm->x_pShmMap,
            pShm->m_pShmMapO,
            pShm->m_iMaxSizeO,
            pShm->m_pShmData,
            (unsigned int)((char *)pShm->m_pShmData - (char *)pShm->x_pShmMap)
           );
}

void debugBase::dumpShm(LsShmPool *pool, int mode, void *udata)
{
    LsShm *pShm;
    pShm = pool->m_pShm;
    fprintf(m_fp, ">>>>>>>>>>>>>>>>START SHARE-MEMORY-MAP-DUMP\n");
    dumpHeader(pShm);
    dumpMapHeader(pShm);
    dumpMapCheckFree(pShm);
    fprintf(m_fp, "END <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n\n");
    fflush(m_fp);
}

//
//  print status
//
int debugBase::checkStatus(const char *tag, const char *mapName,
                           LsShmStatus_t status)
{
    switch (status)
    {
    case LSSHM_READY:
        HttpLog::log(LSI_LOG_NOTICE,  "%s %s READY\r\n",
                     tag, mapName);
        return 0;

    case LSSHM_NOTREADY:
        HttpLog::log(LSI_LOG_NOTICE,  "%s %s NOTREADY\r\n",
                     tag, mapName);
        break;
    case LSSHM_BADMAPFILE:
        HttpLog::log(LSI_LOG_NOTICE,  "%s %s BADMAPFILE\r\n",
                     tag, mapName);
        break;
    case LSSHM_BADPARAM:
        HttpLog::log(LSI_LOG_NOTICE,  "%s %s BADPARAM\r\n",
                     tag, mapName);
        break;
    case LSSHM_BADVERSION:
        HttpLog::log(LSI_LOG_NOTICE,  "%s %s BADVERSION\r\n",
                     tag, mapName);
        break;
    default:
        HttpLog::log(LSI_LOG_NOTICE,  "%s %s UNKNOWN %d\r\n",
                     tag, mapName, status);
        break;
    }
    return LS_FAIL;
}

void debugBase::dumpPoolPage(LsShmPool *pool)
{
    ;
}

void debugBase::dumpPoolDataFreeList(LsShmPool *pool)
{
    LsShmOffset_t offset;
    LsShmFreeList *pFree;

    fprintf(debugBase::fp(), "FreeList %8X ",
            pool->x_pDataMap->x_iFreeList);
    for (offset = pool->x_pDataMap->x_iFreeList; offset;)
    {
        pFree = (LsShmFreeList *) pool->offset2ptr(offset);
        fprintf(debugBase::fp(), "<%4X %4X %4X>",
                pFree->x_iPrev, pFree->x_iSize, pFree->x_iNext);
        offset = pFree->x_iNext;
    }
    fprintf(debugBase::fp(), "\n");
}

void debugBase::dumpPoolDataFreeBucket(LsShmPool *pool)
{
    LsShmOffset_t offset;
    LsShmOffset_t *pBucket;
    int i;
    pBucket = pool->x_pDataMap->x_aFreeBucket;
    for (i = 0; i < LSSHM_POOL_NUMBUCKET; i++)
    {
        if ((offset = *pBucket))
        {
            fprintf(debugBase::fp(), "Bucket[%2d]->%X", i, offset);
            int num = 0;
            while ((num < 8) && offset)
            {
                LsShmOffset_t *xp;
                xp = (LsShmOffset_t *) pool->offset2ptr(offset);
                offset = *xp;
                fprintf(debugBase::fp(), " %X", offset);
                num++;
            }
            fprintf(debugBase::fp(), "\n");
        }
        pBucket++;
    }
}

void debugBase::dumpPoolDataCheck(LsShmPool *pool)
{
    ;
}

void debugBase::dumpPoolData(LsShmPool *pool)
{
    ;
}

void debugBase::dumpPoolHeader(LsShmPool *pool)
{
    fprintf(debugBase::fp(),
            "=====================================================\n");
    fprintf(debugBase::fp(), "LsShmPool %p %.12s %s %p %p [%p %p]\n",
            pool, pool->name(),
            (pool->status() == LSSHM_READY) ? "READY" : "NOTREADY",
            pool->m_pShm,
            pool->x_pPool,
            pool->x_pPageMap,
            pool->x_pDataMap
           );

    fprintf(debugBase::fp(), "MAGIC %8X SIZE %8X AVAIL %8X FREE %8X\n",
            pool->x_pPool->x_iMagic,
            pool->x_pPool->x_iSize,
            pool->m_pShm->getShmMap()->x_iXdataSize,
            pool->m_pShm->getShmMap()->x_iXdataSize - pool->x_pPool->x_iSize
           );

    fprintf(debugBase::fp(),
            "DATA UNIT [%X %X] NUMBUCKET %X CHUNK [%X %X] FREE %X\n",
            pool->x_pDataMap->x_iUnitSize,
            pool->x_pDataMap->x_iMaxUnitSize,
            pool->x_pDataMap->x_iNumFreeBucket,
            pool->x_pDataMap->x_chunk.x_iStart,
            pool->x_pDataMap->x_chunk.x_iEnd,
            pool->x_pDataMap->x_iFreeList
           );
    fprintf(debugBase::fp(),
            "=====================================================\n");
}

void debugBase::dumpShmPool(LsShmPool *pool, int mode, void *udata)
{
    dumpPoolHeader(pool);
    dumpPoolData(pool);
    dumpPoolDataFreeList(pool);
    dumpPoolDataFreeBucket(pool);
}

void debugBase::dumpRegistry(const char *tag, const LsShmReg *p_reg)
{
    fprintf(debugBase::fp(),
            "%s REGISTRY[%d] %.12s %X [%d]\n",
            tag ? tag : "",
            p_reg->x_iRegNum,
            p_reg->x_aName,
            p_reg->x_iValue,
            (int)p_reg->x_iFlag);
}

void debugBase::dumpShmReg(LsShm *pShm)
{
    LsShmOffset_t offset;
    LsShmRegBlkHdr *p_regHdr;
    int    regId, i;
    LsShmRegElem *p_reg;
    char tag[0x100];

    regId = 0;
    offset = pShm->getShmMap()->x_iRegBlkOffset;
    while (offset)
    {
        p_reg = (LsShmRegElem *) pShm->offset2ptr(offset);
        p_regHdr = (LsShmRegBlkHdr *)p_reg;
        int maxNum = p_regHdr->x_iStartNum + p_regHdr->x_iCapacity;


        fprintf(debugBase::fp(), "%4X REG_BLK[%d] %d %d %d -> %X\n",
                pShm->ptr2offset(p_regHdr),
                regId,
                p_regHdr->x_iStartNum,
                p_regHdr->x_iSize,
                p_regHdr->x_iCapacity,
                p_regHdr->x_iNext);
        // regId++;
        p_reg++;
        for (i = p_regHdr->x_iStartNum + 1; i < maxNum; i++)
        {
            if (p_reg->x_reg.x_aName[0])
            {
                snprintf(tag, sizeof(tag), "%4d", regId);
                debugBase:: dumpRegistry(tag, (LsShmReg *)p_reg);
            }
            regId++;
            p_reg++;
        }
        offset = p_regHdr->x_iNext;
    }
}

// simple test decode... dont make this big!
const char *debugBase::decode(const char *p, int size)
{
    char            sbuf[0x21];
    static char     buf[0x100];
    char   *cp, *sp;
    int    nb;

    sp = sbuf;
    cp = buf;
    nb = sprintf(cp, "%p ", buf);
    cp += nb;
    if (size > 0x20)
        size = 0x20;
    while (--size >= 0)
    {
        nb = sprintf(cp, "%02X ", ((unsigned int) * buf) & 0xff) ;
        if ((*p < ' ') || (*p >= 0x7f))
            *sp++ = '.' ;
        else
            *sp++ = *buf;
        p++;
        cp += nb;
    }
    *sp = 0;
    *cp++ = ' ';
    strcpy(cp, sbuf);
    return (buf);
}

void debugBase::dumpBuf(const char *tag, const char *buf, int size)
{
    int    i;
    char            sbuf[0x20];

    while (size)
    {
        if (tag)
            fprintf(fp(), "%-8.8s ", tag);
        fprintf(fp(), "%p ", buf);
        for (i = 0; (i < 0x10) && size; i++, size--, buf++)
        {
            fprintf(fp(), "%02X ", ((unsigned int)*buf) & 0xff) ;
            if ((*buf < ' ') || (*buf >= 0x7f))
                sbuf[i] = '.' ;
            else
                sbuf[i] = *buf;
        }
        sbuf[i--] = '\0' ;
        while (i++ < 0x10)
            fprintf(fp(), "   ") ;
        fprintf(fp(), "\t%s\n", sbuf) ;
    }
}

void debugBase::dumpIterKey(LsShmHash::iterator iter)
{
    fprintf(fp(), "KEY[%s]", decode((char *)iter->getKey(),
                                    iter->getKeyLen()));
}

void debugBase::dumpIterValue(LsShmHash::iterator iter)
{
    fprintf(fp(), "VAL[%s]", decode((char *)iter->getVal(),
                                    iter->getValLen()));
}

void debugBase::dumpIter(const char *tag, LsShmHash::iterator iter)
{
    if (tag)
        fprintf(fp(), "%8.8s", tag);
    dumpIterKey(iter);
    dumpIterValue(iter);
}

