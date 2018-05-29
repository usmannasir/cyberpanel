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
#ifndef ERRORNO_H
#define ERRORNO_H

#include <lsdef.h>

#include <errno.h>


#define ERROR_STR_LEN 128

class ErrorNo
{
private:
    int m_iErrNo;
    char m_achErrStr[ERROR_STR_LEN];
public:
    ErrorNo()
        : m_iErrNo(0)
    {}
    ~ErrorNo()
    {}
    int freezeErrno()
    {   return m_iErrNo = errno;  }
    int getFreezedErrno() const
    {   return m_iErrNo;    }
    int getErrno() const
    {   return errno;     }
    const char *getErrStr();
    const char *getFreezedErrStr();


    LS_NO_COPY_ASSIGN(ErrorNo);
};
#endif
