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
#include "httpresourcemanager.h"

#include <edio/aioeventhandler.h>
#include <edio/aiosendfile.h>
#include <http/chunkinputstream.h>
#include <http/chunkoutputstream.h>
#include <http/httpsession.h>
#include <http/ntwkiolink.h>
#include <lsiapi/modulemanager.h>
#include <util/vmembuf.h>
#include <util/gzipbuf.h>


char HttpResourceManager::g_aBuf[GLOBAL_BUF_SIZE + 8];

HttpResourceManager::HttpResourceManager()
    : m_poolChunkInputStream(0, 10)
    , m_poolChunkOutputStream(10, 10)
    , m_poolVMemBuf(0, 10)
    , m_poolGzipBuf(0, 10)
    , m_poolHttpSession(20, 20)
    , m_poolNtwkIoLink(20, 20)
    , m_pPoolAiosfcb(NULL)
{
}


HttpResourceManager::~HttpResourceManager()
{
}


int HttpResourceManager::initAiosfcbPool()
{
#ifdef LS_AIO_USE_AIO
    m_pPoolAiosfcb = new AiosfcbPool(10, 10);
    return LS_OK;
#else
    return LS_FAIL;
#endif
}


void HttpResourceManager::releaseAll()
{
    m_poolChunkInputStream.shrinkTo(0);
    m_poolChunkOutputStream.shrinkTo(0);
    m_poolVMemBuf.shrinkTo(0);
    m_poolGzipBuf.shrinkTo(0);
    m_poolHttpSession.shrinkTo(0);
    m_poolNtwkIoLink.shrinkTo(0);
    if (m_pPoolAiosfcb != NULL)
        m_pPoolAiosfcb->shrinkTo(0);
}


static int reduceBuf(void *pObj, void *size)
{
    ((VMemBuf *)pObj)->shrinkBuf((long) size);
    //((VMemBuf *)pObj)->resizeFile( (long) size );
    return 0;
}


void HttpResourceManager::onTimer()
{
    m_poolVMemBuf.shrinkTo(20);
    m_poolVMemBuf.applyAll(reduceBuf, (void *)16384);
    //m_poolChunkInputStream( 20 );
    //m_poolChunkOutputStream( 20 );

    m_poolHttpSession.shrinkTo(20);
    m_poolNtwkIoLink.shrinkTo(20);
    if (m_pPoolAiosfcb != NULL)
        m_pPoolAiosfcb->shrinkTo(20);

    //Call module manger timer to check and release some resource
    ModuleManager::getInstance().OnTimer10sec();
}


