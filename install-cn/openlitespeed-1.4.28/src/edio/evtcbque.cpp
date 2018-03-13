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
#include "evtcbque.h"
#include <log4cxx/logger.h>
#include <util/objpool.h>
#include <lsr/ls_lock.h>
#include <edio/multiplexer.h>
#include <edio/multiplexerfactory.h>



struct evtcbnode_s : public DLinkedObj
{
    evtcb_pf        m_callback;
    evtcbhead_t    *m_pSession;
    long            m_lParam;
    void           *m_pParam;
};


typedef ObjPool<evtcbnode_s> CallbackObjPool;
static CallbackObjPool *s_pCbnodePool;


EvtcbQue::EvtcbQue()
{
    s_pCbnodePool = new CallbackObjPool;
    m_pNotifier = new EvtcbQueNotifier;
    m_pNotifier->initNotifier(MultiplexerFactory::getMultiplexer());
    lock_add = 0;
}


EvtcbQue::~EvtcbQue()
{
    s_pCbnodePool->shrinkTo(0);
    delete s_pCbnodePool;
    delete m_pNotifier;
    m_callbackObjList.pop_all();
}


void EvtcbQue::logState(const char *s, evtcbnode_s *p)
{
    if (p)
        LS_DBG_M("[EvtcbQue:%s] Obj=%p Session= %p Param=%p\n",
                 s, p, p->m_pSession, p->m_pParam);
    else
        LS_ERROR("[EvtcbQue:%s] Obj=NULL\n", s);
}


/**
 * session is a filter. If NULL, run all in queue
 */
void EvtcbQue::run(evtcbhead_t *session)
{
    evtcbnode_s *pObj;
    evtcbnode_s *pObjNext;
    evtcbnode_s *pLast;
    int empty;

    ls_atomic_spin_lock(&lock_add);
    empty = m_callbackObjList.empty();
    ls_atomic_spin_unlock(&lock_add);
    if (empty)
        return ;

    assert(session != NULL);
    assert(session->evtcb_head);

    LS_DBG_M("[EvtcbQue:run(%p)]\n", session);

    ls_atomic_spin_lock(&lock_add);
    pObj = session->evtcb_head;
    session->evtcb_head = NULL;
    pLast = (evtcbnode_s *)(m_callbackObjList.end()->prev());
    ls_atomic_spin_unlock(&lock_add);

    while(pObj && pObj->m_pSession == session)
    {
        ls_atomic_spin_lock(&lock_add);
        pObjNext = (evtcbnode_s *)pObj->next();
        ls_atomic_spin_unlock(&lock_add);
        runOne(pObj);
        if (pObj == pLast)
            break;
        pObj = pObjNext;
    }
}


/**
 * session is a filter. If NULL, run all in queue
 */
void EvtcbQue::run()
{
    evtcbnode_s *pObj;
    evtcbnode_s *pObjNext;
    evtcbnode_s *pLast;
    int empty;
    
    ls_atomic_spin_lock(&lock_add);
    empty = m_callbackObjList.empty();
    if (!empty)
    {
        pObj = (evtcbnode_s *)m_callbackObjList.begin();
        pLast = (evtcbnode_s *)(m_callbackObjList.end()->prev());
    }
    ls_atomic_spin_unlock(&lock_add);
    
    if (empty)
    {
        //LS_DBG_M("run() queue is empty");
         return;
    }
    logState("run() starts", pObj);
    
    while (1)
    {
        ls_atomic_spin_lock(&lock_add);
        pObjNext = (evtcbnode_s *)pObj->next();
        if (pObj->m_pSession && pObj->m_pSession->evtcb_head == pObj)
            pObj->m_pSession->evtcb_head = NULL;
        ls_atomic_spin_unlock(&lock_add);
        runOne(pObj);
        if (pObj == pLast)
            break;
        pObj = pObjNext;
    }
}


void EvtcbQue::runOne(evtcbnode_s *pObj)
{
    logState("run()", pObj);

    ls_atomic_spin_lock(&lock_add);
    m_callbackObjList.remove(pObj);
    ls_atomic_spin_unlock(&lock_add);

    if (pObj->m_pSession 
        && pObj->m_pSession->back_ref_ptr == &pObj->m_pSession)
        pObj->m_pSession->back_ref_ptr = NULL;
    
    if (pObj->m_callback)
        pObj->m_callback(pObj->m_pSession, pObj->m_lParam, pObj->m_pParam);

    recycle(pObj);
}


evtcbnode_s * EvtcbQue::getNodeObj(evtcb_pf cb, const evtcbhead_t *session,
                                   long lParam, void *pParam)
{
    ls_atomic_spin_lock(&lock_add);
    evtcbnode_s *pObj = s_pCbnodePool->get();
    ls_atomic_spin_unlock(&lock_add);
    logState("getNodeObj", pObj);

    if (pObj)
    {
        pObj->m_callback = cb;
        pObj->m_pSession = (evtcbhead_t *) session; // violate LSIAPI const - internal code
        pObj->m_lParam = lParam;
        pObj->m_pParam = pParam;
    }
    return pObj;
}


void EvtcbQue::schedule(evtcbnode_s *pObj, bool nowait)
{
    evtcbhead_t *session = pObj->m_pSession;
    logState(nowait?"schedule() nowait" : "schedule()", pObj);
    ls_atomic_spin_lock(&lock_add);
    if (session)
    {
        //set_session_back_ref_ptr(session, &pObj->m_pSession);
        if (session->evtcb_head == NULL)
        {
            session->evtcb_head = pObj;
        }
        else
        {
            m_callbackObjList.insert_after(session->evtcb_head, pObj);
            ls_atomic_spin_unlock(&lock_add);

            logState("schedule()][Header EXIST", pObj);
            return;
        }
    }
    m_callbackObjList.append(pObj);
    ls_atomic_spin_unlock(&lock_add);
    
    if (nowait)
        m_pNotifier->notify();
}


evtcbnode_s *EvtcbQue::schedule(evtcb_pf cb, const evtcbhead_t *session,
                          long lParam, void *pParam)
{
    evtcbnode_s *pObj = getNodeObj(cb, session, lParam, pParam);
    if (pObj)
        schedule(pObj);
    
    return pObj;
}


void EvtcbQue::recycle(evtcbnode_s *pObj)
{
    logState("recycle()", pObj);
    memset(pObj, 0, sizeof(evtcbnode_s));
    s_pCbnodePool->recycle(pObj);
}


void EvtcbQue::removeSessionCb(evtcbhead_t *session)
{
    if (!session->evtcb_head)
        return ;
    

    evtcbnode_s *pObj;
    evtcbnode_s *pObjNext;

    ls_atomic_spin_lock(&lock_add);
    if (m_callbackObjList.size() != 0)
    {
        pObj = session->evtcb_head;
        while (pObj && pObj != (evtcbnode_s *)m_callbackObjList.end())
        {
            logState("removeSessionCb()][header state", pObj);
            pObjNext = (evtcbnode_s *)pObj->next();
            if (pObj->m_pSession == session)
            {
                pObj->m_pSession = NULL;
                pObj->m_callback = NULL;
            }
            else
                break;
            pObj = pObjNext;
        }
    }
    session->evtcb_head = NULL;
    ls_atomic_spin_unlock(&lock_add);
}

evtcbhead_t **EvtcbQue::getSessionRefPtr(evtcbnode_s *nodeObj)
{
    if (!nodeObj)
        return NULL;
    logState("getSessionRefPtr()", nodeObj);
    return &nodeObj->m_pSession;
}
