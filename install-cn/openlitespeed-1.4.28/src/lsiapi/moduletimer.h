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
#ifndef MODULETIMER_H
#define MODULETIMER_H

#include <util/ghash.h>
#include <util/gmap.h>
#include <util/objpool.h>
#include <util/tsingleton.h>

#include <ls.h>


class ModTimer;
class ModTimerList : public TSingleton<ModTimerList>
{
    friend class TSingleton<ModTimerList>;

    int                 m_iTimerIds;
    GMap                m_timerMap;
    GHash               m_timerHash;
    ObjPool<ModTimer>   m_timerPool;

    static void timerCleanup(const void *notused);
    static void initCleanup();

    void operator=(const ModTimerList &);
    ModTimerList(const ModTimerList &);
    ModTimerList();
    ~ModTimerList();
public:

    int addTimer(unsigned int timeout_ms, int repeat,
                 lsi_timercb_pf timer_cb, const void *timer_cb_param);
    int removeTimer(int iId);

    int checkExpired();
};



#endif // MODULETIMER_H
