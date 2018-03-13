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
#ifndef LEVEL_H
#define LEVEL_H


#include <lsdef.h>
#include <log4cxx/nsdefs.h>

BEGIN_LOG4CXX_NS

class Level
{
    static const char  *s_levelName[];
    static int          s_iDefaultLevel;
    Level() {};
    ~Level() {};
public:
    enum
    {
        FATAL = 0,
        ALERT = 1000,
        CRIT  = 2000,
        ERROR = 3000,
        WARN  = 4000,
        NOTICE = 5000,
        INFO  = 6000,
        DEBUG = 7000,
        DBG_LESS = 7020,
        DBG_LOW  = 7020,
        DBG_MEDIUM = 7050,
        DBG_MORE = 7080,
        DBG_HIGH = 7080,
        DBG_IODATA = 7090,
        TRACE = 8000,
        NOTSET = 9000,
        UNKNOWN = 10000
    };

    static const char *toString(int level)
    {   return s_levelName[ level / 1000 ]; }
    static int toInt(const char *levelName);
    static int getSysLogInt(int level)
    {   return level / 1000; }

    ls_attr_inline static int isEnabled(int level)
    {   return level <= s_iDefaultLevel;   }

    static void setDefaultLevel(int level)
    {   s_iDefaultLevel = level;        }
    
    static const int *getDefaultLevelPtr() 
    {   return &s_iDefaultLevel;    }

    LS_NO_COPY_ASSIGN(Level);
};

END_LOG4CXX_NS

#endif
