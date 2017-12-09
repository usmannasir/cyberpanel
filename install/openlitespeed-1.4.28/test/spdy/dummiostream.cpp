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
#ifdef RUN_TEST
#include "dummyiostream.h"
#include "unittest-cpp/UnitTest++.h"
DummySpdyConnStream::DummySpdyConnStream()
    : m_pDatabuff(NULL)
    , m_Datalen(0)
{
}
DummySpdyConnStream::DummySpdyConnStream(char *buff, int length)
{
    m_pDatabuff = buff;
    m_Datalen = length;
    //m_InputBuff.append(m_pDatabuff, length);
    SpdyConnection *pConn = new SpdyConnection();
    pConn->attachStream(this);
    pConn->init(HIOS_PROTO_SPDY2);
    onInitConnected();
}

int DummySpdyConnStream::read(char *buf, int len)
{
    if (m_InputBuff.empty())
        return 0;
    *buf = *m_InputBuff.begin();
    m_InputBuff.pop_front(1);
    return 1;
}

int DummySpdyConnStream::write(const char *buf, int len)
{
    return len;
}

int DummySpdyConnStream::onInitConnected()
{
    getHandler()->onInitConnected();
    m_running = 1;
    eventLoop();
    return 0;
}

int DummySpdyConnStream::sendRespHeaders(HttpRespHeaders *pHeaders,
        int isNoBody)
{
    //TODO:
    return -1;
}


int DummySpdyConnStream::eventLoop()
{
    int lenInBuff = 0;
    int length;

    while (m_running)
    {
        if (m_InputBuff.empty())
        {
            length = m_Datalen - lenInBuff;
            if (length == 0)
            {
                m_running = 0;
                continue;
            }
            if (length > 80)
                length = 80;
            m_InputBuff.append(m_pDatabuff + lenInBuff, length);
            lenInBuff += length;

        }
        if (isWantRead() && !m_InputBuff.empty())
            getHandler()->onReadEx();
        if (isWantWrite())
            getHandler()->onWriteEx();

    }
    return 0;
}


#endif
