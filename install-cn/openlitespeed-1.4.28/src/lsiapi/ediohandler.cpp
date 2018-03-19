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

#include "ediohandler.h"

EdioHandler::EdioHandler(int fd, void *pParam, edio_evt_cb evt_cb,
                         edio_timer_cb timer_cb)
{
    ls_edio_s::pParam = pParam;
    ls_edio_s::evtCb = evt_cb;
    ls_edio_s::timerCb = timer_cb;
    setfd(fd);
}


EdioHandler::~EdioHandler()
{

}


int EdioHandler::handleEvents(short event)
{
    if (ls_edio_s::evtCb != NULL)
        return (*ls_edio_s::evtCb)(getfd(), this, event);
    else
    {
        //suspend event
    }
    return 0;
}


void EdioHandler::onTimer()
{
    if (ls_edio_s::timerCb)
        (*ls_edio_s::timerCb)(getfd(), this);
}

