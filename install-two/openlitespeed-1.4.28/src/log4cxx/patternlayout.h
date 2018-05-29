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
#ifndef PATTERNLAYOUT_H
#define PATTERNLAYOUT_H

#include <lsdef.h>
#include <log4cxx/layout.h>
#include <log4cxx/nsdefs.h>
#include <stdarg.h>

struct timeval;

BEGIN_LOG4CXX_NS


class PatternLayout : public Layout
{
    static struct timeval s_startTime;
    PatternLayout(const char *pName)
        : Layout(pName)
    {}
public:
    ~PatternLayout() {}
    static int init();
    virtual Duplicable *dup(const char *pName);
    virtual int format(LoggingEvent *pEvent, char *pBuf, int len);


    LS_NO_COPY_ASSIGN(PatternLayout);
};

END_LOG4CXX_NS

#endif
