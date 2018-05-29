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
#ifndef LOGSESSION_H
#define LOGSESSION_H



#include <lsdef.h>
#include <log4cxx/nsdefs.h>
#include <util/autostr.h>

#define MAX_LOGID_LEN   127

BEGIN_LOG4CXX_NS
class Logger;
END_LOG4CXX_NS

class LogSession
{
    AutoStr2            m_logId;
    LOG4CXX_NS::Logger *m_pLogger;

public:
    LogSession();
    ~LogSession();

    AutoStr2 &getIdBuf()             {   return m_logId;     }
    //const char * getLogId() const
    //{
    //return m_logID.c_str();  }
    const char *getLogId()
    {
        if (isLogIdBuilt())
            return m_logId.c_str();
        return buildLogId();
    }

    LOG4CXX_NS::Logger *getLogger() const   {   return m_pLogger;   }
    void setLogger(LOG4CXX_NS::Logger *pLogger)
    {   m_pLogger = pLogger;    }

    void clearLogId()     {   *m_logId.buf() = 0;      }
    int  isLogIdBuilt() const       {   return *m_logId.c_str() != '\0';   }
    virtual const char *buildLogId() = 0;



    LS_NO_COPY_ASSIGN(LogSession);
};

#endif
