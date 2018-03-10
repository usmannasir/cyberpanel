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
#ifndef MUTLIPLEXERFACTORY_H
#define MUTLIPLEXERFACTORY_H


#include <lsdef.h>
#include <util/tsingleton.h>

class Multiplexer;
class MultiplexerFactory
{
    friend class TSingleton< MultiplexerFactory >;
    MultiplexerFactory();
    ~MultiplexerFactory();

    static int          s_iMaxFds;
    static Multiplexer *s_pMultiplexer;

public:
    static int          s_iMultiplexerType;

    enum
    {
        POLL,
        SELECT,
        DEV_POLL,
        KQUEUE,
        RT_SIG,
        EPOLL,
        BEST
    };
    static int getType(const char *pType);
    static Multiplexer *getNew(int type);
    static void recycle(Multiplexer *ptr);

    static Multiplexer *getMultiplexer()
    {   return s_pMultiplexer;  }
    static void setMultiplexer(Multiplexer *pMultiplexer)
    {   s_pMultiplexer = pMultiplexer;  }
    LS_NO_COPY_ASSIGN(MultiplexerFactory);
};

#endif
