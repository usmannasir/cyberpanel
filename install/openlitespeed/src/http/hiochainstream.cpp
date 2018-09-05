/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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

#include "hiochainstream.h"
#include <http/httpsession.h>

#include <stdio.h>
#include <sys/uio.h>

HioChainStream::HioChainStream()
    : m_pParentSession(NULL)
    , m_iDepth(0)
    , m_iSequence(0)
    , m_pRespHeaders(NULL)
{

}

HioChainStream::~HioChainStream()
{

}


void HioChainStream::onTimer()
{
    if (getHandler())
        getHandler()->onTimerEx();
}

void HioChainStream::switchWriteToRead()
{
    suspendWrite();
}

void HioChainStream::continueWrite()
{
    int old = getFlag(HIO_FLAG_WANT_WRITE);
    setFlag(HIO_FLAG_WANT_WRITE, 1);
    if (getFlag(HIO_FLAG_BLACK_HOLE))
    {
        if (!old)
            getHandler()->onWriteEx();
    }
    else if (m_pParentSession)
        m_pParentSession->wantWrite(1);
}

void HioChainStream::suspendWrite()
{
    setFlag(HIO_FLAG_WANT_WRITE, 0);
    if (m_pParentSession)
        m_pParentSession->wantWrite(0);
}

void HioChainStream::continueRead()
{
}

void HioChainStream::suspendRead()
{
}

int HioChainStream::passSetCookieToParent()
{
    struct iovec iov[100];
    int count;
    count = m_pRespHeaders->getHeader(HttpRespHeaders::H_SET_COOKIE,
                                      iov, 100);
    if (count > 0)
        m_pParentSession->mergeRespHeaders(HttpRespHeaders::H_SET_COOKIE,
                                           "set-cookie", 10, iov, count);
    return 0;
}

int HioChainStream::sendRespHeaders(HttpRespHeaders *pHeaders)
{
    m_pRespHeaders = pHeaders;
    if (m_pParentSession && getFlag(HIO_FLAG_PASS_SETCOOKIE))
        passSetCookieToParent();
    return 0;
}


int HioChainStream::read(char *pBuf, int size)
{
    return 0;
}

int HioChainStream::close()
{
    //if (getState()!=HIOS_CONNECTED)
    //    return 0;
    setState(HIOS_DISCONNECTED);
    if (m_pParentSession)
    {
        //m_pParentSession->onSubSessionEndResp( (HttpSession *)getHandler() );
        m_pParentSession = NULL;
    }
    /*
    if (getHandler())
    {
        if ( isReadyToRelease() )
        {
            getHandler()->recycle();
            setHandler( NULL );
        }
        else
            getHandler()->onCloseEx();
    }
    */
    return 0;
}

int HioChainStream::flush()
{
    if (m_pParentSession)
        return m_pParentSession->flush();
    return 0;
}

int HioChainStream::writev(IOVec &vec, int total)
{
    //if (getState()!=HIOS_CONNECTED)
    //    return -1;
    return writevToWrite(vec.get(), vec.len());

}

int HioChainStream::writev(const iovec *vector, int count)
{
    //if (getState()!=HIOS_CONNECTED)
    //    return -1;
    return writevToWrite(vector, count);
}

int HioChainStream::write(const char *pBuf, int size)
{
    //if (getState()!=HIOS_CONNECTED)
    //    return -1;
    if (m_pParentSession)
        return m_pParentSession->appendDynBody(pBuf, size);
    if (!getFlag(HIO_FLAG_BLACK_HOLE))
        return 0;
    else
        return size;

}

int HioChainStream::sendfile(int fdSrc, off_t off, off_t size)
{
    //if (getState()!=HIOS_CONNECTED)
    //    return -1;
    if (m_pParentSession)
        return m_pParentSession->writeRespBodySendFile(fdSrc, off, size);
    if (!getFlag(HIO_FLAG_BLACK_HOLE))
        return 0;
    else
        return size;

}

// TODO: Warning: not compiled in ols, verify in lslbd
const char *HioChainStream::buildLogId()
{
    HttpSession *pSession = (HttpSession *)getHandler();
    pSession = pSession->getParent();
    int len ;
    if (!pSession)
    {
        appendLogId("Detached:S-", true);
    }
    else
    {
        appendLogId(pSession->getLogId(), true);
        appendLogId(":S-", true);
    }

    size_t len = snprintf(m_logId.ptr + m_logId.len, MAX_LOGID_LEN - m_logId.len, "%d",
                   m_iSequence);
    m_logId.len += len;

    return m_logId.ptr;
}

int HioChainStream::onWrite()
{
    if (isWantWrite())
        if (getHandler())
            getHandler()->onWriteEx();
    return 0;
}
