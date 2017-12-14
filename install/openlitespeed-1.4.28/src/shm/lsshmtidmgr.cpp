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
#include <shm/lsshmtidmgr.h>


#define LSSHMTID_BLKIDX_INCR    0x100
#define LSSHMTID_BLKIDX_CMP     (LSSHMTID_BLKIDX_INCR - 1)
#define LSSHMTID_BLKIDX_SIZE(x) (x * sizeof(LsShmOffset_t))

typedef struct
{
    uint64_t             x_tid;           // `transaction' id
} LsShmTidLink;

int LsShmTidMgr::init(LsShmHash *pHash, LsShmOffset_t off, bool blkinit)
{
    LsShmTidInfo *pTidInfo;
    m_pHash = pHash;
    m_iOffset = off;
    if (blkinit)
    {
        pTidInfo = getTidInfo();
        ::memset((void *)pTidInfo, 0, sizeof(*pTidInfo));
    }
    return 0;
}


void LsShmTidMgr::clrTidTbl()
{
    LsShmTidInfo *pTidInfo = getTidInfo();
    LsShmOffset_t off = pTidInfo->x_iTidTblCurOff;
    if (off != 0)
    {
        // Blocks are allocated in LSSHMTID_BLKIDX_INCR increments.
        // &~ takes away any lower bits.  If round is less, need to increment.
        LsShmSize_t roundSize = pTidInfo->x_iBlkCnt & ~LSSHMTID_BLKIDX_CMP;
        if (roundSize < pTidInfo->x_iBlkCnt)
            roundSize += LSSHMTID_BLKIDX_INCR;
        m_pHash->release2(pTidInfo->x_iBlkIdxOff,
                          LSSHMTID_BLKIDX_SIZE(roundSize));
    }
    while (off != 0)
    {
        LsShmOffset_t prev;
        prev = ((LsShmTidTblBlk *)m_pHash->offset2ptr(off))->x_iPrev;
        m_pHash->release2(off, (LsShmSize_t)sizeof(LsShmTidTblBlk));
        off = prev;
    }
    pTidInfo->x_iTidTblStrtOff = 0;
    pTidInfo->x_iTidTblCurOff = 0;
    pTidInfo->x_iBlkLastNoti = 0;
    pTidInfo->x_iBlkIdxOff = 0;
    pTidInfo->x_iBlkCnt = 0;
    pTidInfo->x_lastTidPreClear = pTidInfo->x_tid;
    if (m_pHash->isTidMaster())
    {
        // load flush_all notification
        uint64_t tid = 0;
        setTidTblEnt((uint64_t)TIDDEL_FLUSHALL, &tid);
//         LS_DBG_M(m_pHash->getLogger(), "clrTidTbl FLUSHALL: tid=%lld\n", tid);
    }
    return;
}


void LsShmTidMgr::linkTid(LsShmHIterOff offElem, uint64_t *pTid)
{
    LsShmTidLink *pLink;
    uint64_t tid;
    LsShmHElem *pLinkElem;
    if (pTid == NULL)
    {
        tid = 0;
        pTid = &tid;
    }
    setTidTblIter(offElem, pTid);    // careful, may remap
    pLinkElem = m_pHash->offset2iterator(offElem);
    pLink = (LsShmTidLink *)pLinkElem->getExtraPtr(m_iIterOffset);
    pLink->x_tid = *pTid;
}


void LsShmTidMgr::unlinkTid(uint64_t tid)
{
    clrTidTblEnt(tid);
    // new delete tid only processed here in master;
    // slave updates tid table when processing transactions with specified tids.
    if (m_pHash->isTidMaster())
    {
        uint64_t tidNew = 0;
        setTidTblDel(tid, &tidNew);  // careful, may remap
    }
}


void LsShmTidMgr::tidReplaceTid(LsShmHElem *pElem, LsShmHIterOff offElem, uint64_t *pTid)
{
    LsShmTidLink *pLink = (LsShmTidLink *)pElem->getExtraPtr(m_iIterOffset);
    unlinkTid(pLink->x_tid);
    linkTid(offElem, pTid);
}


LsShmHIterOff LsShmTidMgr::doSet(const void* pKey, int iKeyLen,
                                 const void* pVal, int iValLen)
{
    ls_strpair_t parms;
    LsShmHIterOff offElem;
    LsShmHKey hkey;
    LsShmTidLink *pLink;
    m_pHash->setParms(&parms, pKey, iKeyLen, pVal, iValLen);
    offElem = m_pHash->findIterator(&parms);
    if (offElem.m_iOffset != 0)
    {
        LsShmHElem *pElem = m_pHash->offset2iterator(offElem);
        if (iValLen < pElem->getValLen())
        {
            if (pVal != NULL)
                memmove(pElem->getVal(), pVal, iValLen);
            pElem->setValLen(iValLen);
            pLink = (LsShmTidLink *)pElem->getExtraPtr(m_iIterOffset);
            unlinkTid(pLink->x_tid);
            return offElem;
        }
        else
            m_pHash->eraseIterator(offElem);
    }
    hkey = (*m_pHash->getHashFn())(pKey, iKeyLen);
    return m_pHash->insertCopy(hkey, &parms);
}


