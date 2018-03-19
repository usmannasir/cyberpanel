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
#ifndef LOGROTATE_H
#define LOGROTATE_H


#include <lsdef.h>
#include <log4cxx/nsdefs.h>
#include <sys/types.h>

BEGIN_LOG4CXX_NS

class Appender;
class LogRotate
{
public:
    LogRotate();
    ~LogRotate();
    static int roll(Appender *pAppender, uid_t uid, gid_t gid,
                    off_t rollingSize);
    static int testRolling(Appender *pAppender, off_t rollingSize, uid_t uid,
                           gid_t gid);
    static int postRotate(Appender *pAppender, uid_t uid, gid_t gid);

    static int testAndRoll(Appender *pAppender, uid_t uid, gid_t gid);
    static int testRolling(Appender *pAppender, uid_t uid, gid_t gid);




    LS_NO_COPY_ASSIGN(LogRotate);
};

END_LOG4CXX_NS

#endif
