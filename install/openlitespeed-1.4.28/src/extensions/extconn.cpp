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
#include "extconn.h"
#include "extrequest.h"
#include "extworker.h"

#include <edio/multiplexer.h>
#include <edio/multiplexerfactory.h>
#include <http/httpstatuscode.h>
#include <log4cxx/logger.h>
#include <socket/coresocket.h>
#include <socket/gsockaddr.h>
#include <util/datetime.h>

#include <fcntl.h>

ExtConn::ExtConn()
    : m_iState(0)
    , m_iToStop(0)
    , m_iInProcess(0)
    , m_iCPState(0)
    , m_tmLastAccess(0)
    , m_iReqProcessed(0)
    , m_pWorker(NULL)
{
}


ExtConn::~ExtConn()
{
}


//void ExtConn::reset()
//{
//    close();
//    m_iState = DISCONNECTED;
//
//}


void ExtConn::recycle()
{
    if (getState() >= ABORT)
        close();
    m_pWorker->recycleConn(this);
}


void ExtConn::checkInProcess()
{
    assert(!m_iInProcess);
}


int ExtConn::assignReq(ExtRequest *pReq)
{
    int ret;

    if (getState() > PROCESSING)
        close();
    assert(!m_iInProcess);
//    if ( m_iInProcess )
//    {
//        LS_WARN(this, "[ExtConn] connection is still in middle of a request,"
//                " close before assign a new request");
//        close();
//    }
    m_iCPState = 0;
    ret = addRequest(pReq);
    if (ret)
    {
        if (ret == -1)
            ret = SC_500;
        pReq->setHttpError(ret);
        return ret;
    }
    m_tmLastAccess = DateTime::s_curTime;
    if (getState() == PROCESSING)
    {
        ret = doWrite();
        onEventDone();
        //pConn->continueWrite();
    }
    else if (getState() != CONNECTING)
        ret = reconnect();
    if (ret == -1)
        return connError(errno);
    return 0;

}


int ExtConn::close()
{
    LS_DBG_L(this, "[ExtConn] close()");
    EdStream::close();
    m_iState = DISCONNECTED;
    m_iInProcess = 0;
    return 0;
}


int ExtConn::reconnect()
{
    LS_DBG_L(this, "[ExtConn] reconnect()");
    if (m_iState != DISCONNECTED)
        close();
    if (m_pWorker)
        return connect(MultiplexerFactory::getMultiplexer());
    else
        return LS_FAIL;
}


int ExtConn::connect(Multiplexer *pMplx)
{
    m_pWorker->startOnDemond(0);
    return connectEx(pMplx);
}


int ExtConn::connectEx(Multiplexer *pMplx)
{
    int fd;
    int ret;
    ret = CoreSocket::connect(m_pWorker->getServerAddr(), pMplx->getFLTag(),
                              &fd, 1);
    m_iReqProcessed = 0;
    m_iCPState = 0;
    m_iToStop = 0;
    if ((fd == -1) && (errno == ECONNREFUSED))
        ret = CoreSocket::connect(m_pWorker->getServerAddr(), pMplx->getFLTag(),
                                  &fd, 1);
    if (fd != -1)
    {
        LS_DBG_L(this, "[ExtConn] connecting to [%s]...", m_pWorker->getURL());
        m_tmLastAccess = DateTime::s_curTime;
        ::fcntl(fd, F_SETFD, FD_CLOEXEC);
        init(fd, pMplx);
        if (ret == 0)
        {
            m_iState = PROCESSING;
            onWrite();
        }
        else
            m_iState = CONNECTING;
        return 0;
    }
    return LS_FAIL;
}


int ExtConn::onInitConnected()
{
    int error;
    int ret = getSockError(&error);
    if ((ret == -1) || (error != 0))
    {
        if (ret != -1)
            errno = error;
        return LS_FAIL;
    }
    m_iState = PROCESSING;
    if (LS_LOG_ENABLED(LOG4CXX_NS::Level::DBG_LESS))
    {
        char        achSockAddr[128];
        char        achAddr[128]    = "";
        int         port            = 0;
        socklen_t   len             = 128;

        if (getsockname(getfd(), (struct sockaddr *)achSockAddr, &len) == 0)
        {
            GSockAddr::ntop((struct sockaddr *)achSockAddr, achAddr, 128);
            port = GSockAddr::getPort((struct sockaddr *)achSockAddr);
        }

        LS_DBG_L(this, "Connected to [%s] on local address [%s:%d]!",
                 m_pWorker->getURL(), achAddr, port);
    }
    return 0;
}


