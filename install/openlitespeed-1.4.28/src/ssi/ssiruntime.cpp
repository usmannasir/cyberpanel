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
#include "ssiruntime.h"

SSIRuntime::SSIRuntime()
    : m_flag(0)
{
    init();
}


SSIRuntime::~SSIRuntime()
{
}


int SSIRuntime::initConfig(SSIConfig *pConfig)
{
    m_config.copy(pConfig);
    if (m_config.getTimeFmt()->c_str() == NULL)
        m_config.setTimeFmt("%A, %d-%b-%Y %H:%M:%S %Z", 24);
    if (m_config.getErrMsg()->c_str() == NULL)
        m_config.setErrMsg("[an error occurred while processing this directive]",
                           50);
    if (m_config.getEchoMsg()->c_str() == NULL)
        m_config.setEchoMsg("(none)", 6);
    return 0;
}


int SSIRuntime::execRegex(Pcregex *pReg, const char *pSubj, int len)
{
    if ((!pReg) || (!pSubj) || (len < 0) || (len >= 40960))
        return LS_FAIL;
    m_strRegex.setStr(pSubj, len);
    m_regexResult.setBuf(m_strRegex.c_str());
    return pReg->exec(m_strRegex.c_str(), len, 0, 0, &m_regexResult);
}

