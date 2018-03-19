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
#ifndef HTTPLOG_H
#define HTTPLOG_H



#include <lsdef.h>
#include <log4cxx/nsdefs.h>

#include <stdarg.h>
#include <sys/types.h>


BEGIN_LOG4CXX_NS
class Logger;
END_LOG4CXX_NS

class AccessLog;
class HttpSession;

enum
{
    DL_DISABLE = 0,
    DL_LESS   = 2,
    DL_MEDIUM = 5,
    DL_MORE   = 8,
    DL_EVENT  = 5,
    DL_FTRACE = 8,
    DL_IODATA = 9
};

#define ERROR_LOG_PATTERN "patternErrLog"

class HttpLog
{
    static int  s_debugLevel;
    HttpLog();
    ~HttpLog();
public:
    static void init();
    static int logAccess(const char *pVHost, int len, HttpSession *pSession);
    static void error_num(int __errnum, const char *__file,
                          unsigned int __line, const char *__function);
    static void error_detail(const char *__errstr, const char *__file,
                             unsigned int __line, const char *__function);
    static void vlog(int level, const char *format, va_list args);
    static void log(int level, const char *fmt, ...);
    static void error(const char *fmt, ...);
    static void warn(const char *fmt, ...);
    static void notice(const char *fmt, ...);
    static void info(const char *fmt, ...);
    static void debug(const char *fmt, ...);

    static void errmem(const char *pSource);

    static void vlog(LOG4CXX_NS::Logger *pLogger, int level,
                     const char *format, va_list args, int no_linefeed);
    static void lograw(LOG4CXX_NS::Logger *pLogger, const char *pBuf, int len);
    static void log(LOG4CXX_NS::Logger *pLogger, int level,
                    const char *fmt, ...);
    static void error(LOG4CXX_NS::Logger *pLogger, const char *fmt, ...);
    static void warn(LOG4CXX_NS::Logger *pLogger, const char *fmt, ...);
    static void notice(LOG4CXX_NS::Logger *pLogger, const char *fmt, ...);
    static void info(LOG4CXX_NS::Logger *pLogger, const char *fmt, ...);
    static void debug(LOG4CXX_NS::Logger *pLogger, const char *fmt, ...);
    static bool isEnabled(LOG4CXX_NS::Logger *pLogger, int level);
    static inline bool isDebugEnabled(int level)
    {  return (level <= s_debugLevel);   }
    static bool isDebugEnabled(LOG4CXX_NS::Logger *pLogger, int level);
    static int  getDebugLevel()     {   return s_debugLevel;    }
    static void setDebugLevel(int level);
    static void toggleDebugLog();

    static void setLogLevel(int level);
    static void setLogLevel(const char *pLevel);
    static void setLogPattern(const char *pPattern);
    static const char *getLogPattern();

    static int setAccessLogFile(const char *pFileName, int pipe);
    static int setErrorLogFile(const char *pFileName);
    static void offsetChroot(const char *pRoot, int len);
    static const char *getAccessLogFileName();
    static const char *getErrorLogFileName();
    static AccessLog *getAccessLog();
    static LOG4CXX_NS::Logger *getErrorLogger();
    static void onTimer();

    static void perror(const char *pStr, const char *pError);
    static void setCurLogger(LOG4CXX_NS::Logger *pLogger, const char *pId);
    static void parse_error(const char *pCurLine, const char *pError);

    LS_NO_COPY_ASSIGN(HttpLog);
};

//class LogTracker
//{
//    GString             m_logID;
//    LOG4CXX_NS::Logger* m_pLogger;
//
//};

#define ERR_NO_MEM( errstr ) \
    ( HttpLog::errmem( errstr ) )


#define LOG_ERR_CODE( errnum ) \
    ( HttpLog::error_num( errnum, __FILE__, __LINE__, \
                          __PRETTY_FUNCTION__))
#define LOG_DERR( errstr ) \
    ( HttpLog::error_detail( errstr, __FILE__, __LINE__, __PRETTY_FUNCTION__))

/* Call LOG_ERR(("format string...", arg, arg, ...)) to log an event */
/* Note the double parentheses! */
//*
#define LOG(s) \
    HttpLog::log s

#define LOG_ERR(s) \
    HttpLog::error s

//#define LOG_D(...) HttpLog::debug( __VA_ARGS__ )

#define LOG_D(s) \
    HttpLog::debug s

#define LOG_INFO(s) \
    HttpLog::info s

#define LOG_WARN(s) \
    HttpLog::warn s

#define LOG_NOTICE(s) \
    HttpLog::notice s

/*/
#define LOG(s)

#define LOG_ERR(s)

#define LOG_D(s)

#define LOG_INFO(s)

#define LOG_WARN(s)

#define LOG_NOTICE(s)

// */

#define LOG_ENABLED( logger, level ) HttpLog::isEnabled( logger, level )
#define D_ENABLED( level ) HttpLog::isDebugEnabled( level )


extern int archiveFile(const char *pFileName, const char *pSuffix,
                       int compress, uid_t uid, gid_t gid);

#endif

