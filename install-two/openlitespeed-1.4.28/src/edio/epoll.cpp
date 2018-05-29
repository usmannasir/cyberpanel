/*
 * Copyright 2002 Lite Speed Technologies Inc, All Rights Reserved.
 * LITE SPEED PROPRIETARY/CONFIDENTIAL.
 */


#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)

#include "epoll.h"

#include "log4cxx/logger.h"
#include <util/objarray.h>

#include <assert.h>
#include <fcntl.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/epoll.h>
#include <sys/syscall.h>
#include <unistd.h>

#include <sys/types.h>


static int s_loop_fd = -1;
static int s_loop_count = 0;


epoll::epoll()
    : m_epfd(-1)
    , m_pResults(NULL)
    , m_pResEnd(NULL)
    , m_pResCur(NULL)
{
    setFLTag(O_NONBLOCK | O_RDWR);
    m_pUpdates = new TObjArray<int>();
    m_pUpdates->setCapacity(NULL, 100);
}


epoll::~epoll()
{
    if (m_epfd != -1)
        close(m_epfd);
    if (m_pResults)
        free(m_pResults);
    if (m_pUpdates)
        delete m_pUpdates;
}


#define EPOLL_RESULT_BUF_SIZE   4096
//#define EPOLL_RESULT_MAX        EPOLL_RESULT_BUF_SIZE / sizeof( struct epoll_event )
#define EPOLL_RESULT_MAX        10
int epoll::init(int capacity)
{
    if (m_reactorIndex.allocate(capacity) == -1)
        return LS_FAIL;
    if (!m_pResults)
    {
        m_pResults = (struct epoll_event *)malloc(EPOLL_RESULT_BUF_SIZE);
        if (!m_pResults)
            return LS_FAIL;
        memset(m_pResults, 0, EPOLL_RESULT_BUF_SIZE);
    }
    if (m_epfd != -1)
        close(m_epfd);
    m_epfd = epoll_create(capacity);
    if (m_epfd == -1)
        return LS_FAIL;
    ::fcntl(m_epfd, F_SETFD, FD_CLOEXEC);
    return LS_OK;
}


int epoll::reinit()
{
    struct epoll_event epevt;
    close(m_epfd);
    m_epfd = epoll_create(m_reactorIndex.getCapacity());
    if (m_epfd == -1)
        return LS_FAIL;
    epevt.data.u64 = 0;
    ::fcntl(m_epfd, F_SETFD, FD_CLOEXEC);
    int n = m_reactorIndex.getUsed();
    for (int i = 0; i < n; ++i)
    {
        EventReactor *pHandler = m_reactorIndex.get(i);
        if (pHandler)
        {
            epevt.data.u64 = 0;
            epevt.data.fd = pHandler->getfd();
            epevt.events = pHandler->getEvents();
            epoll_ctl(m_epfd, EPOLL_CTL_ADD, epevt.data.fd, &epevt);
        }
    }
    return LS_OK;
}


/*
#include <typeinfo>
void dump_type_info( EventReactor * pHandler, const char * pMsg )
{
    LS_INFO( "[%d] %s EventReactor: %p, fd: %d, type: %s", getpid(), pMsg, pHandler, pHandler->getfd(),
                typeid( *pHandler ).name() ));
}
*/
int epoll::add(EventReactor *pHandler, short mask)
{
    int fd = pHandler->getfd();
    if (fd == -1)
        return LS_OK;
    //assert( fd > 1 );
    if (fd > 1000000)
        return LS_FAIL;
    m_reactorIndex.set(fd, pHandler);
    pHandler->setPollfd();
    pHandler->setMask2(mask);
    pHandler->clearRevent();
    if (addEx(fd, mask) == 0)
    {
        pHandler->updateEventSet();
        return 0;
    }
    return -1;
}