int ExtConn::onRead()
{
    LS_DBG_L(this, "ExtConn::onRead()");
    m_tmLastAccess = DateTime::s_curTime;
    int ret;
    switch (m_iState)
    {
    case CONNECTING:
        ret = onInitConnected();
        break;
    case PROCESSING:
        ret = doRead();
        break;
    case ABORT:
    case CLOSING:
    case DISCONNECTED:
        return 0;
    default:
        // Not suppose to happen;
        return 0;
    }
    if (ret == -1)
        ret = connError(errno);
    return ret;
}


int ExtConn::onWrite()
{
    LS_DBG_L(this, "ExtConn::onWrite()");
    m_tmLastAccess = DateTime::s_curTime;
    int ret;
    switch (m_iState)
    {
    case CONNECTING:
        ret = onInitConnected();
        if (ret)
            break;
    //fall through
    case PROCESSING:
        ret = doWrite();
        break;
    case ABORT:
    case CLOSING:
    case DISCONNECTED:
        return 0;
    default:
        return 0;
    }
    if (ret == -1)
        ret = connError(errno);
    return ret;
}


int ExtConn::onError()
{
    int error = errno;
    int ret = getSockError(&error);
    if ((ret == -1) || (error != 0))
    {
        if (ret != -1)
            errno = error;
    }
    LS_DBG_L(this, "ExtConn::onError()");
    if (error != 0)
    {
        m_iState = CLOSING;
        doError(error);
    }
    else
        onRead();
    return LS_FAIL;
}


void ExtConn::onTimer()
{
}


void ExtConn::onSecTimer()
{
    int secs = DateTime::s_curTime - m_tmLastAccess;
    if (m_iState == CONNECTING)
    {
        if (secs >= 2)
        {
            LS_NOTICE(this, "ExtConn timed out while connecting.");
            connError(ETIMEDOUT);
        }
    }
    else if (m_iState == DISCONNECTED)
    {
    }
    else if (getReq())
    {
        if (!m_iCPState && m_iReqProcessed == 0)
        {
            if (secs >= m_pWorker->getTimeout())
            {
                LS_NOTICE(this, "ExtConn timed out while processing.");
                connError(ETIMEDOUT);
            }
            else if ((secs == 10) && (getReq()->isRecoverable()))
            {
//                 LS_DBG_L(this, "No response in 10 seconds, possible dead "
//                          "lock, try starting a new instance.");
                m_pWorker->addNewProcess();
            }
        }
    }
    else if ((m_iState == PROCESSING)
             && (secs > m_pWorker->getConfigPointer()->getKeepAliveTimeout()))
    {
        LS_DBG_L(this, "Idle connection timed out, close!");
        close();
    }

}


int ExtConn::connError(int errCode)
{
    LS_DBG_L(this,
             "Connection to [%s] on request #%d, confirmed %d, error: %s!",
             m_pWorker->getURL(), m_iReqProcessed, (int)m_iCPState,
             strerror(errCode));
    if (errCode == EINTR)
        return 0;
    close();
    ExtRequest *pReq = getReq();
    if (pReq)
    {
        if (((m_pWorker->getConnPool().getFreeConns() == 0)
             || ((pReq->getAttempts() % 3) == 0)) &&
            ((errCode == EPIPE) || (errCode == ECONNRESET)) &&
            (pReq->isRecoverable()) && (m_iReqProcessed) && (!m_iCPState))
        {
            pReq->incAttempts();
            pReq->resetConnector();
            if (reconnect() == 0)
                return 0;
            close();
        }
    }
    return m_pWorker->connectionError(this, errCode);
//    if ( !m_pWorker->connectionError( this, errCode ) )
//    {
//        //if (( errCode != ENOMEM )&&(errCode != EMFILE )
//        //        &&( errCode != ENFILE ))
//    }
}


int ExtConn::onEventDone()
{
    switch (m_iState)
    {
    case ABORT:
    case CLOSING:
        close();
        if (!getReq())
            m_pWorker->getConnPool().removeConn(this);
        else
            getReq()->endResponse(0, 0);
        //reconnect();
        break;
    }
    return 0;
}


#ifndef _NDEBUG
void ExtConn::continueRead()
{
    LS_DBG_L(this, "ExtConn::continueRead()");
    EdStream::continueRead();
}


void ExtConn::suspendRead()
{
    LS_DBG_L(this, "ExtConn::suspendRead()");
    EdStream::suspendRead();
}


void ExtConn::continueWrite()
{
    LS_DBG_L(this, "ExtConn::continueWrite()");
    /*    if ( getRevents() & POLLOUT )
        {
            onWrite();
        }
        else*/
    EdStream::continueWrite();
}


void ExtConn::suspendWrite()
{
    LS_DBG_L(this, "ExtConn::suspendWrite()");
    EdStream::suspendWrite();
}
#endif

