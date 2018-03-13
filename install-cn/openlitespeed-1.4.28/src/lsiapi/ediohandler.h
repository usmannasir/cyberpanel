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

#ifndef EDIOHANDLER_H
#define EDIOHANDLER_H

#include <lsdef.h>
#include <lsr/ls_edio.h>
#include <edio/eventreactor.h>


class EdioHandler : public ls_edio_s, public EventReactor
{
public:
    EdioHandler(int fd, void *pParam, edio_evt_cb evt_cb,
                edio_timer_cb timer_cb);
    virtual ~EdioHandler();

    virtual int handleEvents(short event);
    virtual void onTimer();

private:

    LS_NO_COPY_ASSIGN(EdioHandler);
};

#endif // EDIOHANDLER_H
