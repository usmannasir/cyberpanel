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
#ifndef LAYOUT_H
#define LAYOUT_H



#include <lsdef.h>
#include <log4cxx/nsdefs.h>
#include <util/duplicable.h>
#include <stddef.h>
#include <stdarg.h>


BEGIN_LOG4CXX_NS

class LoggingEvent;
class Layout : public Duplicable
{
    void    *m_pUserData;
protected:
    Layout(const char *pName)
        : Duplicable(pName)
        , m_pUserData(NULL)
    {};
public:
    virtual ~Layout() {};
    static int init();
    static Layout *getLayout(const char *pName, const char *pType);
    void setUData(void *udata)
    {   m_pUserData = udata;    }
    void *getUData() const
    {   return m_pUserData;     }
    virtual Duplicable *dup(const char *pName);
    virtual int format(LoggingEvent *pEvent, char *pBuf, int len);



    LS_NO_COPY_ASSIGN(Layout);
};

END_LOG4CXX_NS

#endif