int epoll::addEx(int fd, short mask)
{
    struct epoll_event epevt;
    memset(&epevt, 0, sizeof(struct epoll_event));
    epevt.data.fd = fd;
    epevt.events = mask;
    //if (LS_LOG_ENABLED(LOG4CXX_NS::Level::DBG_LESS) || s_problems )
    //    dump_type_info( pHandler, "added" );
    return epoll_ctl(m_epfd, EPOLL_CTL_ADD, fd, &epevt);
}


int epoll::updateEvents(EventReactor *pHandler, short mask)
{
    int fd = pHandler->getfd();
    if (fd == -1)
        return LS_OK;
    assert(pHandler == m_reactorIndex.get(fd));
    pHandler->setMask2(mask);
    if (!(m_reactorIndex.getUpdateFlags(fd) & ERF_UPDATE))
    {
        m_reactorIndex.setUpdateFlags(fd, ERF_UPDATE);
        appendEvent(fd);
    }
    return LS_OK;
    //return updateEventsEx(fd, mask);
}


int epoll::updateEventsEx(int fd, short mask)
{
    struct epoll_event epevt;
    memset(&epevt, 0, sizeof(struct epoll_event));
    epevt.data.fd = fd;
    epevt.events = mask;
    return epoll_ctl(m_epfd, EPOLL_CTL_MOD, fd, &epevt);
}


int epoll::remove(EventReactor *pHandler)
{
    int fd = pHandler->getfd();
    if (fd == -1)
        return LS_OK;
    //assert( pHandler == m_reactorIndex.get( fd ) );
    if (fd <= (int)m_reactorIndex.getUsed())
    {
        pHandler->clearRevent();
        pHandler->setMask2(0);
        pHandler->updateEventSet();
        m_reactorIndex.set(fd, NULL);
    }
    return removeEx(fd);
}


int epoll::removeEx(int fd)
{
    struct epoll_event epevt;
    memset(&epevt, 0, sizeof(struct epoll_event));

    epevt.data.fd = fd;

    //if (LS_LOG_ENABLED(LOG4CXX_NS::Level::DBG_LESS) || s_problems )
    //    dump_type_info( pHandler, "remove" );
    return epoll_ctl(m_epfd, EPOLL_CTL_DEL, fd, &epevt);
}


int epoll::waitAndProcessEvents(int iTimeoutMilliSec)
{
    applyEvents();
    int ret = epoll_wait(m_epfd, m_pResults, EPOLL_RESULT_MAX,
                         iTimeoutMilliSec);
    if (ret <= 0)
        return ret;
    if (ret == 1)
    {
        int fd = m_pResults->data.fd;
        EventReactor *pReactor = m_reactorIndex.get(fd);
        if (pReactor && (pReactor->getfd() == fd))
        {
            if (m_pResults->events & POLLHUP)
                pReactor->incHupCounter();
            pReactor->assignRevent(m_pResults->events);
            pReactor->handleEvents(m_pResults->events);
        }
        return 1;
    }
    //if ( ret > EPOLL_RESULT_MAX )
    //    ret = EPOLL_RESULT_MAX;
    int    problem_detected = 0;
    m_pResEnd = m_pResults + ret;
    m_pResCur = m_pResults;
    struct epoll_event *p = m_pResults;
    while (p < m_pResEnd)
    {
        int fd = p->data.fd;
        EventReactor *pReactor = m_reactorIndex.get(fd);
        assert(p->events);
        if (pReactor)
        {
            if (pReactor->getfd() == fd)
                pReactor->assignRevent(p->events);
            else
                p->data.fd = -1;
        }
        else
        {
            if (removeEx(fd) == -1)
                if (p->events & (POLLHUP | POLLERR))
                    close(fd);
//             //p->data.fd = -1;
//             if ((s_loop_fd == -1) || (s_loop_fd == fd))
//             {
//                 if (s_loop_fd == -1)
//                 {
//                     s_loop_fd = fd;
//                     s_loop_count = 0;
//                 }
//                 problem_detected = 1;
//                 ++s_loop_count;
//                 if (s_loop_count == 10)
//                 {
//                     if (p->events & (POLLHUP | POLLERR))
//                         close(fd);
//                     else
//                     {
//                         struct epoll_event epevt;
//                         memset(&epevt, 0, sizeof(struct epoll_event));
//                         epevt.data.u64 = 0;
//                         epevt.data.fd = fd;
//                         epevt.events = 0;
//                         (syscall(__NR_epoll_ctl, m_epfd, EPOLL_CTL_DEL, fd, &epevt));
//                         LS_WARN("[%d] Remove looping fd: %d, event: %d\n", getpid(), fd,
//                                 p->events);
//                         ++s_problems;
//                     }
//                 }
//                 else if (s_loop_count >= 20)
//                 {
//                     LS_WARN("Looping fd: %d, event: %d\n", fd, p->events);
//                     assert(p->events);
//                     problem_detected = 0;
//                 }
//             }
        }
        ++p;
    }
    if (!problem_detected && s_loop_count)
    {
        s_loop_fd = -1;
        s_loop_count = 0;
    }
    return processEvents();
}


