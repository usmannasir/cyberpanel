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
#ifndef LSSHMTIDMGR_H
#define LSSHMTIDMGR_H

#include <lsdef.h>
#include <shm/lsshmhash.h>

#include <assert.h>

#define TIDTBLBLK_MAXSZ     1024

#define TIDDEL_MAGIC_NUMBER  0x8000000000000000ull


#define TIDDEL_RANGEFLAG    TIDDEL_MAGIC_NUMBER  // this entry specfifies a range
#define TIDDEL_FLUSHALL     ((uint64_t)-1&~TIDDEL_RANGEFLAG)    // special flush

#define TIDLST_DELETE       TIDDEL_MAGIC_NUMBER  // deleted tid

typedef struct
{
    uint64_t        x_tid;
    uint64_t        x_lastTidPreClear;
    LsShmOffset_t   x_iTidTblStrtOff;
    LsShmOffset_t   x_iTidTblCurOff;
    uint64_t        x_tidLastNoti;
    LsShmOffset_t   x_iBlkLastNoti;
    LsShmOffset_t   x_iBlkIdxOff;
    uint64_t        x_iBlkCnt;
    LsShmOffset_t   x_iLockOff;
} LsShmTidInfo;

typedef struct
{
    uint64_t        x_tidBase;
    int16_t         x_iIterCnt;
    int16_t         x_iDelCnt;
    LsShmOffset_t   x_iNext;
    LsShmOffset_t   x_iPrev;
    uint64_t        x_iTidVals[TIDTBLBLK_MAXSZ];
} LsShmTidTblBlk;

class LsShmTidMgr
{
public:
    LsShmTidMgr(LsShmOffset_t iIterOffset)
        : m_pHash(NULL)
        , m_iOffset(0)
        , m_iIterOffset(iIterOffset)
        {}
    ~LsShmTidMgr() {}
    int  init(LsShmHash *pHash, LsShmOffset_t off, bool blkinit);
    void clrTidTbl();
    LsShmOffset_t growTidTbl(uint64_t base, int &remapped);
    int checkTidTbl();

    void linkTid(LsShmHIterOff offElem, uint64_t *pTid);
    void unlinkTid(uint64_t tid);
    void tidReplaceTid(LsShmHElem *pElem, LsShmHIterOff offElem, uint64_t *pTid);

    LsShmHIterOff doSet(const void *pKey, int iKeyLen, const void *pVal,
                        int iValLen);
    LsShmOffset_t setIter(const void *pKey, int iKeyLen, const void *pVal,
                          int iValLen, uint64_t *pTid);
    void delIter(LsShmHIterOff off);

    void insertIterCb(LsShmHIterOff off);
    void eraseIterCb(LsShmHElem *pElem);
    void updateIterCb(LsShmHElem *pElem, LsShmHIterOff off);
    void clearCb();

    int  setTidTblDel(uint64_t tid, uint64_t *pTid)
    {   return setTidTblEnt(tid, pTid);  }

    uint64_t       *nxtTidTblVal(uint64_t *pTid, void **ppBlk);

    bool isTidValIterOff(uint64_t tidVal)
    {   return ((tidVal & TIDDEL_MAGIC_NUMBER) != 0);   }

    uint64_t        iterOff2tidVal(LsShmHIterOff iterOff)
    {   return (iterOff.m_iOffset | TIDDEL_MAGIC_NUMBER);   }

    LsShmOffset_t   tidVal2iterOff(uint64_t tidVal)
    {   return (tidVal & ~TIDDEL_MAGIC_NUMBER);   }

    LsShmHIterOff   tid2iterOff(uint64_t tid, LsShmTidTblBlk **ppBlk)
    {
        LsShmHIterOff off = {0};
        LsShmTidTblBlk *pBlk;
        if ((pBlk = tid2tblBlk(tid)) == NULL)
            return off;
        *ppBlk = pBlk;
        uint64_t tidVal = pBlk->x_iTidVals[tid % TIDTBLBLK_MAXSZ];
        off.m_iOffset = (isTidValIterOff(tidVal) ? tidVal2iterOff(tidVal) : 0);
        return off;
    }

    uint64_t getLastTid() const
    {   return getTidInfo()->x_tid;   }

private:
    LsShmTidMgr(const LsShmTidMgr &other);
    LsShmTidMgr &operator=(const LsShmTidMgr &other);

    ls_attr_inline LsShmTidInfo *getTidInfo() const
    {   return (LsShmTidInfo *)m_pHash->offset2ptr(m_iOffset);   }

    void clrTidTblEnt(uint64_t tid);
    int  setTidTblEnt(uint64_t tidVal, uint64_t *pTid);

    int  setTidTblIter(LsShmHIterOff iterOff, uint64_t *pTid)
    {   return setTidTblEnt(iterOff2tidVal(iterOff), pTid);  }

    LsShmTidTblBlk  *tid2tblBlk(uint64_t tid);

    uint64_t        *nxtValInBlk(LsShmTidTblBlk *pBlk, int *pIndx);
    
    LsShmOffset_t    allocBlkIdx(LsShmOffset_t oldIdx, LsShmSize_t curSize, int &remapped);

    LsShmHash       *m_pHash;
    LsShmOffset_t    m_iOffset;
    LsShmOffset_t    m_iIterOffset;
};

#endif // LSSHMTIDMGR_H

