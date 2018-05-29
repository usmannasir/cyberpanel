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
#ifndef FILECNTL_H
#define FILECNTL_H

#include <unistd.h>
#include <fcntl.h>



class FileCntl
{
private:
    FileCntl() {};
    ~FileCntl() {};
public:
    static  int     fcntl(int fd, int cmd)
    {   return ::fcntl(fd, cmd);   }

    static  int     fcntl(int fd, int cmd, int arg)
    {   return ::fcntl(fd, cmd, arg);  }

    static  int     fcntl(int fd, int cmd, long arg)
    {   return ::fcntl(fd, cmd, arg);  }

    static  int     fcntl(int fd, int cmd, struct flock *lock)
    {   return ::fcntl(fd, cmd, lock); }

    static  int     setNonBlock(int fd, int nonblock = 1)
    {
        int val = fcntl(fd, F_GETFL, 0);
        if (nonblock)
            return fcntl(fd, F_SETFL, val | O_NONBLOCK);
        else
            return fcntl(fd, F_SETFL, val & (~O_NONBLOCK));
    }

    static int      isSet(int fd, int arg)
    {
        int val = fcntl(fd, F_GETFL, 0);
        return (val != -1)
               ? ((val & arg) == arg)
               : val;
    }
};

#endif
