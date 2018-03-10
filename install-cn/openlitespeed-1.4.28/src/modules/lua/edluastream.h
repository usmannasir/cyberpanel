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
#ifndef EDLUASTREAM_H
#define EDLUASTREAM_H

#include <edio/ediostream.h>
#include <util/loopbuf.h>

#include <inttypes.h>

enum
{
    EDLUA_FLAG_NONE         = 0,
    EDLUA_FLAG_LOOKUP       = 1,
    EDLUA_FLAG_CONNECTING   = 2,
    EDLUA_FLAG_RECV         = 4,
    EDLUA_FLAG_SEND         = 8,
    EDLUA_FLAG_CONNECTED    = 16,
    EDLUA_FLAG_RECYCLE      = 32
};


struct lua_State;
class EdLuaStream : public EdStream
{
public:
    EdLuaStream();
    ~EdLuaStream();
    int onInitialConnected();
    virtual int onEventDone();
    virtual int onError();
    virtual int onWrite();
    virtual int onRead();
    virtual void onTimer();
    int connectTo(lua_State *L, const char *pAddr, uint16_t port);
    int send(lua_State *L, const char *pBuf, int32_t iLen);
    int recv(lua_State *L, int32_t len);
    int closeSock(lua_State *L);
    int setTimout(int32_t timeout)
    {
        m_iTimeoutMs = timeout;
        return 0;
    }
    void recycle()
    {   m_iFlag |= EDLUA_FLAG_RECYCLE;  }

    // shutdown the connection regradless
    int forceClose(lua_State *L);

private:
    EdLuaStream(const EdLuaStream &other);
    EdLuaStream &operator=(const EdLuaStream &other);
    bool operator==(const EdLuaStream &other);
    int processInputBuf(lua_State *L);
    int doRead(lua_State *L);
    int resume(lua_State *&L, int nArg);
    int resumeWithError(lua_State *&L, int flag, int errcode);
    int doWrite(lua_State *L);
private:
    lua_State  *m_pRecvState;
    lua_State  *m_pSendState;
    LoopBuf     m_bufOut;
    LoopBuf     m_bufIn;
    int32_t     m_iFlag;
    int32_t     m_iCurInPos;
    int32_t     m_iToRead;
    int32_t     m_iToSend;
    int32_t     m_iTimeoutMs;
    int32_t     m_iReusedTimes;

    int64_t     m_iRecvTimeout;
    int64_t     m_iSendTimeout;
};

void LsLuaCreateTcpsockmeta(lua_State *L);

#endif // EDLUASTREAM_H
