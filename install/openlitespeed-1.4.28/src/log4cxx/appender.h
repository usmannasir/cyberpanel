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
#ifndef APPENDER_H
#define APPENDER_H



#include <lsdef.h>
#include <log4cxx/nsdefs.h>

#include <util/duplicable.h>

#include <stddef.h>
#include <stdarg.h>
#include <sys/types.h>

BEGIN_LOG4CXX_NS

class LoggingEvent;
class Layout;

class Appender : public Duplicable
{
    friend class ::GFactory;
private:

    Layout *m_pLayout;
    off_t    m_iRollingSize;
    char     m_iAppend;
    char     m_iFlock;
    char     m_iCompress;
    char     m_iRotate;
    int      m_iLastDay;
    int      m_iKeepDays;

protected:
    explicit Appender(const char *pName)
        : Duplicable(pName)
        , m_pLayout(NULL)
        , m_iRollingSize(-1)
        , m_iAppend(1)
        , m_iFlock(0)
        , m_iCompress(0)
        , m_iRotate(1)
        , m_iLastDay(0)
        , m_iKeepDays(0)
    {}

public:
    virtual ~Appender() {};
    static Appender *getAppender(const char *pName);
    static Appender *getAppender(const char *pName, const char *pType);

    const Layout *getLayout() const {   return m_pLayout;   }
    Layout *getLayout()             {   return m_pLayout;   }

    void setLayout(Layout *layout)
    {   m_pLayout = layout;     }
    void setAppendMode(int mode)    {   m_iAppend = mode;   }
    char getAppendMode() const      {   return m_iAppend;   }
    void setFlock(int flock)        {   m_iFlock = flock;   }
    char getFlock() const           {   return m_iFlock;    }

    virtual int getfd() const       {   return -1;          }
    virtual int open()  = 0;
    virtual int close() = 0;
    virtual int reopenExist() = 0;
    virtual int append(const char *pBuf, int len) = 0 ;
    virtual int append(LoggingEvent *pEvent);
    virtual int isFull()            {   return 0;               }
    virtual int isFail()            {   return 0;               }
    virtual int flush()             {   return 0;               }
    void setRollingSize(off_t size) {   m_iRollingSize = size;  }
    off_t getRollingSize() const    {   return m_iRollingSize;  }

    void setCompress(int compress)  {   m_iCompress = compress; }
    char getCompress() const        {   return m_iCompress;     }

    void setKeepDays(int days)      {   m_iKeepDays = days;     }
    int getKeepDays() const         {   return m_iKeepDays;     }

    virtual void setAsync()         {}


    LS_NO_COPY_ASSIGN(Appender);
};

END_LOG4CXX_NS


#endif

