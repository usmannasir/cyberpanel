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

#include <lsr/ls_evtcb.h>
#include <util/dlinkqueue.h>
#include <util/tsingleton.h>
#include <edio/eventnotifier.h>


struct evtcbnode_s;

class EvtcbQueNotifier : public EventNotifier
{
public:
    virtual int onNotified(int count){return 0;};
};

class EvtcbQue : public TSingleton<EvtcbQue>
{
    friend class TSingleton<EvtcbQue>;

    EvtcbQue();
    ~EvtcbQue();

    DLinkQueue  m_callbackObjList;

    static void logState(const char *s, evtcbnode_s *p);
    void runOne(evtcbnode_s *pObj);

public:
    void run(evtcbhead_t *session);
    void run();
    void recycle(evtcbnode_s *pObj);

    evtcbnode_s * getNodeObj(evtcb_pf cb, const evtcbhead_t *session,
                             long lParam, void *pParam);
    
    void schedule(evtcbnode_s *pObj, bool nowait = true);
    evtcbnode_s *schedule(evtcb_pf cb, const evtcbhead_t *session,
                          long lParam, void *pParam);
    void removeSessionCb(evtcbhead_t *session);

    static evtcbhead_t **getSessionRefPtr(evtcbnode_s *nodeObj);

    LS_NO_COPY_ASSIGN(EvtcbQue);
    
private:
    int lock_add;
    EvtcbQueNotifier *m_pNotifier;
};
#endif  //CALLBACKQUEUE_H
