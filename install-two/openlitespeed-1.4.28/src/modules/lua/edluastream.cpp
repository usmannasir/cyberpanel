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
#include "edluastream.h"
#include "lsluaapi.h"
#include "lsluaengine.h"
#include "lsluasession.h"

#include <ls.h>
#include <edio/multiplexer.h>
#include <socket/coresocket.h>
#include <socket/gsockaddr.h>

#include <fcntl.h>


#define EDLUA_READ_LINE   0
#define EDLUA_READ_ALL   -1


EdLuaStream::EdLuaStream()
    : m_pRecvState(NULL)
    , m_pSendState(NULL)
    , m_bufOut(4096)
    , m_bufIn(4096)
    , m_iFlag(EDLUA_FLAG_NONE)
    , m_iCurInPos(0)
    , m_iToRead(EDLUA_READ_LINE)
    , m_iToSend(0)
    , m_iTimeoutMs(10000)
    , m_iRecvTimeout(0)
    , m_iSendTimeout(0)
{
}


EdLuaStream::~EdLuaStream()
{
}


inline int64_t getCurTimeMs()
{
    int32_t usec;
    time_t t;
    t = g_api->get_cur_time(&usec);

    return (int64_t)t * 1000 + usec / 1000;
}


static int buildLuaSocketErrorRet(lua_State *L, int error)
{
    char achError[1024] = "socket error: ";
    strerror_r(error, &achError[14], 1000);
    LsLuaApi::pushnil(L);
    LsLuaApi::pushstring(L, achError);
    return 2;
}


int EdLuaStream::resume(lua_State *&L, int nArg)
{
    LsLuaSession *pSession = LsLuaGetSession(L);

    L = NULL;

    LsLuaEngine::resumeNcheck(pSession, nArg);
    return nArg;
}


int EdLuaStream::resumeWithError(lua_State *&L, int flag, int errcode)
{
    int ret;
    m_iFlag &= ~flag;
    ret = buildLuaSocketErrorRet(L, errcode);
    resume(L, ret);
    return ret;
}


int EdLuaStream::connectTo(lua_State *L, const char *pAddr, uint16_t port)
{
    int fd;
    int ret;
    GSockAddr sockAddr;
    Multiplexer *pMplx = (Multiplexer *)g_api->get_multiplexer();
    if (sockAddr.parseAddr(pAddr) == -1)
    {
        LsLuaApi::pushnil(L);
        LsLuaApi::pushstring(L, "Bad address");
        return 2;
    }
    sockAddr.setPort(port);

    ret = CoreSocket::connect(sockAddr, pMplx->getFLTag(), &fd, 1);
    if (fd != -1)
    {
        LsLuaLog(L, LSI_LOG_DEBUG, 0,
                 "[EDLuaStream][%p] connecting to [%s]...",
                 this, pAddr);
        ::fcntl(fd, F_SETFD, FD_CLOEXEC);
        if (ret == 0)
        {
            init(fd, pMplx, POLLHUP | POLLERR);
            m_iFlag |= EDLUA_FLAG_CONNECTED;
            //FIXME: magic number? connect successful
            LsLuaApi::pushinteger(m_pSendState, 1);
            return 1;
        }
        else
        {
            init(fd, pMplx, POLLIN | POLLOUT | POLLHUP | POLLERR);
            m_iFlag |= EDLUA_FLAG_CONNECTING;
            m_iSendTimeout = getCurTimeMs() + m_iTimeoutMs;
            m_pSendState = L;

            return LsLuaApi::yield(m_pSendState, 0);
        }
    }
    return buildLuaSocketErrorRet(L, errno);
}


int EdLuaStream::onInitialConnected()
{
    int n = 0;
    int error;
    int ret = getSockError(&error);
    m_iFlag &= ~EDLUA_FLAG_CONNECTING;
    if ((ret == -1) || (error != 0))
    {
        if (ret != -1)
            errno = error;
        n = buildLuaSocketErrorRet(m_pSendState, errno);
    }
    else
    {
        m_iFlag |= EDLUA_FLAG_CONNECTED;
        //FIXME: magic number? CONNECT SUCCESSFUL
        LsLuaApi::pushinteger(m_pSendState, 1);
        n = 1;
    }
    //resume LUA coroutine
    return resume(m_pSendState, n);

}


