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
#ifndef CALLBACKQUEUE_H
#define CALLBACKQUEUE_H

#include <lsdef.h>
#include <ls.h>
#include <util/dlinkqueue.h>
#include <util/objpool.h>
#include <util/tsingleton.h>

class LsiSession;

struct lsi_callback_linked_obj_s
{
};

struct CallbackLinkedObj : public lsi_callback_linked_obj_s,
    public DLinkedObj
{
    lsi_callback_queue_pf   m_callback;
    LsiSession     *m_pSession;
    long            m_lParam;
    void           *m_pParam;
};

class CBQSessionHeader
{
    CallbackLinkedObj *m_pObj;

public:
    CBQSessionHeader()      {   m_pObj = NULL;  }
    CallbackLinkedObj *get()         {   return m_pObj;  }
    void set(CallbackLinkedObj *v) {   m_pObj = v;     }
};


typedef ObjPool<CallbackLinkedObj> CallbackObjPool;

class CallbackQueue : public TSingleton<CallbackQueue>
{
    friend class TSingleton<CallbackQueue>;

    DLinkQueue  m_callbackObjList;
    inline void logState(const char *s, CallbackLinkedObj *p);

    CallbackLinkedObj *createObj(lsi_callback_queue_pf cb, LsiSession *session,
                                 long lParam, void *pParam);

public:
    CallbackObjPool m_callbackObjPool;
    CallbackQueue() {};
    ~CallbackQueue()
    {
        m_callbackObjPool.shrinkTo(0);
        m_callbackObjList.pop_all();
    }

    CallbackLinkedObj *schedule(lsi_callback_queue_pf cb, LsiSession *session,
                                long lParam, void *pParam);
    void removeObj(CallbackLinkedObj *pObj);
    void recycle(CallbackLinkedObj *pObj)
    {
        memset(pObj, 0, sizeof(CallbackLinkedObj));
        m_callbackObjPool.recycle(pObj);
    }


    void run(CallbackLinkedObj *pFirstObj, LsiSession *pSessionFilter);

    /**
     * Special function for session
     */
    CallbackLinkedObj *scheduleSessionCb(lsi_callback_queue_pf cb,
                                         LsiSession *session, long lParam,
                                         void *pParam, CBQSessionHeader &header);
    void removeSessionCb(LsiSession *pSession, CBQSessionHeader &header);

    LS_NO_COPY_ASSIGN(CallbackQueue);
};
#endif  //CALLBACKQUEUE_H
