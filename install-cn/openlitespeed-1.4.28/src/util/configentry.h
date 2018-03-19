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
#ifndef CONFIGENTRY_H
#define CONFIGENTRY_H

#include <util/autostr.h>
#include <inttypes.h>
/*
class ConfigValidator
{
public:
    ConfigValidator( long long min, long long max, long long def )
    {}
    int operator()(long long val )const
    { return 0; }
};

class ConfigIntValidation
{
    long long m_iDefault;
    long long m_iMin;
    long long m_iMax;
};
*/

class ConfigEntry
{

public:
    ConfigEntry();
    ~ConfigEntry();

public:
    enum
    {
        NUMERIC,
        STRING,
        PATH,
        FILE,
        VALID_PATH,
        VALID_FILE,

    };

private:
    ConfigEntry &operator=(const ConfigEntry &other);
    ConfigEntry(const ConfigEntry &other);

private:
    AutoStr     m_name;
    //short       m_iValueType;
    //short       m_iOptinal;
    //long long   m_iDefault;
    //long long   m_iMin;
    //long long   m_iMax;
    AutoStr     m_regexValidate;


};

#endif // CONFIGENTRY_H