int EdLuaStream::send(lua_State *L, const char *pBuf, int32_t iLen)
{
    int ret;
    if ((m_iFlag & EDLUA_FLAG_CONNECTED) == 0)
        return buildLuaSocketErrorRet(L, ENOTCONN);

    if (m_iFlag & EDLUA_FLAG_SEND)
    {
        LsLuaApi::pushnil(L);
        LsLuaApi::pushstring(L, "socket send in progress");
        return 2;
    }

    m_iToSend = iLen;
    if (m_bufOut.empty())
    {
        ret = write(pBuf, iLen);
        if (ret > 0)
        {
            pBuf += ret;
            iLen -= ret;
        }
        else if (ret < 0)
            return buildLuaSocketErrorRet(L, errno);
    }
    if (iLen > 0)
    {
        m_bufOut.append(pBuf, iLen);
        continueWrite();
        m_iFlag |= EDLUA_FLAG_SEND;
        m_iSendTimeout = getCurTimeMs() + m_iTimeoutMs;
        m_pSendState = L;
        return LsLuaApi::yield(m_pSendState, 0);
    }
    else
    {
        LsLuaApi::pushinteger(L, m_iToSend);
        return 1;
    }
    return 0;
}


int EdLuaStream::doWrite(lua_State *L)
{
    int len;
    int ret = 0;
    while (m_bufOut.size() > 0)
    {
        len = m_bufOut.blockSize();
        ret = write(m_bufOut.begin(), len);
        if (ret >= 0)
        {
            if (ret > 0)
                m_bufOut.pop_front(ret);
            if (ret < len)
                return 0;
        }
        else
        {
            ret = buildLuaSocketErrorRet(L, errno);
            break;
        }
    }
    m_iFlag &= ~EDLUA_FLAG_SEND;
    if (m_bufOut.empty())
    {
        LsLuaApi::pushinteger(m_pSendState, m_iToSend);
        ret = 1;
    }
    suspendWrite();
    return resume(m_pSendState, ret);

}


int EdLuaStream::onWrite()
{
    if (m_iFlag & EDLUA_FLAG_CONNECTING)
    {
        suspendWrite();
        return onInitialConnected();
    }
    if ((m_iFlag & EDLUA_FLAG_SEND) == 0)
    {
        suspendWrite();
        return 0;
    }
    return doWrite(m_pSendState);
}


int EdLuaStream::processInputBuf(lua_State *L)
{
    int ret;
    int res;
    if (m_iToRead == EDLUA_READ_LINE)
    {
        const char *p;
        const char *pBuf = m_bufIn.getPointer(m_iCurInPos);
        if (m_iCurInPos < m_bufIn.blockSize())
        {
            p = (const char *)memchr(pBuf, '\n',
                                     m_bufIn.blockSize() - m_iCurInPos);
            if ((p == NULL) && (m_bufIn.size() > m_bufIn.blockSize()))
            {
                m_iCurInPos = m_bufIn.blockSize();
                pBuf = m_bufIn.getPointer(m_iCurInPos);
                p = (const char *)memchr(pBuf, '\n',
                                         m_bufIn.size() - m_iCurInPos);
            }
        }
        else
        {
            p = (const char *)memchr(pBuf, '\n',
                                     m_bufIn.size() - m_iCurInPos);
        }
        if (p != NULL)
        {
            res = p - pBuf + m_iCurInPos;
            ret = res + 1;
            if ((res > 0) && (*m_bufIn.getPointer(res - 1) == '\r'))
                --res;
        }
        else
            return 0;
    }
    else if (m_iToRead > 0)
    {
        if (m_bufIn.size() < m_iToRead)
            return 0;
        ret = res = m_iToRead;
    }
    else
        return 0;
    if (m_bufIn.blockSize() != m_bufIn.size() && res > m_bufIn.blockSize())
        m_bufIn.straight();
    LsLuaApi::pushlstring(L, m_bufIn.begin(), res);
    m_bufIn.pop_front(ret);
    LsLuaLog(L, LSI_LOG_DEBUG, 0,
             "[%p] return %d bytes, pop buffer: %d, left: %d  ",
             this, res, ret, m_bufIn.size());
    return 1;
}


