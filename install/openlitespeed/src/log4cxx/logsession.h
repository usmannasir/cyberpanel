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
#include <lsr/ls_lock.h>
#include <lsr/ls_str.h>
#include <string.h>
#include <stdio.h>

#define MAX_LOGID_LEN   127

BEGIN_LOG4CXX_NS
class Logger;
END_LOG4CXX_NS

class LogSession
{
public:
    LogSession();
    virtual ~LogSession();


    int  isLogIdBuilt() const
    {
        return ( ls_atomic_fetch_add(&((LogSession *)this)->m_logId.len, 0) );
    }


    void clearLogId()
    {
        ls_atomic_clrint(&m_logId.len);
    }


    const char *getLogId()
    {
        ls_spinlock_lock(&m_buildLock);
        if (isLogIdBuilt()) {
            char * p = m_logId.ptr;
            ls_spinlock_unlock(&m_buildLock);
            return p;
        }

        if (!allocLogId()) {
            ls_spinlock_unlock(&m_buildLock);
            return NULL;
        }

        const char * ret = buildLogId();
        ls_spinlock_unlock(&m_buildLock);
        return ret;
    }


    void lockAppendLogId(const char * str, bool updateLength = false, 
                         size_t reserveChars = 0)
    {
        ls_spinlock_lock(&m_buildLock);
        appendLogId(str, updateLength, reserveChars);
        ls_spinlock_unlock(&m_buildLock);
    }


    /* if you change the allocation from MAX_LOGID_LEN + 1, override
       this function */
    void appendLogId(const char * str, bool updateLength = false, 
                     size_t reserveChars = 0)
    {
         if (MAX_LOGID_LEN - m_logId.len - reserveChars <= 0)
         {
             fprintf(stderr, "appendLogId error: want to reserve %zd, id length: %zd, id: %.*s\n",
                     reserveChars, m_logId.len, (int)m_logId.len, m_logId.ptr);
             return;
         }
//        assert(reserveChars < MAX_LOGID_LEN - m_logId.len);
        // WARNING: assumes LOCKED
        char *end = (char *) memccpy(m_logId.ptr + m_logId.len, str, 0, 
                                     MAX_LOGID_LEN - m_logId.len - reserveChars);

        if (updateLength) {
            if (end) {
                m_logId.len = end - m_logId.ptr - 1;
            }
            else {
                m_logId.len = MAX_LOGID_LEN - reserveChars;
            }
        }
    }


    void lockAddOrReplaceFrom(char anchor, const char * str, 
                              bool updateLength = false, size_t reserveChars = 0)
    {
        ls_spinlock_lock(&m_buildLock);
        addOrReplaceFrom(m_logId.len, anchor, str, updateLength, reserveChars);
        ls_spinlock_unlock(&m_buildLock);
    }


    void lockAddOrReplaceFrom(size_t offset, char anchor, const char * str,
                         bool updateLength = false, size_t reserveChars = 0)
    {
        ls_spinlock_lock(&m_buildLock);
        addOrReplaceFrom(offset, anchor, str, updateLength, reserveChars);
        ls_spinlock_unlock(&m_buildLock);
    }


    /* if you change the allocation from MAX_LOGID_LEN + 1, override
       this function */
    void addOrReplaceFrom(size_t offset, char anchor, const char * str, 
                          bool updateLength = false, size_t reserveChars = 0)
    {
        // WARNING: assumes LOCKED
         if (MAX_LOGID_LEN <= offset)
         {
             fprintf(stderr, "addOrReplaceFrom error: offset %zd, reserve: %zd, id length: %zd, id: %.*s\n",
                     offset, reserveChars, m_logId.len, (int)m_logId.len, 
                     m_logId.ptr);
             return;
         }
        char * p = m_logId.ptr + offset;
        
        while (*p && *p != anchor)
            ++p;

        int copySz = MAX_LOGID_LEN - (p - m_logId.ptr) - 1 - reserveChars;

        if (copySz > 0) {
            *p++ = anchor;

            char * end = (char *) memccpy(p, str, 0, copySz);

            if (updateLength) {
                if (end) {
                    m_logId.len = end - m_logId.ptr - 1;
                }
                else {
                    m_logId.len = MAX_LOGID_LEN - reserveChars;
                }
            }
        }
    }


    LOG4CXX_NS::Logger *getLogger() const
    {
        ls_spinlock_lock(&m_buildLock);
        LOG4CXX_NS::Logger * ret =  m_pLogger;
        ls_spinlock_unlock(&m_buildLock);
        return ret;
    }

    void setLogger(LOG4CXX_NS::Logger *pLogger)
    {
        ls_spinlock_lock(&m_buildLock);
        m_pLogger = pLogger;
        ls_spinlock_unlock(&m_buildLock);
    }


    size_t getIdLen()               {   return m_logId.len;                 }

    void lockLogId()                {   ls_spinlock_lock(&m_buildLock);     }
    void unlockLogId()              {   ls_spinlock_unlock(&m_buildLock);   }

    LS_NO_COPY_ASSIGN(LogSession);

protected:

    /*
     * m_logId.ptr should always be either NULL or allocated memory of
     * at least MAX_LOGID_LEN + 1. logging code assumes sufficient space
     * left in buffer.
     * m_logId.len should always be 0 (before build or after clear) or the
     * length of the base string built during build. loggers modify the buffer
     * past len for supplemental info.
     */
    ls_str_t            m_logId;

private:
    // WARNING: assume LOCKED
    bool        allocLogId();
    virtual const char *buildLogId() = 0;
    // END WARNING: assume LOCKED

    LOG4CXX_NS::Logger *m_pLogger;
    mutable ls_spinlock_t       m_buildLock;
};

#endif
