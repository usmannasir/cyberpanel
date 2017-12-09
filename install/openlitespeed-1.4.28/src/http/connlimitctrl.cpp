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
#include "connlimitctrl.h"

#include <http/httpdefs.h>
#include <http/httplistener.h>
#include <http/httplistenerlist.h>

#include <assert.h>
#include <stdio.h>


ConnLimitCtrl::ConnLimitCtrl()
    : m_iMaxConns(DEFAULT_MAX_CONNS)
    , m_iMaxSSLConns(DEFAULT_MAX_SSL_CONNS)
    , m_iAvailConns(DEFAULT_MAX_CONNS)
    , m_iAvailSSLConns(DEFAULT_MAX_SSL_CONNS)
    , m_iLowWaterMark(DEFAULT_CONN_LOW_MARK)
    , m_iConnOverflow(0)
    , m_pListeners(NULL)
{}


ConnLimitCtrl::~ConnLimitCtrl()
{}


void ConnLimitCtrl::testLimit()
{
    if (!allowConn())
        suspendAll();
}


void ConnLimitCtrl::testSSLLimit()
{
    if (!allowSSLConn() && allowConn())
        suspendSSL();
}


void ConnLimitCtrl::tryResume()
{
    if (allowSSLConn())
    {
//        printf( "allow new connection!\n" );
        resumeAll();
    }
    else
        resumeAllButSSL();
}


void ConnLimitCtrl::tryResumeSSL()
{
    if (allowConn())
        resumeSSL();
}


void ConnLimitCtrl::suspendAll()
{
//    static int i = 0;
//    printf( "%d:stop accepting new connection!\n", i++ );
    assert(m_pListeners);
    m_pListeners->suspendAll();
}


void ConnLimitCtrl::suspendSSL()
{
    assert(m_pListeners);
    m_pListeners->suspendSSL();
}


void ConnLimitCtrl::resumeSSL()
{
    assert(m_pListeners);
    m_pListeners->resumeSSL();
}


void ConnLimitCtrl::resumeAll()
{
    assert(m_pListeners);
    m_pListeners->resumeAll();
}


void ConnLimitCtrl::resumeAllButSSL()
{
    assert(m_pListeners);
    m_pListeners->resumeAllButSSL();
}


void ConnLimitCtrl::tryAcceptNewConn()
{
    HttpListenerList::iterator iter = m_pListeners->begin();
    for (; iter != m_pListeners->end(); ++iter)
    {
        if (!(*iter)->isAdmin())
        {
            if (m_iAvailConns <= 0)
                break;
            if ((*iter)->isSSL() && m_iAvailSSLConns <= 0)
                continue;
            if ((*iter)->getfd() != -1)
                (*iter)->handleEvents(0);
        }
    }
}


void ConnLimitCtrl::checkWaterMark()
{
    m_iConnOverflow &= (m_iAvailConns < m_iMaxConns - m_iLowWaterMark);
}