int EdLuaStream::doRead(lua_State *L)
{
    int ret = 0;
    int toRead = 0;
    int res = 0;
    while (1)
    {
        if (m_iCurInPos >= m_bufIn.size())
        {
            if (m_bufIn.available() < 2048)
                m_bufIn.guarantee(4096);

            toRead = m_bufIn.contiguous();
            ret = read(m_bufIn.end(), toRead);
            if (ret > 0)
            {
                LsLuaLog(L, LSI_LOG_DEBUG, 0, "[%p] read %d bytes. ",
                         this, ret);
                m_bufIn.used(ret);
            }
            else if (ret == 0)
            {
                LsLuaLog(L, LSI_LOG_DEBUG, 0, "[%p] read nothing. ", this);
                break;
            }
            else
            {
                LsLuaLog(L, LSI_LOG_DEBUG, 0, "[%p] socket error: %d:%s ",
                         this, errno, strerror(errno));
                if (errno == ECONNRESET)
                {
                    LsLuaLog(L, LSI_LOG_DEBUG, 0,
                             "[%p] connection closed by peer. ", this);
                }
                if ((errno == ECONNRESET)
                    && (m_iToRead == EDLUA_READ_ALL))
                    res = 0;
                else
                    res = buildLuaSocketErrorRet(L, errno);

                if (m_bufIn.blockSize() != m_bufIn.size())
                {
                    LsLuaLog(L, LSI_LOG_DEBUG, 0,
                             "[%p] buffer straight ", this);
                    m_bufIn.straight();
                }
                LsLuaLog(L, LSI_LOG_DEBUG, 0, "[%p] return %d bytes ",
                         this, m_bufIn.size());
                LsLuaApi::pushlstring(L, m_bufIn.begin(),
                                      m_bufIn.size());
                m_bufIn.clear();
                res++;
            }
        }
        if (res == 0)
        {
            res = processInputBuf(L);
            if (res == 0)
            {
                m_iCurInPos = m_bufIn.size();
                continue;
            }
        }
        if (m_iFlag & EDLUA_FLAG_RECV)
        {
            suspendRead();
            m_iFlag &= ~EDLUA_FLAG_RECV;
            resume(m_pRecvState, res);
        }
        return res;
    }
    if ((m_iFlag & EDLUA_FLAG_RECV) == 0)
    {
        continueRead();
        m_iFlag |= EDLUA_FLAG_RECV;
        m_iRecvTimeout = getCurTimeMs() + m_iTimeoutMs;
        m_pRecvState = L;
        return LsLuaApi::yield(m_pRecvState, 0);
    }
    return 0;
}


int EdLuaStream::recv(lua_State *L, int32_t len)
{
    if ((m_iFlag & EDLUA_FLAG_CONNECTED) == 0)
        return buildLuaSocketErrorRet(L, ENOTCONN);
    if (m_iFlag & EDLUA_FLAG_RECV)
    {
        LsLuaApi::pushnil(L);
        LsLuaApi::pushstring(L, "socket read in progress");
        return 2;
    }
    m_iToRead = len;
    m_iCurInPos = 0;
    return doRead(L);
}


int EdLuaStream::onRead()
{
    if (m_iFlag & EDLUA_FLAG_RECV)
        return doRead(m_pRecvState);

    suspendRead();
    if (m_iFlag & EDLUA_FLAG_CONNECTING)
        return onInitialConnected();
    return 0;
}


int EdLuaStream::onEventDone()
{
    if (m_iFlag & EDLUA_FLAG_RECYCLE)
        delete this;
    return 0;
}


