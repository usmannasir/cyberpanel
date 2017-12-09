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
#ifndef POLLFDREACTOR_H
#define POLLFDREACTOR_H
#include <lsdef.h>
#include <edio/eventreactor.h>

//#include <assert.h>



#include <assert.h>
#include <stddef.h>

class PollfdReactor
{
    // Resizable array of pollfd to pass to poll().  may contain fd = -1.
    // Should not contain duplicate fd's.
    struct pollfd *m_pfds;

    // Resizable array of ptrs to event handlers,
    // indexed by same index as m_pfds.  May contain duplicates.
    EventReactor **m_pReactors;

    struct pollfd *m_pEnd;

    // number of elements allocated in m_pfds[]
    struct pollfd *m_pStoreEnd;

    struct pollfd *m_pCur;
    int m_iEvents;
    int m_iFirstRecycled;
    EventReactor::pri_handler m_priHandler;

    struct pollfd *getAvail()
    {
        struct pollfd *pAdd;
        while (m_iFirstRecycled != 65535)
        {
            pAdd = m_pfds + m_iFirstRecycled;
            m_iFirstRecycled = (unsigned short)pAdd->events;
            if (pAdd < m_pEnd)
                return pAdd;
            pAdd->events = (unsigned short)65535;
        }
        if (m_pEnd >= m_pStoreEnd)
        {
            int ret = grow();
            if (ret)
                return NULL;
        }
        return m_pEnd++;
    }

public:
    enum
    {
        DEFAULT_CAPACITY = 16
    };

    PollfdReactor();
    ~PollfdReactor();

    int allocate(int capacity);
    int deallocate();
    int grow();
    void andMask(int index, short mask)   { m_pfds[index].events &= mask; }
    void orMask(int index, short mask)    { m_pfds[index].events |= mask; }
    void setMask(int index, short mask)   { m_pfds[index].events  = mask; }
    pollfd *getPollfds() const              { return m_pfds;                }
    pollfd *getPollfd(int index) const    { return &m_pfds[index];        }
    EventReactor *&getReactor(int index) const  { return m_pReactors[index];    }
    int getSize() const {   return m_pEnd - m_pfds;     }

    pollfd *getPollfd() const       {   return m_pfds;      }
    int getEventsLeft() const       {   return m_iEvents;   }

    void setEvents(int events)     {   m_iEvents = events;   }

    int add(EventReactor *pReactor, short mask)
    {
        struct pollfd *pAdd = getAvail();
        if (!pAdd)
            return LS_FAIL;
        pReactor->setPollfd(pAdd);
        pAdd->events = mask;
        pAdd->fd = pReactor->getfd();
        m_pReactors[pAdd - m_pfds] = pReactor;
        return pAdd - m_pfds;
    }

    int remove(EventReactor *pHandler);


    int processEvent(int fd, int index, short revents)
    {
        if ((index >= m_pEnd - m_pfds) || (m_pReactors[index]->getfd() != fd))
            return LS_FAIL;
        m_pfds[index].revents |= revents;
//        revents = m_pfds[index].revents & m_pfds[index].events;
//        if ( revents )
        m_pReactors[index]->assignRevent(revents);
        m_pReactors[index]->handleEvents(revents);
        return LS_OK;
    }

    int processEvent(int index, short revents)
    {
        if ((index >= m_pEnd - m_pfds) ||
            (m_pReactors[index]->getfd() != m_pfds[index].fd))
            return LS_FAIL;
        m_pfds[index].revents = revents;
//        revents = m_pfds[index].revents & m_pfds[index].events;
//        if ( revents )
        m_pReactors[index]->assignRevent(revents);
        m_pReactors[index]->handleEvents(revents);
        return LS_OK;
    }


    int processAllEvents()
    {
        m_pCur = m_pfds;
        int interupts = m_iEvents >> 5;
        int interuptPoint;
        interuptPoint = (m_iEvents + interupts + 1) / (interupts + 1);
        while ((m_iEvents > 0) && (m_pCur < m_pEnd))
        {
            if ((m_pCur->fd != -1) && ((m_pCur->revents & m_pCur->events) != 0))
            {
                short revents = (m_pCur->revents & m_pCur->events);
//                assert( m_pCur == m_pReactors[m_pCur - m_pfds]->getPollfd() );
//                assert( m_pCur->fd == m_pReactors[m_pCur - m_pfds]->getfd() );
                m_pReactors[m_pCur - m_pfds]->assignRevent(revents);
                m_pReactors[m_pCur - m_pfds]->handleEvents(revents);
                m_pCur->revents = 0;
                if (m_iEvents <= 0)
                    break;
                if (m_iEvents-- % interuptPoint == 0)
                    if (m_priHandler)
                        (*m_priHandler)();
            }
            ++m_pCur;
        }
        return LS_OK;
    }

    void timerExecute()
    {
        m_pCur = m_pfds;
        EventReactor **pCurReactor = &m_pReactors[ m_pEnd - m_pfds];
        while (pCurReactor > m_pReactors)
        {
            EventReactor *pHandler = *--pCurReactor;
            if (pHandler)
                pHandler->onTimer();
        }
    }

    void setPriHandler(EventReactor::pri_handler handler)
    {   m_priHandler = handler; }

    LS_NO_COPY_ASSIGN(PollfdReactor);
};

#endif
