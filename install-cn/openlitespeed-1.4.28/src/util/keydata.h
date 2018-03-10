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
#ifndef KEYDATA_H
#define KEYDATA_H


#include <util/autostr.h>

class KeyData
{
    AutoStr     m_key;
    KeyData(const KeyData &rhs);
    void operator=(const KeyData &rhs);
public:
    KeyData() {};
    virtual ~KeyData() {};
    const char *getKey() const        {   return m_key.c_str();  }
    void setKey(const char *key)    {   m_key = key;           }
    void setKey(const char *pKey, int len)
    {   m_key.setStr(pKey, len); }



};

#endif
