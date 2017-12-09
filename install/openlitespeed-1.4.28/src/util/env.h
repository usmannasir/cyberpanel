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
#ifndef ENV_H
#define ENV_H


#include <lsdef.h>
#include <util/ienv.h>
#include <util/gpointerlist.h>

class ArrayOfPointer : public TPointerList<char>
{
public:
    ArrayOfPointer() {}
    ArrayOfPointer(int initSize): TPointerList<char>(initSize) {}
    ~ArrayOfPointer()
    {   clear();    }
    void clear();
};

class Env : public IEnv, public ArrayOfPointer
{
public:
    Env() {};
    Env(int initSize): ArrayOfPointer(initSize) {}
    ~Env() {};
    int add(const char *name, const char *value)
    {   return IEnv::add(name, value); }
    int add(const char *name, size_t nameLen,
            const char *value, size_t valLen);
    int add(const char *pEnv);
    int add(const Env *pEnv);
    const char *find(const char *name) const;
    void clear()    { ArrayOfPointer::clear();  }
    char *const *get() const
    {   return &((*this)[0]);   }
    char **get()
    {   return &((*this)[0]);   }
    int update(const char *name, const char *value);


    LS_NO_COPY_ASSIGN(Env);
};


#endif
