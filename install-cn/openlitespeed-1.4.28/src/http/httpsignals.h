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
#ifndef HTTPSIGNALS_H
#define HTTPSIGNALS_H

#include <lsdef.h>
#include <util/signalutil.h>

enum
{
    HS_CHILD = 1,
    HS_ALARM = 2,
    HS_STOP = 4,
    HS_HUP = 8,
    HS_USR1 = 16,
    HS_USR2 = 32
};

class HttpSignals
{
    static int s_iEvents;

    HttpSignals();
    ~HttpSignals();
public:

    static int  gotEvent()      {   return s_iEvents;       }
    static void resetEvents()   {   s_iEvents = 0;          }

    static void resetSigChild() {   s_iEvents &= ~HS_CHILD; }
    static void resetSigAlarm() {   s_iEvents &= ~HS_ALARM; }
    static void setSigStop()    {   s_iEvents |= HS_STOP;   }

    static int  gotSigAlarm()   {   return s_iEvents & HS_ALARM;    }
    static int  gotSigChild()   {   return s_iEvents & HS_CHILD;    }
    static int  gotSigStop()    {   return s_iEvents & HS_STOP;     }
    static int  gotSigHup()     {   return s_iEvents & HS_HUP;      }
    static int  gotSigUsr1()    {   return s_iEvents & HS_USR1;     }
    static int  gotSigUsr2()    {   return s_iEvents & HS_USR2;     }

    static void orEvent(int event);

    static void init(sighandler_t sigchild);

    LS_NO_COPY_ASSIGN(HttpSignals);
};

#endif
