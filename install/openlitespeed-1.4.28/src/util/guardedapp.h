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
#ifndef GUARDEDAPP_H
#define GUARDEDAPP_H



#include <sys/types.h>

class GuardedApp
{
public:
    GuardedApp() {};
    virtual ~GuardedApp() {};
    virtual int forkTooFreq()   {   return 0;   }
    virtual int preFork()       {   return 0;   }
    virtual int forkError(int err)    {   return 0;   }
    virtual int postFork(pid_t pid)     {   return 0;   }
    virtual int childExit(pid_t pid, int stat)   {   return 0;   }
    virtual int childSignaled(pid_t pid, int signal, int coredump)
    {   return 0;   }
    virtual int cleanUp(pid_t pid, char *pBB)       {   return 0;   }
    virtual void onGuardTimer() {}
};

#endif
