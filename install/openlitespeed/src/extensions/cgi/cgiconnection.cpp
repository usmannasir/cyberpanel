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
#include "cgiconnection.h"

// #include <http/httpextconnector.h>
#include <http/httplog.h>
#include <http/httpstatuscode.h>
#include <http/httpresourcemanager.h>
#include <util/pool.h>

#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

CgiConnection::CgiConnection()
{
}


CgiConnection::~CgiConnection()
{
}


//interface defined by EdStream
int CgiConnection::onRead()
{
    if (!getConnector())
        return LS_FAIL;
    LS_DBG_M(this, "CgiConnection::onRead()");
    int len = 0;
    int ret = 0;
    do
    {
        len = ret = read(HttpResourceManager::getGlobalBuf(), GLOBAL_BUF_SIZE);
        if (ret > 0)
        {
            LS_DBG_M(this, "Process STDOUT %d bytes", len);
            //printf( ">>read %d bytes from CGI\n", len );
            //achBuf[ ret ] = 0;
            //printf( "%s", achBuf );
            ret = getConnector()->processRespData(
                      HttpResourceManager::getGlobalBuf(), len);
            if (ret == -1)
                break;
        }
        else
        {
            if (ret)
                getConnector()->endResponse(0, 0);
            break;
        }
    }
    while (len == GLOBAL_BUF_SIZE);
    if ((ret != -1) && (getConnector()))
        getConnector()->flushResp();
    return ret;
}


int CgiConnection::readResp(char *pBuf, int size)
{
    int len = read(pBuf, size);
    if (len == -1)
        getConnector()->endResponse(0, 0);
    return len;

}


int CgiConnection::onWrite()
{
    if (!getConnector())
        return LS_FAIL;
    LS_DBG_M(this, "CgiConnection::onWrite()");
    int ret = extOutputReady();
    if (!(getConnector()->getState() & HEC_FWD_REQ_BODY))
        suspendWrite();
    return ret;
}


int CgiConnection::onError()
{
    if (!getConnector())
        return LS_FAIL;
    LS_DBG_M(this, "CgiConnection::onError()");
    //getState() = HEC_COMPLETE;
    getConnector()->endResponse(SC_500, 0);
    return LS_FAIL;
}


int CgiConnection::onEventDone(short event)
{
    return true;
}


bool CgiConnection::wantRead()
{
    return false;
}


bool CgiConnection::wantWrite()
{
    return false;
}


//interface defined by HttpExtProcessor
void CgiConnection::abort()
{
    ::shutdown(getfd(), SHUT_RDWR);
}


int CgiConnection::init(int fd, Multiplexer *pMultiplexer,
                        HttpExtConnector *pConn)
{
    assert(fd != -1);
    assert(pMultiplexer);
    assert(pConn != NULL);
    setConnector(pConn);
    EdStream::init(fd, pMultiplexer, POLLIN | POLLOUT | POLLHUP | POLLERR);
    return 0;
}


void CgiConnection::cleanUp()
{
    close();
    delete this;
}


int CgiConnection::begin()
{
    return 0;
}


int CgiConnection::beginReqBody()
{
    return 0;
}


int CgiConnection::endOfReqBody()
{
    suspendWrite();
    ::shutdown(getfd(), SHUT_WR);
    return 0;
}


int  CgiConnection::sendReqHeader()
{   return 0;   }


int CgiConnection::sendReqBody(const char *pBuf, int size)
{
    int ret = write(pBuf, size);
    //printf( ">>write %d bytes to CGI\n", ret );

    return ret;
}


int CgiConnection::s_iCgiCount = 0;

void *CgiConnection::operator new(size_t sz)
{
    void *ret = Pool::allocate(sizeof(CgiConnection));
    if (ret)
        ++s_iCgiCount;
    return ret;
}


void CgiConnection::operator delete(void *p)
{
    --s_iCgiCount;
    return Pool::deallocate(p, sizeof(CgiConnection));
}

