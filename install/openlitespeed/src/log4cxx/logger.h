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
#ifndef LOGGER_H
#define LOGGER_H



#include <stdarg.h>

#include <lsdef.h>
#include <log4cxx/nsdefs.h>
#include <log4cxx/level.h>
#include <util/duplicable.h>
#include <sys/uio.h>

#define ROOT_LOGGER_NAME "__root"


#define __logger_log( level, format ) \
    do { \
        if ( isEnabled( level ) ) { \
            va_list  va; va_start( va, format ); \
            vlog( level, format, va ); \
            va_end( va ); \
        } \
    }while(0)

/*
#define ___log( level, ... ) \
{ \
    log4cxx::Logger *l = log4cxx::Logger::getDefault(); \
    if (l->isEnabled( level )) \
        l->log2( level, __VA_ARGS__ ); \
}

#define LS_NOTICE2( ... ) \
       ___log( log4cxx::Level::NOTICE, __VA_ARGS__)
*/

#define LS_LOG_ENABLED(level) log4cxx::Level::isEnabled( level )
#define LS_LOG(level, ...) log4cxx::Logger::s_log( level, __VA_ARGS__);

#define LS_LOGRAW(...) log4cxx::Logger::s_lograw( __VA_ARGS__);

#define LS_DBG_IO( ... ) \
    do { \
        if ( log4cxx::Level::isEnabled( log4cxx::Level::DBG_IODATA ) ) \
            log4cxx::Logger::s_log( log4cxx::Level::DBG_IODATA, __VA_ARGS__); \
    }while(0)

#define LS_DBG_H( ... ) \
    do { \
        if ( log4cxx::Level::isEnabled( log4cxx::Level::DBG_HIGH ) ) \
            log4cxx::Logger::s_log( log4cxx::Level::DBG_HIGH, __VA_ARGS__); \
    }while(0)

#define LS_DBG_M( ... ) \
    do { \
        if ( log4cxx::Level::isEnabled( log4cxx::Level::DBG_MEDIUM ) ) \
            log4cxx::Logger::s_log(  log4cxx::Level::DBG_MEDIUM, __VA_ARGS__); \
    }while(0)

#define LS_DBG_L( ... ) \
    do { \
        if ( log4cxx::Level::isEnabled( log4cxx::Level::DBG_LESS ) ) \
            log4cxx::Logger::s_log( log4cxx::Level::DBG_LESS, __VA_ARGS__); \
    }while(0)

#define LS_DBG( ... ) \
    do { \
        if ( log4cxx::Level::isEnabled( log4cxx::Level::DEBUG ) ) \
            log4cxx::Logger::s_log( log4cxx::Level::DEBUG, __VA_ARGS__); \
    }while(0)


#define LS_INFO( ... ) \
    do { \
        if ( log4cxx::Level::isEnabled( log4cxx::Level::INFO ) ) \
            log4cxx::Logger::s_log( log4cxx::Level::INFO, __VA_ARGS__); \
    }while(0)

#define LS_NOTICE( ... ) \
    do { \
        if ( log4cxx::Level::isEnabled( log4cxx::Level::NOTICE ) ) \
            log4cxx::Logger::s_log( log4cxx::Level::NOTICE, __VA_ARGS__); \
    }while(0)

#define LS_WARN( ... ) \
    do { \
        if ( log4cxx::Level::isEnabled( log4cxx::Level::WARN ) ) \
            log4cxx::Logger::s_log( log4cxx::Level::WARN, __VA_ARGS__); \
    }while(0)

#define LS_ERROR( ... ) \
    do { \
        if ( log4cxx::Level::isEnabled( log4cxx::Level::ERROR ) ) \
            log4cxx::Logger::s_log( log4cxx::Level::ERROR, __VA_ARGS__); \
    }while(0)

#define LS_CRIT( ... ) \
    do { \
        if ( log4cxx::Level::isEnabled( log4cxx::Level::CRIT ) ) \
            log4cxx::Logger::s_log( log4cxx::Level::CRIT, __VA_ARGS__); \
    }while(0)

#define LS_FATAL( ... ) \
    do { \
        if ( log4cxx::Level::isEnabled( log4cxx::Level::FATAL ) ) \
            log4cxx::Logger::s_log( log4cxx::Level::FATAL, __VA_ARGS__); \
    }while(0)

#define LS_ERR_NO_MEM( msg ) \
    ( LOG4CXX_NS::Logger::errmem( msg ) )

class TmpLogId;
class LogSession;

BEGIN_LOG4CXX_NS

class Appender;
class Layout;
class ILog;

class Logger : public Duplicable
{
    int         m_iLevel;
    int         m_iAdditive;
    Appender   *m_pAppender;
    Layout     *m_pLayout;
    Logger     *m_pParent;

    static Logger *s_pDefault;

protected:
    explicit Logger(const char *pName);
    Duplicable *dup(const char *pName);

public:
    ~Logger() {};
    static void init();

    static Logger *getRootLogger()
    {   return getLogger(ROOT_LOGGER_NAME); }

    ls_attr_inline static Logger *getDefault()
    {
        if (!s_pDefault)
            s_pDefault = getLogger(NULL);
        return s_pDefault;
    }

