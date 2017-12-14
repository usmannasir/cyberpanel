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
#ifndef EVENTPROCESSOR_H
#define EVENTPROCESSOR_H
#include <eventnotifier.h>
#include <lsr/ls_lock.h>
#include <util/gpointerlist.h>


typedef int (*event_cb_t)(void *param);

struct EventData
{
    int         m_typeId;
    void       *m_pParam;
    event_cb_t  m_callback;
    EventData(int type, void *param, event_cb_t cb)
        : m_typeId(type)
        , m_pParam(param)
        , m_callback(cb)
    {}

};

class AutoLock
{
public:
    AutoLock(ls_spinlock_t *obj)
        : m_pLockObj(obj)
    {   ls_spinlock_lock(m_pLockObj);      }

    ~AutoLock()
    {   ls_spinlock_unlock(m_pLockObj);    }

private:
    ls_spinlock_t *m_pLockObj;
};

class EventQueue
{
public:
    EventQueue()
    {

    }

    ~EventQueue()
    {

    }

    int append(int type, void *pParam, event_cb_t cb)
    {
        EventData *pData = new EventData(type, pParam, cb);
        AutoLock lock(&m_mutex);
        m_data.push_back(pData);
        return LS_OK;
    }
    int get(EventData **pEvents, int len)
    {
        AutoLock lock(&m_mutex);
        return m_data.pop_front((void **)pEvents, len);
    }

private:
    ls_spinlock_t   m_mutex;
    TPointerList<EventData>  m_data;
};

class EventProcessor : public EventNotifier
{
public:
    EventProcessor();
    virtual ~EventProcessor();
    virtual int onNotified(int count);

private:
    EventProcessor(const EventProcessor &rhs);
    void operator=(const EventProcessor &rhs);

private:
    EventQueue   m_queue;

};

#endif // EVENTPROCESSOR_H
