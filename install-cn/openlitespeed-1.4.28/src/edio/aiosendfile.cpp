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
#include <edio/aiosendfile.h>
#include <log4cxx/logger.h>
#include <lsr/ls_lfqueue.h>
#include <util/gsendfile.h>


Aiosfcb *Aiosfcb::getCbPtr(ls_lfnodei_t *pNode)
{
    return (Aiosfcb *)((char *)pNode - offsetof(Aiosfcb, m_node));
}


void *AioSendFile::aioSendFile(ls_lfnodei_t *item)
{
    Aiosfcb *cb = Aiosfcb::getCbPtr(item);
    if (cb->getFlag(AIOSFCB_FLAG_CANCEL))
    {
        LS_DBG_H("AioSendFile::aioSendFile(), Job Cancelled!");
        cb->setRet(0);
    }
    else
    {
        off_t iOff = cb->getOffset();
#if !defined( NO_SENDFILE )
        cb->setRet(gsendfile(cb->getSendFd(), cb->getReadFd(),
                             &iOff, cb->getSize()));
#else
        LS_DBG_H("AioSendFile::aioSendFile(), No SendFile!");
        cb->setRet(-1);
#endif
        cb->setOffset(iOff);
    }
    return NULL;
}


AioSendFile::AioSendFile()
    : m_wc(this)
{
    m_pFinishedQueue = ls_lfqueue_new();
}


AioSendFile::~AioSendFile()
{
    m_wc.stopProcessing();
    ls_lfqueue_delete(m_pFinishedQueue);
}


int AioSendFile::onNotified(int count)
{
    int i;
    Aiosfcb *event;
    for (i = 0; i < count; ++i)
    {
        event = Aiosfcb::getCbPtr(ls_lfqueue_get(m_pFinishedQueue));
        if (!event)
        {
            LS_DBG_H("AioSendFile::onNotified(), Bad Event Object Returned!");
            return LS_FAIL;
        }
        processEvent(event);
    }
    return LS_OK;
}