    static void setDefault(Logger *pDefault)
    {   s_pDefault = pDefault;      }

    static Logger *getLogger(const char *pName);

    void vlog(int level, const char *format, va_list args,
              int no_linefeed = 0)
    {
        vlog(level, NULL, format, args, no_linefeed);
    }

    void vlog(int level, const char *pId, const char *format, va_list args,
              int no_linefeed);

    void log2(int level, const char *format, ...)
    {
        va_list  va;
        va_start(va, format);
        vlog(level, format, va);
        va_end(va);
    }


    void log(int level, const char *format, ...)
    {
        if (isEnabled(level))
        {
            va_list  va;
            va_start(va, format);
            vlog(level, format, va);
            va_end(va);
        }
    }

    ls_attr_inline void vdebug(const char *format, va_list args)
    {
        vlog(Level::DEBUG, format, args);
    }

    void debug(const char *format, ...)
    {
        __logger_log(Level::DEBUG, format);
    }

    ls_attr_inline void vtrace(const char *format, va_list args)
    {
        vlog(Level::TRACE, format, args);
    }

    void trace(const char *format, ...)
    {
        __logger_log(Level::TRACE, format);
    }

    ls_attr_inline void vinfo(const char *format, va_list args)
    {
        vlog(Level::INFO, format, args);
    }

    void info(const char *format, ...)
    {
        __logger_log(Level::INFO, format);
    }

    ls_attr_inline void vnotice(const char *format, va_list args)
    {
        vlog(Level::NOTICE, format, args);
    }

    void notice(const char *format, ...)
    {
        __logger_log(Level::NOTICE, format);
    }

    ls_attr_inline void vwarn(const char *format, va_list args)
    {
        vlog(Level::WARN, format, args);
    }

    void warn(const char *format, ...)
    {
        __logger_log(Level::WARN, format);
    }

    ls_attr_inline void verror(const char *format, va_list args)
    {
        vlog(Level::ERROR, format, args);
    }

    void error(const char *format, ...)
    {
        __logger_log(Level::ERROR, format);
    }

    ls_attr_inline void vfatal(const char *format, va_list args)
    {
        vlog(Level::FATAL, format, args);
    }

    void fatal(const char *format, ...)
    {
        __logger_log(Level::FATAL, format);
    }

    ls_attr_inline void valert(const char *format, va_list args)
    {
        vlog(Level::ALERT, format, args);
    }

    void alert(const char *format, ...)
    {
        __logger_log(Level::ALERT, format);
    }

    ls_attr_inline void vcrit(const char *format, va_list args)
    {
        vlog(Level::CRIT, format, args);
    }

    void crit(const char *format, ...)
    {
        __logger_log(Level::CRIT, format);
    }

    void lograw(const char *pBuf, int len);
    
    void lograw(const struct iovec *pIov, int size);

    ls_attr_inline int isEnabled(int level) const
    {   return level <= m_iLevel; }

    ls_attr_inline int getLevel() const
    {   return m_iLevel;  }

    void setLevel(int level)
    {   m_iLevel = level;  }

    void setLevel(const char *pLevel)
    {   setLevel(Level::toInt(pLevel)); }

    ls_attr_inline int getAdditivity() const
    {   return m_iAdditive;  }

    void setAdditivity(int additive)
    {   m_iAdditive = additive;   }

    ls_attr_inline Appender *getAppender()
    {   return m_pAppender;  }
    void setAppender(Appender *pAppender)
    {   m_pAppender = pAppender;    }

    ls_attr_inline const Layout *getLaout() const
    {   return m_pLayout;  }
    void setLayout(Layout *pLayout)
    {   m_pLayout = pLayout;    }

    void setParent(Logger *pParent)    {   m_pParent = pParent;    }

    static void errmem(const char *pSource)
    {   LS_ERROR("Out of memory: %s", pSource); }

    static void s_log(int level, log4cxx::Logger *logger,
                      const char *format, ...)
#if __GNUC__
        __attribute__((format(printf, 3, 4)))
#endif
        ;

    static void s_log(int level, log4cxx::ILog *pILog,
                      const char *format, ...)
#if __GNUC__
        __attribute__((format(printf, 3, 4)))
#endif
        ;

    static void s_log(int level, LogSession *pLogSession,
                      const char *format, ...)
#if __GNUC__
        __attribute__((format(printf, 3, 4)))
#endif
        ;

    static void s_log(int level, TmpLogId *pId,
                      const char *format, ...)
#if __GNUC__
        __attribute__((format(printf, 3, 4)))
#endif
        ;

    static void s_log(int level, const char *format, ...)
#if __GNUC__
        __attribute__((format(printf, 2, 3)))
#endif
        ;

    static void s_lograw(const char *format, ...)
#if __GNUC__
        __attribute__((format(printf, 1, 2)))
#endif
        ;

    static void s_vlograw(log4cxx::Logger *l, const char *format, va_list va);
        
    static void s_vlog(int level, LogSession *pLogSession,
                       const char *format, va_list args, int no_linefeed);

    LS_NO_COPY_ASSIGN(Logger);
};


END_LOG4CXX_NS

#endif
