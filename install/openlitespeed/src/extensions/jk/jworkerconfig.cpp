/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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
#include "jworkerconfig.h"
#include <util/pool.h>

JWorkerConfig::JWorkerConfig()
    : m_pSecret(NULL)
      , m_secretLen(0)
{}


JWorkerConfig::JWorkerConfig(const char *pName)
    : ExtWorkerConfig(pName)
    , m_pSecret(NULL)
      , m_secretLen(0)
{}


JWorkerConfig::~JWorkerConfig()
{
    if (m_pSecret)
        Pool::deallocate2(m_pSecret);
}


void JWorkerConfig::setSecret(const char *pSecret)
{
    if (m_pSecret)
        Pool::deallocate2(m_pSecret);
    m_secretLen = strlen(pSecret);
    m_pSecret = Pool::dupstr(pSecret, m_secretLen);
}

