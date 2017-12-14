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
#include "level.h"

#include <string.h>

BEGIN_LOG4CXX_NS

const char *Level::s_levelName[] =
{
    "FATAL",
    "ALERT",
    "CRIT",
    "ERROR",
    "WARN",
    "NOTICE",
    "INFO",
    "DEBUG",
    "TRACE",
    "NOTSET",
    "UNKNOWN"
};


int Level::toInt(const char *levelName)
{
    if (levelName)
    {
        for (int i = 0; i < UNKNOWN / 1000; ++i)
        {
            if (!strcasecmp(s_levelName[i], levelName))
                return i * 1000;
        }
    }
    return UNKNOWN;
}

int Level::s_iDefaultLevel = Level::DEBUG;

END_LOG4CXX_NS