int epoll::processEvents()
{
    struct epoll_event *p;
    int count = m_pResCur >= m_pResEnd;
    if (count > 0)
        return LS_OK;
    while (m_pResCur < m_pResEnd)
    {
        p = m_pResCur++;
        int fd = p->data.fd;
        if (fd != -1)
        {
            EventReactor *pReactor = m_reactorIndex.get(fd);
            if (pReactor && (pReactor->getAssignedRevent() == (int)p->events))
            {
                if (p->events & POLLHUP)
                    pReactor->incHupCounter();
                pReactor->handleEvents(p->events);
            }
        }
    }

    memset(m_pResults, 0, (char *)m_pResEnd - (char *)m_pResults);
    applyEvents();
    return count;

}


void epoll::timerExecute()
{
    m_reactorIndex.timerExec();
}


void epoll::continueRead(EventReactor *pHandler)
{
    if (!(pHandler->getEvents() & POLLIN))
        addEvent(pHandler, POLLIN);
}


void epoll::suspendRead(EventReactor *pHandler)
{
    if (pHandler->getEvents() & POLLIN)
        removeEvent(pHandler, POLLIN);
}


void epoll::continueWrite(EventReactor *pHandler)
{
    if (!(pHandler->getEvents() & POLLOUT))
        addEvent(pHandler, POLLOUT);
}


void epoll::suspendWrite(EventReactor *pHandler)
{
    if (pHandler->getEvents() & POLLOUT)
        removeEvent(pHandler, POLLOUT);
}


void epoll::switchWriteToRead(EventReactor *pHandler)
{
    setEvents(pHandler, POLLIN | POLLHUP | POLLERR);
}


void epoll::switchReadToWrite(EventReactor *pHandler)
{
    setEvents(pHandler, POLLOUT | POLLHUP | POLLERR);
}


void epoll::applyEvents()
{
    struct epoll_event epevt;
    memset(&epevt, 0, sizeof(struct epoll_event));

    int *p = m_pUpdates->begin();
    int *pEnd = m_pUpdates->end();
    while (p < pEnd)
    {
        epevt.data.fd = *p++;
        EventReactor *pReactor = m_reactorIndex.get(epevt.data.fd);
        m_reactorIndex.setUpdateFlags(epevt.data.fd, 0);
        if (pReactor)
        {
            if (pReactor->isApplyEvents())
            {
                epevt.events = pReactor->getEvents();
                if (epoll_ctl(m_epfd, EPOLL_CTL_MOD, epevt.data.fd, &epevt) == 0)
                    pReactor->updateEventSet();
            }
        }
    }
    m_pUpdates->clear();
}


void epoll::appendEvent(int fd)
{
    if (m_pUpdates->getSize() >= m_pUpdates->getCapacity())
        m_pUpdates->guarantee(NULL, m_pUpdates->getCapacity() << 1);
    int *p = m_pUpdates->getNew();
    *p = fd;
}

#endif
