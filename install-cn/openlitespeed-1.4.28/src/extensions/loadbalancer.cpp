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
#include "loadbalancer.h"
#include <extensions/extrequest.h>
#include <http/handlertype.h>


LoadBalancer::LoadBalancer(const char *pName)
    : ExtWorker(HandlerType::HT_LOADBALANCER)
    , m_lastWorker(0)
{
    setConfigPointer(new ExtWorkerConfig(pName));
}


LoadBalancer::~LoadBalancer()
{
}


ExtConn *LoadBalancer::newConn()
{
    return NULL;
}


int LoadBalancer::addWorker(ExtWorker *pWorker)
{
    return m_workers.push_back(pWorker);
}


int LoadBalancer::workerLoadCompare(ExtWorker *pWorker, ExtWorker *pSelect)
{
    if (pWorker->getState() == ExtWorker::ST_BAD)
        return 1;
    int ret = pWorker->getQueuedReqs() - pSelect->getQueuedReqs();
    if (ret)
        return ret;
    return pWorker->getUtilRatio() - pSelect->getUtilRatio();
}


ExtWorker *LoadBalancer::selectWorker(HttpSession *pSession,
                                      ExtRequest *pExtReq)
{
    ExtWorker *pWorker, *pSelected = NULL;
    int select = 0;
    int n = 0;
    int track = pExtReq->getWorkerTrack();
    while (n < m_workers.size())
    {
        if ((track & (1 << n)) == 0)
        {
            if (!pSelected)
            {
                pSelected = m_workers[n];
                select = n;
            }
            else
            {
                pWorker = m_workers[n];
                if (workerLoadCompare(pWorker, pSelected) < 0)
                {
                    pSelected = pWorker;
                    select = n;
                }
            }
        }
        ++n;
    }
    if (pSelected)
        pExtReq->addWorkerTrack(select);
    return pSelected;
}