LsShmOffset_t LsShmTidMgr::setIter(const void* pKey, int iKeyLen,
                                const void* pVal, int iValLen, uint64_t* pTid)
{
    LsShmHIterOff offElem;

    offElem = doSet(pKey, iKeyLen, pVal, iValLen);
    if (offElem.m_iOffset != 0)
    {
        linkTid(offElem, pTid);
        return LS_OK;
    }
    return LS_FAIL;
}


void LsShmTidMgr::delIter(LsShmHIterOff off)
{
    m_pHash->eraseIterator(off);
}


void LsShmTidMgr::insertIterCb(LsShmHIterOff off)
{
    linkTid(off, NULL);
}


void LsShmTidMgr::eraseIterCb(LsShmHElem* pElem)
{
    uint64_t tid;
    LsShmTidLink *pLink = (LsShmTidLink *)pElem->getExtraPtr(m_iIterOffset);
    if ((tid = pLink->x_tid) != 0)
    {
        pLink->x_tid = 0;
        unlinkTid(tid);
    }
}


void LsShmTidMgr::updateIterCb(LsShmHElem* pElem, LsShmHIterOff off)
{
    eraseIterCb(pElem);
    linkTid(off, NULL);
}


void LsShmTidMgr::clearCb()
{
    clrTidTbl();
}


LsShmOffset_t LsShmTidMgr::allocBlkIdx(LsShmOffset_t oldIdx, LsShmSize_t oldCnt,
                                       int &remapped)
{
    LsShmOffset_t off, *pOld, *pNew;
    LsShmSize_t newCnt = oldCnt + LSSHMTID_BLKIDX_INCR;
    if ((off = m_pHash->alloc2(LSSHMTID_BLKIDX_SIZE(newCnt), remapped)) == 0)
        return 0;
    if (oldIdx == 0)
        return off;
    pOld = (LsShmOffset_t *)m_pHash->offset2ptr(oldIdx);
    pNew = (LsShmOffset_t *)m_pHash->offset2ptr(off);
    memmove(pNew, pOld, LSSHMTID_BLKIDX_SIZE(oldCnt));
    m_pHash->release2(oldIdx, LSSHMTID_BLKIDX_SIZE(oldCnt));
    return off;
}


LsShmOffset_t LsShmTidMgr::growTidTbl(uint64_t base, int &remapped)
{
    LsShmTidInfo *pTidInfo;
    LsShmTidTblBlk *pBlk = NULL;
    LsShmOffset_t blkOff, idxOff, *pBlkIdx;
    int iRemap;
    if ((blkOff = m_pHash->alloc2(sizeof(LsShmTidTblBlk), remapped)) == 0)
        return 0;
    pTidInfo = getTidInfo();
    // Increment blk index by LSSHMTID_BLKIDX_INCR (currently 0x100).
    // If count bitwise and LSSHMTID_BLKIDX_CMP (currently 0xff) is 0, 
    // that means I need to allocate more space.
    if ((pTidInfo->x_iBlkCnt & LSSHMTID_BLKIDX_CMP) == 0)
    {
        if ((idxOff = allocBlkIdx(pTidInfo->x_iBlkIdxOff, pTidInfo->x_iBlkCnt,
                                  iRemap)) == 0)
        {
            m_pHash->release2(blkOff, sizeof(LsShmTidTblBlk));
            return 0;
        }
        if (iRemap != 0)
        {
            remapped = iRemap;
            pTidInfo = getTidInfo();
        }
        pTidInfo->x_iBlkIdxOff = idxOff;
    }
    if (pTidInfo->x_iTidTblCurOff != 0)
        pBlk = (LsShmTidTblBlk *)m_pHash->offset2ptr(pTidInfo->x_iTidTblCurOff);
    if (pBlk == NULL)
        pTidInfo->x_iTidTblStrtOff = blkOff;
    else
        pBlk->x_iNext = blkOff;
    pBlkIdx = (LsShmOffset_t *)m_pHash->offset2ptr(pTidInfo->x_iBlkIdxOff);
    pBlkIdx[pTidInfo->x_iBlkCnt++] = blkOff;
    pBlk = (LsShmTidTblBlk *)m_pHash->offset2ptr(blkOff);
    pBlk->x_tidBase = base;
    pBlk->x_iIterCnt = 0;
    pBlk->x_iDelCnt = 0;
    pBlk->x_iNext = 0;
    pBlk->x_iPrev = pTidInfo->x_iTidTblCurOff;
    ::memset((void *)pBlk->x_iTidVals, 0, sizeof(pBlk->x_iTidVals));
    pTidInfo->x_iTidTblCurOff = blkOff;
    return blkOff;
}


