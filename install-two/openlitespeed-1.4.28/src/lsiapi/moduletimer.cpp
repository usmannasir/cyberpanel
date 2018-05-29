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
#include "moduletimer.h"

#include <lsdef.h>
#include <util/datetime.h>

#include <time.h>

typedef struct timerkey_s
{
    int    id;
    time_t sec;
    time_t usec;
} timerkey_t;

class ModTimer
{
public:
    timerkey_t              m_key;
    lsi_timercb_pf   		m_timerCb;
    const void             *m_pTimerCbParam;
    unsigned int            m_repeat;
};


int timerCmp(const void *pKey1, const void *pKey2)
{
    timerkey_t *pExpire1 = (timerkey_t *)pKey1;
    timerkey_t *pExpire2 = (timerkey_t *)pKey2;
    if (pExpire1->sec < pExpire2->sec)
        return -1;
    else if (pExpire1->sec > pExpire2->sec)
        return 1;

    if (pExpire1->usec < pExpire2->usec)
        return -1;
    else if (pExpire1->usec > pExpire2->usec)
        return 1;

    if (pExpire1->id < pExpire2->id)
        return -1;
    else if (pExpire1->id > pExpire2->id)
        return 1;

    return 0;
}


void ModTimerList::timerCleanup(const void *notused)
{
    ModTimerList::getInstance().m_timerPool.shrinkTo(10);
}


ModTimerList::ModTimerList()
    : m_iTimerIds(1)
    , m_timerMap(timerCmp)
    , m_timerHash(10, NULL, NULL)
    , m_timerPool(10, 20)
{
    addTimer(10000, 1, ModTimerList::timerCleanup, NULL);
}


ModTimerList::~ModTimerList()
{}


int ModTimerList::addTimer(unsigned int msTimeout, int repeat,
                           lsi_timercb_pf timerCb,
                           const void *timerCbParam)
{
    ModTimer *pTimer = m_timerPool.get();
    pTimer->m_key.id = m_iTimerIds++;
    pTimer->m_key.sec = DateTime::s_curTime + msTimeout / 1000;
    pTimer->m_key.usec = DateTime::s_curTimeUs + 1000 * (msTimeout % 1000);
    pTimer->m_timerCb = timerCb;
    pTimer->m_pTimerCbParam = timerCbParam;
    if (repeat)
        pTimer->m_repeat = msTimeout;
    else
        pTimer->m_repeat = 0;

    if (m_timerMap.insert(&pTimer->m_key, pTimer) < 0)
    {
        delete pTimer;
        return LS_FAIL;
    }
    if (m_timerHash.insert((void *)(long)pTimer->m_key.id, pTimer) == NULL)
    {
        delete pTimer;
        return LS_FAIL;
    }
    return pTimer->m_key.id;
}


int ModTimerList::removeTimer(int iId)
{
    ModTimer *pTimer;
    GMap::iterator pMapIter;
    GHash::iterator pHashIter = m_timerHash.find((void *)(long)iId);
    if (pHashIter == NULL)
        return LS_FAIL;
    pTimer = (ModTimer *)pHashIter->getData();
    pMapIter = m_timerMap.find(&pTimer->m_key);
    if (pMapIter == NULL)
        return LS_FAIL;
    m_timerHash.erase(pHashIter);
    m_timerMap.deleteNode(pMapIter);
    m_timerPool.recycle(pTimer);
    return LS_OK;
}


int ModTimerList::checkExpired()
{
    int count = 0;
    ModTimer *pTimer;
    GHash::iterator pHashIter;
    GMap::iterator iter;
    while ((m_timerMap.size() > 0) && ((iter = m_timerMap.begin()) != NULL))
    {
        pTimer = (ModTimer *)iter->getValue();
        if ((pTimer->m_key.sec > DateTime::s_curTime)
            || ((pTimer->m_key.sec == DateTime::s_curTime)
                && (pTimer->m_key.usec > DateTime::s_curTimeUs)))
            return count;
        if (pTimer->m_repeat)
        {
            if (m_timerMap.detachNode(iter) != pTimer)
                return LS_FAIL;
            pTimer->m_timerCb(pTimer->m_pTimerCbParam);
            pTimer->m_key.sec = DateTime::s_curTime + pTimer->m_repeat / 1000;
            pTimer->m_key.usec = DateTime::s_curTimeUs + 1000
                                 * (pTimer->m_repeat % 1000);
            if (m_timerMap.attachNode(&pTimer->m_key, pTimer) != LS_OK)
                return LS_FAIL;
        }
        else
        {
            m_timerMap.deleteNode(iter);
            pTimer->m_timerCb(pTimer->m_pTimerCbParam);
            if ((pHashIter = m_timerHash.find((void *)(long)pTimer->m_key.id)) == NULL)
                return LS_FAIL;
            m_timerHash.erase(pHashIter);
            m_timerPool.recycle(pTimer);
        }
        ++count;
    }
    return count;
}


