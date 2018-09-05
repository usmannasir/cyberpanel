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
#include <edio/multiplexer.h>
#include <fcntl.h>
#include <poll.h>

Multiplexer::Multiplexer()
    : m_iFLTag(O_NONBLOCK | O_RDWR)
{}

void Multiplexer::continueRead(EventReactor *pHandler)
{   pHandler->orMask2(POLLIN);    }

void Multiplexer::suspendRead(EventReactor *pHandler)
{   pHandler->andMask2(~POLLIN);  }

void Multiplexer::continueWrite(EventReactor *pHandler)
{   pHandler->orMask2(POLLOUT);   }

void Multiplexer::suspendWrite(EventReactor *pHandler)
{   pHandler->andMask2(~POLLOUT); }

void Multiplexer::switchWriteToRead(EventReactor *pHandler)
{   pHandler->setMask2(POLLIN | POLLHUP | POLLERR);   }

void Multiplexer::switchReadToWrite(EventReactor *pHandler)
{   pHandler->setMask2(POLLOUT | POLLHUP | POLLERR);   }

void Multiplexer::modEvent(EventReactor *pHandler, short mask,
                           int add_remove)
{
    if (add_remove)
        pHandler->orMask2(mask);
    else
        pHandler->andMask2(~mask);
}


