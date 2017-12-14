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
#ifndef _IENV_H_
#define _IENV_H_
#include <string.h>
class IEnv
{
public:
    IEnv() {}
    virtual ~IEnv() {}
    int add(const char *name, const char *value)
    {   return add(name, strlen(name), value, strlen(value)); }
    virtual int add(const char *name, size_t nameLen,
                    const char *value, size_t valLen) = 0;
    virtual void clear() = 0;
};

#define ADD_ENV(a, x, y) if (a->add(x,y) == -1) return -1
#define ADD_ENVL(a, x,xl, y, yl) a->add(x,xl, y, yl);

#endif