void EdLuaStream::onTimer()
{
    int64_t curTime = getCurTimeMs();
    if (m_iFlag & EDLUA_FLAG_RECV)
    {
        if (m_iRecvTimeout < curTime)
        {
            LsLuaLog(m_pRecvState, LSI_LOG_DEBUG, 0,
                     "[%p] receive timed out.", this);
            resumeWithError(m_pRecvState, EDLUA_FLAG_RECV, ETIMEDOUT);
        }
    }
    if (m_iFlag & (EDLUA_FLAG_SEND | EDLUA_FLAG_CONNECTING))
    {
        if (m_iSendTimeout < curTime)
        {
            if (m_iFlag & EDLUA_FLAG_CONNECTING)
            {
                LsLuaLog(m_pSendState, LSI_LOG_DEBUG, 0,
                         "[%p] connect timed out.", this);
            }
            else
            {
                LsLuaLog(m_pSendState, LSI_LOG_DEBUG, 0,
                         "[%p] send timed out.", this);
            }
            resumeWithError(m_pSendState,
                            EDLUA_FLAG_SEND | EDLUA_FLAG_CONNECTING,
                            ETIMEDOUT);
        }
    }
}


int EdLuaStream::onError()
{
    int error = errno;
    int ret = getSockError(&error);
    if ((ret == -1) || (error != 0))
    {
        if (ret != -1)
            errno = error;
    }
    LsLuaLog(NULL, LSI_LOG_DEBUG, 0, " [%p] EdLuaStream::onError()", this);
    EdStream::close();
    errno = ENOTCONN;
    m_iFlag &= ~(EDLUA_FLAG_CONNECTING | EDLUA_FLAG_CONNECTED);
    if (m_iFlag & EDLUA_FLAG_RECV)
        resumeWithError(m_pRecvState, EDLUA_FLAG_RECV, ENOTCONN);
    if (m_iFlag & EDLUA_FLAG_SEND)
        resumeWithError(m_pSendState, EDLUA_FLAG_SEND, ENOTCONN);
    return ret;
}


int EdLuaStream::forceClose(lua_State *L)
{
    if (m_iFlag & EDLUA_FLAG_CONNECTED)
    {
        LsLuaLog(L, LSI_LOG_DEBUG, 0, "closex %d", EdLuaStream::getfd());
        EdStream::close();
        m_iFlag &= ~EDLUA_FLAG_CONNECTED;
    }
    return 0;
}


int EdLuaStream::closeSock(lua_State *L)
{
    int ret;
    LsLuaLog(L, LSI_LOG_DEBUG, 0, "close %d", EdLuaStream::getfd());
    ret = EdStream::close();
    m_iFlag &= ~EDLUA_FLAG_CONNECTED;

    if (m_iFlag & EDLUA_FLAG_CONNECTING)
        resumeWithError(m_pSendState, EDLUA_FLAG_CONNECTING, EBADF);

    if (m_iFlag & EDLUA_FLAG_RECV)
        doRead(m_pRecvState);

    if (m_iFlag & EDLUA_FLAG_SEND)
        doWrite(m_pSendState);

    if (ret == -1)
        ret = buildLuaSocketErrorRet(L, errno);
    else
    {
        LsLuaApi::pushinteger(L, 1);
        ret = 1;
    }
    return ret;
}


static int LsLuaSockToString(lua_State *L)
{
    char    buf[0x100];

    EdLuaStream **p = (EdLuaStream **)LsLuaApi::checkudata(L, 1,
                      LSLUA_TCPSOCKDATA);
    if (p == NULL)
        return 0;
    EdLuaStream *p_sock = *p;
    if (p_sock)
        snprintf(buf, 0x100, "<ls.socket %p>", p_sock);
    else
        strcpy(buf, "<ls.socket DATA-INVALID>");
    LsLuaApi::pushstring(L, buf);
    return 1;
}


static int LsLuaSockGc(lua_State *L)
{
    EdLuaStream **p = (EdLuaStream **)LsLuaApi::checkudata(L, 1,
                      LSLUA_TCPSOCKDATA);
    if (p == NULL)
    {
        LsLuaLog(L, LSI_LOG_NOTICE, 0, "GC <ls.socket INVALID LUA UDATA>");
        return 0;
    }
    return 0;
}


