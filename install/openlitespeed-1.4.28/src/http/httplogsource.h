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
#ifndef HTTPLOGSOURCE_H
#define HTTPLOGSOURCE_H

#include <lsdef.h>
#include <sys/types.h>

class AccessLog;
class AutoStr;
class ConfigCtx;
class XmlNode;


class HttpLogSource
{
private:
    static AutoStr  s_sDefaultAccessLogFormat;
    static short    s_iAioServerAccessLog;
    static short    s_iAioServerErrorLog;
protected:
    short m_iAioAccessLog;
    short m_iAioErrorLog;
public:
    HttpLogSource()
        : m_iAioAccessLog(-1)
        , m_iAioErrorLog(-1)
    {};
    virtual ~HttpLogSource() {};

    virtual void setLogLevel(const char *pLevel) = 0;
    virtual int setAccessLogFile(const char *pFileName, int pipe) = 0;
    virtual int setErrorLogFile(const char *pFileName) = 0;
    virtual void setErrorLogRollingSize(off_t size, int keep_days) = 0;
    virtual void setBytesLogFilePath(const char *pFileName,
                                     off_t rollingSize) {}
    virtual void enableAccessLog(int size) {}
    virtual AccessLog *getAccessLog() const = 0;
    virtual void enableAioLogging() = 0;
    int initAccessLog(const XmlNode *pNode,
                      off_t *pRollingSize);
    int initAccessLog(const XmlNode *pRoot,
                      int setDebugLevel);
    int initErrorLog2(const XmlNode *pNode,
                      int setDebugLevel);
    int initErrorLog(const XmlNode *pRoot,
                     int setDebugLevel);
    int initAllLog(const char *pRoot);

    static void setAioServerAccessLog(short val)
    {   s_iAioServerAccessLog = val;    }
    static int getAioServerAccessLog()
    {   return s_iAioServerAccessLog;   }
    static void setAioServerErrorLog(short val)
    {   s_iAioServerErrorLog = val;    }
    static int getAioServerErrorLog()
    {   return s_iAioServerErrorLog;   }

    LS_NO_COPY_ASSIGN(HttpLogSource);
};

#endif
