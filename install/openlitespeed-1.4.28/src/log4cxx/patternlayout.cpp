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
#include "patternlayout.h"
#include "loggingevent.h"
#include "level.h"

#include <util/gfactory.h>

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

BEGIN_LOG4CXX_NS
struct timeval PatternLayout::s_startTime;


int PatternLayout::init()
{
    gettimeofday(& s_startTime, NULL);
    return s_pFactory->registerType(new PatternLayout("layout.pattern"));
}


Duplicable *PatternLayout::dup(const char *pName)
{
    return new PatternLayout(pName);
}


int PatternLayout::format(LoggingEvent *pEvent, char *pBuf, int len)
{
    struct tm   tm;
    char fmt[30] = "%s";
    char fmtDate[128] = "";
    const char *pPattern = (const char *)getUData();
    char *pBufBegin = pBuf;
    char *pEnd = pBuf + len - 10;
    const char *p;
    char ch;
    int n;
    time_t t;
    struct timeval tv_diff;
    pEnd--;
    if (pPattern == NULL)
        pPattern = "%m";
    p = pPattern;
    while ((pBuf < pEnd) && (ch = *p++) != 0)
    {
        switch (ch)
        {
        case '%':
            if ((ch = *p++) == 0)
                break;
            if ((isdigit(ch)) || ('-' == ch) || ('.' == ch))
            {
                char *f = fmt + 1;
                char *fEnd = fmt + sizeof(fmt) - 1;
                do
                {
                    if (!((isdigit(ch)) || ('-' == ch) || ('.' == ch)))
                        break;
                    *f++ = ch;
                }
                while (((ch = *p++) != 0) && (f < fEnd));
                if (isdigit(ch) || ('-' == ch) || ('.' == ch))
                {
                    *fmt = 0;
                    if (ch)
                    {
                        while (((ch = *p++) != 0) && (isdigit(ch)))
                            ;
                    }
                    if (!ch)
                        break;
                }
                *f++ = 's';
                *f++ = 0;
            }
            switch (ch)
            {

            case '%':
                *pBuf++ = ch;
                break;
            case 'm':
                if (pEvent->m_iMessageLen > pEnd - pBuf)
                    n = pEnd - pBuf;
                else
                    n = pEvent->m_iMessageLen;
                memcpy(pBuf, pEvent->m_pMessageBuf, n);
                pBuf += n;
                break;
            case 'n':
                *pBuf++ = '\n';
                break;
            case 'c':
                pBuf += snprintf(pBuf, pEnd - pBuf, fmt,
                                 pEvent->m_pLoggerName);
                break;
            case 'd':

                ch = *p;
                if (ch == '{')
                {
                    char *f = fmtDate;
                    char *fEnd = fmtDate + sizeof(fmtDate) - 1;
                    ++p;
                    while (((ch = *p++) != 0) && (ch != '}') && (f < fEnd))
                        * f++ = ch;
                    if (ch != '}')
                    {
                        *fmtDate = 0;
                        if (ch)
                        {
                            while (((ch = *p++) != 0) && (ch != '}'))
                                ;
                        }
                        if (!ch)
                            break;
                    }
                    *f++ = 0;
                }
                t = pEvent->m_timestamp.tv_sec;
                localtime_r(&t, &tm);
                if (*fmtDate == 0)
                {
                    pBuf += snprintf(pBuf, pEnd - pBuf,
                                     "%04d-%02d-%02d %02d:%02d:%02d.%03d",
                                     tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday,
                                     tm.tm_hour, tm.tm_min, tm.tm_sec,
                                     (int)(pEvent->m_timestamp.tv_usec / 1000));
                }
                else
                {
                    pBuf += strftime(pBuf, pEnd - pBuf,
                                     fmtDate, &tm);
                }

                break;
            case 'p':
                pBuf += snprintf(pBuf, pEnd - pBuf, fmt,
                                 Level::toString(pEvent->m_level));
                break;
            case 'R':
                tv_diff.tv_sec = pEvent->m_timestamp.tv_sec -
                                 s_startTime.tv_sec;
                pBuf += snprintf(pBuf, pEnd - pBuf, fmt,
                                 tv_diff.tv_sec);
                break;
            case 'r':
                tv_diff.tv_sec = pEvent->m_timestamp.tv_sec -
                                 s_startTime.tv_sec;
                tv_diff.tv_usec = pEvent->m_timestamp.tv_usec -
                                  s_startTime.tv_usec;
                if (tv_diff.tv_usec < 0)
                {
                    tv_diff.tv_usec += 1000000;
                    --tv_diff.tv_sec;
                }
                pBuf += snprintf(pBuf, pEnd - pBuf, "%d%03d",
                                 (int)tv_diff.tv_sec, (int)(tv_diff.tv_usec / 1000));
                break;
            case 'u':   /* not supported */
            case 'x':   /* not supported */
                break;

            }
            break;
        default:
            *pBuf++ = ch;
            break;
        }
        if (!ch)
            break;

    }
    if (pBuf > pEnd)
        pBuf = pEnd;
    if (!(pEvent->m_flag & LOGEVENT_NO_LINEFEED))
        if ((*(pBuf - 1) != '\n'))
            *pBuf++ = '\n';
    *pBuf = 0;

    return  pBuf - pBufBegin;
}

END_LOG4CXX_NS