static int LsLuaSockCreate(lua_State *L)
{
    EdLuaStream *p_sock;
    LsLuaSession *pSession = LsLuaGetSession(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "sock_tcp",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;

    if ((p_sock = LsLuaSession::newEdLuaStream(L)) == NULL)
        LsLuaApi::pushnil(L);
    else
    {
        LsLuaApi::getfield(L, LSLUA_REGISTRYINDEX, LSLUA_TCPSOCKDATA);
        LsLuaApi::setmetatable(L, -2);
    }
    return 1;
}


static int LsLuaSockConnect(lua_State *L)
{
    size_t size;
    const char *cp;
    EdLuaStream *p_sock = NULL;
    EdLuaStream **p;
    LsLuaSession *pSession = LsLuaGetSession(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "sock_connect",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    p = (EdLuaStream **)LsLuaApi::checkudata(L, 1, LSLUA_TCPSOCKDATA);
    if (p)
        p_sock = *p;
    if (p_sock == NULL)
        return LsLuaApi::userError(L, "sock_connect", "Bad Socket");

    if ((cp = LsLuaApi::tolstring(L, 2, &size)) && size)
    {
        int ret =  p_sock->connectTo(L, cp, LsLuaApi::tonumber(L, 3));
        return ret;
    }
    else
        return LsLuaApi::userError(L, "sock_connect", "Bad Socket");
}


static int LsLuaSockClose(lua_State *L)
{
    EdLuaStream *p_sock = NULL;
    EdLuaStream **p;
    LsLuaSession *pSession = LsLuaGetSession(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "sock_close",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    p = (EdLuaStream **)LsLuaApi::checkudata(L, 1, LSLUA_TCPSOCKDATA);
    if (p)
        p_sock = *p;
    if (p_sock == NULL)
        return LsLuaApi::userError(L, "sock_close", "Bad Socket");
    return p_sock->closeSock(L);
}


static int LsLuaSockReceive(lua_State *L)
{
    size_t size;
    int key;
    const char *cp;
    EdLuaStream *p_sock = NULL;
    EdLuaStream **p;
    LsLuaSession *pSession = LsLuaGetSession(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "sock_receive" ,
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    p = (EdLuaStream **)LsLuaApi::checkudata(L, 1, LSLUA_TCPSOCKDATA);
    if (p)
        p_sock = *p;
    if (p_sock == NULL)
        return LsLuaApi::userError(L, "sock_receive", "Bad Socket");

    if ((LsLuaApi::gettop(L) < 2))
        return p_sock->recv(L, EDLUA_READ_LINE);

    if (((cp = LsLuaApi::tolstring(L, 2, &size)) == NULL)
        || (size) == 0)
        return LsLuaApi::userError(L, "sock_receive", "Invalid Pattern.");

    key = EDLUA_READ_LINE;
    if (memcmp(cp, "*l", 2) == 0)
        key = EDLUA_READ_ALL;
    else if (strcmp(cp, "*a") == 0)
        key = EDLUA_READ_LINE;
    else
        key = atoi(cp);

    return p_sock->recv(L, key);
}


static int LsLuaSockSend(lua_State *L)
{
    const char *cp;
    EdLuaStream **p;
    EdLuaStream *p_sock = NULL;
    size_t size = 0;
    LsLuaSession *pSession = LsLuaGetSession(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "sock_send",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    p = (EdLuaStream **)LsLuaApi::checkudata(L, 1, LSLUA_TCPSOCKDATA);
    if (p)
        p_sock = *p;
    if (p_sock == NULL)
        return LsLuaApi::userError(L, "sock_send", "Bad Socket");

    if (((cp = LsLuaApi::tolstring(L, 2, &size)) == NULL)
        || (size == 0))
        return LsLuaApi::userError(L, "sock_send", "Invalid data");

    return p_sock->send(L, cp, size);
}


static int LsLuaSockSetTimeout(lua_State *L)
{
    int timeout;
    EdLuaStream *p_sock = NULL;
    EdLuaStream **p;
    LsLuaSession *pSession = LsLuaGetSession(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "sock_settimeout",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    p = (EdLuaStream **)LsLuaApi::checkudata(L, 1, LSLUA_TCPSOCKDATA);
    if (p)
        p_sock = *p;
    if (p_sock == NULL)
        return LsLuaApi::userError(L, "sock_settimeout", "Bad Socket");

    timeout = LsLuaApi::tonumber(L, 2);
    if (timeout <= 0)
        return LsLuaApi::userError(L, "sock_settimeout", "Invalid Timeout");

    return p_sock->setTimout(timeout);
}


static int LsLuaSockSetOption(lua_State *L)
{
    EdLuaStream *p_sock = NULL;
    EdLuaStream **p;
    LsLuaSession *pSession = LsLuaGetSession(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "sock_setoption",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    p = (EdLuaStream **)LsLuaApi::checkudata(L, 1, LSLUA_TCPSOCKDATA);
    if (p)
        p_sock = *p;
    if (p_sock == NULL)
        return LsLuaApi::userError(L, "sock_setoption", "Bad Socket");

    LsLuaLog(L, LSI_LOG_DEBUG, 0, "setoption not supported yet");
    return 0;
}


static int LsLuaSockSetKeepAlive(lua_State *L)
{
    EdLuaStream *p_sock = NULL;
    EdLuaStream **p;
    LsLuaSession *pSession = LsLuaGetSession(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "sock_setkeepalive",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    p = (EdLuaStream **)LsLuaApi::checkudata(L, 1, LSLUA_TCPSOCKDATA);
    if (p)
        p_sock = *p;
    if (p_sock == NULL)
        return LsLuaApi::userError(L, "sock_setkeepalive", "Bad Socket");

    LsLuaLog(L, LSI_LOG_DEBUG, 0, "setkeepalive not supported yet");

    LsLuaApi::pushinteger(L, 1);
    LsLuaApi::pushlstring(L, "not supported", 13);
    return 1;
}


static int LsLuaSockGetReusedTimes(lua_State *L)
{
    EdLuaStream *p_sock = NULL;
    EdLuaStream **p;
    LsLuaSession *pSession = LsLuaGetSession(L);

    int iRet;
    if ((iRet = LsLuaSession::checkHook(pSession, L, "sock_getreusedtimes",
                                        LSLUA_HOOK_REWRITE
                                        | LSLUA_HOOK_AUTH
                                        | LSLUA_HOOK_HANDLER)) != 0)
        return iRet;
    p = (EdLuaStream **)LsLuaApi::checkudata(L, 1, LSLUA_TCPSOCKDATA);
    if (p)
        p_sock = *p;
    if (p_sock == NULL)
        return LsLuaApi::userError(L, "sock_getreusedtimes", "Bad Socket");

    LsLuaLog(L, LSI_LOG_DEBUG, 0, "getreusetimes not supported yet");
    return 0;
}


static const luaL_Reg sockSub[] =
{
    { "tcp",                LsLuaSockCreate           },
    { "receive",            LsLuaSockReceive          },
    { "send",               LsLuaSockSend             },
    { "connect",            LsLuaSockConnect          },
    { "close",              LsLuaSockClose            },
    { "settimeout",         LsLuaSockSetTimeout       },
    { "setoption",          LsLuaSockSetOption        },
    { "setkeepalive",       LsLuaSockSetKeepAlive     },
    { "getreusedtimes",     LsLuaSockGetReusedTimes   },
    { NULL, NULL    }
};

static const luaL_Reg sockMetaSub[] =
{
    { "__gc",               LsLuaSockGc               },
    { "__tostring",         LsLuaSockToString         },
    { NULL, NULL    }
};


void LsLuaCreateTcpsockmeta(lua_State *L)
{
    LsLuaApi::openlib(L, LS_LUA ".socket", sockSub, 0);
    LsLuaApi::pushlstring(L, "__metatable", 11);
    LsLuaApi::newmetatable(L, LSLUA_TCPSOCKDATA);
    LsLuaApi::pushlstring(L, "__index", 7);
    LsLuaApi::openlib(L, NULL, sockMetaSub, 0);
    LsLuaApi::rawset(L, -3);
    LsLuaApi::rawset(L, -3);
}

