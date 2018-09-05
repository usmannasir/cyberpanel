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
#ifndef APPENDERMANAGER_H
#define APPENDERMANAGER_H


#include <lsdef.h>
#include <log4cxx/nsdefs.h>
#include <util/gpointerlist.h>

BEGIN_LOG4CXX_NS

class Appender;

class AppenderManager
{
    TPointerList<Appender>  m_appenders;
    Appender               *m_pCurAppender;
    int                     m_curAppender;
    int                     m_strategy;

    Appender *getNextAppender();
    Appender *findAppender(Appender *pExcept);

public:
    enum
    {
        AM_TILLFULL,
        AM_TILLFAIL,
        AM_RROBIN

    };
    AppenderManager();

    ~AppenderManager();
    void addAppender(Appender *p);
    Appender *getAppender();

    void setStrategy(int st)      {   m_strategy = st;    }
    void releaseAppenders();


    LS_NO_COPY_ASSIGN(AppenderManager);
};


END_LOG4CXX_NS

#endif
