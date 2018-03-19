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
#include "callbackqueue.h"
#include <log4cxx/logger.h>

void CallbackQueue::logState(const char *s, CallbackLinkedObj *p)
{
    if (p)
        LS_DBG_M("[CallbackQueue:%s] Obj=%p Session= %p Param=%p\n",
                 s, p, p->m_pSession, p->m_pParam);
    else
        LS_ERROR("[CallbackQueue:%s] Obj=NULL\n", s);
}

void CallbackQueue::run(CallbackLinkedObj *pFirstObj,
                        LsiSession *pSessionFilter)
{
    CallbackLinkedObj *pObj;
    CallbackLinkedObj *pObjNext;

    if (pFirstObj == NULL)
        pObj = (CallbackLinkedObj *)m_callbackObjList.begin();
    else
        pObj = pFirstObj;

    int count = m_callbackObjList.size();
    while (count > 0
           && pObj && pObj != (CallbackLinkedObj *)m_callbackObjList.end()
           && (!pSessionFilter || pObj->m_pSession == pSessionFilter))
    {
        pObjNext = (CallbackLinkedObj *)pObj->next();
        logState("run()", pObj);

        --count;

        m_callbackObjList.remove(pObj);

        assert(pObj->m_callback);
        if (pObj->m_callback)
            pObj->m_callback((lsi_session_t *)pObj->m_pSession, pObj->m_lParam,
                             pObj->m_pParam);
        else
            logState("run()][Error: NULL calback", pObj);

        /**
         * Comment: the above cb may release the data, so checking here to avoid
         * recycle again!
         */
        recycle(pObj);
        pObj = pObjNext;
    }
    assert((pFirstObj && pSessionFilter) || (count == 0));
}


CallbackLinkedObj *CallbackQueue::createObj(lsi_callback_queue_pf cb,
        LsiSession *session,
        long lParam,
        void *pParam)
{
    CallbackLinkedObj *pObj = m_callbackObjPool.get();
    if (pObj)
    {
        pObj->m_callback = cb;
        pObj->m_pSession = session;
        pObj->m_lParam = lParam;
        pObj->m_pParam = pParam;
    }
    logState("createObj()", pObj);
    return pObj;
}

CallbackLinkedObj *CallbackQueue::schedule(lsi_callback_queue_pf cb,
        LsiSession *session,
        long lParam,
        void *pParam)
{
    CallbackLinkedObj *pObj = createObj(cb, session, lParam, pParam);
    if (pObj)
        m_callbackObjList.append(pObj);
    return pObj;
}

CallbackLinkedObj *CallbackQueue::scheduleSessionCb(lsi_callback_queue_pf
        cb,
        LsiSession *pSession,
        long lParam, void *pParam,
        CBQSessionHeader &header)
{
    CallbackLinkedObj *pObj = createObj(cb, pSession, lParam, pParam);
    if (pObj)
    {
        if (header.get() == NULL)
        {
            header.set(pObj);
            m_callbackObjList.append(pObj);
        }
        else
        {
            m_callbackObjList.append(header.get(), pObj);
            logState("scheduleSessionCb()][Header EXIST", pObj);
        }
    }
    return pObj;
}


void CallbackQueue::removeObj(CallbackLinkedObj *pObj)
{
    if (!pObj)
        return;

    logState("removeObj()", pObj);
    if (pObj->next())
    {
        m_callbackObjList.remove(pObj);
        recycle(pObj);
    }
}

void CallbackQueue::removeSessionCb(LsiSession *pSession,
                                    CBQSessionHeader &header)
{
    CallbackLinkedObj *pObj = header.get();
    CallbackLinkedObj *pObjNext;

    logState("removeSessionCb()][header state", pObj);
    while (pObj && pObj != (CallbackLinkedObj *)m_callbackObjList.end())
    {
        pObjNext = (CallbackLinkedObj *)pObj->next();
        if (pObj->m_pSession == pSession)
            removeObj(pObj);
        else
            break;
        pObj = pObjNext;
    }
    header.set(NULL);
}