int LsShmTidMgr::checkTidTbl()
{
    int remapped = 0;
    LsShmTidInfo *pTidInfo = getTidInfo();
    uint64_t tid = pTidInfo->x_tid + 1;
    LsShmTidTblBlk *pBlk =
        (LsShmTidTblBlk *)m_pHash->offset2ptr(pTidInfo->x_iTidTblCurOff);
    if ((pBlk == NULL) || (tid >= (pBlk->x_tidBase + TIDTBLBLK_MAXSZ)))
        growTidTbl(tid - (tid % TIDTBLBLK_MAXSZ), remapped);
    return remapped;
}


int LsShmTidMgr::setTidTblEnt(uint64_t tidVal, uint64_t *pTid)
{
    int indx;
    LsShmTidInfo *pTidInfo = getTidInfo();
    if (*pTid == 0)
        *pTid = ++(pTidInfo->x_tid);
    else if (*pTid > pTidInfo->x_tid)
        pTidInfo->x_tid = *pTid;
    else
        return -1;

    LsShmTidTblBlk *pBlk =
        (LsShmTidTblBlk *)m_pHash->offset2ptr(pTidInfo->x_iTidTblCurOff);
    indx = (*pTid % TIDTBLBLK_MAXSZ);
    if ((pBlk == NULL) || (*pTid >= (pBlk->x_tidBase + TIDTBLBLK_MAXSZ)))
    {
        int remapped;
        LsShmOffset_t blkOff = growTidTbl(*pTid - indx, remapped);
        if (blkOff == 0)
            return -1;
        pBlk = (LsShmTidTblBlk *)m_pHash->offset2ptr(blkOff);
    }
    if (isTidValIterOff(tidVal))
        ++pBlk->x_iIterCnt;
    else
    {
        ++pBlk->x_iDelCnt;
    }
    pBlk->x_iTidVals[indx] = tidVal;
    return 0;
}


void LsShmTidMgr::clrTidTblEnt(uint64_t tid)
{
    LsShmTidTblBlk *pBlk;
    if ((pBlk = tid2tblBlk(tid)) != NULL)
    {
        pBlk->x_iTidVals[tid % TIDTBLBLK_MAXSZ] = 0;
        --pBlk->x_iIterCnt;
    }
    return;
}


LsShmTidTblBlk *LsShmTidMgr::tid2tblBlk(uint64_t tid)
{
    LsShmOffset_t *pBlkOff;
    LsShmTidInfo *pTidInfo = getTidInfo();
    if (tid < pTidInfo->x_lastTidPreClear)
        tid = pTidInfo->x_lastTidPreClear;
    uint64_t iBlkIdx = (tid >> 10) - (pTidInfo->x_lastTidPreClear >> 10);
    if ((pTidInfo->x_iBlkIdxOff == 0) || (iBlkIdx >= pTidInfo->x_iBlkCnt))
        return NULL;
    pBlkOff = (LsShmOffset_t *)m_pHash->offset2ptr(pTidInfo->x_iBlkIdxOff);
    return (LsShmTidTblBlk *)m_pHash->offset2ptr(pBlkOff[iBlkIdx]);
}


uint64_t *LsShmTidMgr::nxtTidTblVal(uint64_t *pTid, void **ppBlk)
{
    uint64_t *pVal;
    int indx;
    LsShmOffset_t off;
    LsShmTidTblBlk *pBlk;
    if ((pBlk = (LsShmTidTblBlk *)*ppBlk) == NULL)
        pBlk = tid2tblBlk(*pTid);
    if (pBlk == NULL)
        return NULL;
    while (1)
    {
        if (*pTid < (pBlk->x_tidBase + TIDTBLBLK_MAXSZ))
        {
            indx = ((*pTid >= pBlk->x_tidBase) ?
                (*pTid % TIDTBLBLK_MAXSZ) + 1 : 0);
            if ((pVal = nxtValInBlk(pBlk, &indx)) != NULL)
                break;
        }
        if ((off = pBlk->x_iNext) == 0)
            return NULL;
        pBlk = (LsShmTidTblBlk *)m_pHash->offset2ptr(off);
    }
    *pTid = pBlk->x_tidBase + indx;
    *ppBlk = (void *)pBlk;
    return pVal;
}


uint64_t *LsShmTidMgr::nxtValInBlk(LsShmTidTblBlk *pBlk, int *pIndx)
{
    int indx = *pIndx;
    uint64_t *pVal = &pBlk->x_iTidVals[indx];
    while (indx < TIDTBLBLK_MAXSZ)
    {
        if (*pVal != 0)
        {
            *pIndx = indx;
            return pVal;
        }
        ++pVal;
        ++indx;
    }
    return NULL;
}

