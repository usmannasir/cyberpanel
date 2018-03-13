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
#include "appendermanager.h"
#include <log4cxx/appender.h>

#include <limits.h>


BEGIN_LOG4CXX_NS


AppenderManager::AppenderManager()
    : m_pCurAppender(NULL)
    , m_curAppender(0)
    , m_strategy(0)
{
}


AppenderManager::~AppenderManager()
{
}

void AppenderManager::releaseAppenders()
{
    m_appenders.release_objects();
}


void AppenderManager::addAppender(Appender *p)
{
    m_appenders.push_back(p);
}


Appender *AppenderManager::getAppender()
{
    switch (m_strategy)
    {
    case AM_TILLFAIL:
        if ((m_pCurAppender == NULL) ||
            m_pCurAppender->isFail())
            return findAppender(m_pCurAppender);
        else
            return m_pCurAppender;
        break;
    case AM_RROBIN:
        return getNextAppender();
    case AM_TILLFULL:
        if ((m_pCurAppender == NULL) ||
            m_pCurAppender->isFull())
            return getNextAppender();
        else
            return m_pCurAppender;
        break;
    default:
        return NULL;
    }
}

Appender *AppenderManager::findAppender(Appender *pExcept)
{
    TPointerList<Appender>::iterator iter;
    m_pCurAppender = NULL;
    for (iter = m_appenders.begin(); iter != m_appenders.end();
         ++iter)
    {
        if (!(*iter)->isFail())
        {
            if ((!m_pCurAppender) && (pExcept != *iter))
                m_pCurAppender = *iter;
            if (!(*iter)->isFull())
            {
                m_pCurAppender = *iter;
                break;
            }
        }
    }
    return m_pCurAppender;
}

Appender *AppenderManager::getNextAppender()
{
    int s = m_appenders.size();
    if (s == 1)
        return (*m_appenders.begin());
    if (s == 0)
        return NULL;
    int n = m_curAppender++;
    int m = -1;
    int factor = INT_MAX;
    int f;
    Appender *p = NULL;
    while (n != m_curAppender)
    {
        if (n >= s)
            n = 0;
        p = m_appenders[n];
        if (!p->isFail())
        {
            f = p->isFull();
            if (!f)
            {
                m_curAppender = n;
                return p;
            }
            if (f < factor)
            {
                factor = f;
                m = n;
            }
            else if (m == -1)
                m = n;
        }
        ++n;
    }
    if (m == -1)   //all are bad
    {
        if (m_curAppender >= s)
            m_curAppender = 0;
        m = m_curAppender;
        m_appenders[m]->close();
        m_appenders[m]->open();
    }
    else
        m_curAppender = m;
    return m_appenders[m];
}

END_LOG4CXX_NS

